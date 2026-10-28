"""In-memory case preparation and execution, shared by transport adapters.

No filesystem, clocks or presentation. Domain validation remains in the engine;
bundle iteration is deliberately sequential and stops on the first exception.
"""
import copy
from typing import NamedTuple, Iterator

from pydantic import AliasChoices, Field, StrictBool, ValidationError as PydanticValidationError

from .input_contracts import InputModel
from .models import SteelCase
from .engine import SteelDesignEngine
from .sections.models import Section
from .results_model import EngineResult, AnalysisStatus, aggregate_case_statuses
from .domain.errors import ValidationError


class OutputOptions(InputModel):
    """Export preferences; the engineering contract remains SteelCase."""

    write_results_json: StrictBool = Field(True, validation_alias=AliasChoices(
        "write_results_json", "write_detailed_json", "save_results_json"))



def merge_case_payload(base_payload: dict, override_payload: dict) -> dict:
    merged = copy.deepcopy(base_payload)
    for key, value in override_payload.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_case_payload(merged[key], value)
        else:
            merged[key] = value
    return merged



def extract_output_options(payload: dict) -> tuple[dict, dict]:
    cleaned = copy.deepcopy(payload)
    output_cfg = cleaned.pop("output", {})
    try:
        options = OutputOptions.model_validate(output_cfg)
    except PydanticValidationError as exc:
        errors = [dict(error, loc=("output", *error["loc"])) for error in exc.errors(include_url=False)]
        raise PydanticValidationError.from_exception_data("OutputOptions", errors) from exc
    return cleaned, options.model_dump()



class CaseExecution(NamedTuple):
    """Internal context of one actual execution, not a new serialized contract."""

    case: SteelCase
    section: Section
    result: EngineResult
    input_payload: dict
    output_options: dict
    case_tag: str | None


def validate_bundle_shape(payload: dict) -> bool:
    """Keep historical early rejection, before any engine call or artifact."""
    is_bundle = isinstance(payload, dict) and "cases" in payload
    if is_bundle:
        case_definitions = payload["cases"]
        if not isinstance(case_definitions, list):
            raise ValidationError("cases must be a list of case objects.", code="INVALID_CASE_BUNDLE",
                                  details={"field": "cases", "received_type": type(case_definitions).__name__})
        if not case_definitions:
            aggregate_case_statuses([])
        for index, definition in enumerate(case_definitions):
            if not isinstance(definition, dict):
                raise ValidationError("Each bundle case must be an object.", code="INVALID_CASE_BUNDLE",
                                      details={"field": f"cases[{index}]", "received_type": type(definition).__name__})
    return is_bundle


def execute_case(*, engine: SteelDesignEngine, case: SteelCase,
                 input_payload: dict | None = None, output_options: dict | None = None,
                 case_tag: str | None = None) -> CaseExecution:
    normalized_case, section, result = engine.run_with_context(case)
    return CaseExecution(normalized_case, section, result,
                         copy.deepcopy(input_payload if input_payload is not None else case.model_dump(mode="json")),
                         copy.deepcopy(output_options if output_options is not None else OutputOptions().model_dump()),
                         case_tag)


def prepare_cases(payload: dict) -> Iterator[tuple[SteelCase, dict, dict, str | None]]:
    """Prepare cases lazily without executing; shared by execution and contracts.

    Yield (case, input payload, output options, tag). Preserve partial overrides,
    explicit fields and historical error order. This is not engine validation.
    """
    is_bundle = validate_bundle_shape(payload)
    if is_bundle:
        base = {key: value for key, value in payload.items() if key != "cases"}
        definitions = payload["cases"]
    else:
        base, definitions = payload, [None]
    for index, definition in enumerate(definitions):
        tag = None
        merged = base
        if is_bundle:
            tag = str(definition.get("name") or f"case_{index+1}")
            merged = merge_case_payload(base, {k: v for k, v in definition.items() if k != "name"})
        case_payload, options = extract_output_options(merged)
        case = SteelCase(**case_payload)
        yield case, case_payload, options, tag


def iter_executions(payload: dict, engine: SteelDesignEngine) -> Iterator[CaseExecution]:
    """Yield each executed case; errors propagate unchanged, without I/O."""
    for case, case_payload, options, tag in prepare_cases(payload):
        yield execute_case(engine=engine, case=case, input_payload=case_payload,
                           output_options=options, case_tag=tag)


def execute_payload(payload: dict, engine: SteelDesignEngine) -> list[CaseExecution]:
    """Materialize a single case or bundle in memory; no export is requested."""
    return list(iter_executions(payload, engine))


def execution_status(executions: list[CaseExecution]) -> AnalysisStatus:
    return aggregate_case_statuses([item.result.status for item in executions])
