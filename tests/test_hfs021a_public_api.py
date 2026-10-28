"""Public identity and migration guards; installed-package checks live in verifier."""
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.hfs021a_invariants import assert_import_migration_only, assert_trace_identifier_compatibility_only

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("module,symbol", [
    ("engine", "SteelDesignEngine"), ("models", "SteelCase"),
    ("sections.models", "Section"), ("sections.repository", "SectionRepository"),
    ("execution", "execute_case"), ("execution", "iter_executions"),
    ("execution", "execute_payload"), ("execution", "execution_status"),
    ("reporting", "build_compact_summary"), ("reporting", "build_detailed_results_payload"),
])
def test_public_api_explicit_module(module, symbol):
    imported = importlib.import_module("steel_design." + module)
    value = getattr(imported, symbol)
    assert callable(value)
    assert value.__module__ == "steel_design." + module
    assert importlib.import_module(value.__module__) is imported


@pytest.mark.parametrize("order", ["canonical-first", "legacy-first"])
@pytest.mark.parametrize("location", ["working", "empty"])
def test_fresh_process_import_identity_and_no_side_effects(order, location, tmp_path):
    directory = ROOT if location == "working" else tmp_path
    command = [sys.executable, "-B", str(ROOT / "scripts/probe_hfs021a_imports.py"),
               "--root", str(directory), "--order", order]
    process = subprocess.run(command, cwd=directory, capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    output = json.loads(process.stdout)
    assert output["class_module"] == "steel_design.models"
    assert output["legacy_rejections"] and not output["side_effects"]
    assert not process.stderr
    assert list(tmp_path.iterdir()) == []


def test_facades_are_same_objects_not_duplicate_models():
    from steel_design import engine, execution, reporting, run
    from steel_design.sections.geometry import build_custom_section
    assert engine._build_custom_section is build_custom_section
    assert run.OutputOptions is execution.OutputOptions
    assert run._build_global_summary is reporting._build_global_summary
    assert run._extract_output_options is execution.extract_output_options


@pytest.mark.parametrize("code", [
    "from src.steel_design.models import SteelCase\n",
    "import src.steel_design.models\n",
    "command = ['python', '-m', 'src.steel_design.run']\n",
    "module = f'src.steel_design.{name}'\n",
])
def test_invariant_accepts_only_package_spelling(code):
    assert_import_migration_only(code, code.replace("src.steel_design", "steel_design"))


@pytest.mark.parametrize("old,new", [
    ("0.8", "0.9"), ("0.8", "0.75"),
    ("x > 1", "x >= 1"), ("'FAIL'", "'PASS'"),
    ("'capacity': 100", "'capacity': 101"), ("capacity == 100", "capacity > 0"),
])
def test_invariant_rejects_real_equation_condition_result_or_oracle_change(old, new):
    before = "factor = 0.8\nif x > 1: status = 'FAIL'\ntrace = {'capacity': 100}\nassert capacity == 100\n"
    with pytest.raises(AssertionError, match="beyond"):
        assert_import_migration_only(before, before.replace(old, new))


def test_module_cli_and_retired_cli(tmp_path):
    conventional = subprocess.run([sys.executable, "-m", "steel_design.run", "--help"],
                                  cwd=tmp_path, capture_output=True, text=True)
    assert conventional.returncode == 0 and "--sections" in conventional.stdout
    legacy = subprocess.run([sys.executable, "-m", "src.steel_design.run", "--help"],
                            cwd=ROOT, capture_output=True, text=True)
    assert legacy.returncode != 0 and not legacy.stdout
    # No sources at the external wheel test root; checkout gives the explicit guard.
    assert "namespace has been retired" in legacy.stderr or "No module named 'src" in legacy.stderr


def test_json_identifier_is_historical_but_class_identity_is_canonical():
    from steel_design.execution import execute_payload
    from steel_design.engine import SteelDesignEngine
    from steel_design.sections.repository import SectionRepository
    from steel_design.domain.rules.axial_rules import AxialE3Rule
    payload = dict(section_name="solid", custom_section=dict(type="SOLID_RECTANGULAR", B=20, H=100),
                   material=dict(Fy=345, Fu=450), loads=dict(Pu=10),
                   lengths=dict(Lx=1000, Ly=1000, Lz=1000, Lb=1000))
    item, = execute_payload(payload, SteelDesignEngine(SectionRepository()))
    assert AxialE3Rule.__module__ == "steel_design.domain.rules.axial_rules"
    assert item.result.coverage.executions[0].implementation == "src.steel_design.domain.rules.axial_rules.AxialE3Rule"
    assert item.result.status.value == "INCOMPLETE"
    assert not any(n.startswith("src.steel_design") for n in sys.modules)


def test_identifier_invariant_rejects_coverage_changes():
    before = ('def f():\n    claims = _CLAIMS.get(implementation, ())\n'
              '    record(implementation=f"{implementation.__module__}.{implementation.__qualname__}")\n'
              '    accepted = False\n')
    after = before.replace('    claims = _CLAIMS.get(implementation, ())\n',
                          '    claims = _CLAIMS.get(implementation, ())\n'
                          '    module = implementation.__module__\n'
                          '    identifier_module = "src." + module if module.startswith("steel_design.") else module\n')
    after = after.replace('{implementation.__module__}', '{identifier_module}')
    assert_trace_identifier_compatibility_only(before, after)
    with pytest.raises(AssertionError, match="beyond"):
        assert_trace_identifier_compatibility_only(before, after.replace('accepted = False', 'accepted = True'))
