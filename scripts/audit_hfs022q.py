"""HFS-022Q: explicit AST metrics, dependency graph and protected-source evidence.

No runtime imports from steel_design and no new dependency. Metrics are a
declared syntactic convention, not Radon scores or a numerical quality grade.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from audit_hfs022 import archive

ROOT = Path(__file__).resolve().parents[1]
BASE = "449549d9fcc73159d40924b83be988c29ebe196e"
OUT = ROOT / "docs/audit/hfs022/final-quality-review/evidence"
TARGETS = ("contracts", "preparation", "execution", "input_contracts")


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    # Invocation-local support for already tracked long historical paths on
    # Windows; does not change repository/global configuration or permissions.
    return subprocess.check_output(["git", "-c", "core.longpaths=true", *args], cwd=ROOT)


class Decisions(ast.NodeVisitor):
    """Per-function decisions, excluding nested function/class bodies.

    CC = 1 + if/if-expression/for/while/assert/except + short-circuit operands
    beyond the first + comprehension generators/filters. Else/finally/with
    are not new decisions. Nesting counts control constructs, including with
    and try, and comprehension generators/filters; bool operands do not nest.
    """
    def __init__(self):
        self.complexity = 1
        self.depth = 0
        self.maximum_depth = 0

    def visit(self, node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        controls = (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.Try,
                    ast.With, ast.AsyncWith, ast.ExceptHandler)
        decisions = (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.Assert, ast.ExceptHandler)
        self.complexity += int(isinstance(node, decisions))
        if isinstance(node, ast.BoolOp):
            self.complexity += len(node.values) - 1
        increment = int(isinstance(node, controls))
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            increment = sum(1 + len(g.ifs) for g in node.generators)
            self.complexity += increment
        self.depth += increment
        self.maximum_depth = max(self.maximum_depth, self.depth)
        super().visit(node)
        self.depth -= increment


def function_metrics(tree):
    rows = []

    def walk(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visitor = Decisions()
                for statement in child.body:
                    visitor.visit(statement)
                rows.append({"name": prefix + child.name, "line": child.lineno,
                             "lines": child.end_lineno - child.lineno + 1,
                             "complexity": visitor.complexity, "max_control_nesting": visitor.maximum_depth})
                walk(child, prefix + child.name + ".")
            elif isinstance(child, ast.ClassDef):
                walk(child, prefix + child.name + ".")
            else:
                walk(child, prefix)
    walk(tree)
    return rows


def metrics():
    modules = {}
    for path in (ROOT / "src/steel_design").rglob("*.py"):
        name = ".".join(path.relative_to(ROOT / "src").with_suffix("").parts)
        name = name.removesuffix(".__init__")
        modules[name] = (path, ast.parse(path.read_text(encoding="utf-8")))
    graph = {}
    for name, (path, tree) in modules.items():
        dependencies = set()
        package = name if path.name == "__init__.py" else name.rsplit(".", 1)[0]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                dependencies.update(alias.name for alias in node.names if alias.name in modules)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    parts = package.split(".")
                    base = ".".join(parts[:len(parts) - node.level + 1] + ([base] if base else []))
                if base in modules:
                    dependencies.add(base)
                dependencies.update(f"{base}.{alias.name}" for alias in node.names if f"{base}.{alias.name}" in modules)
        graph[name] = sorted(dependencies)
    cycles = set()

    def search(name, stack):
        if name in stack:
            ring = stack[stack.index(name):]
            cycles.add(min(tuple(ring[i:] + ring[:i]) for i in range(len(ring))))
            return
        for target in graph[name]:
            search(target, stack + [name])
    for name in graph:
        search(name, [])
    counts = {}
    for name in TARGETS:
        module = "steel_design." + name
        path, tree = modules[module]
        text = path.read_text(encoding="utf-8")
        counts[module] = {"physical_lines": len(text.splitlines()),
            "nonblank_lines": sum(bool(line.strip()) for line in text.splitlines()),
            "functions": function_metrics(tree), "imports": graph[module],
            "fan_out": len(graph[module]), "fan_in": sum(module in targets for targets in graph.values())}
    write(OUT / "metrics.json", {"convention": Decisions.__doc__, "modules": counts})
    write(OUT / "dependency-graph.json", {"scope": "All local Python imports found by AST, including function-local imports; no claim about arbitrary dynamic imports or third-party package internals.",
         "modules": graph, "cycles": [list(cycle) for cycle in sorted(cycles)]})


def finalize(capture):
    assert git("branch", "--show-current").decode().strip() == "main"
    assert git("rev-parse", "HEAD").decode().strip() == BASE
    protected = git("ls-files", "src", "tests/test_*.py", "docs/audit", "docs/schemas", "data/sections.xlsx").decode().splitlines()
    blobs = {entry.split(b"\t", 1)[1].decode(): entry.split(b"\t", 1)[0].split()[2].decode()
             for entry in git("ls-tree", "-rz", BASE).split(b"\0") if entry}
    proof = {}
    for name in protected:
        old, new = git("cat-file", "blob", blobs[name]), (ROOT / name).read_bytes()
        # Git text=auto can store LF while the Windows checkout has CRLF,
        # including historical JSON. Use Git's configured clean conversion,
        # not a new numerical/JSON/SVG equivalence rule. Preserve both hashes.
        if old != new:
            assert git("hash-object", "--path", name, name).decode().strip() == blobs[name], name
        proof[name] = {"git_sha256": digest(old), "checkout_sha256": digest(new),
                       "byte_identical": old == new, "git_content_identical": True}
    preparation = json.loads((OUT / "preparation.json").read_text(encoding="utf-8"))
    assert preparation["manual_fixture_sha256_before_execution"] == digest((ROOT / "tests/fixtures/hfs022q/manual.json").read_bytes())
    verification = json.loads((capture / "verification.json").read_text())
    assert verification["accepted"]
    wheel, = (capture / "dist").glob("*.whl")
    with zipfile.ZipFile(wheel) as archive_file:
        for name in archive_file.namelist():
            if name.startswith("steel_design/"):
                assert archive_file.read(name) == (ROOT / "src" / name).read_bytes()
    write(OUT / "scope.json", {"base": BASE, "branch": "main", "protected": proof,
          "production_changes": [], "wheel_matches_checkout": True, "manual_expectations_unchanged_since_pre_execution": True})
    write(OUT / "regression.json", verification)
    consumers = {}
    for mode in ("project", "wheel", "editable"):
        process = json.loads((capture / f"independent-consumer-{mode}.json").read_text(encoding="utf-8"))
        assert process["returncode"] == 0
        observed = json.loads(process["stdout"])
        freeze = json.loads((capture / f"freeze-{mode}.json").read_text(encoding="utf-8"))
        assert "jsonschema" not in freeze["stdout"].lower()
        consumers[mode] = {"command": process["command"], "cwd": process["cwd"],
            "guarded_contract_phase": observed["guarded_contract_phase"],
            "contract_modules": observed["contract_modules"], "module_files": observed["module_files"],
            "sys_path": observed["sys_path"], "fixture_sha256": observed["fixture_sha256"],
            "fixture_count": len(observed["fixtures"]), "public_aliases": observed["public_aliases"],
            "prepared_bundle": observed["prepared_bundle"], "jsonschema_absent_from_runtime_install": True}
    write(OUT / "external-consumers.json", consumers)
    # Independent structural decisions against frozen files; Python decisions
    # come from the external wheel consumer, not reconstructed from generators.
    from jsonschema import Draft202012Validator
    specimens = json.loads((ROOT / "tests/fixtures/hfs022q/manual.json").read_bytes())["cases"]
    process = json.loads((capture / "independent-consumer-wheel.json").read_text(encoding="utf-8"))
    assert process["returncode"] == 0
    consumer = json.loads(process["stdout"])
    decisions = {row["id"]: row for row in consumer["fixtures"]}
    matrix = []
    for fixture in specimens:
        raw = json.loads(fixture["json_text"]) if "json_text" in fixture else fixture["document"]
        row = {"id": fixture["id"], "reason": fixture["reason"], "python": decisions[fixture["id"]], "schema": {}}
        assert row["python"]["accepted"] == fixture["python"]
        for mode in ("validation", "serialization"):
            schema = json.loads((ROOT / f"docs/schemas/contracts/1.0/{raw['kind']}.{mode}.json").read_bytes())
            errors = list(Draft202012Validator(schema).iter_errors(raw))
            assert (not errors) == fixture["schema"]
            row["schema"][mode] = {"accepted": not errors, "errors": [{"keyword": error.validator,
                "path": "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in error.absolute_path)
                if error.absolute_path else "", "message": error.message} for error in errors]}
        matrix.append(row)
    write(OUT / "interoperability.json", matrix)
    archives = {"verification": archive(capture, OUT / "verification.zip")}
    development = ROOT / ".venv/22q-work"
    archives["development"] = archive(development, OUT / "development.zip", ["*.json", "*.log", "*.xml"])
    write(OUT / "archives.json", archives)
    paths = set(git("diff", "--name-only", BASE).decode().splitlines())
    paths.update(git("ls-files", "--others", "--exclude-standard", "docs/audit/hfs022/final-quality-review",
                    "scripts/audit_hfs022q.py", "scripts/probe_hfs022q_consumer.py", "tests/test_hfs022q_independent.py",
                    "tests/fixtures/hfs022q").decode().splitlines())
    own = {OUT.relative_to(ROOT).as_posix() + "/" + name for name in ("file-inventory.json", "SHA256SUMS.json")}
    write(OUT / "file-inventory.json", {"base": BASE, "paths": sorted(paths | own),
          "sha256": {name: digest((ROOT / name).read_bytes()) for name in sorted(paths - own)}, "self_exclusions": sorted(own)})
    write(OUT / "SHA256SUMS.json", {path.name: digest(path.read_bytes()) for path in sorted(OUT.iterdir()) if path.is_file() and path.name != "SHA256SUMS.json"})
    print("HFS-022Q: sources, history, expectations, wheel and archives verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path)
    args = parser.parse_args()
    metrics()
    if args.capture:
        finalize(args.capture.resolve())
