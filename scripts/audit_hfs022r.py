"""HFS-022R evidence: installed snapshots, exact regression and protected-source audit.

Uses the existing archive/comparison functions. No Git mutations, cleanup,
normative calculations or rewrites of accepted historical evidence.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from audit_hfs022 import archive
from compare_hfs021 import compare_results

ROOT = Path(__file__).resolve().parents[1]
BASE = "bae64633751ae96bd9780ce626045f2da0c66cc9"
OUT = ROOT / "docs/audit/hfs022/architecture-review/evidence"
MOVED = {"OutputOptions", "merge_case_payload", "extract_output_options", "validate_bundle_shape", "prepare_cases"}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def capture(python, cwd, destination):
    """Run against an installed interpreter; only fixture helpers come from tests."""
    probes = {
        "imports": "import sys,json; import steel_design.contracts; print(json.dumps(sorted(n for n in sys.modules if n.startswith('steel_design'))))",
        "contracts": '''
import inspect,json,sys
from pathlib import Path
sys.path.insert(0,'tests')
from test_hfs022_contracts import document
from steel_design import contracts,execution
out={'documents':{},'signatures':{},'owners':{}}
for name in ['OutputOptions','merge_case_payload','extract_output_options','validate_bundle_shape','prepare_cases']:
    value=getattr(execution,name)
    out['signatures'][name]=str(inspect.signature(value))
    out['owners'][name]=value.__module__
for kind in contracts.CONTRACT_KINDS:
    out['documents'][kind]=contracts.dump_json(document(kind))
for path in sorted(Path('examples').glob('*.json')):
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    kind='case_bundle' if 'cases' in data else 'case_input'
    out['documents'][path.name]=contracts.dump_json(contracts.migrate_legacy(data,kind=kind))
history=json.loads(Path('docs/audit/hfs017/evidence/after/engine-results.json').read_text())
for name,rows in history.items():
    for index,row in enumerate(rows):
        data=row['result']
        if 'error' in data:
            try:
                contracts.migrate_legacy(data,kind='engine_result')
            except contracts.ContractError as exc:
                out['documents'][f'{name}/{index}/error']=exc.code
            else:
                raise AssertionError('Historical execution error accepted')
        else:
            out['documents'][f'{name}/{index}/result']=contracts.dump_json(contracts.migrate_legacy(data,kind='engine_result'))
print(json.dumps(out))
''',
    }
    results = {}
    for name, code in probes.items():
        command = [str(python), "-I", "-B", "-c", code]
        run = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=120)
        results[name] = {"command": command, "cwd": str(cwd), "exit": run.returncode,
                         "stdout": run.stdout, "stderr": run.stderr}
        assert run.returncode == 0, results[name]
    write(destination, results)


def source_proof():
    assert git("branch", "--show-current").decode().strip() == "main"
    assert git("rev-parse", "HEAD").decode().strip() == BASE
    protected = git("ls-files", "src/steel_design", "tests/test_*.py", "docs/schemas/contracts",
                    "docs/audit/hfs022", "data/sections.xlsx").decode().splitlines()
    proofs = {}
    for name in protected:
        if name in {"src/steel_design/contracts.py", "src/steel_design/execution.py"}:
            continue
        old, current = git("show", f"{BASE}:{name}"), (ROOT / name).read_bytes()
        assert old == current or old == current.replace(b"\r\n", b"\n"), name
        proofs[name] = {"base_sha256": digest(old), "checkout_sha256": digest(current)}
    old = ast.parse(git("show", f"{BASE}:src/steel_design/execution.py").decode())
    new = ast.parse((ROOT / "src/steel_design/execution.py").read_text(encoding="utf-8"))
    preparation = ast.parse((ROOT / "src/steel_design/preparation.py").read_text(encoding="utf-8"))
    def functions(module):
        return {node.name: node for node in module.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    old_functions, new_functions, moved = functions(old), functions(new), functions(preparation)
    assert set(moved) == MOVED
    assert set(new_functions) == set(old_functions) - MOVED
    for name, node in old_functions.items():
        target = moved[name] if name in MOVED else new_functions[name]
        assert ast.dump(node) == ast.dump(target), name
    return {"base": BASE, "branch": "main", "protected": proofs,
            "moved_ast_identical": sorted(MOVED), "execution_functions_ast_identical": sorted(new_functions)}


def finalize(before, after, development):
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / "scope.json", source_proof())
    write(OUT / "regression.json", compare_results(before, after))
    snapshots = [json.loads((development / f"snapshot-{label}.json").read_text(encoding="utf-8")) for label in ("before", "after")]
    old, new = [json.loads(snapshot["contracts"]["stdout"]) for snapshot in snapshots]
    assert old["documents"] == new["documents"]
    assert old["signatures"] == new["signatures"]
    errors = sum(name.endswith("/error") for name in old["documents"])
    write(OUT / "contract-comparison.json", {"versioned_documents_exact": len(old["documents"]) - errors,
          "historical_error_codes_identical": errors,
          "signatures_identical": old["signatures"], "owners_before": old["owners"], "owners_after": new["owners"],
          "imports_before": json.loads(snapshots[0]["imports"]["stdout"]),
          "imports_after": json.loads(snapshots[1]["imports"]["stdout"])})
    wheels = {}
    suites = {}
    runtime_dependencies = {}
    for label, directory in (("before", before), ("after", after)):
        verification = json.loads((directory / "verification.json").read_text())
        assert verification["accepted"]
        suites[label] = verification["suites"]
        for mode in ("project", "wheel", "editable"):
            freeze = json.loads((directory / f"freeze-{mode}.json").read_text(encoding="utf-8"))
            assert "jsonschema" not in freeze["stdout"].lower()
            runtime_dependencies[f"{label}/{mode}"] = freeze["stdout"].splitlines()
        wheel, = (directory / "dist").glob("*.whl")
        with zipfile.ZipFile(wheel) as source:
            wheels[label] = {name: source.read(name) for name in source.namelist() if name.startswith("steel_design/")}
    assert all((ROOT / "src" / name).read_bytes() == data for name, data in wheels["after"].items())
    runtime_changes = sorted(name for name in wheels["before"].keys() | wheels["after"].keys()
                             if wheels["before"].get(name) != wheels["after"].get(name))
    assert runtime_changes == ["steel_design/contracts.py", "steel_design/execution.py", "steel_design/preparation.py"]
    write(OUT / "runtime-wheel.json", {"checkout_equals_after_wheel": True, "changed": runtime_changes,
                                       "python_files": len(wheels["after"])})
    write(OUT / "tests.json", suites)
    write(OUT / "runtime-dependencies.json", runtime_dependencies)
    archives = {label: archive(folder, OUT / f"{label}.zip") for label, folder in (("before", before), ("after", after))}
    archives["development"] = archive(development, OUT / "development.zip",
        ["*.json", "*.log", "*.xml"])
    write(OUT / "archives.json", archives)
    paths = set(git("diff", "--name-only", BASE).decode().splitlines())
    paths.update(git("ls-files", "--others", "--exclude-standard", "docs/audit/hfs022/architecture-review",
                     "scripts/audit_hfs022r.py", "tests/test_hfs022r_review.py", "src/steel_design/preparation.py").decode().splitlines())
    own = {OUT.relative_to(ROOT).as_posix() + "/" + name for name in ("file-inventory.json", "SHA256SUMS.json")}
    write(OUT / "file-inventory.json", {"base": BASE, "paths": sorted(paths | own),
        "sha256": {name: digest((ROOT / name).read_bytes()) for name in sorted(paths - own)}, "self_exclusions": sorted(own)})
    write(OUT / "SHA256SUMS.json", {p.name: digest(p.read_bytes()) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "SHA256SUMS.json"})
    print("HFS-022R: protected history, source scope, exact contracts/results and archives verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--python", type=Path)
    parser.add_argument("--cwd", type=Path)
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after", type=Path)
    parser.add_argument("--development", type=Path)
    args = parser.parse_args()
    if args.snapshot:
        capture(args.python.resolve(), args.cwd.resolve(), args.snapshot.resolve())
    else:
        finalize(args.before.resolve(), args.after.resolve(), args.development.resolve())
