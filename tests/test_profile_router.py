import unittest

from src.steel_design.domain.errors import IncompleteSectionDataError, RuleNotImplementedError
from src.steel_design.domain.routing.profile_router import ProfileRouter
from src.steel_design.models import Connection, Factors, Lengths, Loads, Material, SteelCase
from src.steel_design.sections.models import Section


def _build_case(*, pu: float, mux: float, muy: float, vu: float) -> SteelCase:
    return SteelCase(
        section_name="W14X90",
        material=Material(Fy=345.0, Fu=450.0, E=200000.0),
        loads=Loads(Pu=pu, Mux=mux, Muy=muy, Vu=vu),
        lengths=Lengths(Lx=3000.0, Ly=3000.0, Lz=3000.0, Lb=3000.0),
        factors=Factors(Kx=1.0, Ky=1.0, Kz=1.0, Cb=1.0),
        connection=Connection(Ae=None),
    )


def _build_w_section(*, zx):
    return Section(
        name="W14X90",
        type="W",
        A=17000.0,
        Ix=1.0,
        Iy=1.0,
        Sx=1.0,
        Sy=1.0,
        Zx=zx,
        Zy=1.0,
        rx=90.0,
        ry=55.0,
        **{"bf/2tf": 4.0, "h/tw": 25.0},
        J=1.0,
        Cw=1.0,
    )


class ProfileRouterTests(unittest.TestCase):
    def test_router_fails_hard_when_non_implemented_rule_is_required(self):
        case = _build_case(pu=0.0, mux=0.0, muy=0.0, vu=100.0)
        section = _build_w_section(zx=120000.0)

        with self.assertRaises(RuleNotImplementedError) as raised:
            ProfileRouter.get_rules(case, section)

        self.assertEqual("RULE_NOT_IMPLEMENTED", raised.exception.code)
        self.assertEqual("G2", raised.exception.details["rule_id"])

    def test_router_returns_only_implemented_rules_for_supported_case(self):
        case = _build_case(pu=0.0, mux=150.0, muy=0.0, vu=0.0)
        section = _build_w_section(zx=120000.0)

        rules = ProfileRouter.get_rules(case, section)

        self.assertEqual(1, len(rules))
        self.assertEqual("FlexureRule", rules[0].__class__.__name__)

    def test_router_fails_when_required_section_data_is_missing(self):
        case = _build_case(pu=0.0, mux=150.0, muy=0.0, vu=0.0)
        section = _build_w_section(zx=None)

        with self.assertRaises(IncompleteSectionDataError) as raised:
            ProfileRouter.get_rules(case, section)

        self.assertEqual("INCOMPLETE_SECTION_DATA", raised.exception.code)
        self.assertIn("zx", raised.exception.details["missing_fields"])

    def test_router_skips_e7_for_non_slender_w_section(self):
        case = _build_case(pu=600.0, mux=0.0, muy=0.0, vu=0.0)
        section = Section(
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

        rules = ProfileRouter.get_rules(case, section)
        rule_names = {rule.__class__.__name__ for rule in rules}
        self.assertIn("AxialE3Rule", rule_names)
        self.assertIn("AxialE4Rule", rule_names)
        self.assertNotIn("AxialE7Rule", rule_names)

    def test_router_includes_e7_for_slender_w_section(self):
        case = _build_case(pu=600.0, mux=0.0, muy=0.0, vu=0.0)
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

        rules = ProfileRouter.get_rules(case, section)
        rule_names = {rule.__class__.__name__ for rule in rules}
        self.assertIn("AxialE7Rule", rule_names)


if __name__ == "__main__":
    unittest.main()
