from ...models import SteelCase
from ...sections.models import Section
from ...codes.aisc_360_22 import tension_calc

class TensionEvaluator:
    def evaluate(self, case: SteelCase, section: Section) -> dict:
        """
        Evaluates the available tensile strength (kips) and returns a dict with details
        for both limit states: yielding and rupture.
        """
        Ag = section.area
        an = case.connection.An or 0.0
        u_factor = case.connection.U or 0.0
        ae = u_factor * an
        
        # 1. Tensile Yielding
        Pn_y = tension_calc.calculate_Pn_yielding(case.material.Fy, Ag)
        avail_y = tension_calc.calculate_available_tensile_strength(
            Pn_y, case.design_method, limit_state="yielding"
        )
        
        # 2. Tensile Rupture
        Pn_r = tension_calc.calculate_Pn_rupture(case.material.Fu, ae)
        avail_r = tension_calc.calculate_available_tensile_strength(
            Pn_r, case.design_method, limit_state="rupture"
        )
        
        # Determine governing
        if avail_y <= avail_r:
            governing_capacity = avail_y
            governing_clause = "D2-1 (Yielding)"
            governing_limit_state = "yielding"
        else:
            governing_capacity = avail_r
            governing_clause = "D2-2 (Rupture)"
            governing_limit_state = "rupture"
            
        return {
            "capacity": governing_capacity,
            "clause": governing_clause,
            "governing_limit_state": governing_limit_state,
            "Ag_mm2": Ag,
            "An_mm2": an,
            "U_factor": u_factor,
            "Ae_mm2": ae,
            "Pn_y_N": Pn_y,
            "Pn_r_N": Pn_r,
            "yielding_capacity": avail_y,
            "rupture_capacity": avail_r,
        }
