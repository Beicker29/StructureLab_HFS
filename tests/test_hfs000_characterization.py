"""HFS-000 known defects: safety expectations, NOT accepted design behavior.

Each strict xfail records a reproduced omission. XPASS requires review/removal
when fixed; it must never be changed into an assertion approving unsafe output.
These probes are software characterization, not independent AISC validation.
"""
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.steel_design.domain.errors import SteelDesignError
from src.steel_design.engine import SteelDesignEngine
from src.steel_design.models import CheckResult, Loads, SteelCase
from src.steel_design.results_model import EngineResult
from src.steel_design.run import _build_global_summary
from src.steel_design.sections.loader import load_sections_from_excel
from src.steel_design.sections.models import Section
from src.steel_design.sections.repository import SectionRepository


ROOT = Path(__file__).resolve().parents[1]


def known_defect(reason):
    return pytest.mark.xfail(strict=True, raises=AssertionError, reason="known defect: " + reason)


@pytest.fixture(scope="module")
def repository():
    repo = SectionRepository()
    repo.load(load_sections_from_excel(str(ROOT / "data/sections.xlsx")))
    return repo


def case_payload(loads):
    return {"section_name": "W12X26", "design_method": "LRFD",
            "material": {"Fy": 345, "Fu": 450, "E": 200000}, "loads": loads,
            "lengths": {"Lx": 1000, "Ly": 1000, "Lz": 1000, "Lb": 1000}}


def run_case(repository, loads):
    result = SteelDesignEngine(repository).run(SteelCase(**case_payload(loads)))
    print(result.model_dump_json())
    return result


# HFS-011: corrected input rejection, demonstrated before removing strict xfail.
def test_empty_loads_must_not_pass(repository):
    try:
        result = run_case(repository, {})
    except (SteelDesignError, PydanticValidationError):
        return
    assert result.status.value != "PASS"


# HFS-011: corrected input rejection, demonstrated before removing strict xfail.
def test_load_typo_must_be_rejected(repository):
    try:
        result = run_case(repository, {"Mxu": 1000000})
    except (SteelDesignError, PydanticValidationError):
        return
    assert result.status.value != "PASS"


# HFS-011: corrected input rejection, demonstrated before removing strict xfail.
def test_nan_load_must_be_rejected(repository):
    try:
        result = run_case(repository, {"Pu": "NaN"})
    except (SteelDesignError, PydanticValidationError):
        return
    assert result.status.value != "PASS"


@known_defect("F-01: W compression plus biaxial bending has no H interaction")
def test_w_combination_requires_interaction_or_block(repository):
    try:
        result = run_case(repository, {"Pu": 1, "Mux": 1, "Muy": 1})
    except SteelDesignError:
        return
    assert any(check.clause.startswith("H") for check in result.checks)


@known_defect("F-03: missing slenderness ratios select F2")
def test_missing_slenderness_must_block(repository):
    section = repository.get("W12X26").model_copy(update={"bf_2tf_ratio": None, "h_tw_ratio": None})
    repo = SectionRepository()
    repo.load([section])
    try:
        result = run_case(repo, {"Mux": 1})
    except SteelDesignError:
        return
    assert result.status.value != "PASS"


@known_defect("F-31: channel minor-axis rules hide unsupported major-axis demand")
def test_channel_both_axes_must_block_if_major_axis_is_unsupported(repository):
    # Synthetic routing probe, not a physically validated catalog section.
    section = repository.get("W12X26").model_copy(update={
        "type": "CHANNEL", "bf_2tf_ratio": 50, "h_tw_ratio": 300})
    repo = SectionRepository()
    repo.load([section])
    try:
        result = run_case(repo, {"Mux": 1, "Muy": 1})
    except SteelDesignError:
        return
    assert any("major" in check.name.lower() for check in result.checks)


# HFS-011: corrected input rejection, demonstrated before removing strict xfail.
def test_conflicting_shear_must_be_rejected():
    try:
        loads = Loads(Vu=99, Vux=3, Vuy=4)
    except PydanticValidationError:
        return
    print(loads.model_dump())
    assert False, "Contradictory shear inputs were accepted"


@known_defect("F-13: duplicate section silently replaces prior properties")
def test_duplicate_sections_must_be_rejected():
    repo = SectionRepository()
    try:
        repo.load([Section(name="duplicate", A=100), Section(name="DUPLICATE", A=200)])
    except SteelDesignError:
        return
    print({"count": len(repo.get_all()), "retained_area": repo.get("duplicate").area})
    assert len(repo.get_all()) == 2, "Duplicate silently collapsed without error"


@known_defect("F-05: summary compares force and moment magnitudes")
def test_mixed_dimension_summary_must_not_report_scalar_minimum():
    checks = [CheckResult(name="axial", clause="E3-1", demand=90, capacity=100, dcr=.9, status="PASS"),
              CheckResult(name="flexure", clause="F2-1", demand=1, capacity=50, dcr=.02, status="PASS")]
    summary = _build_global_summary(EngineResult(checks=checks, status="PASS"))
    print(summary)
    assert summary.get("governing_capacity_kn_or_knm") is None


@known_defect("F-09: FAIL is published with dcr=1.0 after rounding")
def test_failed_check_must_retain_dcr_above_one():
    payload = case_payload({"Pu": -310.53105})
    payload.update(section_name="solid", custom_section={"type": "SOLID_RECTANGULAR", "B": 10, "H": 100},
                   connection={"An": 1000, "U": 1})
    result = SteelDesignEngine(SectionRepository()).run(SteelCase(**payload))
    check = next(c for c in result.checks if c.clause == "D2-1")
    print(check.model_dump_json())
    assert check.status.value == "FAIL" and check.dcr > 1


@known_defect("F-29: empty CLI bundle returns PASS")
def test_empty_bundle_must_not_pass(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text('{"cases": []}', encoding="utf-8")
    completed = subprocess.run([sys.executable, "-m", "src.steel_design.run", str(path),
                               "--sections", str(ROOT / "data/sections.xlsx"),
                               "--results-dir", str(tmp_path / "results")],
                              cwd=ROOT, capture_output=True, text=True, check=False)
    print(completed.stdout, completed.stderr)
    if completed.returncode != 0:
        assert json.loads(completed.stderr)["error"]
        return
    assert json.loads(completed.stdout)["status"] != "PASS"


@known_defect("F-02: explicit zero demand still gives PASS with zero checks; HFS-010 pending")
def test_explicit_zero_loads_must_not_pass_without_checks(repository):
    result = run_case(repository, {"Pu": 0})
    assert result.status.value != "PASS"
