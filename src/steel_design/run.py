import json
import argparse
import sys
from pathlib import Path

from .models import SteelCase
from .engine import SteelDesignEngine
from .sections.loader import load_sections_from_excel
from .sections.repository import SectionRepository
from .domain.errors import SteelDesignError

def main():
    parser = argparse.ArgumentParser(description="AISC 360-22 Steel Design Engine CLI")
    parser.add_argument("input_file", type=str, help="Path to the JSON input case file.")
    parser.add_argument("--sections", type=str, default="data/sections.xlsx", help="Path to the sections Excel file.")
    args = parser.parse_args()

    # Load sections
    try:
        sections = load_sections_from_excel(args.sections)
    except Exception as e:
        print(f"Error loading sections: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Init repository
    repo = SectionRepository()
    repo.load(sections)
    
    # Init Engine
    engine = SteelDesignEngine(repository=repo)
    
    # Read input payload
    try:
        with open(args.input_file, "r") as f:
            payload = json.load(f)
            case = SteelCase(**payload)
    except Exception as e:
        print(f"Error parsing input file: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Run
    try:
        result = engine.run(case)
        print(result.model_dump_json(indent=2))
        
    except SteelDesignError as e:
        print(f"Design Engine Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
