"""Manual third-party specimens: expectations never come from a product generator."""
import copy
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator
import pytest

from steel_design.contracts import ContractError, dump_json, load_json, validate_document

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/hfs022q/manual.json"
CASES = json.loads(FIXTURES.read_bytes())["cases"]


@pytest.mark.parametrize("fixture", CASES, ids=lambda item: item["id"])
@pytest.mark.parametrize("mode", ["validation", "serialization"])
def test_manual_contract_schema_and_python(fixture, mode):
    text = fixture.get("json_text") or json.dumps(fixture["document"], ensure_ascii=False)
    raw = json.loads(text)
    untouched = copy.deepcopy(raw)
    schema = json.loads((ROOT / f"docs/schemas/contracts/1.0/{raw['kind']}.{mode}.json").read_bytes())
    validator = Draft202012Validator(schema)
    assert validator.is_valid(raw) == fixture["schema"], fixture["reason"]
    if fixture["python"]:
        doc = load_json(text)
        encoded = dump_json(doc)
        assert json.loads(encoded) == untouched
        assert dump_json(load_json(encoded)) == encoded
        assert dump_json(validate_document(raw)) == encoded
        assert dump_json(doc) == encoded
    else:
        with pytest.raises(ContractError) as caught:
            load_json(text)
        assert (caught.value.code, caught.value.path) == (fixture["code"], fixture["path"])
        assert bool(caught.value.__cause__) == fixture["cause"]
        if "json_text" not in fixture:
            with pytest.raises(ContractError) as dictionary_error:
                validate_document(raw)
            assert (dictionary_error.value.code, dictionary_error.value.path) == (fixture["code"], fixture["path"])
    assert raw == untouched


@pytest.mark.parametrize("aliases", [False, True], ids=["contracts-only", "public-execution-aliases"])
def test_standalone_installed_consumer(tmp_path, aliases):
    command = [sys.executable, "-I", "-B", str(ROOT / "scripts/probe_hfs022q_consumer.py"), str(FIXTURES)]
    if aliases:
        command.append("--aliases")
    process = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result["guarded_contract_phase"]
    assert len(result["fixtures"]) == len(CASES)
    assert list(tmp_path.iterdir()) == []
    if aliases:
        assert len(result["public_aliases"]) == 5
