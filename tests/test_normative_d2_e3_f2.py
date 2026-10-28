import unittest

from steel_design.codes.aisc_360_22 import axial_calc, flexure_calc, tension_calc
from steel_design.domain.rules.axial_rules import AxialE3Rule
from steel_design.domain.rules.flexure_rule import FlexureRule
from steel_design.domain.rules.tension_rule import TensionRuptureRule, TensionRule
from steel_design.models import Connection, Factors, Lengths, Loads, Material, SteelCase
from steel_design.sections.models import Section


class NormativeD2E3F2Tests(unittest.TestCase):
    def _section(self) -> Section:
        return Section(
            name="W14X90",
            type="W",
            A=17000.0,
            Ix=2500.0e6,
            Iy=350.0e6,
            Sx=1800.0e3,
            Sy=500.0e3,
            Zx=1500000.0,
            Zy=700.0e3,
            rx=90.0,
            ry=55.0,
            ho=300.0,
            **{"bf/2tf": 4.0, "h/tw": 25.0},
            J=4000.0e3,
            Cw=20000.0e9,
        )

    def test_D2_tension_capacity_in_kN_and_clause(self):
        pn_y = tension_calc.calculate_Pn_yielding(345.0, 1000.0)
        available_y = tension_calc.calculate_available_tensile_strength(pn_y, "LRFD", "yielding")
        self.assertAlmostEqual(310.5, available_y, places=3)

        case = SteelCase(
            section_name="W14X90",
            material=Material(Fy=345.0, Fu=450.0, E=200000.0),
            loads=Loads(Pu=-150.0, Mux=0.0, Muy=0.0, Vu=0.0),
            lengths=Lengths(Lx=3000.0, Ly=3000.0, Lz=3000.0, Lb=3000.0),
            factors=Factors(Kx=1.0, Ky=1.0, Kz=1.0, Cb=1.0),
            connection=Connection(An=18000.0, U=0.8),
        )
        result_yield = TensionRule().check(case, self._section())
        result_rupture = TensionRuptureRule().check(case, self._section())

        self.assertEqual("D2-1", result_yield.clause)
        self.assertGreater(result_yield.capacity, 0.0)
        self.assertEqual(150.0, result_yield.demand)

        self.assertEqual("D2-2", result_rupture.clause)
        self.assertGreater(result_rupture.capacity, 0.0)
        self.assertEqual(150.0, result_rupture.demand)
        self.assertAlmostEqual(14400.0, result_rupture.details["memory"]["inputs"]["Ae_mm2"])
        self.assertEqual(
            "Ae = U*An",
            result_rupture.details["memory"]["intermediate"]["d3_effective_net_area_expression"],
        )

    def test_E3_axial_rule_returns_clause_and_positive_capacity_kN(self):
        fe = axial_calc.calculate_Fe_flexural(200000.0, 1.0, 3000.0, 90.0)
        fcr = axial_calc.calculate_Fcr(345.0, fe)
        pn = axial_calc.calculate_Pn(fcr, 17000.0)
        phi_pn = axial_calc.calculate_available_compressive_strength(pn, "LRFD")
        self.assertGreater(phi_pn, 0.0)

        case = SteelCase(
            section_name="W14X90",
            material=Material(Fy=345.0, Fu=450.0, E=200000.0),
            loads=Loads(Pu=300.0, Mux=0.0, Muy=0.0, Vu=0.0),
            lengths=Lengths(Lx=3000.0, Ly=3000.0, Lz=3000.0, Lb=3000.0),
            factors=Factors(Kx=1.0, Ky=1.0, Kz=1.0, Cb=1.0),
            connection=Connection(),
        )
        result = AxialE3Rule().check(case, self._section())

        self.assertEqual("E3-1", result.clause)
        self.assertGreater(result.capacity, 0.0)

    def test_F2_flexure_rule_uses_kN_m_and_absolute_demand(self):
        mp = 345.0 * 1000000.0
        available = flexure_calc.available_flexural_strength_lrfd(mp)
        self.assertAlmostEqual(310.5, available, places=3)

        case = SteelCase(
            section_name="W14X90",
            material=Material(Fy=345.0, Fu=450.0, E=200000.0),
            loads=Loads(Pu=0.0, Mux=-120.0, Muy=0.0, Vu=0.0),
            lengths=Lengths(Lx=3000.0, Ly=3000.0, Lz=3000.0, Lb=3000.0),
            factors=Factors(Kx=1.0, Ky=1.0, Kz=1.0, Cb=1.0),
            connection=Connection(),
        )
        result = FlexureRule().check(case, self._section())

        self.assertEqual("F2-1", result.clause)
        self.assertEqual(120.0, result.demand)
        self.assertGreater(result.capacity, 0.0)


if __name__ == "__main__":
    unittest.main()
