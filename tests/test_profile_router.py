import unittest

from steel_design.domain.errors import IncompleteSectionDataError
from steel_design.domain.routing.profile_router import ProfileRouter
from steel_design.models import Connection, Factors, Lengths, Loads, Material, SteelCase
from steel_design.sections.models import Section


def _build_case(*, pu: float, mux: float, muy: float, vu: float) -> SteelCase:
    return SteelCase(
        section_name="W14X90",
        material=Material(Fy=345.0, Fu=450.0, E=200000.0),
        loads=Loads(Pu=pu, Mux=mux, Muy=muy, Vu=vu),
        lengths=Lengths(Lx=3000.0, Ly=3000.0, Lz=3000.0, Lb=3000.0),
        factors=Factors(Kx=1.0, Ky=1.0, Kz=1.0, Cb=1.0),
        connection=Connection(),
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
        ho=300.0,
        **{"bf/2tf": 4.0, "h/tw": 25.0},
        J=1.0,
        Cw=1.0,
    )


class ProfileRouterTests(unittest.TestCase):
    def test_router_fails_when_shear_rule_is_applicable_but_section_data_is_incomplete(self):
        case = _build_case(pu=0.0, mux=0.0, muy=0.0, vu=100.0)
        section = _build_w_section(zx=120000.0)

        with self.assertRaises(IncompleteSectionDataError) as raised:
            ProfileRouter.get_rules(case, section)

        self.assertEqual("INCOMPLETE_SECTION_DATA", raised.exception.code)
        self.assertEqual("G2-Vx", raised.exception.details["rule_id"])
        self.assertIn("tw", raised.exception.details["missing_fields"])

    def test_router_returns_only_implemented_rules_for_supported_case(self):
        case = _build_case(pu=0.0, mux=150.0, muy=0.0, vu=0.0)
        section = _build_w_section(zx=120000.0)

        rules = ProfileRouter.get_rules(case, section)

        rule_names = {rule.__class__.__name__ for rule in rules}
        self.assertEqual(2, len(rules))
        self.assertIn("FlexureF2YieldRule", rule_names)
        self.assertIn("FlexureF2LtbRule", rule_names)

    def test_router_reports_major_and_minor_flexure_rules_when_mux_and_muy_exist(self):
        case = _build_case(pu=0.0, mux=150.0, muy=80.0, vu=0.0)
        section = _build_w_section(zx=120000.0)

        rules = ProfileRouter.get_rules(case, section)

        rule_names = {rule.__class__.__name__ for rule in rules}
        self.assertEqual(4, len(rules))
        self.assertEqual(
            {"FlexureF2YieldRule", "FlexureF2LtbRule", "FlexureF6YieldRule", "FlexureF6FlbRule"},
            rule_names,
        )

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
            ho=600.0,
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
            ho=900.0,
            J=2500.0e3,
            Cw=96000.0e9,
            **{"bf/2tf": 20.0, "h/tw": 120.0},
        )

        rules = ProfileRouter.get_rules(case, section)
        rule_names = {rule.__class__.__name__ for rule in rules}
        self.assertIn("AxialE7Rule", rule_names)

    def test_router_uses_only_e3_for_solid_rectangular_compression(self):
        case = _build_case(pu=600.0, mux=0.0, muy=0.0, vu=0.0)
        section = Section(
            name="SR200X100",
            type="SOLID_RECTANGULAR",
            A=20000.0,
            Ix=66.6666667e6,
            Iy=16.6666667e6,
            rx=57.7350269,
            ry=28.8675135,
        )

        rules = ProfileRouter.get_rules(case, section)
        rule_names = {rule.__class__.__name__ for rule in rules}
        self.assertEqual(1, len(rules))
        self.assertIn("AxialE3Rule", rule_names)

    def test_router_uses_only_d2_for_solid_circular_tension(self):
        case = _build_case(pu=-250.0, mux=0.0, muy=0.0, vu=0.0)
        section = Section(
            name="SC150",
            type="SOLID_CIRCULAR",
            A=17671.4587,
            Ix=24.852272e6,
            Iy=24.852272e6,
            rx=37.5,
            ry=37.5,
        )

        rules = ProfileRouter.get_rules(case, section)
        rule_names = {rule.__class__.__name__ for rule in rules}
        self.assertEqual(2, len(rules))
        self.assertIn("TensionRule", rule_names)
        self.assertIn("TensionRuptureRule", rule_names)


if __name__ == "__main__":
    unittest.main()
