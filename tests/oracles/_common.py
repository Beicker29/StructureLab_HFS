"""Helpers shared by the independent oracles. They never import steel_design."""
from decimal import Decimal as D


def _plain(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def sqrt(x):
    return x.sqrt()
