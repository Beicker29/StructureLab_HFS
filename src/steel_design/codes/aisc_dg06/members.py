"""AISC Design Guide 6, 2nd ed. (2025), member checks that ANSI/AISC 360-22 does not print. Not a standard. Units N, mm, MPa."""
E_STEEL = 200000.0
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
    """Equations 2-12 and 2-13: round filled members. Rectangular ones (2-14) need a Jc that the guide does not define."""
    return GsJs + min(2 * As_over_Ag + 2 / 5, 1.0) * GcJc
