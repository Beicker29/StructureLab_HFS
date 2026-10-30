"""Catalog identity, shared by import and repository lookup.

Only ASCII letter case and ASCII whitespace are presentation differences.
Separators, units, punctuation and all non-ASCII characters remain significant.
"""
import re

from ..errors import ValidationError

_UPPER_ASCII = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_SPACE = re.compile(r"[ \t\r\n\f\v]+")


def section_identity(name: str) -> str:
    if not isinstance(name, str):
        raise ValidationError("Section name must be a string.", details={"field": "section_name"})
    identity = _SPACE.sub(" ", name).strip(" ").translate(_UPPER_ASCII)
    if not identity:
        raise ValidationError("Section name must not be blank.", details={"field": "section_name"})
    return identity


_DOUBLE_ANGLE = re.compile(r"^2L(?P<a>[^X]+)X(?P<b>[^X]+)X(?P<t>[^X]+?)(?:X(?P<gap>[^X]+?))?(?P<config>LLBB|SLBB)?$")


def double_angle_label(name: str) -> dict:
    """Read an AISC_Manual_Label such as 2L4X4X1/4, 2L4X4X1/4X3/4 or 2L8X4X1/2X3/8LLBB.

    The optional fourth dimension is the back-to-back separation; without it
    the angles are in continuous contact. Returns the single-angle component name.
    """
    match = _DOUBLE_ANGLE.match(section_identity(name))
    if match is None:
        raise ValidationError("Not a double-angle AISC_Manual_Label.", details={"section": name})
    return {"component": f"L{match['a']}X{match['b']}X{match['t']}", "separation": match["gap"],
            "in_contact": match["gap"] is None, "configuration": match["config"]}
