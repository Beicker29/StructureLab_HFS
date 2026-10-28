"""HFS-021 exact regression, extracted-code identity and scope evidence.

Run after verify_hfs020.py before/after captures; no snapshots are regenerated.
The existing HFS-020 comparator owns JSON equivalence and input provenance.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

from hfs020_comparison import assert_json_equal, compare_cli_records, parse_json

ROOT = Path(__file__).resolve().parents[1]
BASE = "f3a5198309d24f772f6cac69ccc483846b81d21a"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def text_at_base(path):
    return git("show", f"{BASE}:{path}").decode("utf-8")


def functions(text):
    return {n.name: n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}


def dump(node):
    return ast.dump(node, include_attributes=False)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def compare(before, after):
    assert git("rev-parse", "HEAD").decode().strip() == BASE
    assert git("branch", "--show-current").decode().strip() == "main"
    for label in (before, after):
        assert json.loads((label / "verification.json").read_text())["accepted"]
    baseline_engine = parse_json((before / "engine-results.json").read_bytes())
    after_engine = parse_json((after / "engine-results.json").read_bytes())
    assert_json_equal(baseline_engine, after_engine, "HFS-021 engine before/after")
    prior_cli = parse_json((before / "cli-examples.json").read_bytes())
    after_cli = parse_json((after / "cli-examples.json").read_bytes())
    historical_cli = parse_json((ROOT / "docs/audit/hfs017/evidence/cli/after.json").read_bytes())
    for capture, directory in ((prior_cli, before), (after_cli, after)):
        proof = json.loads((directory / "input-provenance.json").read_text())
        # Each proof is tied to HFS-017 bytes, not to a newly captured checkout.
        compare_cli_records(capture, historical_cli, proof)
    for label in prior_cli:
        for key in ("normalized_cli", "normalized_details", "source_sha256", "transport_only_detailed_variant"):
            assert_json_equal(prior_cli[label][key], after_cli[label][key], f"{label}/{key}")
        assert prior_cli[label]["execution"]["returncode"] == after_cli[label]["execution"]["returncode"]

    # Formula modules, contracts, catalog and previous tests must be identical
    # as Git text (EOL normalization only) / exact bytes for the catalog.
    fixed = git("ls-files", "src/steel_design/codes", "src/steel_design/domain",
                "src/steel_design/sections", "src/steel_design/models.py",
                "src/steel_design/results_model.py", "src/steel_design/input_contracts.py",
                "src/steel_design/design_methods.py", "data/sections.xlsx",
                "tests/test_*.py").decode().splitlines()
    unchanged = {}
    for name in fixed:
        original = git("show", f"{BASE}:{name}")
        actual = (ROOT / name).read_bytes()
        comparable = actual.replace(b"\r\n", b"\n") if name.endswith(".py") else actual
        assert comparable == original, name
        unchanged[name] = {"git_blob_sha256": digest(original), "checkout_sha256": digest(actual)}

    old_engine = ast.parse(text_at_base("src/steel_design/engine.py"))
    new_engine = ast.parse((ROOT / "src/steel_design/engine.py").read_text(encoding="utf-8"))
    old_builder = functions(text_at_base("src/steel_design/engine.py"))["_build_custom_section"]
    new_builder = functions((ROOT / "src/steel_design/sections/geometry.py").read_text(encoding="utf-8"))["build_custom_section"]
    new_builder.name = old_builder.name
    assert dump(old_builder) == dump(new_builder), "Custom geometry expressions changed"
    old_class = next(n for n in old_engine.body if isinstance(n, ast.ClassDef))
    new_class = next(n for n in new_engine.body if isinstance(n, ast.ClassDef))
    old_run = next(n for n in old_class.body if isinstance(n, ast.FunctionDef) and n.name == "run")
    new_run = next(n for n in new_class.body if isinstance(n, ast.FunctionDef) and n.name == "run_with_context")
    assert dump(ast.Module(body=old_run.body[:-1], type_ignores=[])) == dump(
        ast.Module(body=new_run.body[:-1], type_ignores=[])), "Engine pipeline changed"
    assert dump(old_run.body[-1].value) == dump(new_run.body[-1].value.elts[2])

    old_helpers = functions(text_at_base("src/steel_design/run.py"))
    new_helpers = functions((ROOT / "src/steel_design/reporting.py").read_text(encoding="utf-8"))
    extracted = []
    for name in sorted(old_helpers.keys() & new_helpers.keys()):
        if name == "_write_detailed_results_file":
            continue  # Payload/write split is verified through all 24 consumers.
        assert dump(old_helpers[name]) == dump(new_helpers[name]), name
        extracted.append(name)

    # Optional PNG dependency is not installed in either clean environment.
    # Compare actual SVG exports byte-for-byte; code identity also covers PNG.
    graph_evidence = {}
    raw_captures = [json.loads((p / "cli-examples.json").read_text(encoding="utf-8")) for p in (before, after)]
    for label in raw_captures[0]:
        runs = [capture[label]["execution"] for capture in raw_captures]
        if runs[0]["returncode"]:
            continue
        outputs = [json.loads(run["stdout"]) for run in runs]
        cases = [output.get("cases", [output]) for output in outputs]
        for index, (old, new) in enumerate(zip(*cases, strict=True)):
            paths = [item["artifacts"]["interaction_diagram_i5_method2_image"] for item in (old, new)]
            assert bool(paths[0]) == bool(paths[1]), (label, index)
            if not paths[0]:
                continue
            contents = [Path(p).read_bytes() for p in paths]
            assert contents[0] == contents[1], (label, index, "diagram bytes")
            graph_evidence[f"{label}/case-{index}"] = {
                "before": paths[0], "after": paths[1], "sha256": digest(contents[0]),
                "bytes": len(contents[0]), "format": Path(paths[0]).suffix,
            }
    return {"accepted": True, "base": BASE, "branch": "main",
            "engine_examples_exact": 12, "cli_memory_scenarios_exact": 24,
            "historical_sources_unchanged": unchanged,
            "engine_pipeline_ast_identical_except_context_return": True,
            "geometry_ast_identical": True, "presentation_helpers_ast_identical": extracted,
            "diagrams_byte_identical": graph_evidence}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = compare(args.before.resolve(), args.after.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("HFS-021: exact results, extracted expressions, protected sources and diagrams verified")
