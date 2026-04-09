import json
import argparse
import sys
import re
from datetime import datetime, timezone
from pathlib import Path

from .models import SteelCase
from .engine import SteelDesignEngine
from .sections.loader import load_sections_from_excel
from .sections.repository import SectionRepository
from .domain.errors import SteelDesignError


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
    print(json.dumps(payload, indent=2), file=sys.stderr)


def _sanitize_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", text)


def _build_global_summary(result) -> dict:
    checks = result.checks or []
    positive_capacity_checks = [check for check in checks if (check.capacity or 0.0) > 0.0]
    if not positive_capacity_checks:
        return {
            "governing_capacity_kn_or_knm": None,
            "governing_clauses": [],
            "governing_check_names": [],
        }

    min_capacity = min(check.capacity for check in positive_capacity_checks)
    governing_checks = [check for check in positive_capacity_checks if abs(check.capacity - min_capacity) <= 1e-9]
    return {
        "governing_capacity_kn_or_knm": min_capacity,
        "governing_clauses": [check.clause for check in governing_checks],
        "governing_check_names": [check.name for check in governing_checks],
    }


def _extract_shared_context(clause_results: list[dict]) -> dict:
    contexts = [entry.get("context", {}) for entry in clause_results if "context" in entry]
    if len(contexts) != len(clause_results) or not contexts:
        return {}

    shared_keys = set(contexts[0].keys())
    for context in contexts[1:]:
        shared_keys &= set(context.keys())

    shared_context = {}
    for key in sorted(shared_keys):
        value = contexts[0][key]
        if all(context[key] == value for context in contexts[1:]):
            shared_context[key] = value

    if not shared_context:
        return {}

    for entry in clause_results:
        context = entry.get("context", {})
        for key in shared_context:
            context.pop(key, None)
        if not context and "context" in entry:
            entry.pop("context")

    return shared_context


def _write_detailed_results_file(
    *,
    result,
    case: SteelCase,
    input_payload: dict,
    input_file: str,
    sections_file: str,
    profile_type: str,
    results_dir: str,
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    safe_section = _sanitize_filename(case.section_name.upper())
    safe_profile = _sanitize_filename((profile_type or "UNKNOWN").upper())

    output_dir = Path(results_dir) / safe_profile
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{safe_section}__{timestamp}.json"
    output_summary = result.model_dump(exclude={"checks": {"__all__": {"details"}}})

    clause_results = []
    for check in result.checks:
        details = check.details or {}
        entry = {
            "clause": check.clause,
            "name": check.name,
            "calculations": details.get("memory"),
        }
        context = {key: value for key, value in details.items() if key != "memory"}
        if context:
            entry["context"] = context
        clause_results.append(entry)
    shared_context = _extract_shared_context(clause_results)

    payload = {
        "meta": {
            "generated_at_utc": timestamp,
            "profile_type": safe_profile,
            "section_name": case.section_name,
            "input_file": str(input_file),
            "sections_file": str(sections_file),
        },
        "memory": {
            "global_summary": {
                **_build_global_summary(result),
                "overall_status": result.status.value,
            },
            "shared_context": shared_context,
            "clause_results": clause_results,
        },
        "input": input_payload,
        "output": output_summary,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


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
            payload = json.load(f)
            case = SteelCase(**payload)
    except Exception as e:
        _print_structured_error(e, stage="parse_input")
        sys.exit(1)
        
    # Run
    try:
        result = engine.run(case)
        section = repo.get(case.section_name)
        profile_type = section.type if section is not None else "UNKNOWN"
        _write_detailed_results_file(
            result=result,
            case=case,
            input_payload=payload,
            input_file=args.input_file,
            sections_file=args.sections,
            profile_type=profile_type,
            results_dir=args.results_dir,
        )

        # Keep CLI summary output compact: hide internal check details in stdout.
        summary = result.model_dump(exclude={"checks": {"__all__": {"details"}}})
        print(json.dumps(summary, indent=2))
        
    except Exception as e:
        _print_structured_error(e, stage="run_engine")
        sys.exit(1)

if __name__ == "__main__":
    main()
