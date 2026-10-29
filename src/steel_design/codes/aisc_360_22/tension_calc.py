from ...design_methods import require_design_method
from ...tracing import observed_value, quantity
def calculate_Pn_yielding(Fy: float, Ag: float) -> float:
    """
    Calculate Nominal Tensile Strength for Yielding in Gross Section (D2-1)
    Returns N
    """
    return observed_value(Fy * Ag, name="Pn", unit="N", producer=__name__+":calculate_Pn_yielding",
        limit_state="gross_section_yielding", branch="yielding", reference="D2(a)", equation="D2-1",
        expression="Fy * Ag", inputs=(quantity("Fy", Fy, "MPa"), quantity("Ag", Ag, "mm2")))

def calculate_Pn_rupture(Fu: float, Ae: float) -> float:
    """
    Calculate Nominal Tensile Strength for Rupture in Net Section (D2-2)
    Returns N
    """
    return observed_value(Fu * Ae, name="Pn", unit="N", producer=__name__+":calculate_Pn_rupture",
        limit_state="effective_net_section_rupture", branch="rupture", reference="D2(b)", equation="D2-2",
        expression="Fu * Ae", inputs=(quantity("Fu", Fu, "MPa"), quantity("Ae", Ae, "mm2")))

def calculate_available_tensile_strength(Pn: float, method: str, limit_state: str) -> float:
    """
    Calculates Available Tensile Strength.
    Pn is in N. Returns kN.
    limit_state can be "yielding" or "rupture"
    LRFD: phi_t = 0.90 (yielding), 0.75 (rupture)
    ASD: omega_t = 1.67 (yielding), 2.00 (rupture)
    """
    Pn_kn = Pn / 1000.0
    
    factor = tension_design_factor(method, limit_state)

    if factor["design_method"] == "LRFD":
        return observed_value(factor["phi"] * Pn_kn, name="available", unit="kN",
            producer=__name__+":calculate_available_tensile_strength", limit_state=limit_state,
            branch="LRFD", reference="D2", equation=None, expression="phi * (Pn / 1000)",
            inputs=(quantity("Pn", Pn, "N"),), intermediates=(quantity("Pn_kn", Pn_kn, "kN"),),
            factors=(quantity("phi", factor["phi"], "ratio", "tension_design_factor"),),
            unknowns=("Available-strength conversion, not a separately numbered D2 equation.",))
    else:
        return observed_value(Pn_kn / factor["omega"], name="available", unit="kN",
            producer=__name__+":calculate_available_tensile_strength", limit_state=limit_state,
            branch="ASD", reference="D2", equation=None, expression="(Pn / 1000) / omega",
            inputs=(quantity("Pn", Pn, "N"),), intermediates=(quantity("Pn_kn", Pn_kn, "kN"),),
            factors=(quantity("omega", factor["omega"], "ratio", "tension_design_factor"),),
            unknowns=("Available-strength conversion, not a separately numbered D2 equation.",))


def tension_design_factor(method: str, limit_state: str) -> dict:
    method = require_design_method(method).value
    if limit_state == "yielding":
        phi_t = 0.90
        omega_t = 1.67
    elif limit_state == "rupture":
        phi_t = 0.75
        omega_t = 2.00
    else:
        raise ValueError("Invalid limit state for tension")

    return {"design_method": method, "phi": phi_t if method == "LRFD" else None,
            "omega": omega_t if method == "ASD" else None,
            "capacity_expression": "phi*Pn" if method == "LRFD" else "Pn/omega"}
