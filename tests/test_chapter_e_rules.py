import unittest

from steel_design.domain.errors import RuleNotImplementedError, IncompleteSectionDataError, ValidationError
from steel_design.domain.rules.axial_rules import AxialE3Rule, AxialE4Rule, AxialE5Rule, AxialE7Rule
from steel_design.engine import SteelDesignEngine
from steel_design.models import Connection, Factors, Lengths, Loads, Material, SteelCase
from steel_design.sections.models import Section
from steel_design.sections.repository import SectionRepository


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
    def test_e4_channel_rule_is_contained(self):
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

        # HFS-031R0: neither an offset nor channel coupling may be ignored.
        with self.assertRaises(RuleNotImplementedError) as raised:
            AxialE4Rule().check(case, section)
        self.assertEqual("COMPRESSION_DOMAIN_BLOCKED", raised.exception.code)

    def test_e5_modes_require_unrepresented_conditions(self):
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

        for case in (case_one, case_both):
            with self.assertRaises(RuleNotImplementedError) as raised:
                AxialE5Rule().check(case, section)
            self.assertIn("F-36", raised.exception.details["findings"])

    def test_e7_slender_domain_blocks_e3_and_e7(self):
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

        for rule in (AxialE3Rule(), AxialE7Rule()):
            with self.assertRaises(RuleNotImplementedError) as raised:
                rule.check(case, section)
            self.assertIn("F-35", raised.exception.details["findings"])

    def test_e4_for_slender_w_shape_cannot_use_gross_area(self):
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

        # h/tw=47.2 exceeds 1.49*sqrt(200000/345); this is not an E3/E4 domain.
        for rule in (AxialE3Rule(), AxialE4Rule()):
            with self.assertRaises(RuleNotImplementedError) as raised:
                rule.check(case, section)
            self.assertIn("F-35", raised.exception.details["findings"])

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
