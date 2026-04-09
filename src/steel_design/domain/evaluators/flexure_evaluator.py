from ...models import SteelCase, DesignMethod
from ...sections.models import Section
from ...codes.aisc_360_22 import flexure_calc

class FlexureEvaluator:
    def evaluate(self, case: SteelCase, section: Section) -> dict:
        """
        Evaluates the available flexural strength in kip-ft.
        """
        # Calculate plastic moment
        Mp = flexure_calc.calculate_Mp(case.material.Fy, section.zx)
        
        # Calculate nominal moment
        Mn = flexure_calc.calculate_Mn_F2(Mp)
        
        # Calculate available moment based on LRFD/ASD
        available = flexure_calc.calculate_available_flexural_strength(Mn, case.design_method)
        
        return {
            "capacity": available,
            "Mp_Nmm": Mp,
            "Mn_Nmm": Mn,
            "Zx_mm3": section.zx,
            "Fy_mpa": case.material.Fy,
            "design_method": str(case.design_method),
        }
