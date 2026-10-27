import unittest

from src.steel_design.domain.errors import IncompleteSectionDataError, ValidationError
from src.steel_design.domain.rules.axial_rules import AxialE3Rule, AxialE4Rule, AxialE5Rule, AxialE7Rule
from src.steel_design.engine import SteelDesignEngine
from src.steel_design.models import Connection, Factors, Lengths, Loads, Material, SteelCase
from src.steel_design.sections.models import Section
from src.steel_design.sections.repository import SectionRepository


def _compression_case(section_name: str, pu: float, *, e: float = 200000.0, mode=None, xa: float = 0.0, ya: float = 0.0) -> SteelCase:
    return SteelCase(
        section_name=section_name,
        design_method="LRFD",
        material=Material(Fy=345.0, Fu=450.0, E=e),
        loads=Loads(Pu=pu, Mux=0.0, Muy=0.0, Vu=0.0),
        lengths=Lengths(Lx=3000.0, Ly=3000.0, Lz=3000.0, Lb=3000.0),
        factors=Factors(Kx=1.0, Ky=1.0, Kz=1.0, Cb=1.0, xa=xa, ya=ya),
        connection=Connection(angle_compression_mode=mode),
    )


class ChapterERulesTests(unittest.TestCase):
    def test_e4_channel_rule_returns_capacity(self):
        case = _compression_case("C15X50", pu=300.0, xa=25.0, ya=0.0)
        section = Section(
            name="C15X50",
            type="CHANNEL",
            A=9480.0,
            Ix=168.0e6,
            Iy=4.58e6,
            Sx=882.0e3,
            Sy=61.8e3,
            Zx=1120.0e3,
            Zy=133.0e3,
            rx=133.0,
            ry=22.0,
            J=1100.0e3,
            Cw=132.0e9,
            ro=139.0,
            H=0.937,
            **{"b/t": 5.72, "h/tw": 17.3},
        )

        result = AxialE4Rule().check(case, section)
        self.assertEqual("E4-1", result.clause)
        self.assertGreater(result.capacity, 0.0)
        self.assertIn("element_classification", result.details)
        self.assertEqual("non_slender", result.details["element_classification"]["elements"]["web"]["classification"])
        self.assertEqual(25.0, result.details["memory"]["inputs"]["xa_mm"])
        self.assertEqual(0.0, result.details["memory"]["inputs"]["ya_mm"])
        self.assertIn("Fex_mpa", result.details["memory"]["intermediate"])
        self.assertIn("Fey_mpa", result.details["memory"]["intermediate"])
        self.assertIn("Fez_mpa", result.details["memory"]["intermediate"])
        self.assertIn("Fe_mpa", result.details["memory"]["intermediate"])
        self.assertIn("be_mm", result.details["memory"]["intermediate"])
        self.assertIn("warping_term_n", result.details["memory"]["intermediate"])
        self.assertIn("stvenant_term_n", result.details["memory"]["intermediate"])
        self.assertIn("torsional_stiffness_n", result.details["memory"]["intermediate"])

    def test_e5_mode_one_leg_is_more_conservative_than_both_legs(self):
        section = Section(
            name="L12X12X1-3/8",
            type="SINGLE_ANGLE",
            A=20100.0,
            Ix=172.0e6,
            Iy=172.0e6,
            Sx=797.0e3,
            Sy=797.0e3,
            Zx=1440.0e3,
            Zy=1440.0e3,
            rx=92.5,
            ry=92.5,
            J=8280.0e3,
            Cw=56.7e9,
            **{"b/t": 8.7},
        )
        case_one = _compression_case("L12X12X1-3/8", pu=220.0, mode="one_leg")
        case_both = _compression_case("L12X12X1-3/8", pu=220.0, mode="both_legs")

        result_one = AxialE5Rule().check(case_one, section)
        result_both = AxialE5Rule().check(case_both, section)

        self.assertLess(result_one.capacity, result_both.capacity)
        self.assertEqual("E5-1a", result_one.clause)
        self.assertEqual("E5-1b", result_both.clause)

    def test_e7_reduction_decreases_capacity_vs_e3(self):
        case = _compression_case("W44X262", pu=500.0)
        section = Section(
            name="W44X262",
            type="W",
            A=49800.0,
            Ix=11400.0e6,
            Iy=360.0e6,
            Sx=21000.0e3,
            Sy=1760.0e3,
            Zx=24500.0e3,
            Zy=2700.0e3,
            rx=478.0,
            ry=85.0,
            J=2500.0e3,
            Cw=96000.0e9,
            **{"bf/2tf": 20.0, "h/tw": 120.0},
        )

        e3 = AxialE3Rule().check(case, section)
        e7 = AxialE7Rule().check(case, section)

        self.assertLess(e7.capacity, e3.capacity)
        self.assertEqual("E7-1", e7.clause)
        self.assertEqual("slender", e7.details["element_classification"]["overall"])

    def test_e4_for_w_shape_uses_torsional_mode_and_can_differ_from_e3(self):
        case = _compression_case("W12X26", pu=300.0)
        section = Section(
            name="W12X26",
            type="W",
            A=4903.0,
            Ix=226.0e6,
            Iy=19.4e6,
            Sx=37.6e3,
            Sy=12.6e3,
            Zx=42.4e3,
            Zy=19.7e3,
            rx=215.0,
            ry=63.3,
            J=160.0e3,
            Cw=950.0e9,
            **{"bf/2tf": 8.54, "h/tw": 47.2},
        )

        e3 = AxialE3Rule().check(case, section)
        e4 = AxialE4Rule().check(case, section)

        self.assertNotEqual(e3.capacity, e4.capacity)
        self.assertGreater(e4.capacity, e3.capacity)

    def test_engine_validates_fixed_elastic_modulus(self):
        repo = SectionRepository()
        repo.load(
            [
                Section(
                    name="W44X262",
                    type="W",
                    A=49800.0,
                    Ix=11400.0e6,
                    Iy=360.0e6,
                    Sx=21000.0e3,
                    Sy=1760.0e3,
                    Zx=24500.0e3,
                    Zy=2700.0e3,
                    rx=478.0,
                    ry=85.0,
                    J=2500.0e3,
                    Cw=96000.0e9,
                    **{"bf/2tf": 6.0, "h/tw": 40.0},
                )
            ]
        )
        engine = SteelDesignEngine(repo)
        case = _compression_case("W44X262", pu=500.0, e=205000.0)

        with self.assertRaises(ValidationError):
            engine.run(case)

    def test_engine_requires_angle_mode_for_single_angle_compression(self):
        repo = SectionRepository()
        repo.load(
            [
                Section(
                    name="L12X12X1-3/8",
                    type="SINGLE_ANGLE",
                    A=20100.0,
                    Ix=172.0e6,
                    Iy=172.0e6,
                    Sx=797.0e3,
                    Sy=797.0e3,
                    Zx=1440.0e3,
                    Zy=1440.0e3,
                    rx=92.5,
                    ry=92.5,
                    J=8280.0e3,
                    Cw=56.7e9,
                    **{"b/t": 8.7},
                )
            ]
        )
        engine = SteelDesignEngine(repo)
        case = _compression_case("L12X12X1-3/8", pu=220.0, mode=None)

        with self.assertRaises(ValidationError):
            engine.run(case)

    def test_engine_reports_missing_2l_e4_properties(self):
        repo = SectionRepository()
        repo.load(
            [
                Section(
                    name="2L12X12X1-3/8",
                    type="DOUBLE_ANGLE",
                    A=40100.0,
                    Ix=344.0e6,
                    Iy=662.0e6,
                    Sx=1590.0e3,
                    Sy=2180.0e3,
                    Zx=2880.0e3,
                    Zy=3570.0e3,
                    rx=92.5,
                    ry=129.0,
                    ro=174.0,
                    H=0.831,
                    **{"b/t": 8.7},
                )
            ]
        )
        engine = SteelDesignEngine(repo)
        case = _compression_case("2L12X12X1-3/8", pu=250.0)

        with self.assertRaises(IncompleteSectionDataError) as raised:
            engine.run(case)

        self.assertEqual("E4", raised.exception.details["rule_id"])
        self.assertIn("j", raised.exception.details["missing_fields"])
        self.assertIn("cw", raised.exception.details["missing_fields"])

    def test_engine_rejects_negative_bracing_offsets(self):
        repo = SectionRepository()
        repo.load(
            [
                Section(
                    name="W24X131",
                    type="W",
                    A=24900.0,
                    Ix=2730.0e6,
                    Iy=494.0e6,
                    Sx=2270.0e3,
                    Sy=691.0e3,
                    Zx=2590.0e3,
                    Zy=1080.0e3,
                    rx=331.0,
                    ry=141.0,
                    J=6130.0e3,
                    Cw=30000.0e9,
                    **{"bf/2tf": 6.7, "h/tw": 35.6},
                )
            ]
        )
        engine = SteelDesignEngine(repo)
        case = _compression_case("W24X131", pu=500.0, xa=0.0, ya=0.0)
        # HFS-011 rejects xa<0 at construction; exercise the engine boundary too.
        case.factors = case.factors.model_copy(update={"xa": -1.0})

        with self.assertRaises(ValidationError):
            engine.run(case)


if __name__ == "__main__":
    unittest.main()
