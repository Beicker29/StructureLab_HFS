"""ANSI/AISC 360-22 Chapter D formulations (tension). Pure functions; units N, mm, MPa.

Each limit state has its own resistance factor, so design strengths are
computed per limit state (D2) and the lowest design strength governs. LRFD only.
"""
import math

# D2(a) tensile yielding and D2(b) tensile rupture: phi_t (LRFD)
PHI_T = {"yielding": 0.90, "rupture": 0.75}


def _positive(**values):
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive, got {value!r}")


def yielding_strength(*, Fy: float, Ag: float) -> dict:
    """D2-1: Pn = Fy * Ag (N)."""
    _positive(Fy=Fy, Ag=Ag)
    return {"Pn_N": Fy * Ag, "equation": "D2-1"}


def effective_net_area(*, An: float, U: float) -> dict:
    """D3-1: Ae = An * U (mm2). An per B4.3b and U per Table D3.1 are supplied by the caller."""
    _positive(An=An, U=U)
    if U > 1:
        raise ValueError("Shear lag factor U must not exceed 1")
    return {"Ae_mm2": An * U, "equation": "D3-1"}


def rupture_strength(*, Fu: float, Ae: float) -> dict:
    """D2-2: Pn = Fu * Ae (N)."""
    _positive(Fu=Fu, Ae=Ae)
    return {"Pn_N": Fu * Ae, "equation": "D2-2"}


def available_strength(Pn_N: float, limit_state: str) -> float:
    """Design tensile strength phi_t*Pn (LRFD) in kN, with the D2 factor of that limit state."""
    return PHI_T[limit_state] * Pn_N / 1000.0
