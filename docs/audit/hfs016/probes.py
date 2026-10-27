"""Reproduce catalog identity observations on a selected checkout.

Run this file with --root pointing to either the frozen before-work copy or the
current checkout. Output must be new. This is software evidence, not AISC QA.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root, out = Path(args.root).resolve(), Path(args.out).resolve()
    if out.exists():
        raise SystemExit("Output exists; choose a new path.")
    sys.path.insert(0, str(root))
    from src.steel_design.sections.loader import load_sections_from_excel
    from src.steel_design.sections.repository import SectionRepository
    from src.steel_design.domain.errors import SteelDesignError

    path = root / "data/sections.xlsx"
    records = load_sections_from_excel(str(path))
    observations = {}
    for label, values in [("forward", records), ("reverse", list(reversed(records)))]:
        repo = SectionRepository()
        repo.load(values)
        selected = {}
        for name in ("HEA 100", "PTEXXMM", "W12X26", "  hea  100 "):
            try:
                value = repo.get(name)
                selected[name] = value.model_dump(mode="json") if value else None
            except SteelDesignError as exc:
                selected[name] = {"error": exc.to_dict()}
        observations[label] = {"get_all_count": len(repo.get_all()), "queries": selected}
    output = {
        "root": str(root), "catalog_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "loaded_records": len(records), "loaded_name_counts": {
            name: count for name, count in Counter(r.name for r in records).items() if count > 1},
        "observations": observations,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"loaded": len(records), "get_all": {k: v["get_all_count"] for k, v in observations.items()}}))


if __name__ == "__main__":
    main()
