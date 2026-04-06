def calculate_Mp(Fy: float, Zx: float) -> float:
    """
    Calculate Plastic Moment (Mp) per F2.1
    Returns N-mm
    """
    return Fy * Zx

def calculate_Mn_F2(Mp: float) -> float:
    """
    Calculate Nominal Flexural Strength for Yielding (F2.1)
    Currently assumes continuously braced / yielding governs
    Returns N-mm
    """
    return Mp

def calculate_available_flexural_strength(Mn: float, method: str) -> float:
    """
    Calculate Available Flexural Strength
    Mn is in N-mm. Returns kN-m.
    LRFD: phi_b = 0.90
    ASD: omega_b = 1.67
    """
    Mn_kn_m = Mn / 1000000.0
    if method.upper() == "LRFD":
        return 0.90 * Mn_kn_m
    else:
        return Mn_kn_m / 1.67
