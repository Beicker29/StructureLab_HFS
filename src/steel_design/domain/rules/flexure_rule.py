from ...models import SteelCase, CheckResult, CheckStatus
from ...sections.models import Section
from ..evaluators.flexure_evaluator import FlexureEvaluator

class FlexureRule:
    def __init__(self):
        self.evaluator = FlexureEvaluator()

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        """
        Calculates the DCR for flexure and returns a CheckResult.
        """
        demand = abs(case.loads.Mux)
        evaluation = self.evaluator.evaluate(case, section)
        capacity = evaluation["capacity"]
        
        dcr = demand / capacity if capacity > 0 else float('inf')
        status = CheckStatus.PASS if dcr <= 1.0 else CheckStatus.FAIL
        
        return CheckResult(
            name="Flexure Major F2",
            clause="F2-1",
            demand=demand,
            capacity=capacity,
            dcr=round(dcr, 3),
            status=status,
            details={
                "memory": {
                    "clause": "F2",
                    "inputs": {
                        "Fy_mpa": evaluation["Fy_mpa"],
                        "Zx_mm3": evaluation["Zx_mm3"],
                        "Mux_kn_m": demand,
                    },
                    "intermediate": {
                        "Mp_Nmm": evaluation["Mp_Nmm"],
                        "Mn_Nmm": evaluation["Mn_Nmm"],
                    },
                    "capacity_kn_m": capacity,
                    "design_method": evaluation["design_method"],
                }
            },
        )
