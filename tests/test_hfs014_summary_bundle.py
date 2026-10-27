"""F-05/F-29 contract oracles, independent of capacities/formulas/routing.

Published DCR is the only ranking input. Fake ratios deliberately disagree with
rounded demand/capacity so reconstruction would fail. Complete PASS/FAIL CLI
fixtures use the previously bounded HFS-010 solid-tie domain, without new credit.
"""
import itertools
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

from src.steel_design.domain.errors import ValidationError
from src.steel_design.models import CheckResult, SteelCase
from src.steel_design.results_model import (
    AnalysisStatus, CoverageObligation, CoverageReport, EngineResult, aggregate_case_statuses,
)
from src.steel_design import run as cli

ROOT = Path(__file__).resolve().parents[1]


def check(name="axial", clause="E3-1", demand=90, capacity=100, dcr=.9, status="PASS"):
    return CheckResult(name=name,clause=clause,demand=demand,capacity=capacity,dcr=dcr,status=status)


def result(checks, resistance_indices=None):
    if resistance_indices is None:
        return EngineResult(checks=checks)
    obligations=[CoverageObligation(id="resistance",normative_ids=["synthetic"],
        limit_state="declared_resistance",component="synthetic",condition="test only",reason="pending",
        executed_checks=resistance_indices)]
    return EngineResult(checks=checks, coverage=CoverageReport(method="LRFD",section_name="synthetic",
        profile_type="synthetic", demand_components={},obligations=obligations))


def test_f05_axial_governs_over_smaller_bending_capacity():
    r=result([check(),check("bending","F2-1",1,50,.02)])
    summary=cli._build_global_summary(r)
    assert "governing_capacity_kn_or_knm" not in summary
    assert summary["max_dcr_published"]==.9
    assert summary["observed_governing_checks"]==[
        {"check_index":0,"clause":"E3-1","name":"axial","dcr_published":.9,"status":"PASS"}]


@pytest.mark.parametrize("winner", range(4))
def test_axial_bending_shear_and_interaction_are_ranked_by_published_dcr(winner):
    checks=[check("axial","D2-1",9,100,.1),check("bending","F7",1,50,.2),
            check("shear","G4",2,20,.3),check("interaction","H3-2",.7,1,.4)]
    checks[winner]=checks[winner].model_copy(update={"dcr":.95})
    summary=cli._build_global_summary(result(checks))
    assert [c["check_index"] for c in summary["observed_governing_checks"]]==[winner]
    assert summary["max_dcr_published"]==.95  # NOT demand/capacity


def test_ties_are_preserved_at_published_precision_without_status_reconstruction():
    r=result([check(demand=99.96,dcr=1),check("other","F7",50.02,50,1,"FAIL")])
    summary=cli._build_global_summary(r)
    assert [c["check_index"] for c in summary["observed_governing_checks"]]==[0,1]
    assert [c["status"] for c in summary["observed_governing_checks"]]==["PASS","FAIL"]
    assert summary["failed_checks"]==[summary["observed_governing_checks"][1]]
    assert summary["overall_status"]=="INCOMPLETE"
    assert summary["scope"]=="executed_checks_only"


def test_all_known_failures_retained_even_if_not_governing_or_not_eligible():
    r=result([check(dcr=1.2,status="FAIL"),check("highest","G",2,1,2,"FAIL"),
              check("filler","arbitrary",0,0,0,"FAIL")])
    summary=cli._build_global_summary(r)
    assert [c["check_index"] for c in summary["failed_checks"]]==[0,1,2]
    assert [c["check_index"] for c in summary["observed_governing_checks"]]==[1]
    assert r.known_failures==[0,1,2] and r.status.value=="INCOMPLETE"


@pytest.mark.parametrize("checks", [[],[check("filler","anything",0,0,0)],
    [check("inactive","D2",0,100,0)], [check("no_capacity","F2",1,0,math.inf,"FAIL")]])
def test_no_eligible_check_has_no_governing(checks):
    summary=cli._build_global_summary(result(checks))
    assert summary["max_dcr_published"] is None
    assert summary["observed_governing_checks"]==[]
    json.dumps(summary,allow_nan=False)


def test_nonresistant_or_unlinked_checks_excluded_using_existing_coverage_not_names():
    # The arbitrary label must not be interpreted as a force/moment unit or rule.
    r=result([check("resistant","unrecognizable",1,20,.8),
              check("eligibility","H3-2",3,1,3,"FAIL")],resistance_indices=[0])
    before=r.model_dump(mode="json")
    summary=cli._build_global_summary(r)
    assert [c["check_index"] for c in summary["observed_governing_checks"]]==[0]
    assert summary["failed_checks"][0]["check_index"]==1
    assert summary["excluded_checks"]==[{"check_index":1,"reason":"no_executed_resistance_obligation"}]
    assert r.model_dump(mode="json")==before


def test_summary_does_not_use_units_or_reconstruct_trace(monkeypatch):
    def forbidden(*args):
        raise AssertionError("Summary must not infer units or recalculate DCR")
    monkeypatch.setattr(cli,"_infer_check_units",forbidden)
    monkeypatch.setattr(cli,"_build_dcr_trace",forbidden)
    summary=cli._build_global_summary(result([check("opaque","UNKNOWN",100,1,.1)]))
    assert summary["max_dcr_published"]==.1


def test_empty_aggregation_is_a_structured_input_error():
    with pytest.raises(ValidationError) as caught:
        aggregate_case_statuses([])
    assert caught.value.code=="EMPTY_CASE_BUNDLE"
    assert caught.value.details=={"field":"cases","minimum_items":1,"received_items":0}


@pytest.mark.parametrize("statuses", list(itertools.product(list(AnalysisStatus),repeat=1))+
    list(itertools.product(list(AnalysisStatus),repeat=2))+list(itertools.product(list(AnalysisStatus),repeat=3)))
def test_nonempty_status_truth_table(statuses):
    expected = "INCOMPLETE" if "INCOMPLETE" in statuses else "FAIL" if "FAIL" in statuses else "PASS"
    assert aggregate_case_statuses(list(statuses)).value==expected


def payload(status="PASS", write=True):
    scope=dict(ordinary_prismatic_member=True,concentric_axial_force=True,no_special_conditions=True,
        material_reference="Stipulated material for HFS-014 transport fixture",
        demand_reference="Stipulated tie load",net_area_reference="An=800 U=.8 externally established",
        connection_reference="External connection review",external_checks_reference="External scope review")
    return dict(section_name="tie",custom_section=dict(type="SOLID_RECTANGULAR",B=10,H=100),
        material=dict(Fy=345,Fu=450),loads=dict(Pu=-220 if status in {"FAIL","INCOMPLETE"} else -50),
        lengths=dict(Lx=1000,Ly=1000,Lz=1000,Lb=1000),connection=dict(An=800,U=.8),
        tension_scope=None if status=="INCOMPLETE" else scope,output=dict(write_results_json=write))


def invoke(tmp_path, data):
    path=tmp_path/"input.json"
    path.write_text(json.dumps(data),encoding="utf-8")
    output=tmp_path/"results"
    process=subprocess.run([sys.executable,"-m","src.steel_design.run",str(path),
        "--sections",str(ROOT/"data/sections.xlsx"),"--results-dir",str(output)],
        cwd=ROOT,capture_output=True,text=True,encoding="utf-8")
    return process,output


@pytest.mark.parametrize("statuses", [("PASS",),("FAIL",),("INCOMPLETE",),("PASS","FAIL"),
    ("PASS","INCOMPLETE"),("FAIL","INCOMPLETE"),("PASS","PASS","PASS"),
    ("PASS","FAIL","INCOMPLETE")])
def test_cli_bundle_states_failures_and_detailed_consumers(tmp_path,statuses):
    data={"cases":[dict(name=f"case-{i}",**payload(status)) for i,status in enumerate(statuses)]}
    process,_=invoke(tmp_path,data)
    assert process.returncode==0,process.stderr  # F-32 unchanged, even FAIL/INCOMPLETE
    bundle=json.loads(process.stdout)
    expected="INCOMPLETE" if "INCOMPLETE" in statuses else "FAIL" if "FAIL" in statuses else "PASS"
    assert bundle["status"]==expected
    assert bundle["total_cases"]==len(statuses)
    for status,item in zip(statuses,bundle["cases"]):
        assert item["status"]==status
        summary=item["global_summary"]
        assert summary["overall_status"]==status
        if status in {"FAIL","INCOMPLETE"}:
            assert item["known_failures"]
            assert [c["check_index"] for c in summary["failed_checks"]]==item["known_failures"]
        detail=json.loads(Path(item["artifacts"]["detailed_results_json"]).read_text(encoding="utf-8"))
        assert {k:v for k,v in detail["memory"]["global_summary"].items() if k!="admissibility"}==summary
        assert detail["output"]["global_summary"]==summary
        for governing in summary["observed_governing_checks"]:
            index=governing["check_index"]
            assert governing["dcr_published"]==item["checks"][index]["dcr"]
            assert governing["status"]==detail["memory"]["clause_results"][index]["check_summary"]["status"]


@pytest.mark.parametrize("write", [False,True])
def test_single_case_cli_uses_same_summary_with_or_without_memory(tmp_path,write):
    process,_=invoke(tmp_path,payload("INCOMPLETE",write))
    assert process.returncode==0,process.stderr
    item=json.loads(process.stdout)
    assert item["global_summary"]["scope"]=="executed_checks_only"
    assert item["global_summary"]["failed_checks"]
    if not write:
        assert item["artifacts"]["detailed_results_json"] is None


@pytest.mark.parametrize("cases,code", [([],"EMPTY_CASE_BUNDLE"),(None,"INVALID_CASE_BUNDLE"),
    ({},"INVALID_CASE_BUNDLE"),("bad","INVALID_CASE_BUNDLE"),(12,"INVALID_CASE_BUNDLE"),
    (False,"INVALID_CASE_BUNDLE"),([None],"INVALID_CASE_BUNDLE"),
    ([payload(),"bad"],"INVALID_CASE_BUNDLE")])
def test_malformed_bundle_rejected_before_engine_or_artifacts(tmp_path,monkeypatch,capsys,cases,code):
    path=tmp_path/"invalid.json"; path.write_text(json.dumps({"cases":cases}),encoding="utf-8")
    output=tmp_path/"not_created"
    monkeypatch.setattr(sys,"argv",["run",str(path),"--results-dir",str(output)])
    monkeypatch.setattr(cli,"load_sections_from_excel",lambda path:[])
    def forbidden(*args,**kwargs):
        raise AssertionError("Invalid bundle must not execute or publish any case")
    monkeypatch.setattr(cli,"_run_single_case",forbidden)
    monkeypatch.setattr(cli,"_build_execution_results_dir",forbidden)
    with pytest.raises(SystemExit) as caught:
        cli.main()
    assert caught.value.code==1
    streams=capsys.readouterr()
    assert not streams.out
    error=json.loads(streams.err)["error"]
    assert error["code"]==code and error["stage"]=="run_engine"
    assert not output.exists()


def test_empty_bundle_real_process_has_no_compliance_or_output_directory(tmp_path):
    process,output=invoke(tmp_path,{"cases":[]})
    assert process.returncode==1 and not process.stdout
    error=json.loads(process.stderr)
    assert error["error"]["code"]=="EMPTY_CASE_BUNDLE"
    assert "status" not in error and not output.exists()
