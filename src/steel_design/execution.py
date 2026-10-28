"""In-memory case preparation and execution, shared by transport adapters.

No filesystem, clocks or presentation. Domain validation remains in the engine;
bundle iteration is deliberately sequential and stops on the first exception.
"""
import copy
from typing import NamedTuple, Iterator

from .models import SteelCase
from .engine import SteelDesignEngine
from .sections.models import Section
from .results_model import EngineResult, AnalysisStatus, aggregate_case_statuses
# Explicit reexports preserve the public preparation paths and object identity.
from .preparation import (
    OutputOptions as OutputOptions,
    merge_case_payload as merge_case_payload,
    extract_output_options as extract_output_options,
    validate_bundle_shape as validate_bundle_shape,
    prepare_cases as prepare_cases,
)


class CaseExecution(NamedTuple):
    """Internal context of one actual execution, not a new serialized contract."""

    case: SteelCase
    section: Section
    result: EngineResult
    input_payload: dict
    output_options: dict
    case_tag: str | None


def execute_case(*, engine: SteelDesignEngine, case: SteelCase,
                 input_payload: dict | None = None, output_options: dict | None = None,
                 case_tag: str | None = None) -> CaseExecution:
    normalized_case, section, result = engine.run_with_context(case)
    return CaseExecution(normalized_case, section, result,
                         copy.deepcopy(input_payload if input_payload is not None else case.model_dump(mode="json")),
                         copy.deepcopy(output_options if output_options is not None else OutputOptions().model_dump()),
                         case_tag)


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
