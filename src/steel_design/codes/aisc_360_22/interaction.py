"""ANSI/AISC 360-22 Chapter H formulations (combined forces). Pure functions. LRFD only.

All terms are taken as positive (User Note H1.1). Strengths in kN and kN*m; H1-2 in N, mm, MPa.
"""
import math

ALPHA = 1.0   # H1.2, LRFD


def h1(*, Pr, Pc, Mrx, Mcx, Mry, Mcy) -> dict:
    """H1-1a when Pr/Pc >= 0.2, otherwise H1-1b. A zero demand needs no capacity."""
    ax = Pr / Pc if Pr else 0.0
    mx = Mrx / Mcx if Mrx else 0.0
    my = Mry / Mcy if Mry else 0.0
    if ax >= 0.2:
        return {"ratio": ax + 8.0 / 9.0 * (mx + my), "equation": "H1-1a", "Pr_Pc": ax, "Mrx_Mcx": mx, "Mry_Mcy": my}
    return {"ratio": ax / 2.0 + mx + my, "equation": "H1-1b", "Pr_Pc": ax, "Mrx_Mcx": mx, "Mry_Mcy": my}


def tension_cb_factor(*, Pr_N, E, Iy, Lb) -> dict:
    """H1.2: Cb may be multiplied by sqrt(1 + alpha*Pr/Pey), Pey = pi^2*E*Iy/Lb^2 (H1-2)."""
    for name, value in (("Pr_N", Pr_N), ("E", E), ("Iy", Iy), ("Lb", Lb)):
        if not (isinstance(value, (int, float)) and math.isfinite(value) and value > 0):
            raise ValueError(f"{name} must be finite and positive, got {value!r}")
    pey = math.pi**2 * E * Iy / Lb**2
    return {"factor": math.sqrt(1.0 + ALPHA * Pr_N / pey), "Pey_N": pey, "equation": "H1-2"}


def h4(*, Pr, Pc, Mrx, Mcx) -> dict:
    """H4-1 for the flange in tension: Pr/Pc + Mrx/Mcx <= 1 (axial tension and flexure both positive)."""
    return {"ratio": Pr / Pc + Mrx / Mcx, "equation": "H4-1", "Pr_Pc": Pr / Pc, "Mrx_Mcx": Mrx / Mcx}
