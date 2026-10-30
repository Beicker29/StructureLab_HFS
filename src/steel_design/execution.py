"""In-memory execution of a JSON payload: one case, or a bundle {"cases": [...]} with shared defaults.

No filesystem access; a future web API calls execute_payload directly.
"""
import copy

from .errors import ValidationError
from .engine import SteelDesignEngine
from .models import DesignResult, SteelCase, Status


def _merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        merged[key] = _merge(merged[key], value) if isinstance(value, dict) and isinstance(merged.get(key), dict) else value
    return merged


def prepare_cases(payload: dict) -> list[tuple[str | None, SteelCase]]:
    if not isinstance(payload, dict):
        raise ValidationError("La entrada debe ser un objeto JSON.", code="INVALID_INPUT")
    if "cases" not in payload:
        return [(None, SteelCase(**payload))]
    cases = payload["cases"]
    if not isinstance(cases, list) or not cases or not all(isinstance(c, dict) for c in cases):
        raise ValidationError("cases debe ser una lista no vacía de objetos.", code="INVALID_CASE_BUNDLE")
    base = {k: v for k, v in payload.items() if k != "cases"}
    return [(str(c.get("name") or f"case_{i + 1}"), SteelCase(**_merge(base, {k: v for k, v in c.items() if k != "name"})))
            for i, c in enumerate(cases)]


def execute_payload(payload: dict, engine: SteelDesignEngine) -> list[tuple[str | None, SteelCase, DesignResult]]:
    """Run every case; returns (name or None, validated input case, result)."""
    return [(tag, case, engine.run(case)) for tag, case in prepare_cases(payload)]


def governing(executions: list[tuple[str | None, SteelCase, DesignResult]]) -> dict | None:
    """Load combination with the largest demand/capacity ratio among those with a strength."""
    rated = [(tag, r) for tag, _, r in executions if r.ratio is not None]
    if not rated:
        return None
    tag, r = max(rated, key=lambda item: item[1].ratio)
    return {"name": tag, "chapter": r.chapter, "status": r.status.value, "ratio": r.ratio,
            "capacity_kN": r.capacity_kN, "demand_kN": r.demand_kN}


def overall_status(results: list[DesignResult]) -> Status:
    statuses = {r.status for r in results}
    if Status.INCOMPLETE in statuses:
        return Status.INCOMPLETE
    return Status.FAIL if Status.FAIL in statuses else Status.PASS
