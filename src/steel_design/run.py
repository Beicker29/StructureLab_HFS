"""CLI: read a JSON case (or bundle), run Chapter E, print the JSON result.

Nothing is written to disk unless --output is given.
"""
import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from .domain.errors import SteelDesignError
from .engine import SteelDesignEngine
from .execution import execute_payload, overall_status
from .input_contracts import unique_json_object
from .sections.loader import load_sections_from_excel
from .sections.repository import SectionRepository


def _error(error: Exception, *, stage: str):
    payload = {"type": error.__class__.__name__, "message": str(error), "stage": stage}
    if isinstance(error, SteelDesignError):
        payload.update(code=error.code, details=error.details)
    if isinstance(error, PydanticValidationError):
        payload.update(code="VALIDATION_ERROR", details={"fields": error.errors(
            include_url=False, include_context=False, include_input=False)})
    print(json.dumps({"error": payload}, indent=2, default=str), file=sys.stderr)
    sys.exit(1)


def main(argv=None):
    parser = argparse.ArgumentParser(description="ANSI/AISC 360-22 Chapter E compression design")
    parser.add_argument("input_file", help="JSON case or bundle")
    parser.add_argument("--sections", default="data/sections.xlsx", help="Section catalog (.xlsx)")
    parser.add_argument("--output", default=None, help="Optional path to also write the JSON result")
    args = parser.parse_args(argv)

    try:
        repository = SectionRepository()
        repository.load(load_sections_from_excel(args.sections))
    except Exception as exc:
        _error(exc, stage="load_sections")
    try:
        payload = json.loads(Path(args.input_file).read_text(encoding="utf-8-sig"), object_pairs_hook=unique_json_object)
    except Exception as exc:
        _error(exc, stage="parse_input")
    try:
        executions = execute_payload(payload, SteelDesignEngine(repository))
    except Exception as exc:
        _error(exc, stage="run_engine")

    if executions[0][0] is None:
        output = executions[0][1].model_dump(mode="json")
    else:
        output = {"status": overall_status([r for _, r in executions]).value,
                  "cases": [{"name": tag, **r.model_dump(mode="json")} for tag, r in executions]}
    text = json.dumps(output, indent=2, allow_nan=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
