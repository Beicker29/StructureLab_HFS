import unittest

from src.steel_design.domain.errors import ValidationError
from src.steel_design.engine import SteelDesignEngine
from src.steel_design.models import Connection, Factors, Lengths, Loads, Material, SteelCase
from src.steel_design.sections.repository import SectionRepository


def _base_case_kwargs() -> dict:
    return {
        "design_method": "LRFD",
        "material": Material(Fy=345.0, Fu=450.0, E=200000.0),
        "lengths": Lengths(Lx=3000.0, Ly=3000.0, Lz=3000.0, Lb=3000.0),
        "factors": Factors(Kx=1.0, Ky=1.0, Kz=1.0, Cb=1.0),
    }


class CustomSolidSectionsTests(unittest.TestCase):
    def test_custom_solid_circular_compression_routes_to_e3_only(self):
        engine = SteelDesignEngine(SectionRepository())
        case = SteelCase(
            section_name="SC200",
            loads=Loads(Pu=350.0, Mux=0.0, Muy=0.0, Vu=0.0),
            connection=Connection(),
            custom_section={"type": "SOLID_CIRCULAR", "diameter": 200.0},
            **_base_case_kwargs(),
        )

        result = engine.run(case)

        self.assertEqual("PASS", result.status.value)
        self.assertEqual(1, len(result.checks))
        clauses = {check.clause for check in result.checks}
        self.assertIn("E3-1", clauses)
        compression_check = next(check for check in result.checks if check.clause == "E3-1")
        self.assertGreater(compression_check.capacity, 0.0)

    def test_custom_solid_rectangular_tension_uses_d2_with_d3_effective_area(self):
        engine = SteelDesignEngine(SectionRepository())
        case = SteelCase(
            section_name="SR200X100",
            loads=Loads(Pu=-120.0, Mux=0.0, Muy=0.0, Vu=0.0),
            connection=Connection(An=15000.0, U=0.85),
            custom_section={"type": "SOLID_RECTANGULAR", "H": 200.0, "B": 100.0},
            **_base_case_kwargs(),
        )

        result = engine.run(case)

        self.assertEqual("PASS", result.status.value)
        self.assertEqual(2, len(result.checks))
        clauses = {check.clause for check in result.checks}
        self.assertIn("D2-1", clauses)
        self.assertIn("D2-2", clauses)
        rupture_check = next(check for check in result.checks if check.clause == "D2-2")
        self.assertAlmostEqual(12750.0, rupture_check.details["memory"]["inputs"]["Ae_mm2"])

    def test_custom_solid_sections_reject_non_axial_actions(self):
        engine = SteelDesignEngine(SectionRepository())
        case = SteelCase(
            section_name="SC160",
            loads=Loads(Pu=250.0, Mux=20.0, Muy=0.0, Vu=0.0),
            connection=Connection(),
            custom_section={"type": "SOLID_CIRCULAR", "diameter": 160.0},
            **_base_case_kwargs(),
        )

        with self.assertRaises(ValidationError):
            engine.run(case)

    def test_tension_requires_an_and_u(self):
        engine = SteelDesignEngine(SectionRepository())
        case = SteelCase(
            section_name="SC160",
            loads=Loads(Pu=-80.0, Mux=0.0, Muy=0.0, Vu=0.0),
            connection=Connection(),
            custom_section={"type": "SOLID_CIRCULAR", "diameter": 160.0},
            **_base_case_kwargs(),
        )

        with self.assertRaises(ValidationError):
            engine.run(case)

    def test_tension_rejects_invalid_u_factor(self):
        engine = SteelDesignEngine(SectionRepository())
        case = SteelCase(
            section_name="SR100X100",
            loads=Loads(Pu=-80.0, Mux=0.0, Muy=0.0, Vu=0.0),
            connection=Connection(An=5000.0, U=1.2),
            custom_section={"type": "SOLID_RECTANGULAR", "H": 100.0, "B": 100.0},
            **_base_case_kwargs(),
        )

        with self.assertRaises(ValidationError):
            engine.run(case)

    def test_tension_rejects_effective_area_greater_than_gross_area(self):
        engine = SteelDesignEngine(SectionRepository())
        case = SteelCase(
            section_name="SR100X100",
            loads=Loads(Pu=-80.0, Mux=0.0, Muy=0.0, Vu=0.0),
            connection=Connection(An=15000.0, U=0.9),
            custom_section={"type": "SOLID_RECTANGULAR", "H": 100.0, "B": 100.0},
            **_base_case_kwargs(),
        )

        with self.assertRaises(ValidationError):
            engine.run(case)


if __name__ == "__main__":
    unittest.main()
