"""AISC Design Guide 38 (2023), Chapter 6: SpeedCore walls under fire. Not a standard. Units N, mm, MPa, s, unless stated."""
import math

MM_PER_IN = 25.4
VENT_MIN_DIAMETER = 25.4     # 6.3.5: 1 in.
VENT_MAX_SPACING = 3657.6    # 6.3.5: 12 ft


def ambient_strength(*, Pno, EI_eff, Lc) -> float:
    """Equations 6-6a and 6-6c, as written in the guide, without the elastic branch of I2-3."""
    Pe = math.pi**2 * EI_eff / Lc**2
    return 0.658 ** (Pno / Pe) * Pno


def fire_resistance_rating(*, Pu_over_Pn, L, tsc) -> float:
    """Equation 6-5, hours; L and tsc enter in inches. Valid only for L/tsc <= 20 and Pu/Pn <= 0.2."""
    slenderness = L / tsc
    rating = (-18.5 * Pu_over_Pn ** (0.24 - slenderness / 230) + 15) * (1.9 * (tsc / MM_PER_IN) / 8 - 1)
    return min(rating, 8.0)


def elevated_strength(*, Pno_T, EI_eff_T, Lc) -> dict:
    """Equations 6-1 and 6-4."""
    Pe = math.pi**2 * EI_eff_T / Lc**2
    return {"Pe_T": Pe, "Pn_T": 0.32 ** ((Pno_T / Pe) ** 0.3) * Pno_T}


def vent_hole_area(*, s1, s2, Tdc, tdc, omega, rho_w, rho_c, hc) -> float:
    """Equation 6-10; the constant 116 keeps its value in any length unit because the lengths reduce to a square one."""
    return 116 * s1 * s2 * Tdc * omega * rho_w / (tdc * rho_c * hc)
