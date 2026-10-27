"""Nine separate suites; preserve engine results exactly in HFS-014.

CLI and detailed-memory differences are captured separately by
audit_hfs014_cli.py and checked by compare_hfs014_cli.py.
"""
import argparse

from audit_hfs011 import capture


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--work", required=True)
    args = parser.parse_args()
    args.extra_suite = ["tests/test_hfs016_catalog_integrity.py", "tests/test_hfs010_coverage.py",
        "tests/test_hfs012_flexure_selection.py", "tests/test_hfs013_directional_h3.py",
        "tests/test_hfs013_design_method.py", "tests/test_hfs014_summary_bundle.py"]
    raise SystemExit(capture(args))
