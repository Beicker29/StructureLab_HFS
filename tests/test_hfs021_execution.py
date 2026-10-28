"""Architectural regression and independent geometric identities (mm units).

Rectangle expectations use fixed hand-integrated properties; circles use radius
identities A=pi*r², I=pi*r⁴/4, S=I/r, Z=4*r³/3. These are geometric oracles,
not accreditation of any AISC state. Historical numerical suites stay unchanged.
"""
import builtins
import copy
import importlib
import itertools
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError as PydanticValidationError

from steel_design import engine as engine_module, reporting, run as cli
from steel_design.domain.errors import SectionNotFoundError, ValidationError
from steel_design.engine import SteelDesignEngine, _build_custom_section
from steel_design.execution import (
    execute_case, execute_payload, execution_status, iter_executions,
    extract_output_options, merge_case_payload,
)
from steel_design.models import SteelCase
from steel_design.sections.geometry import build_custom_section
from steel_design.sections.loader import load_sections_from_excel
from steel_design.sections.models import Section
from steel_design.sections.repository import SectionRepository

ROOT = Path(__file__).resolve().parents[1]
SCOPE = dict(ordinary_prismatic_member=True, concentric_axial_force=True, no_special_conditions=True,
             material_reference="Stipulated material, regression only",
             demand_reference="Externally supplied concentric load",
             net_area_reference="External An/U", connection_reference="External connections",
             external_checks_reference="External checks, regression only")


def payload(state="PASS", method="LRFD", write=False):
    data = dict(section_name="tie", custom_section=dict(type="SOLID_RECTANGULAR", B=10, H=100),
                material=dict(Fy=345, Fu=450), loads=dict(Pu=-50 if state == "PASS" else -350),
                lengths=dict(Lx=1000, Ly=1000, Lz=1000, Lb=1000),
                connection=dict(An=800, U=.8), tension_scope=SCOPE,
                design_method=method, output=dict(write_results_json=write))
    if state == "INCOMPLETE":
        data.pop("tension_scope")
    return data


def case(data=None):
    return SteelCase(**extract_output_options(data or payload())[0])


def engine():
    return SteelDesignEngine(SectionRepository())


def invoke(tmp_path, data, catalog=None):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    return subprocess.run([sys.executable, "-m", "steel_design.run", str(source),
                           "--sections", str(catalog or ROOT / "data/sections.xlsx"),
                           "--results-dir", str(tmp_path / "out")],
                          capture_output=True, text=True, encoding="utf-8", cwd=ROOT)


@pytest.mark.parametrize("scale", [.1, 1, 10])
def test_rectangle_independent_properties(scale):
    data = payload()
    data["custom_section"].update(B=20*scale, H=60*scale)
    section = build_custom_section(case(data))
    # Integral of y² dA = 360000, x² dA = 40000 at B=20, H=60.
    expected = dict(area=1200*scale**2, ix=360000*scale**4, iy=40000*scale**4,
                    sx=12000*scale**3, sy=4000*scale**3,
                    zx=18000*scale**3, zy=6000*scale**3,
                    rx=math.sqrt(300)*scale, ry=math.sqrt(100/3)*scale)
    for key, value in expected.items():
        assert getattr(section, key) == pytest.approx(value, rel=1e-14, abs=0)


@pytest.mark.parametrize("radius", [.5, 10, 125])
def test_circle_independent_properties(radius):
    data = payload()
    data["custom_section"] = dict(type="SOLID_CIRCULAR", diameter=2*radius)
    section = build_custom_section(case(data))
    expected = dict(area=math.pi*radius**2, ix=math.pi*radius**4/4, iy=math.pi*radius**4/4,
                    sx=math.pi*radius**3/4, sy=math.pi*radius**3/4,
                    zx=4*radius**3/3, zy=4*radius**3/3, rx=radius/2, ry=radius/2)
    for key, value in expected.items():
        assert getattr(section, key) == pytest.approx(value, rel=1e-14, abs=0)


@pytest.mark.parametrize("geometry", [dict(type="SOLID_RECTANGULAR", B=10),
    dict(type="SOLID_CIRCULAR"), dict(type="SOLID_RECTANGULAR", B=0, H=10),
    dict(type="SOLID_CIRCULAR", diameter=-1), dict(type="SOLID_CIRCULAR", diameter=float("inf")),
    dict(type="SOLID_RECTANGULAR", B=10, H=float("nan"))])
def test_geometry_input_errors_stay_in_shared_model(geometry):
    data = payload()
    data["custom_section"] = geometry
    with pytest.raises(PydanticValidationError):
        execute_payload(data, engine())


def test_missing_custom_and_overflow_errors_preserved():
    data = payload()
    data.pop("custom_section")
    with pytest.raises(ValidationError, match="custom_section is required"):
        build_custom_section(case(data))
    data["custom_section"] = dict(type="SOLID_CIRCULAR", diameter=1e200)
    with pytest.raises(ValidationError, match="floating-point range"):
        execute_payload(data, engine())


@pytest.mark.parametrize("state,method", list(itertools.product(["PASS", "FAIL", "INCOMPLETE"], ["LRFD", "ASD"])))
def test_service_without_files_console_or_cli(monkeypatch, capsys, state, method):
    data = payload(state, method)
    original = copy.deepcopy(data)
    def forbidden(*args, **kwargs):
        raise AssertionError("No transport or export allowed")
    with monkeypatch.context() as patch:
        for owner, name in [(builtins, "open"), (builtins, "print"), (sys, "exit"),
                            (Path, "open"), (Path, "mkdir"), (cli, "main"),
                            (reporting, "export_execution")]:
            patch.setattr(owner, name, forbidden)
        executions = execute_payload(data, engine())
        summary = reporting.build_compact_summary(executions[0])
        detail = reporting.build_detailed_results_payload(result=executions[0].result,
            case=executions[0].case, section=executions[0].section,
            input_payload=executions[0].input_payload, input_file="", sections_file="",
            profile_type=executions[0].section.type, timestamp="provided-by-caller")
    assert data == original
    assert execution_status(executions).value == state
    assert summary["status"] == detail["output"]["status"] == state
    assert not capsys.readouterr().out


@pytest.mark.parametrize("states", [("PASS",), ("FAIL",), ("INCOMPLETE",),
                                    ("PASS", "FAIL"), ("FAIL", "INCOMPLETE"),
                                    ("INCOMPLETE", "PASS", "FAIL")])
def test_bundle_preserves_states_and_order(states):
    data = {"cases": [dict(name=f"s{i}", **payload(state)) for i, state in enumerate(states)]}
    executions = execute_payload(data, engine())
    assert [e.result.status.value for e in executions] == list(states)
    assert [e.case_tag for e in executions] == [f"s{i}" for i in range(len(states))]
    expected = "INCOMPLETE" if "INCOMPLETE" in states else "FAIL" if "FAIL" in states else "PASS"
    assert execution_status(executions).value == expected


@pytest.mark.parametrize("definitions,code", [([], "EMPTY_CASE_BUNDLE"), (None, "INVALID_CASE_BUNDLE"),
    ({}, "INVALID_CASE_BUNDLE"), ([{} , None], "INVALID_CASE_BUNDLE")])
def test_bundle_errors_before_execution(definitions, code, monkeypatch):
    e = engine()
    def forbidden(*args, **kwargs):
        raise AssertionError("Engine must not execute")
    monkeypatch.setattr(e, "run_with_context", forbidden)
    with pytest.raises(ValidationError) as caught:
        execute_payload({"cases": definitions}, e)
    assert caught.value.code == code


def test_empty_aggregation_has_no_pass():
    with pytest.raises(ValidationError) as caught:
        execution_status([])
    assert caught.value.code == "EMPTY_CASE_BUNDLE"


@pytest.mark.parametrize("state,method", list(itertools.product(["PASS", "FAIL", "INCOMPLETE"], ["LRFD", "ASD"])))
def test_cli_and_memory_equal_service(tmp_path, state, method):
    data = payload(state, method, True)
    execution, = execute_payload(data, engine())
    process = invoke(tmp_path, data)
    assert process.returncode == 0, process.stderr  # F-32 preserved, including FAIL.
    actual = json.loads(process.stdout)
    expected = reporting.build_compact_summary(execution)
    assert {k: v for k, v in actual.items() if k != "artifacts"} == {
        k: v for k, v in expected.items() if k != "artifacts"}
    detail = json.loads(Path(actual["artifacts"]["detailed_results_json"]).read_text(encoding="utf-8"))
    expected_detail = reporting.build_detailed_results_payload(
        result=execution.result, case=execution.case, section=execution.section,
        input_payload=execution.input_payload, input_file=detail["meta"]["input_file"],
        sections_file=detail["meta"]["sections_file"], profile_type=execution.section.type,
        timestamp=detail["meta"]["generated_at_utc"])
    assert detail == expected_detail


def test_cli_mixed_bundle_and_late_error_keep_prior_artifact(tmp_path):
    data = {"cases": [dict(name=state, **payload(state, write=True)) for state in ("PASS", "FAIL", "INCOMPLETE")]}
    process = invoke(tmp_path, data)
    assert process.returncode == 0, process.stderr
    actual = json.loads(process.stdout)
    assert actual["status"] == "INCOMPLETE"
    assert [s["status"] for s in actual["cases"]] == ["PASS", "FAIL", "INCOMPLETE"]
    data["cases"][1]["material"]["Fy"] = -1
    process = invoke(tmp_path, data)
    assert process.returncode == 1 and not process.stdout
    assert json.loads(process.stderr)["error"]["stage"] == "run_engine"
    # A successful earlier item is exported before preparation of the next item.
    assert len(list((tmp_path / "out").rglob("*.json"))) == 4


def test_context_reuses_exact_section_and_result(monkeypatch):
    e = engine()
    seen = []
    original = engine_module.build_coverage_plan
    def record(c, s):
        seen.append(s)
        return original(c, s)
    monkeypatch.setattr(engine_module, "build_coverage_plan", record)
    execution = execute_case(engine=e, case=case())
    assert execution.section is seen[0]
    before = execution.result.model_dump()
    advice = reporting._build_chapter_admissibility
    def inspect(c, s):
        assert s is execution.section
        return advice(c, s)
    monkeypatch.setattr(reporting, "_build_chapter_admissibility", inspect)
    reporting.build_compact_summary(execution)
    assert execution.result.model_dump() == before
    assert e.run(case()).model_dump() == before


def test_custom_geometry_constructed_once(monkeypatch):
    calls = []
    original = engine_module._build_custom_section
    def count(c):
        calls.append(c)
        return original(c)
    monkeypatch.setattr(engine_module, "_build_custom_section", count)
    execution, = execute_payload(payload(), engine())
    reporting.build_compact_summary(execution)
    assert len(calls) == 1


def test_catalog_once_and_normalized_section_reused(monkeypatch):
    repo = SectionRepository()
    repo.load([Section(name="solid", type="SOLID_RECTANGULAR", A=1000, rx=10, ry=10)])
    data = payload()
    data.pop("custom_section")
    data["section_name"] = "solid"
    calls = []
    original = repo.get
    def count(name):
        calls.append(name)
        return original(name)
    monkeypatch.setattr(repo, "get", count)
    execution, = execute_payload(data, SteelDesignEngine(repo))
    reporting.build_compact_summary(execution)
    assert calls == ["solid"]
    assert execution.section.name == "solid"
    data["section_name"] = "absent"
    with pytest.raises(SectionNotFoundError):
        execute_payload(data, SteelDesignEngine(repo))


def test_external_catalog_and_missing_section(tmp_path):
    catalog = tmp_path / "external.xlsx"
    catalog.write_bytes((ROOT / "data/sections.xlsx").read_bytes())
    data = json.loads((ROOT / "examples/w_shape_case.json").read_text(encoding="utf-8-sig"))
    repo = SectionRepository()
    repo.load(load_sections_from_excel(str(catalog)))
    execution, = execute_payload(data, SteelDesignEngine(repo))
    process = invoke(tmp_path, data, catalog)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["checks"] == reporting.build_compact_summary(execution)["checks"]
    data["section_name"] = "absent"
    process = invoke(tmp_path, data, catalog)
    assert process.returncode == 1
    assert json.loads(process.stderr)["error"]["code"] == "SECTION_NOT_FOUND"


def test_asd_flexure_block_not_bypassed():
    data = payload(method="ASD")
    data["loads"]["Mux"] = 1
    with pytest.raises(ValidationError, match="only for LRFD"):
        execute_payload(data, engine())


def test_legacy_helper_imports_still_delegate():
    assert _build_custom_section is build_custom_section
    assert cli._extract_output_options is extract_output_options
    assert cli._merge_case_payload is merge_case_payload
    assert cli._build_global_summary is reporting._build_global_summary
    assert cli._build_case_section(case(), SectionRepository()) == build_custom_section(case())
    data = payload()
    data.pop("custom_section")
    assert cli._build_case_section(case(data), SectionRepository()) is None


def test_merge_and_output_do_not_mutate_input():
    data = payload()
    before = copy.deepcopy(data)
    override = {"loads": {"Pu": -300}, "output": {"write_results_json": True}}
    merged = merge_case_payload(data, override)
    assert data == before
    assert merged["loads"]["Pu"] == -300 and merged["output"]["write_results_json"]
    clean, options = extract_output_options(merged)
    assert "output" in merged and "output" not in clean and options["write_results_json"]


def test_iteration_is_lazy_after_validating_bundle_shape():
    data = {"cases": [payload(), {"unknown": "invalid later case"}]}
    iterator = iter_executions(data, engine())
    assert next(iterator).result.status.value == "PASS"
    with pytest.raises(PydanticValidationError):
        next(iterator)


@pytest.mark.parametrize("first", ["execution", "reporting", "run", "engine", "sections.geometry"])
def test_import_orders_without_cycles_or_cli_side_effects(first, tmp_path):
    modules = [first, "execution", "reporting", "run", "engine", "models", "results_model", "sections.geometry"]
    code = f"import importlib, sys; sys.path.insert(0, {str(ROOT)!r}); " + "; ".join(
        f"importlib.import_module('steel_design.{m}')" for m in modules)
    result = subprocess.run([sys.executable, "-B", "-c", code], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert not result.stdout and not result.stderr
    assert list(tmp_path.iterdir()) == []


def test_execution_module_has_no_transport_dependencies():
    module = importlib.import_module("steel_design.execution")
    assert not any(name in vars(module) for name in ("argparse", "sys", "Path", "datetime", "json", "reporting"))
