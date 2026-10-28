"""Verify package migration without changing historical expectations or tolerances."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from compare_hfs021 import compare_results
from hfs021a_invariants import assert_import_migration_only, assert_trace_identifier_compatibility_only

BASE = "39a7614a413a06eef78f597e142f7ba0e889c123"
ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def compare(before, after):
    regression = compare_results(before, after)
    names = git("ls-tree", "-r", "--name-only", BASE).decode().splitlines()
    proof = {}
    for name in names:
        runtime = name.startswith("src/steel_design/") and name.endswith(".py")
        test = name.startswith("tests/test_") and name.endswith(".py")
        protected = (name.startswith("examples/") and name.endswith(".json")) or name in (
            "data/sections.xlsx", "scripts/hfs020_comparison.py")
        if not (runtime or test or protected):
            continue
        original = git("show", f"{BASE}:{name}")
        actual = (ROOT / name).read_bytes()
        if name == "src/steel_design/domain/coverage_evidence.py":
            assert_trace_identifier_compatibility_only(original.decode("utf-8"), actual.decode("utf-8"))
            mode = "full_AST_with_historical_identifier_adapter_only"
        elif test:
            assert_import_migration_only(original.decode("utf-8"), actual.decode("utf-8"))
            mode = "full_AST_with_package_prefix_only"
        else:
            normalized = actual.replace(b"\r\n", b"\n") if name.endswith((".py", ".json")) else actual
            assert normalized == original, name
            mode = "identical_bytes_except_checkout_EOL" if name.endswith((".py", ".json")) else "identical_bytes"
        proof[name] = {"comparison": mode, "base_sha256": hashlib.sha256(original).hexdigest(),
                       "working_sha256": hashlib.sha256(actual).hexdigest()}
    changed = git("diff", "--name-only", BASE).decode().splitlines()
    assert not any(name in names and name.startswith(("docs/audit/", "docs/contracts/", "docs/adr/", "docs/normative/"))
                   for name in changed), "Historical evidence or contracts changed"
    return {"accepted": True, "base": BASE, "head": git("rev-parse", "HEAD").decode().strip(),
            **regression, "protected_sources": proof, "historical_documents_unchanged": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = compare(args.before.resolve(), args.after.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("HFS-021A: exact results, SVGs, engineering code and historical oracles preserved")
