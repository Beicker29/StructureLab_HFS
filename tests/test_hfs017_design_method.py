"""Method separation, not accreditation of nominal equations or coverage.

Independent factors: S22 D2 PDF100-101, E1 PDF106, F1 PDF120,
G1/G2 PDF143-144, H3 PDF153. Force N -> kN; moment Nmm -> kNm.
"""
import inspect
import math
import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.steel_design.codes.aisc_360_22 import axial_calc, tension_calc, shear_calc, flexure_calc, combined_hss_calc
from src.steel_design.domain.errors import ValidationError
from src.steel_design.domain.rules import axial_rules, tension_rule, shear_rules, flexure_rule, combined_hss_rules, composite_rules
from src.steel_design.domain.evaluators.flexure_evaluator import FlexureEvaluator
from src.steel_design.domain.evaluators.tension_evaluator import TensionEvaluator
from src.steel_design.domain.evaluators.hss_shear import evaluate_hss_shear
from src.steel_design.domain.routing.profile_router import ProfileRouter
from src.steel_design.engine import SteelDesignEngine
from src.steel_design.models import SteelCase
from src.steel_design.sections.models import Section
from src.steel_design.sections.repository import SectionRepository


def case(method="LRFD", active=False, composite=False):
    data = dict(section_name="test", design_method=method, material=dict(Fy=320, Fu=450),
                loads=dict(Pu=10 if active else 0, Mux=1 if active else 0),
                lengths=dict(Lx=1000, Ly=2000, Lz=1000, Lb=100), connection=dict(An=1000,U=1))
    if composite:
        data["composite"] = dict(role="FILLED_MEMBER", nominal_strength_method="PLASTIC", concrete=dict(fc=28,wc=2400))
    return SteelCase(**data)


def section():
    return Section(name="test",type="RECTANGULAR_HSS",A=1900,h=120,b=60,tdes=5,
                   Ix=4000000,Iy=1500000,Sx=60000,Sy=40000,Zx=70000,Zy=45000,
                   rx=45,ry=28,J=2000000,C=100000,b_tdes_ratio=12,h_tdes_ratio=24)


def rule_classes(*modules):
    return [cls for mod in modules for _,cls in inspect.getmembers(mod,inspect.isclass)
            if cls.__module__==mod.__name__ and hasattr(cls,"check")]


ALL_RULES=rule_classes(axial_rules,tension_rule,shear_rules,flexure_rule,combined_hss_rules,composite_rules)
LRFD_RULES=rule_classes(flexure_rule,composite_rules)


@pytest.mark.parametrize("rule",LRFD_RULES,ids=lambda c:c.__name__)
@pytest.mark.parametrize("active",[False,True])
def test_direct_f_i_reject_asd_before_any_work(rule,active):
    with pytest.raises(ValidationError) as caught:
        rule().check(case("ASD",active,True),section())
    assert caught.value.details["design_method_required"]=="LRFD"
    assert caught.value.details["field"]=="design_method"


@pytest.mark.parametrize("rule",ALL_RULES,ids=lambda c:c.__name__)
@pytest.mark.parametrize("active",[False,True])
def test_all_direct_rules_reject_corrupt_method_even_inactive(rule,active):
    broken=case(active=active,composite=True).model_copy(update={"design_method":"LFRD"})
    with pytest.raises(ValidationError) as caught:
        rule().check(broken,section())
    assert caught.value.details["field"]=="design_method"


CONVERSIONS=[
    ("D2yield",lambda n,m:tension_calc.calculate_available_tensile_strength(n,m,"yielding"),.90,1.67,1000),
    ("D2rupture",lambda n,m:tension_calc.calculate_available_tensile_strength(n,m,"rupture"),.75,2.0,1000),
    ("E1",axial_calc.calculate_available_compressive_strength,.90,1.67,1000),
    ("F1",flexure_calc.available_flexural_strength,.90,1.67,1e6),
    ("G1",lambda n,m:shear_calc.calculate_available_shear_strength(vn_n=n,design_method=m,phi_v=.90,omega_v=1.67),.90,1.67,1000),
    ("G2exception",lambda n,m:shear_calc.calculate_available_shear_strength(vn_n=n,design_method=m,phi_v=1,omega_v=1.5),1,1.5,1000),
    ("H3",lambda n,m:combined_hss_calc.calculate_available_torsional_strength(tn_nmm=n,design_method=m),.90,1.67,1e6),
]


@pytest.mark.parametrize("label,convert,phi,omega,unit",CONVERSIONS,ids=[c[0] for c in CONVERSIONS])
@pytest.mark.parametrize("nominal",[0,123456.789])
def test_independent_factors_and_cross_method(label,convert,phi,omega,unit,nominal):
    lrfd,asd=convert(nominal,"LRFD"),convert(nominal,"ASD")
    assert lrfd==pytest.approx(phi*nominal/unit,rel=1e-12,abs=1e-12)
    assert asd==pytest.approx(nominal/omega/unit,rel=1e-12,abs=1e-12)
    assert lrfd==pytest.approx(asd*phi*omega,rel=1e-12,abs=1e-12)


@pytest.mark.parametrize("label,convert,phi,omega,unit",CONVERSIONS,ids=[c[0] for c in CONVERSIONS])
@pytest.mark.parametrize("method",["LFRD","",None,False,1," ASD "])
@pytest.mark.parametrize("nominal",[0,100000])
def test_converters_never_default_unknown_method(label,convert,phi,omega,unit,method,nominal):
    with pytest.raises(ValueError,match="method"):
        convert(nominal,method)


@pytest.mark.parametrize("entry",[FlexureEvaluator().evaluate,ProfileRouter.get_rules])
def test_direct_f_evaluator_and_router_block_asd(entry):
    with pytest.raises(ValidationError,match="only for LRFD"):
        entry(case("ASD",True),section())


@pytest.mark.parametrize("composite",[False,True])
def test_engine_preserves_asd_public_rejection(composite):
    repo=SectionRepository(); repo.load([section()])
    with pytest.raises(ValidationError,match="only for LRFD"):
        SteelDesignEngine(repo).run(case("ASD",not composite,composite))


@pytest.mark.parametrize("method",["LRFD","ASD"])
def test_d2_e3_independent_rule_capacities_and_trace(method):
    c=case(method); s=section()
    c.loads.Pu=-10
    e=TensionEvaluator().evaluate(c,s)
    assert e["Pn_y_N"]==320*1900
    assert e["Pn_r_N"]==450*1000
    fy=.9 if method=="LRFD" else 1/1.67
    fr=.75 if method=="LRFD" else 1/2
    assert e["yielding_capacity"]==pytest.approx(320*1900*fy/1000)
    assert e["rupture_capacity"]==pytest.approx(450*1000*fr/1000)
    for rule in (tension_rule.TensionRule(),tension_rule.TensionRuptureRule()):
        check=rule.check(c,s)
        assert check.details["memory"]["design_factor"]["design_method"]==method
    c.loads.Pu=10
    fe=math.pi**2*200000/(2000/28)**2
    pn=(.658**(320/fe))*320*1900
    check=axial_rules.AxialE3Rule().check(c,s)
    assert check.capacity==pytest.approx(pn*fy/1000,rel=1e-12)
    assert check.details["memory"]["design_factor"]["design_method"]==method


I_HELPERS=[
    ("steel_shear",lambda c,s:composite_rules._steel_shear_capacity_k_n(c,s)),
    ("steel_floor",lambda c,s:composite_rules._bare_steel_compression_capacity_k_n(c,s)),
    ("filled_m",lambda c,s:composite_rules._filled_flexural_capacity_i3_axis(c,s,axis="x")),
    ("encased_m",lambda c,s:composite_rules._encased_steel_only_flexural_capacity_axis(c,s,axis="y")),
    ("i5_m",lambda c,s:composite_rules._composite_flexural_capacities_i5(c,s)),
    ("i5_p",lambda c,s:composite_rules._composite_axial_capacity_i5(c,s)),
    ("i5_ratio",lambda c,s:composite_rules._i5_moment_ratio_sum(c,{})),
    ("i5_method1",lambda c,s:composite_rules._i5_method_1_h1_interaction(c,10,0)),
    ("i5_table",lambda c,s:composite_rules._i5_method2_encased_table_points(c,s,{},{})),
    ("i5_method2",lambda c,s:composite_rules._i5_method_2_interaction(c,s,10,{},{})),
    ("i5_method4",lambda c,s:composite_rules._i5_method_4_interaction(c,s,10,0)),
    ("router",lambda c,s:ProfileRouter._get_composite_rules(c,s)),
]


@pytest.mark.parametrize("label,helper",I_HELPERS,ids=[h[0] for h in I_HELPERS])
def test_i_available_strength_helpers_cannot_bypass_method(label,helper):
    with pytest.raises(ValidationError,match="only for LRFD"):
        helper(case("ASD",False,True),section())


@pytest.mark.parametrize("entry",[
    lambda c,s:TensionEvaluator().evaluate(c,s),
    lambda c,s:FlexureEvaluator().evaluate(c,s),
    lambda c,s:evaluate_hss_shear(c,s,"x"),
    lambda c,s:combined_hss_rules._available_axial_strength(c,s),
    lambda c,s:combined_hss_rules._available_flexural_strength(c,s,"x"),
    lambda c,s:combined_hss_rules._available_shear_strength(c,s),
    lambda c,s:combined_hss_rules._torsion_capacity_h3(c,s),
    lambda c,s:combined_hss_rules._compute_h1_interaction(c,s),
])
def test_evaluators_and_h_helpers_reject_corrupt_method(entry):
    with pytest.raises(ValidationError):
        entry(case().model_copy(update={"design_method":None}),section())


@pytest.mark.parametrize("method",["LRFD","ASD"])
@pytest.mark.parametrize("family",["W","CHANNEL"])
def test_g2_independent_exception_not_shared_with_other_chapters(method,family):
    c=case(method); c.loads.Vux=1
    s=Section(name="g2",type=family,A=4000,d=200,tw=8,h=180,tf=10,h_tw_ratio=22.5)
    check=shear_rules.ShearG2VxRule().check(c,s)
    phi,omega=(1,1.5) if family=="W" else (.9,1.67)
    vn=.6*320*200*8
    assert check.capacity==pytest.approx(vn*(phi if method=="LRFD" else 1/omega)/1000,rel=1e-12)
    assert check.details["memory"]["design_factor"]["design_method"]==method


@pytest.mark.parametrize("method",["LRFD","ASD"])
def test_g4_h3_independent_same_method_without_bending(method):
    c=case(method); s=section(); c.loads.Vux=2; c.loads.Vuy=3; c.loads.Tu=5
    factor=.9 if method=="LRFD" else 1/1.67
    vx=.6*320*2*120*5*factor/1000
    vy=.6*320*2*60*5*factor/1000
    tc=.6*320*100000*factor/1e6
    assert evaluate_hss_shear(c,s,"x")["capacity_kN"]==pytest.approx(vx)
    assert evaluate_hss_shear(c,s,"y")["capacity_kN"]==pytest.approx(vy)
    check=combined_hss_rules.HssCombinedH3_2Rule().check(c,s)
    assert check.dcr==pytest.approx((max(2/vx,3/vy)+5/tc)**2,rel=1e-12)
    assert check.details["memory"]["design_factor"]["design_method"]==method
    repo=SectionRepository(); repo.load([s])
    result=SteelDesignEngine(repo).run(c)
    assert result.coverage.method==method
    assert result.status.value=="INCOMPLETE"


@pytest.mark.parametrize("method",["LRFD","ASD"])
def test_cli_and_detailed_memory_preserve_method_and_external_demand(tmp_path,method):
    payload=dict(section_name="tie",design_method=method,material=dict(Fy=320,Fu=450),
                 loads=dict(Pu=-10),connection=dict(An=800,U=.8),
                 lengths=dict(Lx=1000,Ly=1000,Lz=1000,Lb=1000),
                 custom_section=dict(type="SOLID_RECTANGULAR",B=10,H=100),
                 output=dict(write_results_json=True))
    source=tmp_path/'case.json'; source.write_text(json.dumps(payload),encoding="utf-8")
    run=subprocess.run([sys.executable,"-m","src.steel_design.run",str(source),
                        "--results-dir",str(tmp_path/'out')],capture_output=True,text=True,encoding="utf-8")
    assert run.returncode==0,run.stderr
    cli=json.loads(run.stdout)
    memory=json.loads(Path(cli["artifacts"]["detailed_results_json"]).read_text(encoding="utf-8"))
    for result in (cli,memory["output"]):
        assert result["coverage"]["method"]==method
        assert result["coverage"]["demand_components"]["Pu"]==-10
        assert result["status"]=="INCOMPLETE"
        assert all(check["demand"]==10 for check in result["checks"])
    for check in memory["memory"]["clause_results"]:
        assert check["calculations"]["design_factor"]["design_method"]==method
