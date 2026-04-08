import json
import argparse
import sys

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


def main():
    parser = argparse.ArgumentParser(description="AISC 360-22 Steel Design Engine CLI")
    parser.add_argument("input_file", type=str, help="Path to the JSON input case file.")
    parser.add_argument("--sections", type=str, default="data/sections.xlsx", help="Path to the sections Excel file.")
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
        print(result.model_dump_json(indent=2))
        
    except Exception as e:
        _print_structured_error(e, stage="run_engine")
        sys.exit(1)

if __name__ == "__main__":
    main()
