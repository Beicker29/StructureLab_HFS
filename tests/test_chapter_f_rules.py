import unittest

from src.steel_design.domain.errors import ValidationError
from src.steel_design.domain.routing.profile_router import ProfileRouter
from src.steel_design.domain.rules.flexure_rule import FlexureF10Rule, FlexureF11Rule
from src.steel_design.domain.validation import validate_case
from src.steel_design.models import (
    AngleFlexureAxis,
    AngleLtbRestraint,
    Connection,
    Factors,
    Lengths,
    Loads,
    Material,
    SteelCase,
)
from src.steel_design.sections.models import Section


def _case(*, mux=0.0, muy=0.0, design_method="LRFD", connection=None):
    return SteelCase(
        section_name="TEST",
        design_method=design_method,
        material=Material(Fy=345.0, Fu=450.0, E=200000.0),
        loads=Loads(Pu=0.0, Mux=mux, Muy=muy, Vu=0.0),
        lengths=Lengths(Lx=3000.0, Ly=3000.0, Lz=3000.0, Lb=3000.0),
        factors=Factors(Kx=1.0, Ky=1.0, Kz=1.0, Cb=1.0),
        connection=connection or Connection(),
    )


class ChapterFRoutingAndRulesTests(unittest.TestCase):
    def _w_section(self, *, flange_ratio, web_ratio):
        return Section(
            name="W14X90",
            type="W",
            A=17000.0,
            Ix=2500.0e6,
            Iy=350.0e6,
            Sx=1800.0e3,
            Sy=500.0e3,
            Zx=2200.0e3,
            Zy=700.0e3,
            # HFS-012: keep the declared class, with consistent synthetic geometry.
            bf=2.0 * 16.0 * flange_ratio,
            tf=16.0,
            tw=10.0,
            h=10.0 * web_ratio,
            rx=90.0,
            ry=55.0,
            J=4000.0e3,
            Cw=20000.0e9,
            ho=300.0,
            **{"bf/2tf": flange_ratio, "h/tw": web_ratio},
        )

    def test_router_selects_f2_for_compact_w_major(self):
        rules = ProfileRouter.get_rules(_case(mux=120.0), self._w_section(flange_ratio=6.0, web_ratio=30.0))
        rule_names = {rule.__class__.__name__ for rule in rules}
        self.assertEqual({"FlexureF2YieldRule", "FlexureF2LtbRule"}, rule_names)

    def test_router_selects_f3_f4_f5_for_w_major_by_web_flange_class(self):
        rules_f3 = ProfileRouter.get_rules(_case(mux=120.0), self._w_section(flange_ratio=12.0, web_ratio=30.0))
        self.assertEqual(
            {"FlexureF3YieldRule", "FlexureF3LtbRule", "FlexureF3FlbRule"},
            {rule.__class__.__name__ for rule in rules_f3},
        )

        rules_f4 = ProfileRouter.get_rules(_case(mux=120.0), self._w_section(flange_ratio=8.0, web_ratio=100.0))
        self.assertEqual(
            {"FlexureF4CompressionYieldRule", "FlexureF4LtbRule", "FlexureF4FlbRule", "FlexureF4TensionYieldRule"},
            {rule.__class__.__name__ for rule in rules_f4},
        )

        rules_f5 = ProfileRouter.get_rules(_case(mux=120.0), self._w_section(flange_ratio=8.0, web_ratio=150.0))
        self.assertEqual(
            {"FlexureF5CompressionYieldRule", "FlexureF5LtbRule", "FlexureF5FlbRule", "FlexureF5TensionYieldRule"},
            {rule.__class__.__name__ for rule in rules_f5},
        )

    def test_router_selects_f6_for_w_minor_axis(self):
        rules = ProfileRouter.get_rules(_case(muy=80.0), self._w_section(flange_ratio=6.0, web_ratio=30.0))
        self.assertEqual({"FlexureF6YieldRule", "FlexureF6FlbRule"}, {rule.__class__.__name__ for rule in rules})

    def test_validate_case_rejects_asd_for_flexure_scope(self):
        with self.assertRaises(ValidationError):
            validate_case(_case(mux=100.0, design_method="ASD"))

    def test_f10_requires_explicit_connection_fields(self):
        section = Section(
            name="L4X4X3/8",
            type="SINGLE_ANGLE",
            A=1800.0,
            b=100.0,
            t=9.5,
            Sx=30000.0,
            Sy=22000.0,
            Sz=18000.0,
            **{"b/t": 10.5},
        )
        with self.assertRaises(ValidationError):
            FlexureF10Rule().check(_case(mux=40.0), section)

        case_ok = _case(
            mux=40.0,
            connection=Connection(
                angle_flexure_axis=AngleFlexureAxis.MAJOR_PRINCIPAL,
                angle_ltb_restraint=AngleLtbRestraint.DISCRETE_UNBRACED,
            ),
        )
        result = FlexureF10Rule().check(case_ok, section)
        self.assertEqual("F10-3", result.clause)
        self.assertGreater(result.capacity, 0.0)

    def test_f11_runs_for_solid_rectangular(self):
        section = Section(
            name="SR200X100",
            type="SOLID_RECTANGULAR",
            A=20000.0,
            h=200.0,
            b=100.0,
            Ix=66.6666667e6,
            Iy=16.6666667e6,
            Sx=666666.667,
            Sy=333333.333,
            Zx=1000000.0,
            Zy=500000.0,
            rx=57.7350269,
            ry=28.8675135,
        )
        result = FlexureF11Rule().check(_case(mux=120.0), section)
        self.assertEqual("F11-2", result.clause)
        self.assertGreater(result.capacity, 0.0)


if __name__ == "__main__":
    unittest.main()
