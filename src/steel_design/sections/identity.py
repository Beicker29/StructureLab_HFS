"""Catalog identity, shared by import and repository lookup.

Only ASCII letter case and ASCII whitespace are presentation differences.
Separators, units, punctuation and all non-ASCII characters remain significant.
"""
import re

from ..domain.errors import ValidationError

_UPPER_ASCII = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_SPACE = re.compile(r"[ \t\r\n\f\v]+")


def section_identity(name: str) -> str:
    if not isinstance(name, str):
        raise ValidationError("Section name must be a string.", details={"field": "section_name"})
    identity = _SPACE.sub(" ", name).strip(" ").translate(_UPPER_ASCII)
    if not identity:
        raise ValidationError("Section name must not be blank.", details={"field": "section_name"})
    return identity
