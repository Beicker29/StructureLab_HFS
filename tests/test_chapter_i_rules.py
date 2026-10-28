import unittest

from steel_design.domain.errors import RuleNotImplementedError
from steel_design.domain.routing.profile_router import ProfileRouter
from steel_design.domain.rules.composite_rules import (
    CompositeI2EncasedCompressionRule,
    CompositeI2FilledCompressionRule,
    CompositeI5CombinedRule,
    CompositeI3_1cRule,
    CompositeI4_1EncasedGoverningRule,
    CompositeI4_1FilledRule,
)
from steel_design.models import Connection, Factors, Lengths, Loads, Material, SteelCase
from steel_design.sections.models import Section


def _base_case(*, section_name: str, loads: Loads, composite: dict) -> SteelCase:
    return SteelCase(
        section_name=section_name,
        design_method="LRFD",
        material=Material(Fy=345.0, Fu=450.0, E=200000.0),
        loads=loads,
        lengths=Lengths(Lx=3000.0, Ly=3000.0, Lz=3000.0, Lb=3000.0),
        factors=Factors(Kx=1.0, Ky=1.0, Kz=1.0, Cb=1.0),
        connection=Connection(),
        composite=composite,
    )


def _w_section() -> Section:
    return Section(
        name="W14X90",
        type="W",
        A=17000.0,
        Ix=2730.0e6,
        Iy=494.0e6,
        Sx=2270.0e3,
        Sy=691.0e3,
        Zx=2590.0e3,
        Zy=1080.0e3,
        rx=331.0,
        ry=141.0,
        d=373.0,
        tw=11.0,
        bf=373.0,
        tf=18.0,
        ho=600.0,
        J=6130.0e3,
        Cw=30000.0e9,
        **{"bf/2tf": 6.7, "h/tw": 35.6},
    )


def _rect_hss_section() -> Section:
    return Section(
        name="PTE100X60X4",
        type="RECTANGULAR_HSS",
        A=1210.0,
        Ix=1.64e6,
        Iy=0.71e6,
        Sx=32800.0,
        Sy=23600.0,
        Zx=38100.0,
        Zy=27700.0,
        rx=36.8,
        ry=24.2,
        h=92.0,
        b=52.0,
        tdes=3.6,
        **{"h/tdes": 25.56, "b/tdes": 14.44},
    )


def _round_hss_section() -> Section:
    return Section(
        name='HSS8X0.375',
        type="CIRCULAR_HSS",
        A=5700.0,
        Ix=20.8e6,
        Iy=20.8e6,
        Sx=230000.0,
        Sy=230000.0,
        Zx=270000.0,
        Zy=270000.0,
        rx=60.4,
        ry=60.4,
        OD=219.1,
        tdes=8.8,
        **{"D/t": 24.9},
    )


def _rect_hss_noncompact_section() -> Section:
    return Section(
        name="PTE200X200X2",
        type="RECTANGULAR_HSS",
        A=1550.0,
        Ix=8.20e6,
        Iy=8.20e6,
        Sx=82000.0,
        Sy=82000.0,
        Zx=94000.0,
        Zy=94000.0,
        rx=72.7,
        ry=72.7,
        h=200.0,
        b=200.0,
        tdes=2.0,
        **{"h/tdes": 100.0, "b/tdes": 100.0},
    )


class ChapterIRulesTests(unittest.TestCase):
    def test_router_selects_chapter_i_for_encased_case(self):
        case = _base_case(
            section_name="W14X90",
            loads=Loads(Pu=800.0, Mux=0.0, Muy=0.0, Vux=200.0, Vuy=0.0),
            composite={
                "role": "ENCASED_MEMBER",
                "nominal_strength_method": "PLASTIC",
                "concrete": {"fc": 35.0, "wc": 2400.0},
                "geometry": {"B": 500.0, "H": 500.0, "cover": 40.0},
                "reinforcement": {
                    "longitudinal_bars": [{"count": 8, "db": 25.0, "fy": 420.0, "x": 180.0, "y": 180.0}],
                    "transverse": {"db": 10.0, "spacing": 200.0, "fy": 420.0, "type": "ties"},
                },
            },
        )
        rules = ProfileRouter.get_rules(case, _w_section())
        names = {rule.__class__.__name__ for rule in rules}
        self.assertIn("CompositeI1Rule", names)
        self.assertIn("CompositeI2EncasedCompressionRule", names)
        self.assertIn("CompositeI3_3Rule", names)
        self.assertIn("CompositeI4_1EncasedGoverningRule", names)

    def test_router_adds_i5_for_filled_axial_plus_flexure(self):
        case = _base_case(
            section_name="PTE100X60X4",
            loads=Loads(Pu=250.0, Mux=30.0, Muy=0.0, Vu=0.0),
            composite={
                "role": "FILLED_MEMBER",
                "nominal_strength_method": "ELASTIC",
                "concrete": {"fc": 30.0, "wc": 2400.0},
                "reinforcement": {"longitudinal_bars": []},
            },
        )
        rules = ProfileRouter.get_rules(case, _rect_hss_section())
        names = {rule.__class__.__name__ for rule in rules}
        self.assertIn("CompositeI5CombinedRule", names)

    def test_router_fails_hard_for_strain_compat_method(self):
        case = _base_case(
            section_name="W14X90",
            loads=Loads(Pu=600.0, Mux=0.0, Muy=0.0, Vu=0.0),
            composite={
                "role": "ENCASED_MEMBER",
                "nominal_strength_method": "STRAIN_COMPAT",
                "concrete": {"fc": 35.0, "wc": 2400.0},
                "geometry": {"B": 500.0, "H": 500.0, "cover": 40.0},
                "reinforcement": {
                    "longitudinal_bars": [{"count": 8, "db": 25.0, "fy": 420.0, "x": 180.0, "y": 180.0}],
                    "transverse": {"db": 10.0, "spacing": 200.0, "fy": 420.0, "type": "ties"},
                },
            },
        )
        with self.assertRaises(RuleNotImplementedError) as raised:
            ProfileRouter.get_rules(case, _w_section())
        self.assertEqual("RULE_NOT_IMPLEMENTED", raised.exception.code)
        self.assertEqual("I1.2", raised.exception.details["rule_id"])

    def test_i2_encased_compression_rule_returns_positive_capacity(self):
        case = _base_case(
            section_name="W14X90",
            loads=Loads(Pu=1200.0, Mux=0.0, Muy=0.0, Vu=0.0),
            composite={
                "role": "ENCASED_MEMBER",
                "nominal_strength_method": "ELASTIC",
                "concrete": {"fc": 35.0, "wc": 2400.0},
                "geometry": {"B": 600.0, "H": 600.0, "cover": 40.0},
                "reinforcement": {
                    "longitudinal_bars": [{"count": 8, "db": 28.0, "fy": 420.0, "x": 220.0, "y": 220.0}],
                    "transverse": {"db": 10.0, "spacing": 180.0, "fy": 420.0, "type": "ties"},
                },
            },
        )
        result = CompositeI2EncasedCompressionRule().check(case, _w_section())
        self.assertEqual("I2-1b", result.clause)
        self.assertGreater(result.capacity, 0.0)
        self.assertIn("Pno_n_I2_7", result.details["memory"]["intermediate"])

    def test_i2_filled_compression_rule_returns_positive_capacity(self):
        case = _base_case(
            section_name="PTE100X60X4",
            loads=Loads(Pu=400.0, Mux=0.0, Muy=0.0, Vu=0.0),
            composite={
                "role": "FILLED_MEMBER",
                "nominal_strength_method": "PLASTIC",
                "concrete": {"fc": 30.0, "wc": 2400.0},
                "reinforcement": {"longitudinal_bars": []},
            },
        )
        result = CompositeI2FilledCompressionRule().check(case, _rect_hss_section())
        self.assertEqual("I2-2", result.clause)
        self.assertGreater(result.capacity, 0.0)
        self.assertIn("classification_I1_4", result.details["memory"]["intermediate"])

    def test_i3_1c_fails_when_no_anchor_capacity(self):
        case = _base_case(
            section_name="W14X90",
            loads=Loads(Pu=0.0, Mux=120.0, Muy=0.0, Vu=0.0),
            composite={
                "role": "COMPOSITE_BEAM",
                "nominal_strength_method": "PLASTIC",
                "concrete": {"fc": 30.0, "wc": 2400.0},
                "geometry": {"slab_effective_width": 2000.0, "slab_thickness": 120.0, "deck_present": True},
                "anchors": {"groups": []},
            },
        )
        result = CompositeI3_1cRule().check(case, _w_section())
        self.assertEqual("I3-1c", result.clause)
        self.assertEqual("FAIL", result.status.value)

    def test_i4_encased_governing_reports_subcheck_governance(self):
        case = _base_case(
            section_name="W14X90",
            loads=Loads(Pu=200.0, Mux=0.0, Muy=0.0, Vux=180.0, Vuy=0.0),
            composite={
                "role": "ENCASED_MEMBER",
                "nominal_strength_method": "PLASTIC",
                "concrete": {"fc": 35.0, "wc": 2400.0},
                "geometry": {"B": 500.0, "H": 600.0, "cover": 40.0},
                "reinforcement": {
                    "longitudinal_bars": [{"count": 8, "db": 25.0, "fy": 420.0, "x": 180.0, "y": 220.0}],
                    "transverse": {"db": 10.0, "spacing": 150.0, "fy": 420.0, "type": "ties"},
                },
            },
        )
        result = CompositeI4_1EncasedGoverningRule().check(case, _w_section())
        self.assertEqual("I4-1", result.clause)
        self.assertIn("governing_subcheck", result.details["memory"]["intermediate"])

    def test_i4_filled_round_returns_capacity(self):
        case = _base_case(
            section_name='HSS8X0.375',
            loads=Loads(Pu=150.0, Mux=20.0, Muy=0.0, Vux=100.0, Vuy=0.0),
            composite={
                "role": "FILLED_MEMBER",
                "nominal_strength_method": "ELASTIC",
                "concrete": {"fc": 30.0, "wc": 2400.0},
                "reinforcement": {"longitudinal_bars": []},
            },
        )
        result = CompositeI4_1FilledRule().check(case, _round_hss_section())
        self.assertEqual("I4-1", result.clause)
        self.assertGreater(result.capacity, 0.0)

    def test_i5_method_1_h1_1_returns_interaction_ratio(self):
        case = _base_case(
            section_name="PTE100X60X4",
            loads=Loads(Pu=250.0, Mux=25.0, Muy=0.0, Vu=0.0),
            composite={
                "role": "FILLED_MEMBER",
                "nominal_strength_method": "ELASTIC",
                "concrete": {"fc": 30.0, "wc": 2400.0},
                "reinforcement": {"longitudinal_bars": []},
                "i5": {"method": "METHOD_1_H1_1"},
            },
        )
        result = CompositeI5CombinedRule().check(case, _rect_hss_section())
        self.assertEqual("I5", result.clause)
        self.assertEqual("METHOD_1_H1_1", result.details["memory"]["inputs"]["method"])

    def test_i5_method_2_runs_for_filled_with_tabulated_points(self):
        case = _base_case(
            section_name="PTE100X60X4",
            loads=Loads(Pu=250.0, Mux=25.0, Muy=5.0, Vu=0.0),
            composite={
                "role": "FILLED_MEMBER",
                "nominal_strength_method": "PLASTIC",
                "concrete": {"fc": 30.0, "wc": 2400.0},
                "reinforcement": {"longitudinal_bars": []},
                "i5": {"method": "METHOD_2_PLASTIC_INTERACTION"},
            },
        )
        result = CompositeI5CombinedRule().check(case, _rect_hss_section())
        self.assertEqual("I5", result.clause)
        self.assertEqual("METHOD_2_PLASTIC_INTERACTION", result.details["memory"]["inputs"]["method"])
        method_data = result.details["memory"]["intermediate"]["method_data"]
        self.assertEqual("6-3", method_data["table_reference"])
        self.assertIn("interaction_points_by_axis", method_data)
        self.assertIn("x", method_data["interaction_points_by_axis"])
        self.assertIn("y", method_data["interaction_points_by_axis"])

    def test_i5_method_4_direct_interaction_runs_for_noncompact_filled(self):
        case = _base_case(
            section_name="PTE200X200X2",
            loads=Loads(Pu=250.0, Mux=20.0, Muy=10.0, Vu=0.0),
            composite={
                "role": "FILLED_MEMBER",
                "nominal_strength_method": "ELASTIC",
                "concrete": {"fc": 30.0, "wc": 2400.0},
                "reinforcement": {"longitudinal_bars": []},
                "i5": {"method": "METHOD_4_DIRECT_INTERACTION"},
            },
        )
        result = CompositeI5CombinedRule().check(case, _rect_hss_noncompact_section())
        self.assertEqual("I5", result.clause)
        self.assertEqual("METHOD_4_DIRECT_INTERACTION", result.details["memory"]["inputs"]["method"])


if __name__ == "__main__":
    unittest.main()
