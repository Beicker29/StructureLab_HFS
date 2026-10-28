"""CLI transport and compatibility facade for historical helper imports."""
import json
import argparse
import sys

from pydantic import ValidationError as PydanticValidationError

from . import execution as _execution
from .models import SteelCase, finite_json_payload
from .engine import SteelDesignEngine
from .sections.models import Section
from .sections.geometry import build_custom_section
from .sections.loader import load_sections_from_excel
from .sections.repository import SectionRepository
from .domain.errors import SteelDesignError
from .execution import (execute_case, iter_executions, execution_status, validate_bundle_shape,
                        OutputOptions as OutputOptions)
from .reporting import export_execution
from .reporting import _sanitize_filename as _sanitize_filename
from .reporting import _build_global_summary as _build_global_summary
from .reporting import _build_chapter_admissibility as _build_chapter_admissibility
from .reporting import _build_compact_admissibility as _build_compact_admissibility
from .reporting import _extract_shared_context as _extract_shared_context
from .reporting import _infer_check_units as _infer_check_units
from .reporting import _extract_capacity_from_memory as _extract_capacity_from_memory
from .reporting import _build_dcr_trace as _build_dcr_trace
from .reporting import _extract_i5_method2_points as _extract_i5_method2_points
from .reporting import _ordered_pm_points as _ordered_pm_points
from .reporting import _write_i5_interaction_diagram_svg as _write_i5_interaction_diagram_svg
from .reporting import _write_i5_interaction_diagram_png as _write_i5_interaction_diagram_png
from .reporting import _write_detailed_results_file as _write_detailed_results_file
from .reporting import _build_execution_results_dir as _build_execution_results_dir

# Historical facades refer directly to their canonical owner.
_extract_output_options = _execution.extract_output_options
_merge_case_payload = _execution.merge_case_payload


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field {key!r}; supply exactly one value per field.")
        result[key] = value
    return result



def _print_structured_error(error: Exception, *, stage: str):
    payload = {
        "error": {
            "type": error.__class__.__name__,
            "message": str(error),
            "stage": stage,
        }
    }
    if isinstance(error, SteelDesignError):
        payload["error"].update(
            {
                "code": error.code,
                "details": error.details,
            }
        )
    if isinstance(error, PydanticValidationError):
        payload["error"]["code"] = "VALIDATION_ERROR"
        payload["error"]["details"] = {"fields": error.errors(
            include_url=False, include_context=False, include_input=False)}
    print(json.dumps(payload, indent=2, allow_nan=False), file=sys.stderr)



def _build_case_section(case: SteelCase, repo: SectionRepository) -> Section | None:
    """Compatibility lookup only; normal execution reuses the engine's Section."""
    return build_custom_section(case) if case.custom_section is not None else repo.get(case.section_name)


def _run_single_case(
    *,
    engine: SteelDesignEngine,
    repo: SectionRepository,
    case: SteelCase,
    input_payload: dict,
    input_file: str,
    sections_file: str,
    results_dir: str,
    write_results_json: bool,
    case_tag: str | None = None,
) -> dict:
    # repo remains in the signature for existing callers; the engine owns lookup.
    execution = execute_case(engine=engine, case=case, input_payload=input_payload,
                             output_options={"write_results_json": write_results_json}, case_tag=case_tag)
    return export_execution(execution, input_file=input_file, sections_file=sections_file,
                            results_dir=results_dir)


def main():
    parser = argparse.ArgumentParser(description="AISC 360-22 Steel Design Engine CLI")
    parser.add_argument("input_file", type=str, help="Path to the JSON input case file.")
    parser.add_argument("--sections", type=str, default="data/sections.xlsx", help="Path to the sections Excel file.")
    parser.add_argument("--results-dir", type=str, default="results", help="Directory to store detailed JSON results.")
    args = parser.parse_args()

    # Load sections
    try:
        sections = load_sections_from_excel(args.sections)
    except Exception as e:
        _print_structured_error(e, stage="load_sections")
        sys.exit(1)
        
    # Init repository
    repo = SectionRepository()
    repo.load(sections)
    
    # Init Engine
    engine = SteelDesignEngine(repository=repo)
    
    # Read input payload
    try:
        with open(args.input_file, "r", encoding="utf-8") as f:
            payload = json.load(f, object_pairs_hook=_unique_json_object)
    except Exception as e:
        _print_structured_error(e, stage="parse_input")
        sys.exit(1)

    # Run
    try:
        is_bundle = validate_bundle_shape(payload)
        execution_results_dir = _build_execution_results_dir(base_results_dir=args.results_dir, input_file=args.input_file)
        executions, summaries = [], []
        for execution in iter_executions(payload, engine):
            executions.append(execution)
            summaries.append(export_execution(execution, input_file=args.input_file,
                             sections_file=args.sections, results_dir=execution_results_dir))
        if is_bundle:
            output = {"bundle": True, "total_cases": len(summaries),
                      "status": execution_status(executions),
                      "results_run_dir": execution_results_dir, "cases": summaries}
            print(json.dumps(output, indent=2, allow_nan=False))
        else:
            print(json.dumps(finite_json_payload(summaries[0]), indent=2, allow_nan=False))

    except Exception as e:
        _print_structured_error(e, stage="run_engine")
        sys.exit(1)



if __name__ == "__main__":
    main()
