"""Independent Draft 2020-12 interoperability and architecture/diagnostic regressions.

Schema assertions read frozen files, never get_schema. HFS-022 sample builders
are inputs, not expected validator decisions. No engineering oracle is added.
"""
import copy
import importlib.metadata
import inspect
import json
import math
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator
import pytest

from steel_design.contracts import ContractError, dump_json, load_json, migrate_legacy, validate_document
from steel_design.execution import iter_executions
from test_hfs022_contracts import case_payload, document

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("case_input", "case_bundle", "coverage_report", "check_result", "engine_result")
MODES = ("validation", "serialization")


@pytest.fixture(params=[(kind, mode) for kind in KINDS for mode in MODES], ids=lambda pair: "-".join(pair))
def schema_case(request):
    kind, mode = request.param
    schema = json.loads((ROOT / f"docs/schemas/contracts/1.0/{kind}.{mode}.json").read_bytes())
    raw = json.loads(dump_json(document(kind)))
    return kind, schema, Draft202012Validator(schema), raw


def test_frozen_schema_dialect_and_complete_document(schema_case):
    _, schema, validator, raw = schema_case
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(schema)
    validator.validate(raw)
    # Resolve all local refs, even definitions unused by a bundle fragment.
    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"]
                assert ref.startswith("#/")
                target = schema
                for key in ref[2:].split("/"):
                    target = target[key.replace("~1", "/").replace("~0", "~")]
                assert isinstance(target, dict)
                Draft202012Validator.check_schema(target)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(schema)


@pytest.mark.parametrize("mutation", ["future", "distribution_version", "wrong_kind", "missing_version",
    "missing_kind", "missing_payload", "extra", "null_payload", "array_payload", "string_payload"])
def test_schema_envelope_rejections(schema_case, mutation):
    _, _, validator, raw = schema_case
    if mutation == "future":
        raw["contract_version"] = "2.0"
    elif mutation == "distribution_version":
        raw["contract_version"] = "0.2.0"
    elif mutation == "wrong_kind":
        raw["kind"] = "other"
    elif mutation.startswith("missing_"):
        raw.pop(mutation.removeprefix("missing_").replace("version", "contract_version"))
    elif mutation == "extra":
        raw["typo"] = 0
    else:
        raw["payload"] = {"null_payload": None, "array_payload": [], "string_payload": "{}"}[mutation]
    assert not validator.is_valid(raw)
    with pytest.raises(ContractError):
        validate_document(raw)


def test_schema_all_required_payload_fields(schema_case):
    _, schema, validator, raw = schema_case
    for field in schema["properties"]["payload"].get("required", []):
        invalid = copy.deepcopy(raw)
        invalid["payload"].pop(field)
        assert not validator.is_valid(invalid), field


def test_schema_closed_payload(schema_case):
    _, _, validator, raw = schema_case
    raw["payload"]["unexpected"] = True
    assert not validator.is_valid(raw)


@pytest.mark.parametrize("mutation", ["boolean_number", "string_number", "null_number", "invalid_enum", "nested_extra"])
def test_schema_nested_types_enums_and_refs(schema_case, mutation):
    kind, _, validator, raw = schema_case
    payload = raw["payload"]
    if kind == "case_bundle":
        # Fragment values are deliberately not effective-case constraints.
        # Exercise the typed bundle structure here; semantic differences below.
        if mutation == "nested_extra":
            payload["cases"][0]["unknown"] = 1
        else:
            payload["cases"] = {"boolean_number": True, "string_number": "cases",
                                "null_number": None, "invalid_enum": ["not_an_object"]}[mutation]
    else:
        target = payload
        number = "demand"
        enum = "status"
        if kind == "case_input":
            if mutation == "invalid_enum":
                payload["design_method"] = "UNKNOWN"
            target, number = payload["material"], "Fy"
        elif kind == "coverage_report":
            target, number = payload["executions"][0], "check_index"
            if mutation == "invalid_enum":
                payload["obligations"][0]["applicability"] = "MAYBE"
        elif kind == "engine_result":
            target = payload["checks"][0]
        if mutation.endswith("_number"):
            target[number] = {"boolean_number": True, "string_number": "1", "null_number": None}[mutation]
        elif mutation == "nested_extra":
            target["typo"] = 1
        elif kind in ("check_result", "engine_result"):
            target[enum] = "NOT_EVALUATED"
    assert not validator.is_valid(raw)
    with pytest.raises(ContractError):
        validate_document(raw)


def test_schema_nullable_and_dynamic_json(schema_case):
    kind, _, validator, raw = schema_case
    if kind == "case_input":
        raw["payload"]["tension_scope"] = None
    elif kind == "case_bundle":
        raw["payload"]["cases"][0]["name"] = None
    elif kind == "coverage_report":
        raw["payload"]["scope_evidence"] = {"a/b~c": [None, -0.0, False, 2**60]}
    else:
        target = raw["payload"] if kind == "check_result" else raw["payload"]["checks"][0]
        target["details"] = {"a/b~c": [None, -0.0, False, 2**60]}
    validator.validate(raw)
    restored = validate_document(raw)
    assert json.loads(dump_json(restored)) == raw


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("filename", sorted(p.name for p in (ROOT / "examples").glob("*.json")))
def test_independent_schema_accepts_migrated_existing_examples(mode, filename):
    legacy = json.loads((ROOT / "examples" / filename).read_text(encoding="utf-8-sig"))
    kind = "case_bundle" if "cases" in legacy else "case_input"
    raw = json.loads(dump_json(migrate_legacy(legacy, kind=kind)))
    schema = json.loads((ROOT / f"docs/schemas/contracts/1.0/{kind}.{mode}.json").read_bytes())
    Draft202012Validator(schema).validate(raw)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("scenario", ["material_order", "asd_flexure", "bundle_effective_case",
    "derived_state", "coverage_link", "dcr", "display", "float_index"])
def test_schema_acceptance_does_not_replace_canonical_validation(mode, scenario):
    kind = ("case_input" if scenario in ("material_order", "asd_flexure") else
            "case_bundle" if scenario == "bundle_effective_case" else "engine_result")
    raw = json.loads(dump_json(document(kind)))
    payload = raw["payload"]
    if scenario == "material_order":
        payload["material"].update(Fy=500, Fu=450)
    elif scenario == "asd_flexure":
        payload["design_method"] = "ASD"
        payload["loads"]["Mux"] = 1
    elif scenario == "bundle_effective_case":
        payload["cases"][0]["loads"] = {"Pu": "not_number"}
    elif scenario == "derived_state":
        payload["status"] = "INCOMPLETE"
    elif scenario == "coverage_link":
        payload["coverage"]["obligations"][0]["accepted_checks"] = [99]
    elif scenario == "dcr":
        payload["checks"][0]["dcr"] = .6
    elif scenario == "display":
        payload["checks"][0]["display"]["dcr"] = "manipulated"
    else:
        payload["coverage"]["executions"][0]["check_index"] = 0.0
    schema = json.loads((ROOT / f"docs/schemas/contracts/1.0/{kind}.{mode}.json").read_bytes())
    Draft202012Validator(schema).validate(raw)
    with pytest.raises(ContractError):
        validate_document(raw)


def test_contract_import_and_preparation_without_engine_or_application_effects(tmp_path):
    code = '''
import sys, json
class BlockExecution:
    def find_spec(self, fullname, path=None, target=None):
        if fullname in ('steel_design.engine', 'steel_design.execution', 'steel_design.run',
                        'steel_design.reporting', 'steel_design.sections.loader',
                        'steel_design.sections.repository', 'steel_design.domain.coverage',
                        'steel_design.domain.coverage_evidence') or fullname.startswith(
                        ('steel_design.domain.rules', 'steel_design.domain.routing', 'steel_design.domain.evaluators')):
            raise AssertionError('Unnecessary import: ' + fullname)
sys.meta_path.insert(0, BlockExecution())
def guard(event, args):
    if event in ('socket.connect', 'subprocess.Popen', 'os.mkdir'):
        raise AssertionError(event)
    if event == 'open':
        if isinstance(args[1], str) and any(c in args[1] for c in 'wax+'):
            raise AssertionError('write')
        if str(args[0]).lower().endswith(('.xlsx', '.json', '.svg', '.pdf')):
            raise AssertionError('application file')
sys.addaudithook(guard)
def profile(frame, event, arg):
    if event == 'call' and frame.f_globals.get('__name__', '').startswith('steel_design.codes') and frame.f_code.co_name != '<module>':
        raise AssertionError('Calculation executed')
sys.setprofile(profile)
from steel_design.contracts import migrate_legacy, dump_json, load_json
raw = json.loads(sys.argv[1])
for kind, data in [('case_input',raw), ('case_bundle',dict(raw,cases=[{},{}]))]:
    assert dump_json(load_json(dump_json(migrate_legacy(data,kind=kind))))
sys.setprofile(None)
print(json.dumps(sorted(n for n in sys.modules if n.startswith('steel_design'))))
'''
    process = subprocess.run([sys.executable, "-I", "-B", "-c", code, json.dumps(case_payload())],
                             cwd=tmp_path, capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("change,path", [
    ("accepted", "/payload/coverage/obligations/0/accepted_checks"),
    ("duplicate_execution", "/payload/coverage/executions/1/check_index"),
    ("duplicate_id", "/payload/coverage/obligations/1/id"),
    ("execution_index", "/payload/coverage/executions/0/check_index"),
    ("links", "/payload/coverage/obligations/0/executed_checks"),
    ("applicability", "/payload/coverage/obligations/0/applicability"),
    ("dcr", "/payload/checks/0/dcr"),
    ("status", "/payload/checks/0/status"),
    ("null", "/payload/checks/0/demand"),
    ("missing", "/payload/known_failures"),
    ("extra", "/payload/a~1b~0c"),
])
def test_conflict_paths(change, path):
    raw = json.loads(dump_json(document("engine_result")))
    payload, cov = raw["payload"], raw["payload"]["coverage"]
    if change == "accepted":
        cov["obligations"][0]["accepted_checks"] = [2]
    elif change == "duplicate_execution":
        cov["executions"].append(copy.deepcopy(cov["executions"][0]))
    elif change == "duplicate_id":
        cov["obligations"].append(copy.deepcopy(cov["obligations"][0]))
    elif change == "execution_index":
        cov["executions"][0]["check_index"] = 2
    elif change == "links":
        cov["executions"][0]["obligation_ids"] = []
    elif change == "applicability":
        cov["obligations"][0]["applicability"] = "UNKNOWN"
    elif change == "dcr":
        payload["checks"][0]["dcr"] = .7
    elif change == "status":
        payload["checks"][0]["status"] = "FAIL"
    elif change == "null":
        payload["checks"][0]["demand"] = None
    elif change == "missing":
        payload.pop("known_failures")
    else:
        payload["a/b~c"] = 0
    with pytest.raises(ContractError) as error:
        validate_document(raw)
    assert error.value.path == path


def test_output_options_path_and_original_cause():
    raw = json.loads(dump_json(document("case_input")))
    raw["output"] = {"write_results_json": "no"}
    with pytest.raises(ContractError) as error:
        validate_document(raw)
    assert error.value.path == "/output/write_results_json"
    assert error.value.__cause__ is not None


def test_dump_nonfinite_path_includes_payload():
    doc = document("check_result")
    doc.payload.details = {"a/b~c": [math.inf]}
    with pytest.raises(ContractError) as error:
        dump_json(doc)
    assert error.value.path == "/payload/details/a~1b~0c/0"


def test_bundle_error_identifies_effective_case():
    raw = json.loads(dump_json(document("case_bundle")))
    raw["payload"]["cases"][1]["loads"]["Pu"] = "wrong"
    with pytest.raises(ContractError) as error:
        validate_document(raw)
    assert error.value.path == "/payload/cases/1/loads/Pu"
    assert error.value.__cause__ is not None


def test_preparation_reexports_are_identical_and_signatures_retained():
    from steel_design import execution, preparation, run
    for name in ("OutputOptions", "prepare_cases", "merge_case_payload", "extract_output_options", "validate_bundle_shape"):
        assert getattr(execution, name) is getattr(preparation, name)
        assert inspect.signature(getattr(execution, name)) == inspect.signature(getattr(preparation, name))
    assert run.OutputOptions is preparation.OutputOptions
    assert run._merge_case_payload is preparation.merge_case_payload
    assert run._extract_output_options is preparation.extract_output_options


def test_iter_executions_stops_after_first_executed_case_on_later_invalid_input():
    calls = []
    class Engine:
        def run_with_context(self, case):
            calls.append(case.loads.Pu)
            return case, None, None
    raw = {**case_payload(), "cases": [{}, {"loads": {"Pu": "bad"}}, {}]}
    iterator = iter_executions(raw, Engine())
    assert next(iterator).case.loads.Pu == -50
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        next(iterator)
    assert calls == [-50]


def test_jsonschema_is_only_a_development_dependency():
    requirements = importlib.metadata.requires("structurelab-hfs")
    assert not any("jsonschema" in requirement and 'extra == "dev"' not in requirement for requirement in requirements)


def test_new_unknown_key_and_nested_computed_names_never_disappear():
    doc = document("check_result")
    doc.payload.details = {"display": {"status": "external"}, "complete": False, "known_failures": [999]}
    encoded = dump_json(doc)
    assert dump_json(load_json(encoded)) == encoded


def test_large_dynamic_integer_is_not_coerced_to_float():
    doc = document("check_result")
    doc.payload.details = {"number": 2**64 + 1}
    restored = load_json(dump_json(doc))
    assert restored.payload.details["number"] == 2**64 + 1
    assert type(restored.payload.details["number"]) is int


@pytest.mark.parametrize("mode", MODES)
def test_independent_schema_empty_bundle_and_numeric_boundaries(mode):
    schema = json.loads((ROOT / f"docs/schemas/contracts/1.0/case_bundle.{mode}.json").read_bytes())
    raw = json.loads(dump_json(document("case_bundle")))
    raw["payload"]["cases"] = []
    assert not Draft202012Validator(schema).is_valid(raw)
    schema = json.loads((ROOT / f"docs/schemas/contracts/1.0/case_input.{mode}.json").read_bytes())
    validator = Draft202012Validator(schema)
    for value in (0, -1, False, None, "345"):
        raw = json.loads(dump_json(document("case_input")))
        raw["payload"]["material"]["Fy"] = value
        assert not validator.is_valid(raw)
    for value in (1, 345.0):
        raw["payload"]["material"]["Fy"] = value
        validator.validate(raw)


@pytest.mark.parametrize("mode", MODES)
def test_independent_schema_output_options_and_nested_partial_override(mode):
    schema = json.loads((ROOT / f"docs/schemas/contracts/1.0/case_input.{mode}.json").read_bytes())
    validator = Draft202012Validator(schema)
    raw = json.loads(dump_json(document("case_input")))
    for value in (True, False):
        raw["output"] = {"write_results_json": value}
        validator.validate(raw)
        validate_document(raw)
    for value in (None, 0, "false"):
        raw["output"] = {"write_results_json": value}
        assert not validator.is_valid(raw)
    raw = {**case_payload(), "material": {"Fy": "overridden", "Fu": 450},
           "cases": [{"material": {"Fy": 345}}]}
    versioned = json.loads(dump_json(migrate_legacy(raw, kind="case_bundle")))
    schema = json.loads((ROOT / f"docs/schemas/contracts/1.0/case_bundle.{mode}.json").read_bytes())
    Draft202012Validator(schema).validate(versioned)
    assert validate_document(versioned).payload == raw


@pytest.mark.parametrize("kind", ["coverage_report", "check_result"])
def test_standalone_output_diagnostics_use_payload_root(kind):
    raw = json.loads(dump_json(document(kind)))
    if kind == "coverage_report":
        raw["payload"]["obligations"][0]["accepted_checks"] = [2]
        expected = "/payload/obligations/0/accepted_checks"
    else:
        raw["payload"]["dcr"] = .9
        expected = "/payload/dcr"
    with pytest.raises(ContractError) as error:
        validate_document(raw)
    assert error.value.path == expected


def test_legacy_domain_error_keeps_cause_and_declared_location():
    raw = case_payload()
    raw["connection"].pop("U")
    with pytest.raises(ContractError) as error:
        migrate_legacy(raw, kind="case_input")
    assert error.value.path == "/payload/connection/U"
    assert error.value.__cause__.details["required_field"] == "connection.U"


def test_bundle_shape_location_is_not_prefixed_with_effective_case():
    raw = {**case_payload(), "cases": [{}, None]}
    with pytest.raises(ContractError) as error:
        migrate_legacy(raw, kind="case_bundle")
    assert error.value.path == "/payload/cases/1"
