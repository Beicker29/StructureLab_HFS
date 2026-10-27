"""HFS-015: original numbers, explicit units and S22 User Notes.

Ratio oracles are elementary independent divisions. D2 oracle: S22 D2-1,
Fy=345 MPa, A=1000 mm2, phi=.9 => 310.5 kN. No productive capacity helper.
H1/H3 use the separately derived geometry/reference cases from F-43, not its
productive selector. E5 tests distinguish applicability conditions, not certify E5.
"""
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from src.steel_design.models import CheckResult, SteelCase, SlendernessAdviceBasis
from src.steel_design.results_model import EngineResult
from src.steel_design.domain.recommendations import slenderness_recommendations
from src.steel_design.domain.rules import axial_rules, shear_rules, combined_hss_rules, composite_rules
from src.steel_design.domain.rules.flexure_rule import _build_flexure_result
from src.steel_design.domain.rules.tension_rule import TensionRule
from src.steel_design.engine import SteelDesignEngine
from src.steel_design.sections.models import Section
from src.steel_design.sections.repository import SectionRepository
from src.steel_design import run as cli


ROOT = Path(__file__).resolve().parents[1]


def case(pu=-1, length=1000, **changes):
    data=dict(section_name="solid", material=dict(Fy=345,Fu=450), loads=dict(Pu=pu),
              lengths=dict(Lx=length,Ly=length,Lz=length,Lb=100),
              connection=dict(An=1000,U=1),
              custom_section=dict(type="SOLID_RECTANGULAR",B=10,H=100))
    data.update(changes)
    return SteelCase(**data)


def strict_json(text):
    def forbidden(token):
        raise AssertionError(f"Nonstandard numeric token: {token}")
    return json.loads(text,parse_constant=forbidden)


@pytest.mark.parametrize("ratio,status",[(.9999,"PASS"),(1.0,"PASS"),(1.0001,"FAIL")])
@pytest.mark.parametrize("unit,capacity",[("kN",123.456789),("kN-m",9.87654321),("ratio",1.0)])
def test_original_values_and_boundary_display(ratio,status,unit,capacity):
    demand=ratio*capacity
    c=CheckResult.from_values(name="opaque",clause="not-a-unit",demand=demand,capacity=capacity,unit=unit)
    assert c.demand==demand and c.capacity==capacity
    assert c.dcr==demand/capacity and c.status.value==status
    assert c.display["dcr"]=="1.000"
    assert status in c.display["dcr_label"] and repr(c.dcr) in c.display["dcr_label"]
    assert strict_json(c.model_dump_json())["dcr"]==c.dcr
    trace=cli._build_dcr_trace(c)
    assert trace["steps"][2]["value_raw"]==c.dcr
    assert trace["steps"][0]["value"]==demand
    assert trace["units"]==dict(demand=unit,capacity=unit)


@pytest.mark.parametrize("ratio,status",[(.9999,"PASS"),(1.0,"PASS"),(1.0001,"FAIL")])
def test_d2_independent_capacity_boundary(ratio,status):
    # S22 D2-1 and F-09 reproduction. 310.5 is independently stipulated.
    result=SteelDesignEngine(SectionRepository()).run(case(-310.5*ratio))
    c=next(c for c in result.checks if c.clause=="D2-1")
    assert c.capacity==310.5 and c.dcr==pytest.approx(ratio,rel=0,abs=2e-16)
    assert c.status.value==status and result.status.value=="INCOMPLETE"
    if status=="FAIL": assert 0 in result.known_failures


@pytest.mark.parametrize("producer",["D","E","F","G","H","I"])
def test_all_chapter_result_producers_keep_original_precision(producer):
    demand,capacity=2.123456789,2.123333333
    kwargs=dict(name="opaque",clause="unknown",demand=demand,capacity=capacity,details={})
    if producer=="D":
        c=TensionRule().check(case(-310.53105),Section(name="s",A=1000))
        demand,capacity=310.53105,310.5
    elif producer=="E": c=axial_rules._result(**kwargs)
    elif producer=="F":
        c=_build_flexure_result(case=case(),name="opaque",clause="unknown",demand=demand,
            evaluation=dict(Mn_Nmm=capacity*1e6/.9,limit_states={},intermediate={}),inputs={})
    elif producer=="G":
        c=shear_rules._build_result(name="opaque",clause="unknown",demand_kn=demand,capacity_kn=capacity,details={})
    elif producer=="H": c=combined_hss_rules._build_result(**kwargs,unit="ratio")
    else: c=composite_rules._build_result(**kwargs,unit="ratio")
    assert c.demand==demand
    assert c.capacity==pytest.approx(capacity,rel=1e-15,abs=1e-15)
    assert c.dcr==pytest.approx(demand/capacity,rel=1e-15,abs=1e-15)
    assert c.status.value=="FAIL" and c.unit is not None


def test_raw_ranking_breaks_display_ties_and_keeps_real_ties():
    checks=[CheckResult.from_values(name=str(i),clause="opaque",demand=d,capacity=1,unit="ratio")
            for i,d in enumerate([.9999,1.0001,1.0001])]
    r=EngineResult(checks=checks)
    s=cli._build_global_summary(r)
    assert {c.display["dcr"] for c in checks}=={"1.000"}
    assert s["version"]=="HFS-015-v2" and s["max_dcr_published"]==1.0001
    assert [c["check_index"] for c in s["observed_governing_checks"]]==[1,2]
    assert [c["check_index"] for c in s["failed_checks"]]==[1,2]
    assert s["overall_status"]=="INCOMPLETE"


def test_trace_does_not_reconstruct_or_infer_units(monkeypatch):
    def forbidden(*args): raise AssertionError("No approximate reconstruction")
    monkeypatch.setattr(cli,"_infer_check_units",forbidden)
    monkeypatch.setattr(cli,"_extract_capacity_from_memory",forbidden)
    c=CheckResult(name="x",clause="H3",demand=10,capacity=3,dcr=3.3333333333333335,
                  status="FAIL",unit="kN",details={"memory":{"capacity_kn":1}})
    t=cli._build_dcr_trace(c)
    assert t["steps"][2]["value_raw"]==c.dcr
    assert t["steps"][1]["value_used_for_dcr"]==3 and t["units"]["demand"]=="kN"
    assert cli._build_dcr_trace(c.model_copy(update={"unit":None}))["units"]["demand"] is None


@pytest.mark.parametrize("demand,capacity",[(1,0),(0,0),(1,-1),(1,math.inf),
    (math.inf,1),(math.nan,1),(1,math.nan),(1e308,1e-308)])
def test_undefined_results_never_pass_or_emit_nonstandard_json(demand,capacity):
    c=CheckResult.from_values(name="undefined",clause="opaque",demand=demand,capacity=capacity,unit="kN")
    assert c.status.value=="FAIL" and c.numeric_issue
    r=EngineResult(checks=[c])
    assert r.status.value=="INCOMPLETE" and r.known_failures==[0]
    for payload in (c.model_dump(),strict_json(c.model_dump_json()),strict_json(r.model_dump_json())["checks"][0]):
        json.dumps(payload,allow_nan=False)
        assert payload["dcr"] is None and payload["nonfinite_values"]
    assert cli._build_global_summary(r)["observed_governing_checks"]==[]
    json.dumps(cli._build_dcr_trace(c),allow_nan=False)


def test_nonfinite_details_keep_diagnostic_in_every_serializer():
    c=CheckResult.from_values(name="x",clause="opaque",demand=1,capacity=2,unit="kN",
        details={"inactive_axis":math.inf,"nested":[math.nan,-math.inf]})
    py=c.model_dump(); js=strict_json(c.model_dump_json())
    assert py==js
    assert js["details"]["inactive_axis"] is None
    assert len(js["details"]["nonfinite_values"])==3
    assert math.isinf(c.details["inactive_axis"])  # source values not mutated


@pytest.mark.parametrize("family",["rectangular","round"])
@pytest.mark.parametrize("method",["LRFD","ASD"])
@pytest.mark.parametrize("moments",["x","y","both"])
def test_h3_raw_oracles_and_f43(family,method,moments):
    # Reuse independent reference geometry, never productive calculation helpers.
    from test_hfs013_design_method import load_case
    section,c,ref=load_case(family,method,moments,shear=True)
    check=combined_hss_rules.HssCombinedH3_2Rule().check(c,section)
    scale=1 if method=="LRFD" else .9*1.67
    bending=(.4 if moments in {"x","both"} else 0)+(.2 if moments in {"y","both"} else 0)
    expected=bending*scale+(.5*scale)**2
    assert check.dcr==pytest.approx(expected,rel=1e-12,abs=1e-12)
    assert check.demand==check.details["memory"]["intermediate"]["interaction_ratio"]
    assert check.unit=="ratio"


@pytest.mark.parametrize("family",["rectangular","round"])
@pytest.mark.parametrize("method",["LRFD","ASD"])
@pytest.mark.parametrize("axial",["tension","low","high"])
def test_h1_raw_regression_preserves_f43(family,method,axial):
    from test_hfs013_design_method import load_case
    section,c,ref=load_case(family,method,axial=axial,torsion=False)
    check=combined_hss_rules.CombinedH1HssRule().check(c,section)
    scale=1 if method=="LRFD" else .9*1.67
    expected=(.75 if axial=="tension" else .65 if axial=="low" else .25+8/9*.6)*scale
    assert check.dcr==pytest.approx(expected,rel=1e-12,abs=1e-12)
    assert check.dcr==check.details["memory"]["intermediate"]["interaction_ratio"]


@pytest.mark.parametrize("ratio,assessment",[(299.999,"WITHIN_RECOMMENDATION"),
    (300,"WITHIN_RECOMMENDATION"),(300.001,"EXCEEDS_RECOMMENDATION")])
def test_d1_fabricated_ratio_not_effective_klr(ratio,assessment):
    c=case(slenderness_advice_basis=dict(fabricated_length=ratio*10,least_radius=10,is_rod=False),
           factors=dict(Kx=2,Ky=3))
    s=Section(name="s",A=1000,rx=20,ry=10)
    r=slenderness_recommendations(c,s)
    assert r["D1"]["assessment"]==assessment and r["D1"]["ratio"]==ratio
    assert r["D1"]["resistance"] is False
    assert "admissible" not in r["D1"] and r["inputs"]["KL_over_r_y"]==300


@pytest.mark.parametrize("klr",[299.999,300,300.001])
def test_tension_klr_does_not_establish_fabricated_slenderness(klr):
    r=slenderness_recommendations(case(length=klr*10),Section(name="s",A=1000,rx=20,ry=10))
    assert r["inputs"]["KL_over_r_governing_observed"]==klr
    assert r["D1"]["assessment"]=="UNKNOWN" and r["D1"]["ratio"] is None


@pytest.mark.parametrize("ratio",[299.999,300,300.001])
def test_e2_fabricated_recommendation_is_separate(ratio):
    c=case(10,slenderness_advice_basis=dict(fabricated_length=ratio*10,least_radius=10))
    r=slenderness_recommendations(c,Section(name="s",A=1000,rx=20,ry=10))
    assert r["E2"]["assessment"]=="WITHIN_RECOMMENDATION"
    assert r["E2"]["fabricated_member"]["assessment"]==("WITHIN_RECOMMENDATION" if ratio<=300 else "EXCEEDS_RECOMMENDATION")


@pytest.mark.parametrize("ratio,assessment",[(199.999,"WITHIN_RECOMMENDATION"),
    (200,"WITHIN_RECOMMENDATION"),(200.001,"EXCEEDS_RECOMMENDATION")])
def test_e2_effective_ratio_boundary(ratio,assessment):
    c=case(10,length=ratio*10)
    r=slenderness_recommendations(c,Section(name="s",A=1000,rx=20,ry=10))
    assert r["E2"]["assessment"]==assessment
    assert r["inputs"]["governing_axes"]==["y"] and r["E2"]["resistance"] is False
    assert r["E2"]["fabricated_member"]["assessment"]=="UNKNOWN"


@pytest.mark.parametrize("rod,expected",[(True,"NOT_APPLICABLE"),(False,"EXCEEDS_RECOMMENDATION"),(None,"UNKNOWN")])
def test_d1_rod_exception_not_inferred_from_shape(rod,expected):
    c=case(slenderness_advice_basis=dict(fabricated_length=4000,least_radius=10,is_rod=rod))
    r=slenderness_recommendations(c,Section(name="s",A=1000,rx=20,ry=10))
    assert r["D1"]["assessment"]==expected


@pytest.mark.parametrize("section",[None,Section(name="s",A=1000,rx=10),Section(name="s",A=1000)])
def test_missing_slenderness_stays_unknown(section):
    r=slenderness_recommendations(case(10),section)
    assert r["E2"]["assessment"]=="UNKNOWN"
    assert r["E2"]["ratio"] is None


@pytest.mark.parametrize("ratio",[199.999,200,200.001])
def test_e5_condition_cannot_be_displaced_by_general_advice(ratio):
    c=case(10,length=10*ratio)
    r=slenderness_recommendations(c,Section(name="a",type="ANGLE",A=1000,rx=10,ry=10))
    condition=r["mandatory_conditions"][0]
    assert condition["source_type"]=="Specification" and condition["assessment"]=="NOT_EVALUATED"
    assert "E5(4)" in condition["reference"]


def test_recommendations_never_change_coverage_or_resistance():
    c=case(-310.53105)
    engine=SteelDesignEngine(SectionRepository())
    before=engine.run(c).model_dump()
    c=c.model_copy(update={"slenderness_advice_basis":SlendernessAdviceBasis(
        fabricated_length=100000,least_radius=1,is_rod=False)})
    after=engine.run(c).model_dump()
    assert before==after
    advice=slenderness_recommendations(c,cli._build_case_section(c,SectionRepository()))
    assert advice["D1"]["assessment"]=="EXCEEDS_RECOMMENDATION"


@pytest.mark.parametrize("field,value",[("fabricated_length",0),("least_radius",float("nan")),
    ("least_radius",-1),("is_rod","false"),("is_rod",1)])
def test_advice_input_contract_rejects_invalid_data(field,value):
    with pytest.raises(ValidationError): SlendernessAdviceBasis(**{field:value})


def test_i4_aggregation_keeps_raw_capacity_between_checks(monkeypatch):
    # Independently stipulated capacities isolate propagation, NOT validation of I4.
    capacities=[1.00049,1.00041,.99999]
    classes=[composite_rules.CompositeI4_1aEncasedRule,composite_rules.CompositeI4_1bEncasedRule,
             composite_rules.CompositeI4_1cEncasedRule]
    for cls,value in zip(classes,capacities):
        monkeypatch.setattr(cls,"check",lambda self,c,s,v=value: CheckResult.from_values(
            name="stipulated",clause="opaque",demand=1.00045,capacity=v,unit="kN"))
    c=case(1,loads=dict(Vux=1.00045),composite=dict(role="ENCASED_MEMBER",nominal_strength_method="PLASTIC",
            concrete=dict(fc=30,wc=2400)))
    r=composite_rules.CompositeI4_1EncasedGoverningRule().check(c,Section(name="s",A=1000))
    assert r.capacity==1.00049 and r.dcr==1.00045/1.00049 and r.status.value=="PASS"
    # Prior 3-decimal intermediate would use 1.000 and falsely fail this propagation probe.
    assert 1.00045/round(1.00049,3)>1


@pytest.mark.parametrize("method",["METHOD_1_H1_1"])
def test_i5_interaction_consumes_raw_i2_capacity(monkeypatch,method):
    # Stipulated upstream physical capacities; numerical propagation regression,
    # not certification of the Chapter I domain or its H1-labelled expression.
    raw_capacity=1.00049
    monkeypatch.setattr(composite_rules.CompositeI2EncasedCompressionRule,"check",
        lambda self,c,s:CheckResult.from_values(name="stipulated",clause="I2-1b",demand=.100049,
                                              capacity=raw_capacity,unit="kN"))
    monkeypatch.setattr(composite_rules,"_composite_flexural_capacities_i5",
                        lambda c,s:{"x":{"Mc_kN_m":1},"y":{"Mc_kN_m":1}})
    c=case(.100049,loads=dict(Pu=.100049,Mux=.94999),
        composite=dict(role="ENCASED_MEMBER",nominal_strength_method="PLASTIC",
                       concrete=dict(fc=30,wc=2400),i5=dict(method=method)))
    r=composite_rules.CompositeI5CombinedRule().check(c,Section(name="s",A=1000))
    expected=(.100049/1.00049)/2+.94999
    assert r.dcr==expected and r.status.value=="PASS"
    assert (.100049/round(1.00049,3))/2+.94999>1  # previous intermediate loses the distinction


@pytest.mark.parametrize("write",[True,False])
def test_cli_raw_precision_and_advisory_consumers(tmp_path,write):
    data=case(-310.53105,slenderness_advice_basis=dict(fabricated_length=4000,least_radius=10,is_rod=False)).model_dump(mode="json")
    data["output"]={"write_results_json":write}
    path=tmp_path/"c.json"; path.write_text(json.dumps(data),encoding="utf-8")
    p=subprocess.run([sys.executable,"-m","src.steel_design.run",str(path),"--sections",
        str(ROOT/"data/sections.xlsx"),"--results-dir",str(tmp_path/"r")],cwd=ROOT,
        capture_output=True,text=True,encoding="utf-8")
    assert p.returncode==0,p.stderr
    output=strict_json(p.stdout)
    check=next(c for c in output["checks"] if c["clause"]=="D2-1")
    assert check["dcr"]==1.0001 and check["status"]=="FAIL"
    assert output["admissibility"]["D1"]["assessment"]=="EXCEEDS_RECOMMENDATION"
    assert output["status"]=="INCOMPLETE" and output["known_failures"]
    if write:
        memory=strict_json(Path(output["artifacts"]["detailed_results_json"]).read_text(encoding="utf-8"))
        assert memory["admissibility"]==output["admissibility"]
        assert memory["output"]["checks"]==output["checks"]
        assert memory["memory"]["clause_results"][0]["check_trace"]["steps"][2]["value_raw"]==1.0001
