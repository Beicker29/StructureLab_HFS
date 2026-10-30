"""Design-method identifiers only; factors remain with their AISC provision."""
from enum import Enum


class DesignMethod(str, Enum):
    LRFD = "LRFD"
    ASD = "ASD"


def require_design_method(value: str) -> DesignMethod:
    """Accept a DesignMethod or a case-insensitive "LRFD"/"ASD"; reject anything else."""
    if isinstance(value, str):
        try:
            return DesignMethod(value.upper())
        except ValueError:
            pass
    raise ValueError(f"Unsupported design method: {value!r}; expected LRFD or ASD")
