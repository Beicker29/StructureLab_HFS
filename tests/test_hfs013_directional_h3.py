"""Independent references: S22 G1/G4-1/G5-1..2, H3-1..6 (PDF148-155).

Expected values below are hand expressions from the identified provisions and
geometric identities, not values obtained from productive selection/evaluators.
Synthetic box: sharp 200x100x5 mm; h=190,b=90, Ag=2900. Torsional C is the
explicit conservative H3 User Note value from the stated OUTER dimensions.
These references qualify the tested arithmetic/domain only, not full AISC.
"""
import math
from pathlib import Path

import pytest

from src.steel_design.codes.aisc_360_22 import combined_hss_calc, shear_calc
from src.steel_design.domain.actions import shear_demand, shear_trace
from src.steel_design.domain.errors import IncompleteSectionDataError, RuleNotImplementedError
from src.steel_design.domain.evaluators.hss_shear import evaluate_hss_shear
from src.steel_design.domain.rules.combined_hss_rules import HssCombinedH3_2Rule, HssTorsionH3_1Rule
from src.steel_design.domain.rules.shear_rules import ShearG2VxRule, ShearG4VxRule, ShearG4VyRule, ShearG5VxRule, ShearG6VyRule
from src.steel_design.engine import SteelDesignEngine
from src.steel_design.models import SteelCase
from src.steel_design.sections.loader import load_sections_from_excel
from src.steel_design.sections.models import Section
from src.steel_design.sections.repository import SectionRepository


# Independent G4 and H3 references, SI: N/mm2 * mm2 /1000; Nmm /1e6.
VCX = .9 * .6 * 320 * (2 * 190 * 5) / 1000  # 328.32 kN, local-y force
VCY = .9 * .6 * 320 * (2 * 90 * 5) / 1000   # 155.52 kN, local-x force
C_BOX = 2 * 95 * 195 * 5 - 4.5 * (4 - math.pi) * 125
TC_BOX = .9 * .6 * 320 * C_BOX / 1e6


def box(**changes):
    ix = (100 * 200**3 - 90 * 190**3) / 12
    iy = (200 * 100**3 - 190 * 90**3) / 12
    values = dict(name="reference", type="RECTANGULAR_HSS", A=2900, h=190, b=90,
                  tdes=5, Ix=ix, Iy=iy, Sx=ix/100, Sy=iy/50, Zx=187750, Zy=115250,
                  rx=math.sqrt(ix/2900), ry=math.sqrt(iy/2900), J=1e6, C=C_BOX,
                  b_tdes_ratio=18, h_tdes_ratio=38)
    values.update(changes)
    return Section(**values)


def tube(**changes):
    values = dict(name="reference", type="CIRCULAR_HSS", A=475*math.pi, OD=100,
                  tdes=5, J=math.pi*(100**4-90**4)/32, C=None)
    values.update(changes)
    return Section(**values)


def case(method="LRFD", **loads):
    return SteelCase(section_name="reference", design_method=method,
        material=dict(Fy=320, Fu=450, E=200000), loads=loads,
        lengths=dict(Lx=1000, Ly=2000, Lz=3000, Lb=100),
        connection=dict(An=2900, U=1))


def run(section, c):
    repo = SectionRepository()
    repo.load([section])
    # Connection is unused for shear, but do not give the engine an impossible An.
    if not c.loads.Pu:
        c = c.model_copy(update={"connection": c.connection.model_copy(update={"An": None})})
    return SteelDesignEngine(repo).run(c)


@pytest.mark.parametrize("loads,demands", [(dict(Vux=40), (40,0)), (dict(Vuy=20),(0,20)),
    (dict(Vux=40,Vuy=20),(40,20)), (dict(Vu=40),(40,0)),
    (dict(Vux=-40,Vuy=-20),(40,20)), (dict(Vu=-40),(40,0))])
def test_physical_planes_and_legacy_alias(loads, demands):
    c = case(**loads)
    assert (shear_demand(c,"x"),shear_demand(c,"y")) == demands
    assert shear_trace(c,"x")["force_direction"] == "local_y"
    assert shear_trace(c,"y")["force_direction"] == "local_x"
    assert shear_trace(c,"x")["input_component"] == ("Vu" if "Vu" in loads else "Vux")
    result = run(box(), c)
    checks = {ch.details["memory"]["inputs"]["bending_axis"]: ch for ch in result.checks}
    for axis, demand, capacity in (("x",demands[0],VCX),("y",demands[1],VCY)):
        if demand:
            assert checks[axis].details["memory"]["capacity_kn"] == pytest.approx(capacity, abs=1e-9)
            assert checks[axis].demand == demand
    assert result.status.value == "INCOMPLETE"


@pytest.mark.parametrize("method,factor", [("LRFD", .9),("ASD",1/1.67)])
@pytest.mark.parametrize("axis,width", [("x",190),("y",90)])
def test_g4_independent_capacity_and_method(axis, width, method, factor):
    expected = factor*.6*320*2*width*5/1000
    evaluation = evaluate_hss_shear(case(method, Vux=1,Vuy=1),box(),axis)
    assert evaluation["capacity_kN"] == pytest.approx(expected,rel=1e-12,abs=1e-9)


def test_unequal_axes_swap_changes_decision():
    c = case(Vux=VCX*.4, Vuy=VCY*1.2)
    x = ShearG4VxRule().check(c,box())
    y = ShearG4VyRule().check(c,box())
    assert x.status.value == "PASS" and y.status.value == "FAIL"
    assert y.dcr == 1.2
    assert abs(c.loads.Vuy)/VCX < 1  # erroneous swap would falsely pass


@pytest.mark.parametrize("loads,ratio,governing", [
    (dict(Vux=VCX*.4,Vuy=VCY*.6), .6,"y"),
    (dict(Vux=VCX*.6,Vuy=VCY*.4), .6,"x"),
    (dict(Vux=-VCX*.4,Vuy=-VCY*.6), .6,"y"),
    (dict(Vu=VCX*.6), .6,"x"),
    (dict(Vuy=VCY*.6), .6,"y"), (dict(Vux=VCX*.6), .6,"x"),
])
def test_h3_paired_ratio_and_shared_raw_capacities(loads,ratio,governing):
    c = case(Tu=TC_BOX*.5,**loads)
    result = HssCombinedH3_2Rule().check(c,box())
    memory = result.details["memory"]
    assert memory["intermediate"]["Vr_over_Vrc"] == pytest.approx(ratio)
    assert memory["intermediate"]["shear_governing_axis"] == governing
    assert memory["intermediate"]["interaction_ratio"] == pytest.approx((ratio+.5)**2)
    for axis,evaluation in memory["components"]["shear"]["evaluations"].items():
        standalone = (ShearG4VxRule() if axis=="x" else ShearG4VyRule()).check(c,box())
        assert evaluation["capacity_kN"] == standalone.details["memory"]["capacity_kn"]


def test_full_axial_biaxial_shear_torsion_reference_changes_pass_to_fail():
    # Smaller 130x70x5 box: both walls compact even as the minor bending flange.
    # Independent difference-of-rectangles: Ag=1900,Zx=79750,Zy=51250 mm units.
    # D2 yielding controls: 547.2 kN. Compact F7 strengths: 22.968 / 14.76 kNm.
    # normal=.20+.15+.05=.40, max shear=.60, torsion=.50 => .40+1.10^2=1.61.
    ix=(70*130**3-60*120**3)/12
    iy=(130*70**3-120*60**3)/12
    torsional_c=2*65*125*5-4.5*(4-math.pi)*125
    s=box(A=1900,h=120,b=60,C=torsional_c,Zx=79750,Zy=51250,
          Ix=ix,Iy=iy,Sx=ix/65,Sy=iy/35,rx=math.sqrt(ix/1900),ry=math.sqrt(iy/1900),
          b_tdes_ratio=12,h_tdes_ratio=24)
    c=case(Pu=-109.44,Mux=3.4452,Muy=.738,Vux=82.944,Vuy=62.208,Tu=.5*.9*192*torsional_c/1e6)
    c=c.model_copy(update={"connection":c.connection.model_copy(update={"An":1900})})
    check=HssCombinedH3_2Rule().check(c,s)
    memory=check.details["memory"]
    assert memory["capacities"]["Pc_kN"] == pytest.approx(547.2)
    assert memory["capacities"]["Mcx_kN_m"] == pytest.approx(22.968)
    assert memory["capacities"]["Mcy_kN_m"] == pytest.approx(14.76)
    assert memory["intermediate"]["normal_ratio_sum"] == pytest.approx(.4)
    assert memory["intermediate"]["interaction_ratio"] == pytest.approx(1.61)
    assert check.status.value=="FAIL"
    old_wrong=.4**2+(.4+.5)**2
    assert old_wrong == pytest.approx(.97) and old_wrong < 1
    result=run(s,c)
    assert result.status.value=="INCOMPLETE" and result.known_failures


@pytest.mark.parametrize("normal,shear,expected", [(.4,.9,1.21),(0,1,1),(.5,.5,.75),(1.2,0,1.2)])
def test_h3_6_normal_term_is_linear(normal,shear,expected):
    assert combined_hss_calc.calculate_h3_6_interaction(normal_ratio=normal,shear_torsion_ratio=shear)==pytest.approx(expected)


@pytest.mark.parametrize("ratio,branch,expected", [
    (61.25,"H3-3",192), (math.nextafter(math.nextafter(61.25,math.inf),math.inf),"H3-4",192),
    (76.75,"H3-4",192*61.25/76.75),
    (100,"H3-5",.458*math.pi**2*200000/10000),
    (260,"H3-5",.458*math.pi**2*200000/260**2)])
def test_rectangular_torsion_regions_independent(ratio,branch,expected):
    # E/Fy=625 -> 2.45sqrt=61.25, 3.07sqrt=76.75. No epsilon at boundaries.
    data=combined_hss_calc.calculate_rectangular_hss_fcr_h3(E_mpa=200000,Fy_mpa=320,h_mm=ratio,t_mm=1)
    assert data["branch"]==branch
    assert data["Fcr_mpa"]==pytest.approx(expected,rel=1e-12,abs=1e-10)


def test_rectangular_torsion_above_260_is_blocked():
    ratio=math.nextafter(260,math.inf)
    with pytest.raises(RuleNotImplementedError,match="260"):
        HssTorsionH3_1Rule().check(case(Tu=1),box(h=ratio*5))
    result=run(box(h=ratio*5),case(Tu=1,Vuy=1))
    assert result.status.value=="INCOMPLETE"
    assert result.checks and all(c.clause=="G4-1" for c in result.checks)


@pytest.mark.parametrize("factor", [.1,.2])
def test_threshold_permission_never_becomes_resistance_pass(factor):
    c=case(Tu=TC_BOX*factor,Vuy=1)
    with pytest.raises(RuleNotImplementedError,match="threshold is not"):
        HssCombinedH3_2Rule().check(c,box())
    result=run(box(),c)
    assert result.status.value=="INCOMPLETE"
    assert any(e["error"]["details"].get("reference")=="H3.2" for e in result.coverage.evaluation_errors)


def test_above_threshold_uses_equation():
    tr=math.nextafter(.2*TC_BOX,math.inf)
    assert "interaction_ratio" in HssCombinedH3_2Rule().check(case(Tu=tr,Vux=1),box()).details["memory"]["intermediate"]


@pytest.mark.parametrize("changes", [dict(C=None),dict(tdes=None,t=5),dict(b=None),dict(h=None)])
def test_rectangular_torsion_no_unsupported_geometric_fallback(changes):
    with pytest.raises(IncompleteSectionDataError):
        HssTorsionH3_1Rule().check(case(Tu=1),box(**changes))


def test_missing_one_wall_preserves_other_shear_and_blocks_h3():
    result=run(box(b=None),case(Vux=1,Vuy=1,Tu=TC_BOX*.5))
    assert result.status.value=="INCOMPLETE"
    assert len(result.checks)==1 and result.checks[0].details["memory"]["inputs"]["input_component"]=="Vux"
    assert result.coverage.evaluation_errors


def test_unused_wall_not_required_for_single_direction_shear():
    assert evaluate_hss_shear(case(Vux=1),box(b=None),"x")["capacity_kN"]==pytest.approx(VCX)


@pytest.mark.parametrize("method,factor", [("LRFD",.9),("ASD",1/1.67)])
def test_round_shear_yielding_without_inferred_lv(method,factor):
    # D/t=20: G5-2b exceeds .6Fy, hence min(max(a,b),.6Fy)=.6Fy for ALL Lv>0.
    expected=factor*192*(475*math.pi)/2/1000
    result=ShearG5VxRule().check(case(method,Vux=1),tube())
    assert result.details["memory"]["capacity_kn"]==pytest.approx(expected,rel=1e-12)
    assert result.details["memory"]["inputs"]["Lv_mm"] is None


def test_round_torsion_no_kz_lz_or_j_inference():
    # H3 User Note C=pi*95^2*5/2. H3-2b exceeds yield, so L is immaterial.
    expected=.9*192*(math.pi*95**2*5/2)/1e6
    c=case(Tu=1)
    a=HssTorsionH3_1Rule().check(c,tube(J=1))
    c=c.model_copy(update={"factors":c.factors.model_copy(update={"Kz":7}),
                           "lengths":c.lengths.model_copy(update={"Lz":8000})})
    b=HssTorsionH3_1Rule().check(c,tube(J=1e12))
    for result in (a,b):
        assert result.details["memory"]["capacity_kN_m"]==pytest.approx(expected,rel=1e-12)
        assert result.details["memory"]["intermediate"]["source"]=="user_note_conservative"


def test_round_slender_needs_real_lengths_and_keeps_pending():
    s=tube(OD=1000,tdes=2,A=1996*math.pi)
    with pytest.raises(IncompleteSectionDataError,match="Lv"):
        ShearG5VxRule().check(case(Vux=1),s)
    with pytest.raises(IncompleteSectionDataError,match="member length"):
        HssTorsionH3_1Rule().check(case(Tu=1),s)
    result=run(s,case(Vux=1,Vuy=2,Tu=1))
    assert not result.checks and result.status.value=="INCOMPLETE"
    assert len(result.coverage.evaluation_errors)==4


@pytest.mark.parametrize("loads", [dict(Vux=1),dict(Vuy=2),dict(Vux=1,Vuy=2),dict(Vu=3)])
def test_round_shear_torsion_combinations(loads):
    # Equal capacities from rotational symmetry; explicit paired ratios still used.
    vc=.9*192*(475*math.pi)/2/1000
    tc=.9*192*(math.pi*95**2*5/2)/1e6
    expected=(max(abs(v) for v in loads.values())/vc+.5)**2
    result=HssCombinedH3_2Rule().check(case(Tu=tc*.5,**loads),tube())
    assert result.details["memory"]["intermediate"]["interaction_ratio"]==pytest.approx(expected)


def test_w_g2_g6_geometry_and_no_torsion_domain():
    s=Section(name="reference",type="W",A=6000,d=300,tw=10,bf=200,tf=10,bf_2tf_ratio=10,h_tw_ratio=25)
    # G2.1(a) phi=1, Aw=3000; G6 two equal flanges -> Aw=4000, phi=.9.
    c=case(Vux=100,Vuy=100)
    assert ShearG2VxRule().check(c,s).capacity==pytest.approx(.6*320*3000/1000)
    assert ShearG6VyRule().check(c,s).capacity==pytest.approx(.9*.6*320*4000/1000)
    with pytest.raises(RuleNotImplementedError,match="no torsion"):
        ShearG6VyRule().check(case(Vuy=1,Tu=1),s)


@pytest.mark.parametrize("profile", ["SINGLE_ANGLE","DOUBLE_ANGLE","CHANNEL"])
def test_unaccredited_directional_domains_remain_incomplete(profile):
    s=Section(name="reference",type=profile,A=1000,b=50,t=5,bf=50,tf=5,b_t_ratio=10)
    result=run(s,case(Vuy=1))
    assert result.status.value=="INCOMPLETE" and not result.checks
    assert result.coverage.evaluation_errors


def test_unsupported_non_hss_torsion_does_not_erase_independent_shear():
    s=Section(name="reference",type="W",A=6000,d=300,tw=10,h_tw_ratio=25)
    result=run(s,case(Vux=1,Tu=1))
    assert [c.clause for c in result.checks]==["G2-1"]
    assert result.status.value=="INCOMPLETE" and result.coverage.evaluation_errors


def test_solid_shear_never_uses_hollow_tube_capacity():
    c=case(Vux=1)
    c=c.model_copy(update={"custom_section":None})
    result=run(Section(name="reference",type="SOLID_CIRCULAR",A=1000),c)
    assert not result.checks and result.status.value=="INCOMPLETE"
    assert "G5 is for hollow" in result.coverage.evaluation_errors[0]["error"]["message"]


def test_real_asymmetric_catalog_directional_reference_and_missing_c():
    repo=SectionRepository()
    repo.load(load_sections_from_excel(str(Path(__file__).resolve().parents[1]/"data/sections.xlsx")))
    s=repo.get("PTE50X30X2.5MM")
    # Independent values transcribed from the catalog for this reference, not read from s.
    x=.9*.6*345*2*43.025*2.325/1000
    y=.9*.6*345*2*23.025*2.325/1000
    c=case(Vux=x*.4,Vuy=y*1.2)
    c=c.model_copy(update={"material":c.material.model_copy(update={"Fy":345})})
    assert evaluate_hss_shear(c,s,"x")["capacity_kN"]==pytest.approx(x)
    assert evaluate_hss_shear(c,s,"y")["capacity_kN"]==pytest.approx(y)
    assert ShearG4VyRule().check(c,s).status.value=="FAIL"
    assert s.c is None
    with pytest.raises(IncompleteSectionDataError):
        HssTorsionH3_1Rule().check(case(Tu=1),s)


@pytest.mark.parametrize("length,g5_expected,h3_expected", [(500,192,192),(5000000,156,120)])
def test_round_numeric_functions_with_independently_given_lengths(length,g5_expected,h3_expected):
    # D/t=100. Long case: G5-2b=.78*200000/1000=156 MPa;
    # H3-2b=.60*200000/1000=120 MPa. Short case: the a branch reaches 192 MPa cap.
    g=shear_calc.calculate_round_hss_fcr(e_mpa=200000,fy_mpa=320,lv_mm=length,diameter_mm=500,thickness_mm=5)
    h=combined_hss_calc.calculate_round_hss_fcr_h3(E_mpa=200000,Fy_mpa=320,L_mm=length,D_mm=500,t_mm=5)
    assert g["Fcr_mpa"]==pytest.approx(g5_expected,abs=1e-10)
    assert h["Fcr_mpa"]==pytest.approx(h3_expected,abs=1e-10)


def test_round_shear_is_independent_of_column_lengths_when_yielding_is_proved():
    c=case(Vux=1,Vuy=2)
    changed=c.model_copy(update={"lengths":c.lengths.model_copy(update={"Lx":1e9,"Ly":1})})
    assert evaluate_hss_shear(c,tube(),"x")==evaluate_hss_shear(changed,tube(),"x")
    assert evaluate_hss_shear(c,tube(),"y")==evaluate_hss_shear(changed,tube(),"y")


@pytest.mark.parametrize("profile", ["W", "CHANNEL"])
def test_missing_flange_data_does_not_erase_independent_web_shear(profile):
    s=Section(name="reference",type=profile,A=6000,d=300,tw=10,h_tw_ratio=25)
    result=run(s,case(Vux=1,Vuy=1))
    assert [check.clause for check in result.checks]==["G2-1"]
    assert result.status.value=="INCOMPLETE"
    assert result.coverage.evaluation_errors[0]["implementation"]=="ShearG6VyRule"
