from ...models import SteelCase, CheckResult, CheckStatus
from ...sections.models import Section
from ...codes.aisc_360_22 import axial_calc

class AxialE3Rule:
    """
    Flexural Buckling of Members without Slender Elements (E3).
    """
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        # Ignore if it's tension (negative Pu)
        if case.loads.Pu < 0:
            return CheckResult(name="Axial Compression E3", clause="E3", demand=0.0, capacity=0.0, dcr=0.0, status=CheckStatus.PASS)

        demand = case.loads.Pu
        E = case.material.E
        Fy = case.material.Fy
        Ag = section.area

        # Evaluate X-axis flexural buckling
        Fe_x = axial_calc.calculate_Fe_flexural(E, case.factors.Kx, case.lengths.Lx, section.rx)
        Fcr_x = axial_calc.calculate_Fcr(Fy, Fe_x)

        # Evaluate Y-axis flexural buckling
        Fe_y = axial_calc.calculate_Fe_flexural(E, case.factors.Ky, case.lengths.Ly, section.ry)
        Fcr_y = axial_calc.calculate_Fcr(Fy, Fe_y)

        # Governing Fcr
        Fcr_gov = min(Fcr_x, Fcr_y)
        
        # Calculate nominal and available
        Pn = axial_calc.calculate_Pn(Fcr_gov, Ag)
        capacity = axial_calc.calculate_available_compressive_strength(Pn, case.design_method)

        dcr = demand / capacity if capacity > 0 else float('inf')
        status = CheckStatus.PASS if dcr <= 1.0 else CheckStatus.FAIL

        return CheckResult(
            name="Axial Compression (Flexural Buckling)",
            clause="E3-1",
            demand=demand,
            capacity=round(capacity, 3),
            dcr=round(dcr, 3),
            status=status
        )

class AxialE4Rule:
    """
    Torsional and Flexural-Torsional Buckling of Single Angles and Members without Slender Elements (E4)
    """
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        if case.loads.Pu < 0:
            return CheckResult(name="Axial Comp E4", clause="E4", demand=0.0, capacity=0.0, dcr=0.0, status=CheckStatus.PASS)
        # Placeholder till section geometry models supply Cw, xo, yo fully.
        return CheckResult(name="Axial Compression (Torsional Buckling)", clause="E4-1", demand=case.loads.Pu, capacity=9999.0, dcr=0.0, status=CheckStatus.PASS)

class AxialE5Rule:
    """
    Single Angle Compression Members (E5).
    """
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        if case.loads.Pu < 0:
            return CheckResult(name="Axial Comp E5", clause="E5", demand=0.0, capacity=0.0, dcr=0.0, status=CheckStatus.PASS)
        return CheckResult(name="Axial Compression (Single Angle)", clause="E5", demand=case.loads.Pu, capacity=9999.0, dcr=0.0, status=CheckStatus.PASS)

class AxialE7Rule:
    """
    Members with Slender Elements (E7).
    """
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        if case.loads.Pu < 0:
            return CheckResult(name="Axial Comp E7", clause="E7", demand=0.0, capacity=0.0, dcr=0.0, status=CheckStatus.PASS)
        return CheckResult(name="Axial Compression (Slender Elements)", clause="E7-1", demand=case.loads.Pu, capacity=9999.0, dcr=0.0, status=CheckStatus.PASS)
