"""In-memory execution of a JSON payload: one case, or a bundle {"cases": [...]} with shared defaults.

No filesystem access; a future web API calls execute_payload directly.
"""
import copy
from typing import cast

from .engine import SteelDesignEngine
from .errors import ValidationError
from .materials import material_by_name
from .models import DesignResult, Status, SteelCase, worst_status
from .sections.loader import SECTIONS_CATALOG, load_sections_from_excel
from .sections.repository import SectionRepository


def load_engine(catalog=SECTIONS_CATALOG) -> SteelDesignEngine:
    """The engine with its section catalog: the one that travels with the package, unless another file is given."""
    repository = SectionRepository()
    repository.load(load_sections_from_excel(catalog))
    return SteelDesignEngine(repository)


def _merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        merged[key] = _merge(merged[key], value) if isinstance(value, dict) and isinstance(merged.get(key), dict) else value
    return merged


def _case(data: dict) -> SteelCase:
    """A JSON input names its material; Fy and Fu come from src/steel_design/data/Materiales.xlsx."""
    if "material" in data:
        data = {**data, "material": material_by_name(data["material"])}
    return SteelCase(**data)


def prepare_cases(payload: dict) -> list[tuple[str | None, SteelCase]]:
    if not isinstance(payload, dict):
        raise ValidationError("La entrada debe ser un objeto JSON.", code="INVALID_INPUT")
    if "cases" not in payload:
        return [(None, _case(payload))]
    cases = payload["cases"]
    if not isinstance(cases, list) or not cases or not all(isinstance(c, dict) for c in cases):
        raise ValidationError("cases debe ser una lista no vacía de objetos.", code="INVALID_CASE_BUNDLE")
    base = {k: v for k, v in payload.items() if k != "cases"}
    return [(str(c.get("name") or f"case_{i + 1}"), _case(_merge(base, {k: v for k, v in c.items() if k != "name"})))
            for i, c in enumerate(cases)]


def execute_payload(payload: dict, engine: SteelDesignEngine) -> list[tuple[str | None, SteelCase, DesignResult]]:
    """Run every case; returns (name or None, validated input case, result)."""
    executions = [(tag, case, engine.run(case)) for tag, case in prepare_cases(payload)]
    for group in member_groups(executions):
        _require_construction_case(group)
    return executions


def member_groups(executions: list) -> list[list]:
    """The cases of each member: one calculation report per section, however many load cases it has."""
    groups: dict[str, list] = {}
    for execution in executions:
        groups.setdefault(execution[1].section_name, []).append(execution)
    return list(groups.values())


def _require_construction_case(group: list) -> None:
    """I3.1b: an unshored composite beam needs a construction case; a single load case cannot know, so the member decides."""
    if any(case.condition == "construction" for _, case, _ in group):
        return
    for _, case, result in group:
        unshored = case.composite and case.composite.kind == "beam" and not case.composite.beam.shored
        check = result.check("flexure_x_3")
        if unshored and case.Mx_3 > 0 and check:                 # positive flexure: the slab is on the +2 face
            check.errors.append({"code": "COMPOSITE_DATA_INCOMPLETE", "provision": "I3.1b",
                                 "message": "Viga sin apuntalar: agregue un case con condition = construction (I3.1b)."})
            if check.status != Status.FAIL:
                check.status = Status.INCOMPLETE
            if result.status != Status.FAIL:
                result.status = Status.INCOMPLETE


def governing(executions: list[tuple[str | None, SteelCase, DesignResult]]) -> dict | None:
    """Load combination and check with the largest demand/capacity ratio among the evaluated checks."""
    rated = [(tag, c) for tag, _, r in executions for c in r.checks if c.ratio is not None]
    if not rated:
        return None
    tag, c = max(rated, key=lambda item: cast(float, item[1].ratio))
    return {"name": tag, "check": c.id, "chapter": c.chapter, "status": c.status.value, "ratio": c.ratio,
            "capacity": c.capacity, "demand": c.demand, "unit": c.unit}


def overall_status(results: list[DesignResult]) -> Status:
    return worst_status(r.status for r in results)
