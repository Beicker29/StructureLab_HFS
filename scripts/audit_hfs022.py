"""Preserve HFS-022 before/after evidence and check the authorized source scope.

Run after verify_hfs020 twice. No Git mutations, cleanup, engine calculations,
or replacements of historical evidence. Comparison reuses the exact auditor.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from compare_hfs021 import compare_results
from steel_design import execution, models, results_model
from pydantic import BaseModel

BASE = "c91e55d5a194dfb8e80777d9e41efa1ee4b7fe02"
ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def tree(text):
    return ast.parse(text)


def body(function):
    result = function.body
    return result[1:] if isinstance(result[0], ast.Expr) and isinstance(result[0].value, ast.Constant) else result


def dump(nodes):
    return ast.dump(ast.Module(body=nodes, type_ignores=[]), include_attributes=False)


def function(module, name):
    return next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == name)


def source_proof():
    assert git("branch", "--show-current").decode().strip() == "main"
    assert git("rev-parse", "HEAD").decode().strip() == BASE, "HEAD changed; review before continuing"
    modified = {"src/steel_design/execution.py", "src/steel_design/input_contracts.py", "src/steel_design/run.py"}
    protected = git("ls-files", "src/steel_design", "tests/test_*.py", "data/sections.xlsx",
                    "docs/audit/hfs021b", "docs/audit/hfs017", "docs/contracts/hfs021*").decode().splitlines()
    proof = {}
    for name in protected:
        if name in modified:
            continue
        previous = git("show", f"{BASE}:{name}")
        current = (ROOT / name).read_bytes()
        assert current == previous or current.replace(b"\r\n", b"\n") == previous, name
        proof[name] = {"base_sha256": digest(previous), "checkout_sha256": digest(current)}
    old, new = {}, {}
    for name in modified:
        key = Path(name).stem
        old[key] = tree(git("show", f"{BASE}:{name}").decode())
        new[key] = tree((ROOT / name).read_text(encoding="utf-8"))
    # Preparation is the previous lazy body with only its final yield replaced.
    original = body(function(old["execution"], "iter_executions"))
    prepared = body(function(new["execution"], "prepare_cases"))
    prepared[-1].body[-1] = original[-1].body[-1]
    assert dump(prepared) == dump(original), "Preparation/merge/default/error-order expressions changed"
    old_execution = [n for n in old["execution"].body if not (isinstance(n, ast.FunctionDef) and n.name == "iter_executions")]
    new_execution = [n for n in new["execution"].body if not (isinstance(n, ast.FunctionDef) and n.name in {"iter_executions", "prepare_cases"})]
    assert dump(old_execution) == dump(new_execution), "Unrelated execution helpers changed"
    old_helpers = body(function(old["run"], "_unique_json_object"))
    new_helpers = body(function(new["input_contracts"], "unique_json_object"))
    assert dump(old_helpers) == dump(new_helpers), "Duplicate-key policy changed"
    assert dump(old["input_contracts"].body) == dump(new["input_contracts"].body[:-1])
    old_run = [n for n in old["run"].body if not (isinstance(n, ast.FunctionDef) and n.name == "_unique_json_object")]
    new_run = [n for n in new["run"].body if not (isinstance(n, ast.ImportFrom) and n.module == "input_contracts")]
    assert dump(old_run) == dump(new_run), "CLI changed beyond shared duplicate-key facade"
    return {"base": BASE, "branch": "main", "protected_files": proof,
            "preparation_body_preserved": True, "duplicate_policy_body_preserved": True,
            "cli_other_ast_preserved": True, "new_runtime_module": "steel_design.contracts"}


def inventory():
    fields = {}
    for module in (models, results_model, execution):
        for name, cls in vars(module).items():
            if not isinstance(cls, type) or not issubclass(cls, BaseModel) or cls.__module__ != module.__name__:
                continue
            fields[f"{module.__name__}.{name}"] = {
                "config": dict(cls.model_config),
                "fields": {key: {"annotation": str(field.annotation), "required": field.is_required(),
                    "default": repr(field.default), "factory": getattr(field.default_factory, "__qualname__", None),
                    "alias": repr(field.validation_alias), "description": field.description}
                    for key, field in cls.model_fields.items()},
                "computed_fields": list(cls.model_computed_fields),
                "serializers": list(cls.__pydantic_decorators__.field_serializers)
                    + list(cls.__pydantic_decorators__.model_serializers),
                "validators": list(cls.__pydantic_decorators__.model_validators),
            }
    tokens = ("SteelCase", "CheckResult", "EngineResult", "CoverageReport", "CoverageObligation",
              "ExecutedEvaluation", "OutputOptions", "model_dump", "model_validate", "prepare_cases",
              "iter_executions", "_unique_json_object", "unique_json_object", "json.load", "json.dump")
    names = set(git("ls-files", "src/steel_design/*.py", "scripts/*.py", "tests/test_*.py",
                    "docs/contracts/*.md", "README.md", "CONTRIBUTING.md", "AGENTS.md").decode().splitlines())
    names.update(["src/steel_design/contracts.py", "tests/test_hfs022_contracts.py", "scripts/generate_hfs022_schemas.py"])
    consumers = []
    for name in sorted(names):
        path = ROOT / name
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            hits = [token for token in tokens if token in line]
            if hits:
                consumers.append({"file": name, "line": number, "tokens": hits, "text": line.strip()})
    return {"base": BASE, "models": fields, "consumer_candidates": consumers,
            "scope": "Tracked active sources/tests/scripts/contracts plus new HFS-022 modules; text candidates inspected by responsibility. No claim about inaccessible or external consumers."}


def archive(folder, destination, patterns=None):
    members = {}
    paths = folder.rglob("*") if patterns is None else {p for pattern in patterns for p in folder.glob(pattern)}
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as output:
        for path in sorted(paths):
            if path.is_file():
                name = path.relative_to(folder).as_posix()
                content = path.read_bytes()
                output.writestr(name, content)
                members[name] = {"bytes": len(content), "sha256": digest(content)}
    return {"file": destination.name, "sha256": digest(destination.read_bytes()), "members": members}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "docs/audit/hfs022/evidence")
    parser.add_argument("--intermediate", type=Path)
    parser.add_argument("--development", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    scope = source_proof()
    write(args.out / "scope.json", scope)
    write(args.out / "contracts-consumers.json", inventory())
    write(args.out / "comparison.json", compare_results(args.before.resolve(), args.after.resolve()))
    manifests = {}
    for label, folder in (("before", args.before), ("after", args.after)):
        assert json.loads((folder / "verification.json").read_text())["accepted"]
        manifests[label] = archive(folder, args.out / f"{label}.zip")
    if args.intermediate:
        manifests["intermediate"] = archive(args.intermediate, args.out / "intermediate.zip")
    if args.development:
        manifests["development"] = archive(args.development, args.out / "development.zip",
                                            ["pytest*.log", "pytest*.xml", "development-attempts.json"])
    write(args.out / "archives.json", manifests)
    status = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True)
    write(args.out / "git-status.json", {"command": ["git", "status", "--short"], "exit": status.returncode,
                                        "stdout": status.stdout, "stderr": status.stderr})
    changed = set(git("diff", "--name-only", BASE).decode().splitlines())
    changed.update(git("ls-files", "--others", "--exclude-standard", "docs/audit/hfs022",
                       "docs/contracts/hfs022-versioned-json.md", "docs/schemas/contracts",
                       "src/steel_design/contracts.py", "tests/test_hfs022_contracts.py",
                       "scripts/audit_hfs022.py", "scripts/generate_hfs022_schemas.py").decode().splitlines())
    excluded = {args.out.relative_to(ROOT).as_posix() + "/" + n for n in ("file-inventory.json", "SHA256SUMS.json")}
    write(args.out / "file-inventory.json", {"base": BASE, "changed_or_new_files": sorted(changed | excluded),
          "files": {name: {"bytes": (ROOT / name).stat().st_size, "sha256": digest((ROOT / name).read_bytes())}
                    for name in sorted(changed - excluded) if (ROOT / name).is_file()},
          "self_hash_exclusions": sorted(excluded), "commits_created": False, "pushes_created": False})
    write(args.out / "SHA256SUMS.json", {p.name: digest(p.read_bytes()) for p in sorted(args.out.iterdir())
                                      if p.is_file() and p.name != "SHA256SUMS.json"})
    print("HFS-022: exact regression, protected sources, consumers and recoverable archives recorded")


if __name__ == "__main__":
    main()
