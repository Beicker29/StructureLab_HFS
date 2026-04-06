from ...models import SteelCase, CheckResult, CheckStatus
from ...sections.models import Section

class AxialRule:
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = case.loads.Pu
        capacity = 1000.0  # Placeholder
        dcr = demand / capacity
        return CheckResult(
            name="Axial Compression",
            clause="E3-1",
            demand=demand,
            capacity=capacity,
            dcr=round(dcr, 3),
            status=CheckStatus.PASS if dcr <= 1.0 else CheckStatus.FAIL
        )

class ShearRule:
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        demand = case.loads.Vu
        capacity = 500.0  # Placeholder
        dcr = demand / capacity
        return CheckResult(
            name="Shear Major G2",
            clause="G2-1",
            demand=demand,
            capacity=capacity,
            dcr=round(dcr, 3),
            status=CheckStatus.PASS if dcr <= 1.0 else CheckStatus.FAIL
        )

class InteractionRule:
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        # Placeholder H1-1a/b
        dcr = 0.5 # just returning a stub
        return CheckResult(
            name="Interaction",
            clause="H1-1",
            demand=0.0,
            capacity=0.0,
            dcr=round(dcr, 3),
            status=CheckStatus.PASS
        )
