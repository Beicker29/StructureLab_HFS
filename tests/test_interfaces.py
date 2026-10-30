"""CLI and in-memory execution of the example payloads."""
import json
import subprocess
import sys

import pytest

from steel_design.errors import ValidationError
from steel_design.execution import execute_payload, overall_status

from conftest import CATALOG, ROOT

EXAMPLES = sorted((ROOT / "examples").glob("*.json"))


def cli(*args, cwd):
    return subprocess.run([sys.executable, "-m", "steel_design.run", *map(str, args), "--sections", str(CATALOG)],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_examples_run_in_memory(engine, example):
    results = execute_payload(json.loads(example.read_text(encoding="utf-8")), engine)
    assert overall_status([r for _, _, r in results]).value == "PASS"


def test_cli_prints_json_and_writes_nothing_by_default(tmp_path):
    run = cli(ROOT / "examples/channel_case.json", cwd=tmp_path)
    assert run.returncode == 0, run.stderr
    output = json.loads(run.stdout)
    assert output["status"] == "PASS" and output["compression"]["governing_mode"] == "FTB"
    assert list(tmp_path.iterdir()) == []


def test_cli_optional_output_file(tmp_path):
    target = tmp_path / "result.json"
    run = cli(ROOT / "examples/bundle_case.json", "--output", target, cwd=tmp_path)
    assert run.returncode == 0, run.stderr
    assert json.loads(target.read_text(encoding="utf-8")) == json.loads(run.stdout)
    assert [c["name"] for c in json.loads(run.stdout)["cases"]] == ["W8X10 slender web", "W14X90 minor-axis offset bracing"]


def test_cli_structured_errors(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"section_name": "W14X90", "Pu": -1}', encoding="utf-8")
    run = cli(bad, cwd=tmp_path)
    assert run.returncode == 1 and not run.stdout
    assert json.loads(run.stderr)["error"]["code"] == "VALIDATION_ERROR"
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"Pu": 1, "Pu": 2}', encoding="utf-8")
    assert json.loads(cli(duplicate, cwd=tmp_path).stderr)["error"]["stage"] == "parse_input"


@pytest.mark.parametrize("payload", [[], {"cases": []}, {"cases": [1]}])
def test_invalid_bundles(engine, payload):
    with pytest.raises(ValidationError):
        execute_payload(payload, engine)
