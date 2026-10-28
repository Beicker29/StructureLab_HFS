"""F-43: independent F1(a) references for H3 and the shared H1 consumer.

S22 Specification: F1(a) 16.1-52/PDF120; F7-1/F8-1; H3-6 PDF154.
F1 expected factors and nominal yielding moments come from the source and
explicit geometry below, never from the productive helpers. H1 tension is a
regression of the existing expression, NOT validation of its H1-2 label/formula.

Capture identical cases against any source root without running tests:
python tests/test_hfs013_design_method.py SOURCE_ROOT NEW_OUTPUT.json
"""
import json
import math
from pathlib import Path
import sys

if __name__ == "__main__":
    sys.path.insert(0, str(Path(sys.argv[1]).resolve()))

import pytest

from steel_design.codes.aisc_360_22 import flexure_calc
from steel_design.domain.errors import ValidationError
from steel_design.domain.rules.combined_hss_rules import (
    CombinedH1HssRule, HssCombinedH3_2Rule, _available_flexural_strength,
)
from steel_design.engine import SteelDesignEngine
from steel_design.models import SteelCase
from steel_design.sections.models import Section
from steel_design.sections.repository import SectionRepository


def reference(family):
    """Known compact geometries; moments Nmm, forces N, torque Nmm."""
    if family == "rectangular":
        area = 70*130 - 60*120
        ix = (70*130**3 - 60*120**3)/12
        iy = (130*70**3 - 120*60**3)/12
        zx, zy = (70*130**2-60*120**2)/4, (130*70**2-120*60**2)/4
        c = 2*65*125*5 - 4.5*(4-math.pi)*125  # H3 User Note, OUTER dimensions known
        section = Section(name="F43", type="RECTANGULAR_HSS", A=area,
            h=120, b=60, tdes=5, Ix=ix, Iy=iy, Sx=ix/65, Sy=iy/35,
            Zx=zx, Zy=zy, rx=math.sqrt(ix/area), ry=math.sqrt(iy/area),
            J=1e6, C=c, b_tdes_ratio=12, h_tdes_ratio=24)
        vn_x, vn_y = .6*320*2*120*5, .6*320*2*60*5  # G4, Cv2=1
    else:
        area = math.pi*(100**2-90**2)/4
        ix = iy = math.pi*(100**4-90**4)/64
        zx = zy = (100**3-90**3)/6  # plastic modulus by integration of two semicircles
        c = math.pi*95**2*5/2  # H3 User Note
        section = Section(name="F43", type="CIRCULAR_HSS", A=area,
            OD=100, tdes=5, Ix=ix, Iy=iy, Sx=ix/50, Sy=iy/50,
            Zx=zx, Zy=zy, rx=math.sqrt(ix/area), ry=math.sqrt(iy/area),
            J=2*ix, C=c, d_t_ratio=20)
        vn_x = vn_y = .6*320*area/2  # G5 yielding proved independently of Lv
    # B4.1b compact: box max b/t=24 < 1.12*sqrt(625)=28;
    # round D/t=20 < .07*625=43.75. Lb=100 mm below rectangular Lp.
    # E3 controls the declared short/non-slender section vs E4 for these inputs.
    fe = math.pi**2*200000*(iy/area)/2000**2
    pn_compression = (.658**(320/fe))*320*area
    return section, dict(area=area, mn_x=320*zx, mn_y=320*zy,
        tn=.6*320*c, vn_x=vn_x, vn_y=vn_y,
        pn_tension=320*area, pn_compression=pn_compression)


def load_case(family, method, moments="both", *, shear=False, axial=None, torsion=True):
    section, ref = reference(family)
    loads = dict(Mux=.4*.9*ref["mn_x"]/1e6 if moments in {"x","both"} else 0,
                 Muy=-.2*.9*ref["mn_y"]/1e6 if moments in {"y","both"} else 0,
                 Tu=.35*.9*ref["tn"]/1e6 if torsion else 0)
    if shear:
        loads.update(Vux=.1*.9*ref["vn_x"]/1000, Vuy=-.15*.9*ref["vn_y"]/1000)
    if axial == "tension":
        loads["Pu"] = -.15*.9*ref["pn_tension"]/1000
    elif axial in {"low", "high"}:
        loads["Pu"] = (.1 if axial == "low" else .25)*.9*ref["pn_compression"]/1000
    case = SteelCase(section_name="F43", design_method=method,
        material=dict(Fy=320, Fu=450, E=200000), loads=loads,
        lengths=dict(Lx=1000, Ly=2000, Lz=3000, Lb=100),
        connection=dict(An=ref["area"], U=1))
    return section, case, ref


def engine(section, case):
    repository = SectionRepository()
    repository.load([section])
    return SteelDesignEngine(repository).run(case)


def assert_moments(memory, ref, method, moments):
    factor = .90 if method == "LRFD" else 1/1.67  # F1(a), independent of production
    for axis in ("x","y"):
        if moments in {axis,"both"}:
            expected = factor*ref[f"mn_{axis}"]/1e6
            assert memory["capacities"][f"Mc{axis}_kN_m"] == pytest.approx(expected,rel=1e-12,abs=1e-10)
            assert memory["components"][f"flexure_{axis}"]["evaluation"]["Mn_Nmm"] == pytest.approx(ref[f"mn_{axis}"],rel=1e-12,abs=1e-7)
        else:
            assert memory["components"][f"flexure_{axis}"]["evaluation"] is None


@pytest.mark.parametrize("family", ["rectangular", "round"])
@pytest.mark.parametrize("method", ["LRFD", "ASD"])
@pytest.mark.parametrize("moments", ["x", "y", "both"])
@pytest.mark.parametrize("shear", [False, True])
def test_h3_f1_oracle(family, method, moments, shear):
    section, case, ref = load_case(family, method, moments, shear=shear)
    check = HssCombinedH3_2Rule().check(case, section)
    memory = check.details["memory"]
    assert_moments(memory,ref,method,moments)
    scale = 1 if method == "LRFD" else .9*1.67
    bending = (.4 if moments in {"x","both"} else 0) + (.2 if moments in {"y","both"} else 0)
    expected = bending*scale + ((.35 + (.15 if shear else 0))*scale)**2
    assert memory["intermediate"]["interaction_ratio"] == pytest.approx(expected,rel=1e-12,abs=1e-12)
    # Three-decimal presentation can round either way at a half-ULP boundary;
    # verify its resolution separately from the strict raw oracle above (F-09).
    assert check.dcr == pytest.approx(expected,rel=0,abs=.0005+1e-12)
    assert check.status.value == ("PASS" if expected<=1 else "FAIL")
    assert memory["design_factor"]["design_method"] == method


@pytest.mark.parametrize("family", ["rectangular", "round"])
@pytest.mark.parametrize("method", ["LRFD", "ASD"])
def test_h3_axial_bending_shear_torsion_method(family,method):
    section,case,ref=load_case(family,method,shear=True,axial="tension")
    check=HssCombinedH3_2Rule().check(case,section)
    memory=check.details["memory"]
    assert_moments(memory,ref,method,"both")
    scale=1 if method=="LRFD" else .9*1.67
    expected=.75*scale+(.5*scale)**2
    assert memory["intermediate"]["interaction_ratio"]==pytest.approx(expected,rel=1e-12,abs=1e-12)
    # Check the raw ratio only here: the LRFD mathematical boundary is 1.0;
    # no tolerance is introduced into the production PASS/FAIL decision.


@pytest.mark.parametrize("family", ["rectangular", "round"])
@pytest.mark.parametrize("method", ["LRFD", "ASD"])
@pytest.mark.parametrize("axial", ["tension", "low", "high"])
def test_h1_f1_regression(family,method,axial):
    section,case,ref=load_case(family,method,axial=axial,torsion=False)
    check=CombinedH1HssRule().check(case,section)
    memory=check.details["memory"]
    assert_moments(memory,ref,method,"both")
    scale=1 if method=="LRFD" else .9*1.67
    if axial=="tension":
        # Existing linear tension expression regression only; F-37 remains open.
        expected=(.15+.6)*scale
        branch="tension"
    elif axial=="low":
        expected=(.1/2+.6)*scale
        branch="compression_low_axial"
    else:
        expected=(.25+8/9*.6)*scale
        branch="compression_high_axial"
    assert memory["intermediate"]["branch"]==branch
    assert memory["intermediate"]["interaction_ratio"]==pytest.approx(expected,rel=1e-12,abs=1e-12)
    assert check.status.value==("PASS" if expected<=1 else "FAIL")


@pytest.mark.parametrize("family", ["rectangular", "round"])
@pytest.mark.parametrize("axis", ["x", "y"])
def test_nominal_evaluation_identical_across_methods(family,axis):
    section,lrfd,ref=load_case(family,"LRFD")
    _,asd,_=load_case(family,"ASD")
    a=_available_flexural_strength(lrfd,section,axis)
    b=_available_flexural_strength(asd,section,axis)
    assert a["evaluation"]==b["evaluation"]
    assert a["evaluation"]["Mn_Nmm"]==pytest.approx(ref[f"mn_{axis}"])
    assert a["available_kN_m"]==.9*ref[f"mn_{axis}"]/1e6
    assert b["available_kN_m"]==pytest.approx(ref[f"mn_{axis}"]/1.67/1e6,rel=1e-12)


@pytest.mark.parametrize("method,expected", [("LRFD",90), ("ASD",100/1.67)])
def test_f1_canonical_conversion_in_knm(method,expected):
    assert flexure_calc.available_flexural_strength(100000000,method)==pytest.approx(expected,rel=1e-12)


def test_lrfd_compatibility_entrypoint_exact_arithmetic():
    for nominal in (0.0,1.2345678901234,25520000.0,14453333.333333334):
        assert flexure_calc.available_flexural_strength_lrfd(nominal)==.90*nominal/1e6


@pytest.mark.parametrize("method", ["", "unknown"])
def test_unknown_method_does_not_default_to_asd(method):
    with pytest.raises(ValueError,match="design method"):
        flexure_calc.available_flexural_strength(1e6,method)


@pytest.mark.parametrize("family", ["rectangular", "round"])
@pytest.mark.parametrize("method", ["LRFD", "ASD"])
@pytest.mark.parametrize("moments", ["x", "y", "both"])
@pytest.mark.parametrize("interaction", ["H1", "H3"])
def test_public_engine_scope_and_coverage_unchanged(family,method,moments,interaction):
    section,case,_=load_case(family,method,moments,
        axial="tension" if interaction=="H1" else None, torsion=interaction=="H3")
    if method=="ASD":
        with pytest.raises(ValidationError,match="only for LRFD") as caught:
            engine(section,case)
        assert caught.value.details["design_method_received"]=="ASD"
    else:
        result=engine(section,case)
        assert result.status.value=="INCOMPLETE"
        obligation=next(o for o in result.coverage.obligations
                        if o.id==("N29.interaction" if interaction=="H1" else "N30.interaction"))
        assert obligation.executed_checks and not obligation.accepted_checks


def snapshot():
    """Behavioral probes; comparisons are not substituted for the oracles above."""
    result={}
    def observe(call):
        try:
            return call().model_dump(mode="json")
        except ValidationError as error:
            return {"error":error.to_dict()}
    for family in ("rectangular","round"):
        for method in ("LRFD","ASD"):
            for moments in ("x","y","both"):
                for shear in (False,True):
                    section,case,ref=load_case(family,method,moments,shear=shear)
                    key=f"H3/{family}/{method}/{moments}/shear={shear}"
                    result[key]={"case":case.model_dump(mode="json"),"section":section.model_dump(mode="json"),
                        "independent_reference":ref,"rule":observe(lambda:HssCombinedH3_2Rule().check(case,section)),
                        "engine":observe(lambda:engine(section,case))}
            for axial in ("tension","low","high"):
                section,case,ref=load_case(family,method,axial=axial,torsion=False)
                result[f"H1/{family}/{method}/{axial}"]={"case":case.model_dump(mode="json"),
                    "section":section.model_dump(mode="json"),"independent_reference":ref,
                    "rule":observe(lambda:CombinedH1HssRule().check(case,section)),
                    "engine":observe(lambda:engine(section,case))}
    return result


if __name__=="__main__":
    output=Path(sys.argv[2])
    if output.exists():
        raise SystemExit("Use a new output path; preserve prior evidence")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(snapshot(),ensure_ascii=False,indent=2),encoding="utf-8")
    print(output)
