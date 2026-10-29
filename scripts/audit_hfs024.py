"""HFS-024 execution capture and structural proof; no normative inference.

--probe needs an installed package and explicit input root (also outside checkout).
--source-proof compares code against the published HFS-023 base using Git.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

BASE = "93e4f8cd523148c8cb3ccff1d94caafb4cfa8af1"
ROOT = Path(__file__).resolve().parents[1]


class WithoutObservations(ast.NodeTransformer):
    """Remove only the declared instrumentation, preserving arithmetic/order."""

    def visit_ImportFrom(self, node):
        return None if node.module == "tracing" else node

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            if node.value.func.id in {"emit_step", "record_analysis"}:
                return None
        return self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == "observed_value":
            assert len(node.args) == 1
            return self.visit(node.args[0])
        return self.generic_visit(node)

    def visit_Assign(self, node):
        # Only the three H1 explanatory string assignments, no arithmetic.
        if (len(node.targets) == 1 and isinstance(node.targets[0], ast.Tuple)
                and [getattr(n, "id", None) for n in node.targets[0].elts] == ["equation", "expression"]):
            assert isinstance(node.value, ast.Tuple)
            assert all(isinstance(v, ast.Constant) and (v.value is None or isinstance(v.value, str)) for v in node.value.elts)
            return None
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.name == "calculation_trace_document":
            return None  # new opt-in export; existing reporting functions compared intact
        node.decorator_list = [d for d in node.decorator_list if not (isinstance(d, ast.Name) and d.id == "traced_rule")]
        if node.name == "run_with_context":
            assignments = [s for s in node.body if isinstance(s, ast.Assign) and len(s.targets) == 1
                           and isinstance(s.targets[0], ast.Name) and s.targets[0].id == "result"
                           and isinstance(s.value, ast.Call) and isinstance(s.value.func, ast.Name)
                           and s.value.func.id == "EngineResult"]
            if assignments:
                assignment, = assignments
                ret = node.body[-1]
                assert isinstance(ret, ast.Return) and isinstance(ret.value, ast.Tuple)
                assert [getattr(e, "id", None) for e in ret.value.elts] == ["case", "section", "result"]
                ret.value.elts[-1] = assignment.value
                node.body.remove(assignment)
        return self.generic_visit(node)


def structural_text(source):
    return ast.dump(WithoutObservations().visit(ast.parse(source)), include_attributes=False)


def source_proof():
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT)
    paths = git("ls-tree", "-r", "--name-only", BASE, "src/steel_design").decode().splitlines()
    proof = {}
    for relative in paths:
        if not relative.endswith(".py"):
            continue
        before = git("show", f"{BASE}:{relative}").decode("utf8")
        after = (ROOT / relative).read_text(encoding="utf8")
        equal = structural_text(before) == structural_text(after)
        proof[relative] = {"arithmetic_control_flow_preserved": equal,
            "base_sha256": hashlib.sha256(before.encode()).hexdigest(),
            "working_lf_sha256": hashlib.sha256(after.encode()).hexdigest()}
    assert all(r["arithmetic_control_flow_preserved"] for r in proof.values()), [p for p, r in proof.items() if not r["arithmetic_control_flow_preserved"]]
    return {"base": BASE, "method": "AST minus explicitly enumerated observation-only nodes; not numeric validation",
            "files": proof}


def probe(root):
    from steel_design.engine import SteelDesignEngine
    from steel_design.models import SteelCase
    from steel_design.sections.repository import SectionRepository
    from steel_design.sections.loader import load_sections_from_excel
    from steel_design.tracing import capture_trace
    from steel_design.reporting import calculation_trace_document
    from steel_design.domain.routing.profile_router import RULE_DEFINITIONS

    repo = SectionRepository()
    repo.load(load_sections_from_excel(str(root / "data/sections.xlsx")))
    engine = SteelDesignEngine(repo)
    records = {}
    for path in sorted((root / "examples").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        data.pop("output", None)
        case = SteelCase(**data)
        error = None
        try:
            before = engine.run(case).model_dump(mode="json")
        except Exception as exc:
            error = exc
            before = None
        try:
            with capture_trace(provenance={"input": path.name, "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}) as capture:
                after = engine.run(case).model_dump(mode="json")
        except Exception as exc:
            assert error is not None and type(exc) is type(error) and str(exc) == str(error)
            after = None
        else:
            assert error is None
        assert before == after, path.name
        records[path.name] = {"identical_result": True, "result": after,
                              "trace": calculation_trace_document(capture.snapshot())}
    assert len(records) == 12
    observed = {}
    for record in records.values():
        for event in record["trace"]["evaluations"]:
            observed.setdefault(event["rule_id"], set()).update(step["producer"] for step in event["steps"])
    inventory = [{"rule_id": rid, "implementation": (r.rule_class.__module__+":"+r.rule_class.__name__) if r.rule_class else None,
                  "boundary_instrumented": bool(r.rule_class and hasattr(r.rule_class.check, "__wrapped__")),
                  "seen_in_examples": rid in observed, "step_producers_seen": sorted(observed.get(rid, ())),
                  "pending": "Complete branch/variable provenance not established" if r.rule_class else "No executable rule to trace",
                  "normative_validation": r.metadata.normative_validation}
                 for rid, r in RULE_DEFINITIONS.items()]
    return {"examples": records, "registry_inventory": inventory}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path)
    parser.add_argument("--source-proof", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("Use a new evidence file")
    if bool(args.probe) == args.source_proof:
        raise SystemExit("Choose exactly one of --probe or --source-proof")
    data = probe(args.probe.resolve()) if args.probe else source_proof()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf8")
    print("Execution/structure evidence recorded; no new normative accreditation.")
