"""Reproduce HFS-010 critical omissions against a selected checkout, no edits."""
import argparse
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
        raise SystemExit("Choose a new evidence path.")
    sys.path.insert(0, str(root))
    from src.steel_design.engine import SteelDesignEngine
    from src.steel_design.models import SteelCase
    from src.steel_design.sections.loader import load_sections_from_excel
    from src.steel_design.sections.repository import SectionRepository
    records = load_sections_from_excel(str(root / "data/sections.xlsx"))
    repo = SectionRepository()
    repo.load(records)
    captures = []
    common = dict(section_name="W12X26", material=dict(Fy=345, Fu=450),
                  lengths=dict(Lx=1000, Ly=1000, Lz=1000, Lb=1000))
    jobs = [
        ("F-01", dict(common, loads=dict(Pu=1, Mux=1)), {}),
        ("F-02", dict(common, loads=dict(Pu=0)), {}),
        ("F-03", dict(common, loads=dict(Mux=1)), dict(bf_2tf_ratio=None, h_tw_ratio=None)),
        ("F-31", dict(common, loads=dict(Mux=1, Muy=1)), dict(type="CHANNEL", bf_2tf_ratio=50, h_tw_ratio=300)),
        ("F-33", dict(common, loads=dict(Mux=1, Muy=1)), {}),
        ("F-35", dict(common, loads=dict(Pu=1)), dict(bf_2tf_ratio=100, h_tw_ratio=300)),
    ]
    for finding, name, demands in [
        ("F-36", "single_angle", [dict(Pu=1)]),
        ("F-06", "rectangular_hss", [None]),
        *[("F-34", name, [dict(Mux=1), dict(Mux=1000000)])
          for name in ("composite_encased", "composite_filled_rectangular_hss", "composite_beam")],
    ]:
        original = json.loads((root / "examples" / f"{name}_case.json").read_text(encoding="utf-8-sig"))
        original.pop("output", None)
        for loads in demands:
            jobs.append((finding, dict(original, loads=loads or original["loads"]), {}))
    for finding, payload, overrides in jobs:
        selected_repo = repo
        if overrides:
            selected_repo = SectionRepository()
            selected_repo.load([repo.get("W12X26").model_copy(update=overrides)])
        try:
            result = SteelDesignEngine(selected_repo).run(SteelCase(**payload)).model_dump(mode="json")
        except Exception as exc:
            result = {"error": {"type": type(exc).__name__, "message": str(exc)}}
        captures.append(dict(finding=finding, input=payload, synthetic_section_overrides=overrides, result=result))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(root=str(root), catalog_sha256=hashlib.sha256((root / "data/sections.xlsx").read_bytes()).hexdigest(),
                                   scope="Behavioral reproduction; not normative capacity validation", captures=captures),
                              indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps([dict(finding=c["finding"], status=c["result"].get("status", "ERROR")) for c in captures]))


if __name__ == "__main__":
    main()
