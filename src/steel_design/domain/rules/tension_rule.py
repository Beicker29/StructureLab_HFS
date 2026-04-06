from ...models import SteelCase, CheckResult, CheckStatus
from ...sections.models import Section
from ..evaluators.tension_evaluator import TensionEvaluator

class TensionRule:
    def __init__(self):
        self.evaluator = TensionEvaluator()

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        """
        Calculates the DCR for tension and returns a CheckResult.
        Note: Pu is positive for compression, negative for tension.
        """
        # If no tension force, skip or return nominal pass
        if case.loads.Pu >= 0:
            return CheckResult(
                name="Tension",
                clause="D2",
                demand=0.0,
                capacity=0.0,
                dcr=0.0,
                status=CheckStatus.PASS
            )
            
        # Absolute value of demand since tension is negative in our convention
        demand = abs(case.loads.Pu)
        evaluation = self.evaluator.evaluate(case, section)
        
        capacity = evaluation["capacity"]
        clause = evaluation["clause"]
        
        dcr = demand / capacity if capacity > 0 else float('inf')
        status = CheckStatus.PASS if dcr <= 1.0 else CheckStatus.FAIL
        
        return CheckResult(
            name="Tensile Strength",
            clause=clause,
            demand=demand,
            capacity=capacity,
            dcr=round(dcr, 3),
            status=status
        )
