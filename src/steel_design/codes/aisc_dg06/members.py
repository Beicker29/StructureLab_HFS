"""AISC Design Guide 6, 2nd ed. (2025), member checks that ANSI/AISC 360-22 does not print. Not a standard. Units N, mm, MPa."""
from ..aisc_360_22.constants import E_STEEL

BIAXIAL_ALPHA = {"encased": 1.25, "rect": 1.5, "round": 2.0}     # Section 2.3.2 (Behnam and Denavit, 2021)


def biaxial_interaction(*, Pr, Pc, Pcc, x, y, alpha) -> dict:
    """Equations 2-2a and 2-2b; x and y are Mrx/Mcx and Mry/Mcy. Both agree at Pr = Pcc; 2-2a also serves Pr = Pcc = 0."""
    if Pr <= Pcc:
        return {"ratio": x**alpha + y**alpha, "equation": "DG6 Ec. 2-2a"}
    return {"ratio": (Pr - Pcc) / (Pc - Pcc) + (x**alpha + y**alpha) ** (1 / alpha), "equation": "DG6 Ec. 2-2b"}


def tension_control(*, hn, h, v_tension, Fysr) -> dict:
    """Section 2.4.1 and Example 2.4: tensile strain of the outermost bar, with the neutral axis at hn from the center."""
    c = h / 2 - hn
    d = h / 2 - v_tension
    strain = 0.003 * (d - c) / c
    limit = Fysr / E_STEEL + 0.003
    return {"epsilon_t": strain, "epsilon_limit": limit, "tension_controlled": strain >= limit}


def service_stiffness(*, kind, EsIs, EsIsr, EcIc, C, P_over_Pno) -> float:
    """Equations 2-7 to 2-10: flexural stiffness for lateral drift under service loads (Section 2.8)."""
    if P_over_Pno < 0.1:
        return EsIs + EsIsr + 0.4 * C * EcIc                     # 2-7, 2-9
    return EsIs + EsIsr + (0.4 if kind == "encased" else 0.6) * EcIc  # 2-8, 2-10


def axial_stiffness(*, EsAs, EsAsr, EcAc) -> float:
    """Equation 2-1."""
    return EsAs + EsAsr + EcAc


def shear_stiffness_rect(*, GsAs, GcAc) -> float:
    """Equation 2-11: rectangular filled members only; the guide gives no expression for other shapes."""
    return GsAs / 2 + GcAc / 1.2


def torsional_stiffness_round(*, GsJs, GcJc, As_over_Ag) -> float:
    """Equations 2-12 and 2-13: round filled members."""
    return GsJs + min(2 * As_over_Ag + 2 / 5, 1.0) * GcJc


def torsional_stiffness_rect(*, GsJs, GcJc, As_over_Ag) -> float:
    """Equations 2-12 and 2-14: rectangular filled members."""
    return GsJs + min(2 / 3 * As_over_Ag + 2 / 15, 1 / 3) * GcJc


def box_torsional_constant(*, B, H, t) -> float:
    """J of a welded box as a closed thin wall (Bredt), which Equation 2-12 needs; the guide does not print it (DI-16)."""
    return 2 * t * (B - t) ** 2 * (H - t) ** 2 / (B + H - 2 * t)


def concrete_torsional_constant_rect(*, width, depth) -> float:
    """Jc of a rectangular core, a >= b: a*b^3*(1/3 - 0.21*(b/a)*(1 - b^4/(12*a^4))).

    The guide does not define Jc; this Saint-Venant approximation was given by the user (decision DI-16).
    """
    a, b = max(width, depth), min(width, depth)
    return a * b**3 * (1 / 3 - 0.21 * (b / a) * (1 - b**4 / (12 * a**4)))
