def calculate_Pn_yielding(Fy: float, Ag: float) -> float:
    """
    Calculate Nominal Tensile Strength for Yielding in Gross Section (D2-1)
    Returns N
    """
    return Fy * Ag

def calculate_Pn_rupture(Fu: float, Ae: float) -> float:
    """
    Calculate Nominal Tensile Strength for Rupture in Net Section (D2-2)
    Returns N
    """
    return Fu * Ae

def calculate_available_tensile_strength(Pn: float, method: str, limit_state: str) -> float:
    """
    Calculates Available Tensile Strength.
    Pn is in N. Returns kN.
    limit_state can be "yielding" or "rupture"
    LRFD: phi_t = 0.90 (yielding), 0.75 (rupture)
    ASD: omega_t = 1.67 (yielding), 2.00 (rupture)
    """
    Pn_kn = Pn / 1000.0
    
    if limit_state == "yielding":
        phi_t = 0.90
        omega_t = 1.67
    elif limit_state == "rupture":
        phi_t = 0.75
        omega_t = 2.00
    else:
        raise ValueError("Invalid limit state for tension")

    if method.upper() == "LRFD":
        return phi_t * Pn_kn
    else:
        return Pn_kn / omega_t
