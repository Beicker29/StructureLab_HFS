"""Reuse separate-suite capture; accept only documented G/H3 differences.

The underlying legacy comparison intentionally reports inequality. This wrapper
does not hide it: saves the HFS-013 comparison and enforces unrelated invariants.
"""
import argparse
import json
from pathlib import Path

from audit_hfs011 import capture
from compare_hfs013 import compare
from audit_baseline import write_json


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--work", required=True)
    args = parser.parse_args()
    args.extra_suite = ["tests/test_hfs016_catalog_integrity.py", "tests/test_hfs010_coverage.py",
                        "tests/test_hfs012_flexure_selection.py", "tests/test_hfs013_directional_h3.py"]
    capture(args)
    out = Path(args.out)
    before = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    after = json.loads((out / "engine-results.json").read_text(encoding="utf-8"))
    differences = compare(before, after)
    write_json(out / "hfs013-comparison.json", differences)
    verification = json.loads((out / "verification.json").read_text(encoding="utf-8"))
    accepted = (all(v["compatible"] for v in differences.values())
                and all(s["exit"] == 0 for s in verification["suites"].values())
                and verification["source_inputs_unchanged_during_capture"])
    write_json(out / "hfs013-verification.json", {"accepted": accepted, "suites": verification["suites"],
        "identical_examples": verification["examples_identical"],
        "comparison_compatible": all(v["compatible"] for v in differences.values()),
        "numerical_oracle": "tests/test_hfs013_directional_h3.py; comparison is regression evidence only"})
    raise SystemExit(0 if accepted else 1)
