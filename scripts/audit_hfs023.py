"""Validate and render the descriptive registry; no engineering calculations.

python scripts/audit_hfs023.py --check
python scripts/audit_hfs023.py --out NEW_DIRECTORY
Without --check, refresh only the derived implementation index (not HFS-002).
"""
import argparse
import ast
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import re
import subprocess

from steel_design.domain.routing.profile_router import RULE_DEFINITIONS, PROFILE_RULE_MAP
from steel_design.domain.routing.registry_metadata import MATRIX, SOURCE_INDEX, METHOD_POLICY, validate_registry

ROOT = Path(__file__).resolve().parents[1]
INDEX = Path("docs/aisc_360_22_traceability.md")
BASE = "1b170929374bd590292ce3f5a17fca1e65bb79ce"


def symbol(value):
    return f"{value.__module__}:{value.__qualname__}" if value is not None else None


def resolve_reference(reference):
    """Audit only: resolve explicit canonical paths, never register plugins."""
    module, separator, name = reference.partition(":")
    if not module.startswith("steel_design."):
        raise ValueError(f"Noncanonical Python reference: {reference}")
    try:
        value = importlib.import_module(module)
        if separator:
            for component in name.split("."):
                value = getattr(value, component)
    except (ImportError, AttributeError) as error:
        raise ValueError(f"Unresolved Python reference: {reference}") from error
    return value


def validate_test_reference(root, reference):
    path, *nodes = reference.split("::")
    file = (root / path).resolve()
    if not file.is_relative_to(root.resolve()) or not path.startswith("tests/test_") or not file.is_file():
        raise ValueError(f"Missing/non-test reference: {reference}")
    body = ast.parse(file.read_text(encoding="utf-8")).body
    for node in nodes:
        matches = [n for n in body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name == node]
        if len(matches) != 1:
            raise ValueError(f"Missing test node: {reference}")
        body = matches[0].body


def validate_references(root, definitions):
    """Integrity != normative approval. Resolve existing evidence, not its truth."""
    matrix = (root / MATRIX).read_text(encoding="utf-8")
    tracking = (root / "docs/audit/tracking.md").read_text(encoding="utf-8")
    sources = (root / SOURCE_INDEX).read_text(encoding="utf-8")
    matrix_ids = set(re.findall(r"^\| (N\d{2}) \|", matrix, re.M))
    finding_ids = set(re.findall(r"^\| (F-\d+) \|", tracking, re.M))
    source_ids = set(re.findall(r"^\| (S22|UN22|C22) \|", sources, re.M))
    chapters = {"tension_rule": "D", "axial_rules": "E", "flexure_rule": "F",
                "shear_rules": "G", "combined_hss_rules": "H", "composite_rules": "I"}
    resolve_reference(METHOD_POLICY)
    for definition in definitions:
        data = definition.metadata
        if not set(data.matrix_ids) <= matrix_ids:
            raise ValueError(f"{definition.rule_id}: unknown matrix reference")
        if not set(data.findings) <= finding_ids:
            raise ValueError(f"{definition.rule_id}: unknown finding")
        if not {c.source for c in data.citations} <= source_ids:
            raise ValueError(f"{definition.rule_id}: unknown source")
        for reference in (*data.software_tests, *data.independent_tests):
            validate_test_reference(root, reference)
        for reference in (*data.calculation_refs, data.selection_ref):
            resolve_reference(reference)
        if definition.rule_class:
            cls = definition.rule_class
            if resolve_reference(symbol(cls)) is not cls:
                raise ValueError(f"{definition.rule_id}: noncanonical class identity")
            owner = cls.__module__.rsplit(".", 1)[1]
            if chapters.get(owner) != data.citations[0].chapter:
                raise ValueError(f"{definition.rule_id}: chapter/implementation owner conflict")


def registry_records():
    return {key: {
        "rule_id": definition.rule_id, "implementation": symbol(definition.rule_class),
        "check_owner": symbol(definition.rule_class.check) if definition.rule_class else None,
        "implemented_class_exists": definition.implemented,
        "runtime_predicate": symbol(definition.applicability),
        "routed_profiles": [p for p, ids in PROFILE_RULE_MAP.items() if key in ids],
        "legacy_required_fields": list(definition.required_section_fields),
        "metadata": definition.metadata.model_dump(mode="json"),
    } for key, definition in RULE_DEFINITIONS.items()}


def render_index():
    lines = ["# AISC 360-22 — Índice de implementación derivado (HFS-023)", "",
             "Generado por `python scripts/audit_hfs023.py`; no editar esta tabla a mano.",
             "La autoridad de metadatos es `RuleDefinition.metadata` en `RULE_DEFINITIONS`.",
             "La [matriz independiente HFS-002](normative/hfs002-applicability.md) no se genera desde el código.",
             "Referencias de software y oráculos acotados no acreditan toda una disposición.",
             "Todas las entradas conservan `NOT_ACCREDITED`; F-31 sigue P0 abierto.",
             "[Contrato, semántica y límites](contracts/hfs023-normative-registry.md).", "",
             "El [índice manual anterior](audit/hfs023/evidence/legacy-traceability.md) queda preservado como evidencia.",
             "Los rangos de ecuaciones son localizadores de la disposición; no una correspondencia validada con cada etiqueta legacy.", "",
             "| ID estable | Fuente / disposición / ecuaciones | N-ID | Implementación responsable | Estado de implementación | Evidencia independiente acotada | F-ID |",
             "|---|---|---|---|---|---|---|"]
    for key, record in registry_records().items():
        data = record["metadata"]
        cites = "; ".join(f"{c['source']} {c['provision']} (PDF {c['pdf_pages']}); eq: {', '.join(c['equations']) or 'ver nota / pendiente'}" for c in data["citations"])
        owner = record["implementation"] or "Sin clase de check; ver condición/documentación"
        independent = "; ".join(data["independent_tests"]) or "No identificada para toda la disposición"
        values = [key, cites, ", ".join(data["matrix_ids"]), owner, data["implementation_state"], independent, ", ".join(data["findings"])]
        lines.append("| " + " | ".join(v.replace("|", "\\|").replace("\n", " ") for v in values) + " |")
    return "\n".join(lines) + "\n"


def source_proof(root):
    """Protect all original logic and the original 56 bindings/maps by AST/bytes."""
    baseline = json.loads((root / "docs/audit/hfs023/evidence/before-inventory.json").read_text(encoding="utf-8"))
    router = "src/steel_design/domain/routing/profile_router.py"
    changed = []
    for path, expected in baseline["protected_sha256"].items():
        original = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=root)
        forms = {hashlib.sha256(original).hexdigest()}
        if Path(path).suffix in {".py", ".json"}:
            lf = original.replace(b"\r\n", b"\n")
            forms.update(hashlib.sha256(data).hexdigest() for data in (lf, lf.replace(b"\n", b"\r\n")))
        assert expected in forms, (path, "historical bytes not tied to Git base")
        actual = hashlib.sha256((root / path).read_bytes()).hexdigest()
        if actual not in forms:
            changed.append(path)
    if changed != [router]:
        raise AssertionError(("Unexpected protected changes", changed))
    before = ast.parse(subprocess.check_output(["git", "show", f"{BASE}:{router}"], cwd=root).decode())
    after = ast.parse((root / router).read_text(encoding="utf-8"))
    protected = []
    for node in before.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_has_interaction":
            assert ast.dump(node.body[0]) == ast.dump(ast.Return(value=ast.Constant(value=False)))
            assert not any(isinstance(n, ast.Name) and n.id == node.name for n in ast.walk(after))
            continue
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name != "RuleDefinition":
            counterpart = next(n for n in after.body if isinstance(n, type(node)) and n.name == node.name)
        elif isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "RULE_DEFINITIONS":
            counterpart = next(n for n in after.body if isinstance(n, ast.AnnAssign) and getattr(n.target, "id", None) == "RULE_DEFINITIONS")
            # The sole permitted baseline-binding change: retire the unused
            # always-False predicate of I2; retain its descriptive stable ID.
            i2 = node.value.values[[k.value for k in node.value.keys].index("I2")]
            assert isinstance(i2.args[-1], ast.Name) and i2.args[-1].id == "_has_interaction"
            i2.args[-1] = ast.Constant(value=None)
        elif isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "PROFILE_RULE_MAP" for t in node.targets):
            counterpart = next(n for n in after.body if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "PROFILE_RULE_MAP" for t in n.targets))
        else:
            continue
        assert ast.dump(node) == ast.dump(counterpart), getattr(node, "name", ast.dump(node)[:60])
        protected.append(getattr(node, "name", "registry/map assignment"))
    return {"base": BASE, "protected_files": len(baseline["protected_sha256"]),
            "byte_policy": "Git base bytes or exact LF/CRLF text representation; binary files exact; raw historical SHA retained",
            "only_changed_original": router, "unchanged_ast": protected,
            "removed_dead_symbol": "_has_interaction (unused I2 placeholder only, constant False)",
            "new_production_files": ["src/steel_design/domain/routing/registry_metadata.py"]}


def class_inventory(root):
    """Include inherited implementations and live dynamic consumers (HFS-017)."""
    rows = []
    registered = [d.rule_class for d in RULE_DEFINITIONS.values() if d.rule_class]
    for module_name in ("tension_rule", "axial_rules", "flexure_rule", "shear_rules", "combined_hss_rules", "composite_rules"):
        module = importlib.import_module("steel_design.domain.rules." + module_name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__ or not hasattr(cls, "check"):
                continue
            ids = [k for k, d in RULE_DEFINITIONS.items() if d.rule_class is cls]
            related = [symbol(c) for c in registered if issubclass(c, cls) or issubclass(cls, c)]
            consumers = []
            for folder in ("src", "scripts", "tests"):
                paths = (root/folder).rglob("*.py") if folder == "src" else (root/folder).glob("*.py")
                for path in paths:
                    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                        if re.search(r"\b" + re.escape(cls.__name__) + r"\b", line) and not line.lstrip().startswith("class "):
                            consumers.append(f"{path.relative_to(root).as_posix()}:{number}")
            rows.append({"symbol": symbol(cls), "check_owner": symbol(cls.check), "registry_ids": ids,
                         "related_registered_classes": related, "textual_references": consumers,
                         "dynamic_consumer": "tests/test_hfs017_design_method.py::rule_classes",
                         "decision": "Preserve: implementation/inheritance or live direct-method-guard consumer; not replaced by metadata"})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    validate_registry(RULE_DEFINITIONS.values(), PROFILE_RULE_MAP)
    validate_references(ROOT, RULE_DEFINITIONS.values())
    rendered = render_index()
    if args.check:
        if (ROOT/INDEX).read_text(encoding="utf-8") != rendered:
            raise SystemExit("Derived implementation index is stale")
    else:
        (ROOT/INDEX).write_text(rendered, encoding="utf-8", newline="\n")
    if args.out:
        args.out.mkdir(parents=True, exist_ok=False)
        for name, value in (("registry.json", registry_records()), ("source-proof.json", source_proof(ROOT)),
                            ("class-consumers.json", class_inventory(ROOT))):
            (args.out/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n", encoding="utf-8", newline="\n")
    print(f"HFS-023: {len(RULE_DEFINITIONS)} entries; integrity checked; no normative accreditation")


if __name__ == "__main__":
    main()
