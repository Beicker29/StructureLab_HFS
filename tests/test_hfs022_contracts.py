"""Independent transport invariants; not AISC validation or a second calculator."""
import copy
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

from steel_design.contracts import (
    CONTRACT_KINDS, ContractDocument, ContractError, dump_json, get_schema,
    load_json, migrate_legacy, validate_document,
)
from steel_design.engine import SteelDesignEngine
from steel_design.execution import OutputOptions, execute_payload, prepare_cases
from steel_design.models import CheckResult, SteelCase
from steel_design.results_model import CoverageReport, EngineResult
from steel_design.sections.repository import SectionRepository

ROOT = Path(__file__).resolve().parents[1]


def case_payload():
    return dict(section_name="tie", custom_section=dict(type="SOLID_RECTANGULAR", H=100, B=10),
                material=dict(Fy=345, Fu=450), loads=dict(Pu=-50),
                lengths=dict(Lx=1000, Ly=1000, Lz=1000, Lb=1000), connection=dict(An=800, U=.8))


def result_payload():
    # Declared synthetic evidence, no normative accreditation. Oracle checks
    # referential integrity/aggregation independently of any router or equation.
    return dict(checks=[dict(name="fixture", code="AISC 360-22", clause="test",
                            demand=2.0, capacity=4.0, dcr=.5, unit="kN", numeric_issue=None,
                            status="PASS", details={"raw": 1.0000000000000002})],
                coverage=dict(method="LRFD", section_name="fixture", profile_type="test",
                    demand_components={"Pu": -2}, obligations=[dict(id="fixture", normative_ids=["test"],
                        limit_state="test", component="Pu", condition="test", reason="synthetic fixture",
                        status="EVALUATED", applicability="TRUE", executed_checks=[0], accepted_checks=[0])],
                    executions=[dict(check_index=0, implementation="src.steel_design.historical.text",
                                     obligation_ids=["fixture"])], evaluation_errors=[]))


def document(kind):
    if kind == "case_input":
        return migrate_legacy(case_payload(), kind=kind)
    if kind == "case_bundle":
        return migrate_legacy({**case_payload(), "cases": [{"name": "a"}, {"loads": {"Pu": -60}}]}, kind=kind)
    raw = result_payload()
    payload = raw if kind == "engine_result" else raw["coverage"] if kind == "coverage_report" else raw["checks"][0]
    return migrate_legacy(payload, kind=kind)


@pytest.mark.parametrize("kind", CONTRACT_KINDS)
def test_roundtrip_and_model_identity(kind):
    initial = document(kind)
    text = dump_json(initial)
    restored = load_json(text, expected_kind=kind)
    assert dump_json(restored) == text
    assert type(restored.payload) is type(initial.payload)
    assert restored.contract_version == "1.0"
    assert json.loads(text)["kind"] == kind


@pytest.mark.parametrize("kind", CONTRACT_KINDS)
@pytest.mark.parametrize("version", [None, "", "0.2.0", "HFS-010-v1", "AISC 360-22", "0.9", "1.1", "2.0", 1, True])
def test_version_is_not_guessed(kind, version):
    with pytest.raises(ContractError, match="UNSUPPORTED_VERSION"):
        validate_document(dict(contract_version=version, kind=kind, payload={}))
    with pytest.raises(ContractError, match="UNSUPPORTED_VERSION"):
        get_schema(kind, version=version)


@pytest.mark.parametrize("field", ["kind", "payload", "contract_version"])
def test_envelope_required(field):
    raw = json.loads(dump_json(document("case_input")))
    raw.pop(field)
    with pytest.raises(ContractError, match="INVALID_DOCUMENT"):
        validate_document(raw)


@pytest.mark.parametrize("payload", [None, [], 1, True, "text"])
def test_nonobject_payload(payload):
    with pytest.raises(ContractError, match="INVALID_PAYLOAD"):
        validate_document(dict(contract_version="1.0", kind="case_input", payload=payload))


@pytest.mark.parametrize("kind", CONTRACT_KINDS)
def test_wrong_kind_and_extra_envelope(kind):
    raw = json.loads(dump_json(document(kind)))
    with pytest.raises(ContractError, match="KIND_MISMATCH"):
        validate_document(raw, expected_kind="wrong")
    raw["kind"] = "unrecognized"
    with pytest.raises(ContractError, match="UNKNOWN_KIND"):
        validate_document(raw)
    raw["kind"], raw["extra"] = kind, 1
    with pytest.raises(ContractError, match="EXTRA_FIELD"):
        validate_document(raw)


@pytest.mark.parametrize("method", ["LRFD", "ASD"])
@pytest.mark.parametrize("loads", [{"Pu": -12.000000000000002}, {"Vux": -3}, {"Vuy": 4},
                                  {"Vux": 3, "Vuy": -4}, {"Vu": -7}, {"Pu": -0.0}])
def test_signs_units_method_precision_and_absence(method, loads):
    data = case_payload()
    data.update(design_method=method, loads=loads)
    restored = load_json(dump_json(migrate_legacy(data, kind="case_input"))).payload
    assert restored.model_dump(mode="json", exclude_unset=True) == SteelCase(**data).model_dump(mode="json", exclude_unset=True)
    assert restored.loads.model_fields_set == set(loads)
    for key, value in loads.items():
        assert getattr(restored.loads, key) == value
        assert math.copysign(1, getattr(restored.loads, key)) == math.copysign(1, value)


@pytest.mark.parametrize("extra", [{}, {"design_method": "LRFD"}, {"tension_scope": None},
                                  {"factors": {}}, {"factors": {"Kx": 1}}])
def test_defaults_explicit_null_and_fields_set(extra):
    data = {**case_payload(), **extra}
    original = SteelCase(**data)
    restored = load_json(dump_json(ContractDocument("case_input", original))).payload
    assert restored.model_fields_set == original.model_fields_set
    assert restored.factors.model_fields_set == original.factors.model_fields_set
    assert restored.model_dump(exclude_unset=True) == original.model_dump(exclude_unset=True)


@pytest.mark.parametrize("alias", ["write_results_json", "write_detailed_json", "save_results_json"])
@pytest.mark.parametrize("flag", [True, False])
def test_output_aliases_migrate_without_becoming_engine_fields(alias, flag):
    raw = {**case_payload(), "output": {alias: flag}}
    migrated = migrate_legacy(raw, kind="case_input")
    restored = load_json(dump_json(migrated))
    assert type(restored.payload) is SteelCase
    assert restored.output.write_results_json is flag
    assert "output" not in restored.payload.model_fields_set
    assert raw["output"] == {alias: flag}


@pytest.mark.parametrize("override", [{"loads": {"Pu": -30}}, {"name": 17},
    {"name": None}, {"output": {"write_results_json": False}}, {"connection": {"U": .5}}])
def test_bundle_merge_names_options_preserve_raw_fragments(override):
    raw = {**case_payload(), "output": {"write_results_json": True}, "cases": [override, {}]}
    original = copy.deepcopy(raw)
    restored = load_json(dump_json(migrate_legacy(raw, kind="case_bundle"))).payload
    assert restored == original == raw
    before, after = list(prepare_cases(raw)), list(prepare_cases(restored))
    assert before == after
    engine = SteelDesignEngine(SectionRepository())
    assert [x.result.model_dump() for x in execute_payload(raw, engine)] == [x.result.model_dump() for x in execute_payload(restored, engine)]


def test_bundle_base_can_be_invalid_until_overridden():
    raw = {**case_payload(), "material": {"Fy": "overridden", "Fu": 450},
           "cases": [{"material": {"Fy": 345}}]}
    assert load_json(dump_json(migrate_legacy(raw, kind="case_bundle"))).payload == raw


@pytest.mark.parametrize("cases", [[], None, {}, "x", [None], [{}, 3]])
def test_invalid_bundle(cases):
    with pytest.raises(ContractError):
        migrate_legacy({**case_payload(), "cases": cases}, kind="case_bundle")


@pytest.mark.parametrize("patch", [
    {"unknown": 1}, {"loads": {}}, {"loads": {"Pu": None}}, {"loads": {"Pu": True}},
    {"loads": {"Pu": "2"}}, {"loads": {"Vux": 3, "Vu": 5}}, {"loads": {"Mxu": 3}},
    {"design_method": "UNKNOWN"}, {"material": {"Fy": 400, "Fu": 300}},
    {"material": {"Fy": 345, "Fu": 450, "E": 210000}},
    {"design_method": "ASD", "loads": {"Mux": 3}}, {"connection": {}},
])
def test_invalid_inputs_remain_invalid(patch):
    with pytest.raises(ContractError):
        migrate_legacy({**case_payload(), **patch}, kind="case_input")


@pytest.mark.parametrize("number", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("kind", CONTRACT_KINDS)
def test_nonfinite_anywhere_rejected(kind, number):
    raw = json.loads(dump_json(document(kind)))
    raw["payload"]["nonfinite"] = {"nested": [number]}
    with pytest.raises(ContractError, match="NONFINITE_NUMBER"):
        validate_document(raw)
    with pytest.raises(ContractError, match="NONFINITE_NUMBER"):
        load_json(json.dumps(raw))


@pytest.mark.parametrize("value", [math.inf, math.nan, (1, 2), {1: "nonstring"}, object()])
def test_serialization_never_silently_loses_dynamic_details(value):
    check = document("check_result").payload
    check.details = {"problem": value}
    with pytest.raises(ContractError):
        dump_json(ContractDocument("check_result", check))


def test_legacy_nonfinite_scalar_projection_blocked_explicitly():
    raw = CheckResult.from_values(name="invalid", clause="test", demand=1, capacity=0, unit="kN").model_dump(mode="json")
    assert raw["dcr"] is None and raw["nonfinite_values"]
    with pytest.raises(ContractError):
        migrate_legacy(raw, kind="check_result")


@pytest.mark.parametrize("field,value", [("status", "INCOMPLETE"), ("known_failures", [0]),
    ("known_failures", [False]), ("coverage", None)])
def test_inconsistent_published_result_rejected(field, value):
    raw = json.loads(dump_json(document("engine_result")))
    raw["payload"][field] = value
    with pytest.raises(ContractError):
        validate_document(raw)


@pytest.mark.parametrize("field", ["complete", "display", "known_failures"])
def test_derived_fields_not_silently_dropped(field):
    raw = json.loads(dump_json(document("engine_result")))
    target = raw["payload"]["coverage"] if field == "complete" else raw["payload"]["checks"][0] if field == "display" else raw["payload"]
    target[field] = "manipulated"
    with pytest.raises(ContractError):
        validate_document(raw)
    with pytest.raises(ContractError):
        migrate_legacy(raw["payload"], kind="engine_result")


@pytest.mark.parametrize("index", [-1, 1, 2, True, 0.0, "0"])
def test_invalid_indices(index):
    raw = json.loads(dump_json(document("engine_result")))
    raw["payload"]["coverage"]["obligations"][0]["accepted_checks"] = [index]
    with pytest.raises(ContractError):
        validate_document(raw)


@pytest.mark.parametrize("mutation", ["pending_accepted", "unknown_evaluated", "na_true", "duplicate_id",
    "missing_link", "missing_execution", "duplicate_execution", "accepted_unexecuted", "extra_execution",
    "duplicate_accepted", "complete_lie"])
def test_contradictory_coverage(mutation):
    raw = json.loads(dump_json(document("engine_result")))
    cov = raw["payload"]["coverage"]
    obligation = cov["obligations"][0]
    if mutation == "pending_accepted":
        obligation["status"] = "PENDING"
    elif mutation == "unknown_evaluated":
        obligation["applicability"] = "UNKNOWN"
    elif mutation == "na_true":
        obligation["status"] = "NOT_APPLICABLE"
    elif mutation == "duplicate_id":
        cov["obligations"].append(copy.deepcopy(obligation))
    elif mutation == "missing_link":
        cov["executions"][0]["obligation_ids"] = []
    elif mutation == "missing_execution":
        cov["executions"] = []
    elif mutation == "duplicate_execution":
        cov["executions"].append(copy.deepcopy(cov["executions"][0]))
    elif mutation == "accepted_unexecuted":
        obligation["executed_checks"] = []
    elif mutation == "extra_execution":
        cov["executions"].append(dict(check_index=1, implementation="text", obligation_ids=[]))
    elif mutation == "duplicate_accepted":
        obligation["accepted_checks"] = [0, 0]
    else:
        cov["complete"] = False
    with pytest.raises(ContractError):
        validate_document(raw)


@pytest.mark.parametrize("path", [(), ("coverage",), ("checks", 0), ("coverage", "obligations", 0), ("coverage", "executions", 0)])
def test_unknown_fields_nested_in_outputs(path):
    raw = json.loads(dump_json(document("engine_result")))
    cursor = raw["payload"]
    for key in path:
        cursor = cursor[key]
    cursor["typo"] = 1
    with pytest.raises(ContractError):
        validate_document(raw)


@pytest.mark.parametrize("kind,field", [("check_result", "display"), ("engine_result", "status"), ("coverage_report", "complete")])
def test_legacy_missing_derived_migrates_but_versioned_requires_complete_snapshot(kind, field):
    raw = json.loads(dump_json(document(kind)))
    raw["payload"].pop(field)
    with pytest.raises(ContractError):
        validate_document(raw)
    migrated = migrate_legacy(raw["payload"], kind=kind)
    assert field in json.loads(dump_json(migrated))["payload"]


@pytest.mark.parametrize("status", ["PASS", "FAIL", "INCOMPLETE"])
@pytest.mark.parametrize("method", ["LRFD", "ASD"])
def test_real_result_and_coverage_roundtrip_preserve_status(status, method):
    data = case_payload()
    data["design_method"] = method
    if status != "INCOMPLETE":
        data["tension_scope"] = dict(ordinary_prismatic_member=True, concentric_axial_force=True,
            no_special_conditions=True, material_reference="test", demand_reference="test",
            net_area_reference="test", connection_reference="test", external_checks_reference="test")
    if status == "FAIL":
        data["loads"]["Pu"] = -350
    result = SteelDesignEngine(SectionRepository()).run(SteelCase(**data))
    assert result.status.value == status
    restored = load_json(dump_json(ContractDocument("engine_result", result))).payload
    assert restored.model_dump(mode="json") == result.model_dump(mode="json")
    assert load_json(dump_json(ContractDocument("coverage_report", result.coverage))).payload.complete == result.coverage.complete


def test_historical_full_json_without_execution_or_dynamic_import(monkeypatch):
    historical = json.loads((ROOT / "docs/audit/hfs017/evidence/after/engine-results.json").read_text(encoding="utf-8"))
    def forbidden(*args, **kwargs):
        raise AssertionError("Contract migration must not execute a motor")
    monkeypatch.setattr(SteelDesignEngine, "run", forbidden)
    monkeypatch.setattr(SteelDesignEngine, "run_with_context", forbidden)
    count, errors = 0, 0
    for records in historical.values():
        for entry in records:
            if "result" not in entry:
                continue
            result = entry["result"]
            if "error" in result:
                with pytest.raises(ContractError):
                    migrate_legacy(result, kind="engine_result")
                errors += 1
                continue
            restored = load_json(dump_json(migrate_legacy(result, kind="engine_result"))).payload
            assert restored.model_dump(mode="json") == result
            count += 1
    assert (count, errors) == (11, 1)
    assert not any(n.startswith("src.steel_design") for n in sys.modules)


@pytest.mark.parametrize("filename", sorted(p.name for p in (ROOT / "examples").glob("*.json")))
def test_existing_example_input_migration(filename):
    raw = json.loads((ROOT / "examples" / filename).read_text(encoding="utf-8-sig"))
    kind = "case_bundle" if "cases" in raw else "case_input"
    migrated = load_json(dump_json(migrate_legacy(raw, kind=kind)))
    if kind == "case_bundle":
        assert migrated.payload == raw
    else:
        case, _, options, _ = next(prepare_cases(raw))
        assert migrated.payload.model_dump() == case.model_dump()
        assert (migrated.output or OutputOptions()).model_dump() == options


@pytest.mark.parametrize("kind", CONTRACT_KINDS)
@pytest.mark.parametrize("mode", ["validation", "serialization"])
def test_frozen_schema_and_repeated_generation(kind, mode):
    schema = get_schema(kind, mode=mode)
    assert schema == get_schema(kind, mode=mode)
    expected = (ROOT / f"docs/schemas/contracts/1.0/{kind}.{mode}.json").read_bytes()
    assert (json.dumps(schema, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode() == expected
    schema["properties"].clear()
    assert get_schema(kind, mode=mode)["properties"]


def test_schema_command_detects_drift_without_writing(tmp_path):
    script = ROOT / "scripts/generate_hfs022_schemas.py"
    command = [sys.executable, str(script), "--directory", str(tmp_path)]
    assert subprocess.run(command, capture_output=True).returncode == 0
    assert subprocess.run([*command, "--check"], capture_output=True).returncode == 0
    path = tmp_path / "case_input.validation.json"
    path.write_bytes(b"{}\n")
    assert subprocess.run([*command, "--check"], capture_output=True).returncode == 1
    assert path.read_bytes() == b"{}\n"


def test_fresh_import_has_no_application_effects(tmp_path):
    code = """
import sys, json
def guard(event, args):
    if event in ('socket.connect', 'subprocess.Popen', 'os.mkdir'):
        raise AssertionError(event)
    if event == 'open' and isinstance(args[1], str) and any(c in args[1] for c in 'wax+'):
        raise AssertionError(event)
sys.addaudithook(guard)
import steel_design.contracts as contracts
assert 'steel_design.run' not in sys.modules
assert 'steel_design.reporting' not in sys.modules
assert 'matplotlib' not in sys.modules
assert contracts.CONTRACT_VERSION == '1.0'
print(json.dumps({'module': contracts.__file__}))
"""
    process = subprocess.run([sys.executable, "-I", "-B", "-c", code], cwd=tmp_path, capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("data", ['{"x":1,"x":2}', '{"nested":{"x":1,"x":2}}', '{', '[]'])
def test_malformed_json(data):
    with pytest.raises(ContractError):
        load_json(data)


def test_no_implicit_migration_or_future_fallback():
    with pytest.raises(ContractError, match="INVALID_DOCUMENT"):
        load_json(json.dumps(case_payload()))
    with pytest.raises(ContractError, match="ALREADY_VERSIONED"):
        migrate_legacy(dict(contract_version="999", kind="case_input", payload=case_payload()), kind="case_input")


def test_mutated_model_revalidation_and_no_mutation():
    model = document("engine_result").payload
    model.status = "FAIL"
    with pytest.raises(ContractError):
        dump_json(ContractDocument("engine_result", model))
    assert model.status == "FAIL"
    case = SteelCase(**case_payload()).model_copy(update={"design_method": "wrong"})
    with pytest.raises(ContractError):
        dump_json(ContractDocument("case_input", case))


def test_noncanonical_model_and_wrong_kind_serialization():
    with pytest.raises(ContractError, match="KIND_MISMATCH"):
        dump_json(ContractDocument("check_result", EngineResult(checks=[])))
    with pytest.raises(ContractError, match="KIND_MISMATCH"):
        dump_json(ContractDocument("coverage_report", {}))


def test_schema_modes_computed_and_dynamic_limits():
    schema = get_schema("check_result")
    assert "display" in schema["properties"]["payload"]["required"]
    assert schema["properties"]["payload"]["properties"]["display"]["readOnly"]
    assert "additionalProperties" in str(schema["properties"]["payload"]["properties"]["details"])
    assert CoverageReport.model_json_schema(mode="validation") != CoverageReport.model_json_schema(mode="serialization")


@pytest.mark.parametrize("field,value", [("status", "FAIL"), ("dcr", .5000000000000001),
    ("numeric_issue", "invented"), ("capacity", 3.0), ("demand", True), ("status", "NOT_EVALUATED")])
def test_check_decision_conflicts_rejected_not_repaired(field, value):
    raw = json.loads(dump_json(document("check_result")))
    raw["payload"][field] = value
    with pytest.raises(ContractError):
        validate_document(raw)
    assert raw["payload"][field] == value


def test_inactive_zero_check_is_preserved_without_coverage_credit():
    check = CheckResult(name="inactive", clause="test", demand=0, capacity=0, dcr=0, status="PASS")
    restored = load_json(dump_json(ContractDocument("engine_result", EngineResult(checks=[check])))).payload
    assert restored.checks[0].model_dump() == check.model_dump()
    assert restored.status.value == "INCOMPLETE"


def test_inactive_placeholder_cannot_be_declared_accepted_resistance():
    check = CheckResult(name="inactive", clause="test", demand=0, capacity=0, dcr=0, status="PASS")
    result = EngineResult(checks=[check], coverage=document("engine_result").payload.coverage)
    # Canonical aggregation trusts the supplied evidence; transport must reject
    # this contradictory graph, not alter aggregation or invent accreditation.
    raw = dict(contract_version="1.0", kind="engine_result", payload=result.model_dump(mode="json"))
    with pytest.raises(ContractError, match="COVERAGE_CONFLICT"):
        validate_document(raw)
    with pytest.raises(ContractError, match="COVERAGE_CONFLICT"):
        dump_json(ContractDocument("engine_result", result))


@pytest.mark.parametrize("output", [None, [], True, {"write_results_json": "false"},
    {"write_results_json": False, "save_results_json": False}, {"typo": False}])
def test_invalid_output_options_have_contract_errors(output):
    with pytest.raises(ContractError):
        migrate_legacy({**case_payload(), "output": output}, kind="case_input")


def test_versioned_output_uses_canonical_names_only():
    raw = json.loads(dump_json(document("case_input")))
    raw["output"] = {"save_results_json": False}
    with pytest.raises(ContractError):
        validate_document(raw)


def test_preparation_is_lazy_and_preserves_error_order():
    raw = {**case_payload(), "cases": [{}, {"loads": {"Pu": "bad"}}]}
    prepared = prepare_cases(raw)
    assert next(prepared)[0].loads.Pu == -50
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        next(prepared)


def test_canonical_duplicate_key_policy_and_legacy_facade():
    from steel_design.input_contracts import unique_json_object
    from steel_design.run import _unique_json_object
    assert _unique_json_object is unique_json_object
    with pytest.raises(ValueError) as error:
        unique_json_object([("Pu", 1), ("Pu", 2)])
    assert type(error.value) is ValueError
    assert str(error.value) == "Duplicate JSON field 'Pu'; supply exactly one value per field."


def test_contract_validation_does_not_select_or_execute(monkeypatch):
    from steel_design.domain.routing.profile_router import ProfileRouter
    def forbidden(*args, **kwargs):
        raise AssertionError("No selection, computation or catalog lookup")
    monkeypatch.setattr(ProfileRouter, "get_rules", forbidden)
    monkeypatch.setattr(SteelDesignEngine, "run_with_context", forbidden)
    monkeypatch.setattr(SectionRepository, "get", forbidden)
    raw = {**case_payload(), "cases": [{}, {"loads": {"Pu": -70}}]}
    assert dump_json(migrate_legacy(raw, kind="case_bundle"))
    assert dump_json(migrate_legacy(case_payload(), kind="case_input"))


@pytest.mark.parametrize("kind", ["case_input", "case_bundle"])
def test_no_rounding_large_integer_input_into_float(kind):
    data = case_payload()
    data["loads"]["Pu"] = -(2**53 + 1)
    if kind == "case_bundle":
        data["cases"] = [{}]
    with pytest.raises(ContractError, match="INCONSISTENT_PAYLOAD"):
        migrate_legacy(data, kind=kind)


def test_dynamic_json_keys_and_values_are_preserved():
    doc = document("check_result")
    doc.payload.details = {"a/b~c": [None, False, 0, -0.0, 1.0000000000000002, "ñ"],
                           "historical": "src.steel_design.not_importable"}
    text = dump_json(doc)
    assert dump_json(load_json(text)) == text


@pytest.mark.parametrize("kind", CONTRACT_KINDS)
def test_migration_deterministic_and_nonmutating(kind):
    raw = json.loads(dump_json(document(kind)))["payload"]
    before = copy.deepcopy(raw)
    assert dump_json(migrate_legacy(raw, kind=kind)) == dump_json(migrate_legacy(raw, kind=kind))
    assert raw == before
