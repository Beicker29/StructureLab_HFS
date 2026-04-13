import unittest

from src.steel_design.domain.routing.profile_router import ProfileRouter
from src.steel_design.domain.rules.shear_rules import ShearG2VxRule, ShearG3VxRule, ShearG5VxRule, ShearG6VyRule
from src.steel_design.models import Connection, Factors, Lengths, Loads, Material, SteelCase
from src.steel_design.sections.models import Section


def _case(*, vux=0.0, vuy=0.0, vu=0.0, method="LRFD") -> SteelCase:
    return SteelCase(
        section_name="TEST",
        design_method=method,
        material=Material(Fy=345.0, Fu=450.0, E=200000.0),
        loads=Loads(Pu=0.0, Mux=0.0, Muy=0.0, Vux=vux, Vuy=vuy, Vu=vu),
        lengths=Lengths(Lx=3000.0, Ly=2500.0, Lz=3000.0, Lb=3000.0),
        factors=Factors(Kx=1.0, Ky=1.0, Kz=1.0, Cb=1.0),
        connection=Connection(),
    )


class ChapterGRulesTests(unittest.TestCase):
    def test_g2_w_major_shear_returns_capacity(self):
        section = Section(
            name="W14X90",
            type="W",
            A=17000.0,
            d=360.0,
            tw=8.0,
            bf=200.0,
            tf=12.0,
            **{"h/tw": 20.0},
        )
        result = ShearG2VxRule().check(_case(vux=180.0), section)
        self.assertEqual("G2-1", result.clause)
        self.assertGreater(result.capacity, 0.0)
        self.assertAlmostEqual(1.0, result.details["memory"]["design_factor"]["phi_v"])

    def test_g3_single_angle_major_shear_returns_capacity(self):
        section = Section(
            name="L4X4X3/8",
            type="SINGLE_ANGLE",
            A=1800.0,
            b=100.0,
            t=9.5,
            **{"b/t": 10.5},
        )
        result = ShearG3VxRule().check(_case(vux=60.0), section)
        self.assertEqual("G3-1", result.clause)
        self.assertGreater(result.capacity, 0.0)

    def test_g4_rectangular_hss_routes_both_axes_with_directional_shear(self):
        case = _case(vux=40.0, vuy=20.0)
        section = Section(
            name="PTE50X30X2mm",
            type="RECTANGULAR_HSS",
            A=600.0,
            h=50.0,
            b=30.0,
            t=2.0,
            tdes=2.0,
        )
        rules = ProfileRouter.get_rules(case, section)
        names = {rule.__class__.__name__ for rule in rules}
        self.assertIn("ShearG4VxRule", names)
        self.assertIn("ShearG4VyRule", names)

    def test_g5_circular_hss_major_shear_returns_capacity(self):
        section = Section(
            name="PTER4X6.0",
            type="CIRCULAR_HSS",
            A=2100.0,
            OD=114.3,
            t=6.0,
            tdes=6.0,
            **{"D/t": 19.05},
        )
        result = ShearG5VxRule().check(_case(vux=50.0), section)
        self.assertEqual("G5-1", result.clause)
        self.assertGreater(result.capacity, 0.0)
        self.assertIn("Fcr_branch", result.details["memory"]["intermediate"])

    def test_g6_channel_minor_shear_returns_capacity(self):
        section = Section(
            name="C15X50",
            type="CHANNEL",
            A=9500.0,
            bf=90.0,
            tf=12.0,
            **{"b/t": 7.5},
        )
        result = ShearG6VyRule().check(_case(vuy=40.0), section)
        self.assertEqual("G6-1", result.clause)
        self.assertGreater(result.capacity, 0.0)

    def test_legacy_vu_routes_major_shear_only(self):
        case = _case(vu=80.0)
        section = Section(
            name="W14X90",
            type="W",
            A=17000.0,
            d=360.0,
            tw=8.0,
            bf=200.0,
            tf=12.0,
            **{"h/tw": 20.0},
        )
        rules = ProfileRouter.get_rules(case, section)
        names = {rule.__class__.__name__ for rule in rules}
        self.assertIn("ShearG2VxRule", names)
        self.assertNotIn("ShearG6VyRule", names)


if __name__ == "__main__":
    unittest.main()
