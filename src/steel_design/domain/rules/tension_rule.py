from ...models import CheckResult, CheckStatus, SteelCase
from ...sections.models import Section
from ..evaluators.tension_evaluator import TensionEvaluator


def _nominal_pass(name: str, clause: str) -> CheckResult:
    return CheckResult(
        name=name,
        clause=clause,
        demand=0.0,
        capacity=0.0,
        dcr=0.0,
        status=CheckStatus.PASS,
    )


class TensionRule:
    """D2-1: tensile yielding in gross section."""

    def __init__(self):
        self.evaluator = TensionEvaluator()

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        if case.loads.Pu >= 0.0:
            return _nominal_pass("Tension Yielding (D2-1)", "D2-1")

        demand = abs(case.loads.Pu)
        evaluation = self.evaluator.evaluate(case, section)
        capacity = evaluation["yielding_capacity"]

        return CheckResult.from_values(
            unit='kN',
            name="Tension Yielding (D2-1)",
            clause="D2-1",
            demand=demand,
            capacity=capacity,
            details={
                "memory": {
                    "clause": "D2-1",
                    "inputs": {
                        "Fy_mpa": case.material.Fy,
                        "Ag_mm2": evaluation["Ag_mm2"],
                        "Pu_tension_kn": demand,
                    },
                    "intermediate": {
                        "Pn_y_N": evaluation["Pn_y_N"],
                        "yielding_capacity_kn": evaluation["yielding_capacity"],
                    },
                    "capacity_kn": capacity,
                }
            },
        )


class TensionRuptureRule:
    """D2-2 with effective net area from D3: Ae = U*An."""

    def __init__(self):
        self.evaluator = TensionEvaluator()

    def check(self, case: SteelCase, section: Section) -> CheckResult:
        if case.loads.Pu >= 0.0:
            return _nominal_pass("Tension Rupture (D2-2/D3)", "D2-2")

        demand = abs(case.loads.Pu)
        evaluation = self.evaluator.evaluate(case, section)
        capacity = evaluation["rupture_capacity"]

        return CheckResult.from_values(
            unit='kN',
            name="Tension Rupture (D2-2/D3)",
            clause="D2-2",
            demand=demand,
            capacity=capacity,
            details={
                "memory": {
                    "clause": "D2-2",
                    "inputs": {
                        "Fu_mpa": case.material.Fu,
                        "An_mm2": evaluation["An_mm2"],
                        "U_factor": evaluation["U_factor"],
                        "Ae_mm2": evaluation["Ae_mm2"],
                        "Pu_tension_kn": demand,
                    },
                    "intermediate": {
                        "Pn_r_N": evaluation["Pn_r_N"],
                        "d3_effective_net_area_expression": "Ae = U*An",
                        "rupture_capacity_kn": evaluation["rupture_capacity"],
                    },
                    "capacity_kn": capacity,
                }
            },
        )
