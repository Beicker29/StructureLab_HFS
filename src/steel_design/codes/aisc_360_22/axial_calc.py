import math

def calculate_Fe_flexural(E: float, K: float, L: float, r: float) -> float:
    """
    Calculate Elastic Critical Buckling Stress (Fe) per E3-4.
    E: MPa -> N/mm2
    K: Effective length factor
    L: Unbraced length in mm
    r: Radius of gyration in mm
    Returns: Fe in MPa
    """
    if r == 0:
        return 0.0
    slenderness = (K * L) / r
    Fe = (math.pi**2 * E) / (slenderness**2)
    return Fe

def calculate_Fcr(Fy: float, Fe: float) -> float:
    """
    Calculate Critical Stress (Fcr) per E3-2 & E3-3.
    Fy: MPa
    Fe: MPa
    Returns: Fcr in MPa
    """
    if Fe <= 0:
        return 0.0
        
    if (Fy / Fe) <= 2.25:
        # Inelastic buckling (E3-2)
        Fcr = (0.658 ** (Fy / Fe)) * Fy
    else:
        # Elastic buckling (E3-3)
        Fcr = 0.877 * Fe
        
    return Fcr

def calculate_Pn(Fcr: float, Ag: float) -> float:
    """
    Calculate Nominal Compressive Strength (E3-1)
    Fcr: MPa -> N/mm2
    Ag: mm2
    Returns: Pn in N.
    """
    return Fcr * Ag

def calculate_available_compressive_strength(Pn: float, method: str) -> float:
    """
    Converts Pn (N) to Available Compressive Strength (kN)
    LRFD: phi_c = 0.90
    ASD: omega_c = 1.67
    """
    Pn_kn = Pn / 1000.0
    if method.upper() == "LRFD":
        return 0.90 * Pn_kn
    else:
        return Pn_kn / 1.67

# Placeholder advanced Euler Buckling stresses (E4, E5)
def calculate_Fe_torsional(E: float, G: float, J: float, Cw: float, Lz: float, Ag: float, r_x: float, r_y: float, x_o: float, y_o: float) -> float:
    """
    E4 Torsional and Flexural-Torsional buckling.
    Returns MPa.
    """
    # Simplifying logic for standard shapes, should be completed correctly later
    return 1000.0 
