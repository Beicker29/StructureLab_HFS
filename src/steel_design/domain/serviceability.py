"""Deflections that the user declares against the limits L/n. Chapter L gives no numeric limits, so they do not decide the status."""
from ..models import Serviceability

NAMES = (("live_short", "Carga viva a corto plazo"), ("dead_short", "Carga muerta a corto plazo"),
         ("total_long", "Carga viva + muerta a largo plazo"))


def deflection_checks(basis: Serviceability | None) -> list[dict]:
    if basis is None:
        return []
    rows = []
    for key, name in NAMES:
        value, divisor = getattr(basis.deflections, key), getattr(basis.limit_divisors, key)
        limit = basis.effective_span / divisor
        rows.append({"id": key, "description": name, "value_mm": value, "divisor": divisor, "limit_mm": limit, "satisfied": value <= limit})
    return rows
