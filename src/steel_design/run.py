"""CLI: read a JSON case (or bundle), run the engine, print the JSON result.

Nothing is written to disk unless --output, --report or --pdf is given.
"""
import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from .errors import SteelDesignError
from .execution import (
    execute_payload,
    governing,
    load_engine,
    member_groups,
    overall_status,
)
from .models import unique_json_object
from .reporting.document import report_blocks
from .reporting.pdf import pdf_bytes
from .reporting.text import render_text
from .sections.loader import SECTIONS_CATALOG

DEFAULT_DIR = "results"  # local output folder, ignored by git; never read by the engine
_AUTO = object()


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
    parser = argparse.ArgumentParser(description="Member design per ANSI/AISC 360-22, LRFD")
    parser.add_argument("input_file", help="JSON case or bundle")
    parser.add_argument("--sections", default=SECTIONS_CATALOG, help="Section catalog (.xlsx); by default, the one of the package")
    parser.add_argument("--output", default=None, help="Optional path to also write the JSON result")
    parser.add_argument("--report", nargs="?", const=_AUTO, default=None,
                        help=f"Calculation report (text); without a path: {DEFAULT_DIR}/<input name>.txt")
    parser.add_argument("--pdf", nargs="?", const=_AUTO, default=None,
                        help=f"Calculation report (PDF, needs fpdf2); without a path: {DEFAULT_DIR}/<input name>.pdf")
    args = parser.parse_args(argv)

    try:
        engine = load_engine(args.sections)
    except Exception as exc:
        _error(exc, stage="load_sections")
    try:
        payload = json.loads(Path(args.input_file).read_text(encoding="utf-8-sig"), object_pairs_hook=unique_json_object)
    except Exception as exc:
        _error(exc, stage="parse_input")
    try:
        executions = execute_payload(payload, engine)
    except Exception as exc:
        _error(exc, stage="run_engine")

    if executions[0][0] is None:
        output = executions[0][2].model_dump(mode="json")
    else:
        output = {"status": overall_status([r for _, _, r in executions]).value,
                  "governing": governing(executions),
                  "cases": [{"name": tag, **r.model_dump(mode="json")} for tag, _, r in executions]}
    text = json.dumps(output, indent=2, allow_nan=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    documents = [report_blocks(group) for group in member_groups(executions)]
    try:
        if args.report:
            text_reports = "\n\f\n".join(render_text(blocks) for blocks in documents)
            _target(args.report, args.input_file, ".txt").write_text(text_reports, encoding="utf-8")
        if args.pdf:
            _target(args.pdf, args.input_file, ".pdf").write_bytes(pdf_bytes(documents))
    except Exception as exc:
        _error(exc, stage="write_report")
    print(text)


def _target(option: str, input_file: str, suffix: str) -> Path:
    """Explicit path, or results/<input name><suffix> (git-ignored, created on demand)."""
    path = Path(DEFAULT_DIR, Path(input_file).stem + suffix) if option is _AUTO else Path(option)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


if __name__ == "__main__":
    main()
