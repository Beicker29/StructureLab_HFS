from ...models import SteelCase
from ...sections.models import Section
from ...codes.aisc_360_22 import tension_calc

class TensionEvaluator:
    def evaluate(self, case: SteelCase, section: Section) -> dict:
        """
        Evaluates the available tensile strength (kips) and returns a dict with details
        for both limit states: yielding and rupture.
        """
        # Section area
        Ag = section.area
        # Effective area
        Ae = case.connection.Ae if case.connection.Ae is not None else Ag
        
        # 1. Tensile Yielding
        Pn_y = tension_calc.calculate_Pn_yielding(case.material.Fy, Ag)
        avail_y = tension_calc.calculate_available_tensile_strength(
            Pn_y, case.design_method, limit_state="yielding"
        )
        
        # 2. Tensile Rupture
        Pn_r = tension_calc.calculate_Pn_rupture(case.material.Fu, Ae)
        avail_r = tension_calc.calculate_available_tensile_strength(
            Pn_r, case.design_method, limit_state="rupture"
        )
        
        # Determine governing
        if avail_y <= avail_r:
            governing_capacity = avail_y
            governing_clause = "D2-1 (Yielding)"
        else:
            governing_capacity = avail_r
            governing_clause = "D2-2 (Rupture)"
            
        return {
            "capacity": governing_capacity,
            "clause": governing_clause,
            "yielding_capacity": avail_y,
            "rupture_capacity": avail_r
        }
