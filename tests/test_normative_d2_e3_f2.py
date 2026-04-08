import unittest

from src.steel_design.codes.aisc_360_22 import axial_calc, flexure_calc, tension_calc
from src.steel_design.domain.rules.axial_rules import AxialE3Rule
from src.steel_design.domain.rules.flexure_rule import FlexureRule
from src.steel_design.domain.rules.tension_rule import TensionRule
from src.steel_design.models import Connection, Factors, Lengths, Loads, Material, SteelCase
from src.steel_design.sections.models import Section


class NormativeD2E3F2Tests(unittest.TestCase):
    def _section(self) -> Section:
        return Section(
            name="W14X90",
            type="W",
            A=17000.0,
            Ix=1.0,
            Iy=1.0,
            Sx=1.0,
            Sy=1.0,
            Zx=1500000.0,
            Zy=1.0,
            rx=90.0,
            ry=55.0,
            J=1.0,
            Cw=1.0,
        )

    def test_D2_tension_capacity_in_kN_and_clause(self):
        pn_y = tension_calc.calculate_Pn_yielding(345.0, 1000.0)
        available_y = tension_calc.calculate_available_tensile_strength(pn_y, "LRFD", "yielding")
        self.assertAlmostEqual(310.5, available_y, places=3)

        case = SteelCase(
            section_name="W14X90",
            material=Material(Fy=345.0, Fu=450.0, E=200000.0),
            loads=Loads(Pu=-150.0, Mux=0.0, Muy=0.0, Vu=0.0),
            lengths=Lengths(Lx=3000.0, Ly=3000.0, Lb=3000.0),
            factors=Factors(),
            connection=Connection(Ae=15000.0),
        )
        result = TensionRule().check(case, self._section())

        self.assertTrue(result.clause.startswith("D2-"))
        self.assertGreater(result.capacity, 0.0)
        self.assertEqual(150.0, result.demand)

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
            lengths=Lengths(Lx=3000.0, Ly=3000.0, Lb=3000.0),
            factors=Factors(),
            connection=Connection(),
        )
        result = AxialE3Rule().check(case, self._section())

        self.assertEqual("E3-1", result.clause)
        self.assertGreater(result.capacity, 0.0)

    def test_F2_flexure_rule_uses_kN_m_and_absolute_demand(self):
        mp = flexure_calc.calculate_Mp(345.0, 1000000.0)
        available = flexure_calc.calculate_available_flexural_strength(mp, "LRFD")
        self.assertAlmostEqual(310.5, available, places=3)

        case = SteelCase(
            section_name="W14X90",
            material=Material(Fy=345.0, Fu=450.0, E=200000.0),
            loads=Loads(Pu=0.0, Mux=-120.0, Muy=0.0, Vu=0.0),
            lengths=Lengths(Lx=3000.0, Ly=3000.0, Lb=3000.0),
            factors=Factors(),
            connection=Connection(),
        )
        result = FlexureRule().check(case, self._section())

        self.assertEqual("F2-1", result.clause)
        self.assertEqual(120.0, result.demand)
        self.assertGreater(result.capacity, 0.0)


if __name__ == "__main__":
    unittest.main()
