"""Opt-in JSON transport. No engine execution, files, clock or presentation.

Engineering models remain canonical. Version 1.0 transports finite JSON data;
lossy legacy nonfinite projections are rejected, never repaired. See
docs/contracts/hfs022-versioned-json.md for integrity checks and schema limits.
"""
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import json
import math
from typing import Any, Literal, get_args, get_origin

from pydantic import BaseModel, ValidationError as PydanticValidationError

from .domain.errors import SteelDesignError
from .domain.validation import validate_case
from .execution import OutputOptions, extract_output_options, prepare_cases
from .input_contracts import unique_json_object
from .models import CheckResult, SteelCase
from .results_model import CoverageReport, CoverageStatus, EngineResult

ContractKind = Literal["case_input", "case_bundle", "coverage_report", "check_result", "engine_result"]
ContractPayload = SteelCase | dict[str, Any] | CoverageReport | CheckResult | EngineResult
CONTRACT_VERSION = "1.0"
CONTRACT_KINDS: tuple[ContractKind, ...] = (
    "case_input", "case_bundle", "coverage_report", "check_result", "engine_result")


class ContractError(ValueError):
    """Transport error; ``code`` and JSON-pointer ``path`` identify the conflict.

    A chained Pydantic/domain exception retains its original field diagnostics.
    Never a resistant FAIL or an execution result.
    """

    def __init__(self, code: str, message: str, path: str = "") -> None:
        self.code, self.path = code, path
        super().__init__(f"{code} at {path or '/'}: {message}")


@dataclass(frozen=True)
class ContractDocument:
    """Light transport envelope; payload is the canonical model (raw dict for bundles).

    ``output`` is optional case-input transport metadata, not engineering data.
    Construction is not validation; dump_json revalidates even mutable payloads.
    """

    kind: ContractKind
    payload: ContractPayload
    contract_version: str = CONTRACT_VERSION
    output: OutputOptions | None = None


def _pointer(path: str, key: object) -> str:
    return path + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _json_tree(value: Any, path: str = "") -> None:
    """Prevent JSON encoders from losing nonfinites, object types or dict keys."""
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ContractError("NONFINITE_NUMBER", "Finite JSON numbers are required.", path)
        return
    if type(value) is list:
        for i, item in enumerate(value):
            _json_tree(item, _pointer(path, i))
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ContractError("LOSSY_JSON", "Object keys must be strings.", path)
            _json_tree(item, _pointer(path, key))
        return
    raise ContractError("LOSSY_JSON", "Only JSON scalar, list and object values are supported.", path)


def _model_data(value: Any) -> Any:
    """Inspect declared values before a serializer can mask a nonfinite as null."""
    if isinstance(value, BaseModel):
        return {key: _model_data(getattr(value, key)) for key in type(value).model_fields}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _model_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_model_data(item) for item in value]
    return value


def _encode(value: Any) -> str:
    _json_tree(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _dump_model(value: BaseModel, *, exclude_unset: bool = False) -> dict:
    try:
        return value.model_dump(mode="json", exclude_unset=exclude_unset, warnings="error")
    except ValueError as exc:
        raise ContractError("LOSSY_JSON", "Canonical serializer rejected the model.") from exc


def _read(data: str | bytes | dict) -> dict:
    try:
        value = json.loads(data, object_pairs_hook=unique_json_object) if isinstance(data, (str, bytes)) else deepcopy(data)
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("INVALID_JSON", "Cannot decode JSON.") from exc
    _json_tree(value)
    if not isinstance(value, dict):
        raise ContractError("INVALID_DOCUMENT", "A JSON object is required.")
    return value


def _select(kind: str, version: str) -> type[BaseModel] | None:
    if version != CONTRACT_VERSION:
        raise ContractError("UNSUPPORTED_VERSION", "Expected contract_version '1.0'; no implicit migration.", "/contract_version")
    if kind == "case_input":
        return SteelCase
    if kind == "case_bundle":
        return None
    if kind == "coverage_report":
        return CoverageReport
    if kind == "check_result":
        return CheckResult
    if kind == "engine_result":
        return EngineResult
    raise ContractError("UNKNOWN_KIND", "Unknown contract kind.", "/kind")


def _strip_derived(data: Any, annotation: Any) -> Any:
    """Strip only Pydantic-declared computed fields, not arbitrary unknown keys."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel) and isinstance(data, dict):
        return {key: _strip_derived(value, annotation.model_fields[key].annotation)
                if key in annotation.model_fields else value
                for key, value in data.items() if key not in annotation.model_computed_fields}
    args = get_args(annotation)
    if get_origin(annotation) is list and isinstance(data, list):
        return [_strip_derived(item, args[0]) for item in data]
    # Optional canonical models; arbitrary dict/Any details are opaque JSON.
    for arg in args:
        if isinstance(arg, type) and issubclass(arg, BaseModel):
            return _strip_derived(data, arg)
    return data


def _same(declared: Any, actual: Any, path: str = "/payload", *, partial: bool = False) -> None:
    """Exact JSON-value equality, with bool distinct from numbers and signed zero retained."""
    if isinstance(declared, dict) and isinstance(actual, dict):
        if not (set(declared) <= set(actual) if partial else set(declared) == set(actual)):
            raise ContractError("INCONSISTENT_PAYLOAD", "Missing, extra or lost fields.", path)
        for key, value in declared.items():
            _same(value, actual[key], _pointer(path, key), partial=partial)
    elif isinstance(declared, list) and isinstance(actual, list):
        if len(declared) != len(actual):
            raise ContractError("INCONSISTENT_PAYLOAD", "List length changed.", path)
        for i, (left, right) in enumerate(zip(declared, actual)):
            _same(left, right, _pointer(path, i), partial=partial)
    elif (declared != actual or isinstance(declared, bool) != isinstance(actual, bool)
          or (isinstance(declared, (int, float)) and not isinstance(declared, bool)
              and declared == actual == 0 and math.copysign(1, declared) != math.copysign(1, actual))):
        raise ContractError("INCONSISTENT_PAYLOAD", "Declared value disagrees with the reconstructed model.", path)


def _coverage_integrity(report: CoverageReport, check_count: int | None = None) -> None:
    """Referential integrity only; never reconstruct or discharge an obligation."""
    ids = [o.id for o in report.obligations]
    executions = {e.check_index: e for e in report.executions}
    if len(set(ids)) != len(ids) or len(executions) != len(report.executions):
        raise ContractError("COVERAGE_CONFLICT", "Duplicate obligation or execution index.")
    if set(executions) != set(range(len(executions))):
        raise ContractError("COVERAGE_CONFLICT", "Execution indices must be contiguous and zero-based.")
    if check_count is not None and set(executions) != set(range(check_count)):
        raise ContractError("COVERAGE_CONFLICT", "Execution indices do not match the checks.")
    for item in report.obligations:
        executed, accepted = set(item.executed_checks), set(item.accepted_checks)
        if (len(executed) != len(item.executed_checks) or len(accepted) != len(item.accepted_checks)
                or not accepted <= executed or not executed <= executions.keys()):
            raise ContractError("COVERAGE_CONFLICT", "Invalid executed/accepted check references.")
        linked = {e.check_index for e in report.executions if item.id in e.obligation_ids}
        if linked != executed:
            raise ContractError("COVERAGE_CONFLICT", "Execution links contradict obligation evidence.")
        if ((item.status == CoverageStatus.NOT_APPLICABLE and item.applicability != "FALSE")
                or (item.status == CoverageStatus.EVALUATED and item.applicability != "TRUE")
                or (accepted and item.status != CoverageStatus.EVALUATED)
                or (item.status == CoverageStatus.EVALUATED and item.resistance and not accepted)):
            raise ContractError("COVERAGE_CONFLICT", "Applicability, status and accepted evidence conflict.")
    for entry in report.executions:
        if len(set(entry.obligation_ids)) != len(entry.obligation_ids):
            raise ContractError("COVERAGE_CONFLICT", "Duplicate execution claim.")
    # Claims about obligations absent from this plan occur legitimately in the
    # current producer. Do not infer new obligations from these strings.


def _output_integrity(value: BaseModel) -> None:
    checks = value.checks if isinstance(value, EngineResult) else [value] if isinstance(value, CheckResult) else []
    for check in checks:
        # Preserve the explicitly represented historical inactive 0/0 check.
        # Otherwise use the existing result constructor, never a second ratio
        # or decision formula. This checks arithmetic consistency, not capacity
        # validity, applicability, or independent normative accreditation.
        if check.demand == check.capacity == check.dcr == 0 and check.status.value == "PASS":
            continue
        expected = CheckResult.from_values(name=check.name, clause=check.clause,
            demand=check.demand, capacity=check.capacity, unit=check.unit)
        if (check.dcr != expected.dcr or check.status != expected.status
                or check.numeric_issue != expected.numeric_issue):
            raise ContractError("CHECK_CONFLICT", "Published check contradicts its canonical raw-value decision.")
    if isinstance(value, EngineResult):
        if value.coverage is not None:
            _coverage_integrity(value.coverage, len(value.checks))
            for obligation in value.coverage.obligations:
                if obligation.resistance and any(value.checks[i].capacity <= 0 for i in obligation.accepted_checks):
                    raise ContractError("COVERAGE_CONFLICT", "Accepted resistance cannot reference a zero-capacity placeholder.")
    elif isinstance(value, CoverageReport):
        _coverage_integrity(value)


def _case_snapshot(case: SteelCase, payload: dict) -> SteelCase:
    value = validate_case(case)
    _same(payload, _dump_model(value, exclude_unset=True))
    return value


def _validate(raw: dict, *, legacy: bool = False) -> ContractDocument:
    if not {"contract_version", "kind", "payload"} <= raw.keys():
        raise ContractError("INVALID_DOCUMENT", "contract_version, kind and payload are required.")
    kind, version = raw["kind"], raw["contract_version"]
    model = _select(kind, version)
    allowed = {"contract_version", "kind", "payload"} | ({"output"} if kind == "case_input" else set())
    if raw.keys() - allowed:
        raise ContractError("EXTRA_FIELD", "Unknown envelope field.")
    payload = raw["payload"]
    if not isinstance(payload, dict):
        raise ContractError("INVALID_PAYLOAD", "payload must be an object.", "/payload")
    try:
        output = OutputOptions.model_validate(raw["output"]) if "output" in raw else None
        if output is not None and not legacy:
            _same(raw["output"], _dump_model(output, exclude_unset=True), "/output")
        if kind == "case_bundle":
            if "cases" not in payload:
                raise ContractError("INVALID_PAYLOAD", "Bundle requires cases.", "/payload/cases")
            for case, case_payload, _, _ in prepare_cases(payload):
                _case_snapshot(case, case_payload)
            value = deepcopy(payload)
        else:
            cleaned = _strip_derived(payload, model)
            value = model.model_validate_json(_encode(cleaned), strict=True, extra="forbid")
            if isinstance(value, SteelCase):
                value = _case_snapshot(value, payload)
            else:
                _output_integrity(value)
                _same(payload, _dump_model(value), partial=legacy)
    except (PydanticValidationError, SteelDesignError) as exc:
        raise ContractError("INVALID_PAYLOAD", str(exc), "/payload") from exc
    return ContractDocument(kind=kind, payload=value, contract_version=version, output=output)


def validate_document(data: dict[str, Any], *, expected_kind: ContractKind | None = None) -> ContractDocument:
    """Validate an explicit versioned object and return canonical payload models.

    Output derived fields are mandatory and checked; legacy uses migrate_legacy.
    Input validation includes validate_case, but no catalog or section checks.
    """
    raw = _read(data)
    document = _validate(raw)
    if expected_kind is not None and document.kind != expected_kind:
        raise ContractError("KIND_MISMATCH", "Unexpected contract kind.", "/kind")
    return document


def load_json(data: str | bytes, *, expected_kind: ContractKind | None = None) -> ContractDocument:
    """Read versioned JSON only; duplicate keys and nonfinite numbers are errors."""
    return validate_document(_read(data), expected_kind=expected_kind)


def dump_json(document: ContractDocument) -> str:
    """Serialize canonical payloads deterministically, revalidating without mutation.

    Input models use exclude_unset to preserve explicit defaults and nulls.
    Outputs publish all canonical fields, including computed fields.
    """
    model = _select(document.kind, document.contract_version)
    if (model is None and type(document.payload) is not dict) or (
            model is not None and type(document.payload) is not model):
        raise ContractError("KIND_MISMATCH", "Payload must be the canonical type for kind.")
    _json_tree(_model_data(document.payload))
    payload = (deepcopy(document.payload) if model is None else
               _dump_model(document.payload, exclude_unset=document.kind == "case_input"))
    raw = dict(contract_version=document.contract_version, kind=document.kind, payload=payload)
    if document.output is not None:
        if type(document.output) is not OutputOptions:
            raise ContractError("INVALID_PAYLOAD", "output must be OutputOptions.", "/output")
        raw["output"] = _dump_model(document.output, exclude_unset=True)
    validated = validate_document(raw)
    if model is not None:
        _same(_model_data(document.payload), _model_data(validated.payload))
    return _encode(raw)


def migrate_legacy(data: str | bytes | dict[str, Any], *, kind: ContractKind) -> ContractDocument:
    """Explicit unversioned -> 1.0 migration; no calculations or files.

    Full legacy model payloads only, not compact CLI/memory projections. Supplied
    derived fields must agree. Compatible omitted defaults are made explicit for
    outputs; input omission is preserved. No future-version fallback is allowed.
    """
    payload = _read(data)
    if "contract_version" in payload:
        raise ContractError("ALREADY_VERSIONED", "Use load_json/validate_document for a versioned document.")
    raw = dict(contract_version=CONTRACT_VERSION, kind=kind, payload=payload)
    if kind == "case_input" and "output" in payload:
        try:
            cleaned, _ = extract_output_options(payload)
        except PydanticValidationError as exc:
            raise ContractError("INVALID_PAYLOAD", str(exc), "/output") from exc
        raw["payload"], raw["output"] = cleaned, payload["output"]
    return _validate(raw, legacy=True)


def get_schema(kind: ContractKind, *, version: str = CONTRACT_VERSION,
               mode: Literal["validation", "serialization"] = "validation") -> dict[str, Any]:
    """Generate Draft 2020-12 envelope schema from canonical Pydantic models.

    Python validation remains mandatory for merges, cross-field conditions and
    referential/derived integrity. Returned schemas are fresh, mutable copies.
    """
    model = _select(kind, version)
    if mode not in ("validation", "serialization"):
        raise ContractError("INVALID_SCHEMA_MODE", "Expected validation or serialization.")
    if model is None:
        canonical = SteelCase.model_json_schema(mode=mode)
        definitions = canonical.pop("$defs", {})
        definitions["EffectiveSteelCase"] = canonical
        # Base/overrides can be individually invalid but valid after merge.
        # Do not apply effective-case constraints to these fragments.
        fragments = {key: {} for key in SteelCase.model_fields}
        fragments["output"] = {}
        payload_schema = {"type": "object", "additionalProperties": False,
                          "properties": {**deepcopy(fragments), "cases": {
                              "type": "array", "minItems": 1, "items": {
                                  "type": "object", "additionalProperties": False,
                                  "properties": {**deepcopy(fragments), "name": {}}}}},
                          "required": ["cases"],
                          "$comment": "Fragments preserve deep-merge semantics. Each effective case must validate against EffectiveSteelCase and canonical Python guards; schema alone is insufficient."}
    else:
        # Outputs are complete serialized snapshots even when being read. Their
        # computed properties must not be discarded by an input-only schema.
        payload_schema = model.model_json_schema(mode=mode if model is SteelCase else "serialization")
        definitions = payload_schema.pop("$defs", {})
        if model is not SteelCase:
            for node in [payload_schema, *definitions.values()]:
                if "properties" in node:
                    node["additionalProperties"] = False
                    node["required"] = list(node["properties"])
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
              "$id": f"urn:structurelab-hfs:contracts:{version}:{kind}:{mode}",
              "title": f"{kind} contract {version} ({mode})", "type": "object",
              "additionalProperties": False,
              "properties": {"contract_version": {"type": "string", "const": version},
                             "kind": {"type": "string", "const": kind}, "payload": payload_schema},
              "required": ["contract_version", "kind", "payload"], "$defs": definitions,
              "$comment": "Finite JSON only. Validate with steel_design.contracts for canonical cross-field and derived/evidence integrity. Dynamic details are opaque JSON, not an accredited normative trace."}
    if kind == "case_input":
        schema["properties"]["output"] = OutputOptions.model_json_schema(mode=mode)
    return schema
