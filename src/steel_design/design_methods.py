"""Design-method identifiers only; factors remain with their AISC provision."""
from enum import Enum


class DesignMethod(str, Enum):
    LRFD = "LRFD"
    ASD = "ASD"


def require_design_method(value: str) -> DesignMethod:
    """Reject unknown methods, including on zero-strength conversion paths.

    Low-level D/E/G/H helpers historically accept case-insensitive tokens.
    Whitespace, nonstrings and missing values are not method aliases.
    SteelCase retains its stricter, uppercase JSON contract.
    """
    if isinstance(value, str):
        try:
            return DesignMethod(value.upper())
        except ValueError:
            pass
    raise ValueError(f"Unsupported design method: {value!r}; expected LRFD or ASD")
