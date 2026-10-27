from ..design_methods import require_case_method
from ...models import SteelCase
from ...sections.models import Section
from ...codes.aisc_360_22 import flexure_calc


class FlexureEvaluator:
    def evaluate(self, case: SteelCase, section: Section) -> dict:
        require_case_method(case, chapter="F")
        evaluation = flexure_calc.evaluate_f2(case, section)
        mn_nmm = evaluation["Mn_Nmm"]
        available = flexure_calc.available_flexural_strength(mn_nmm, case.design_method.value)
        return {
            "capacity": available,
            "Mp_Nmm": evaluation["Mp_Nmm"],
            "Mn_Nmm": mn_nmm,
            "Zx_mm3": section.zx,
            "Fy_mpa": case.material.Fy,
            "design_method": case.design_method.value,
            "intermediate": evaluation["intermediate"],
            "limit_states": evaluation["limit_states"],
        }
