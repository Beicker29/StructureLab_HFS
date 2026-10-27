import unittest

from src.steel_design.domain.routing.profile_router import ProfileRouter
from src.steel_design.domain.errors import IncompleteSectionDataError, RuleNotImplementedError
from src.steel_design.domain.rules.combined_hss_rules import HssCombinedH3_2Rule, HssTorsionH3_1Rule
from src.steel_design.models import Connection, Factors, Lengths, Loads, Material, SteelCase
from src.steel_design.sections.models import Section


def _case(*, pu=0.0, mux=0.0, muy=0.0, vux=0.0, vuy=0.0, vu=0.0, tu=0.0) -> SteelCase:
    return SteelCase(
        section_name="TEST",
        design_method="LRFD",
        material=Material(Fy=345.0, Fu=450.0, E=200000.0),
        loads=Loads(Pu=pu, Mux=mux, Muy=muy, Vux=vux, Vuy=vuy, Vu=vu, Tu=tu),
        lengths=Lengths(Lx=3000.0, Ly=3000.0, Lz=3000.0, Lb=3000.0),
        factors=Factors(Kx=1.0, Ky=1.0, Kz=1.0, Cb=1.0),
        connection=Connection(An=1200.0, U=0.9),
    )


def _rect_hss_section() -> Section:
    return Section(
        name="PTE50X30X2.5MM",
        type="RECTANGULAR_HSS",
        A=336.0,
        Ix=110111.0,
        Iy=46725.0,
        Sx=4300.0,
        Sy=3000.0,
        Zx=5200.0,
        Zy=3600.0,
        rx=18.1,
        ry=11.8,
        J=110111.0,
        h=43.0,
        b=23.0,
        tdes=2.325,
        **{"b/tdes": 9.89, "h/tdes": 18.49},
    )


def _round_hss_section() -> Section:
    return Section(
        name='PTER4"X6.00MM',
        type="CIRCULAR_HSS",
        A=1905.0,
        Ix=2760000.0,
        Iy=2760000.0,
        Sx=48200.0,
        Sy=48200.0,
        Zx=62000.0,
        Zy=62000.0,
        rx=38.0,
        ry=38.0,
        J=5646702.0,
        C=103876.0,
        OD=114.3,
        tdes=5.58,
        **{"D/t": 18.48},
    )


class ChapterHRulesTests(unittest.TestCase):
    def test_router_adds_h1_h3_for_hss_combined_actions(self):
        case = _case(pu=60.0, mux=4.0, muy=2.0, vux=12.0, vuy=6.0, tu=1.5)
        rules = ProfileRouter.get_rules(case, _rect_hss_section())
        names = {rule.__class__.__name__ for rule in rules}
        self.assertIn("CombinedH1HssRule", names)
        self.assertIn("HssTorsionH3_1Rule", names)
        self.assertIn("HssCombinedH3_2Rule", names)

    def test_h3_1_round_hss_returns_positive_torsional_capacity(self):
        case = _case(tu=8.0)
        result = HssTorsionH3_1Rule().check(case, _round_hss_section())
        self.assertEqual("H3-1", result.clause)
        self.assertGreater(result.capacity, 0.0)
        self.assertIn("Fcr_mpa", result.details["memory"]["intermediate"])

    def test_h3_2_uses_threshold_branch_when_tr_not_greater_than_0p2_tc(self):
        case = _case(pu=40.0, mux=2.0, muy=1.0, vux=4.0, tu=0.2)
        # HFS-013: explicit synthetic C isolates the threshold permission.
        section = _rect_hss_section().model_copy(update={"c": 6000.0})
        with self.assertRaises(RuleNotImplementedError) as caught:
            HssCombinedH3_2Rule().check(case, section)
        self.assertLessEqual(caught.exception.details["Tr_over_Tc"], 0.2)

    def test_h3_2_missing_c_does_not_reconstruct_outer_dimensions(self):
        case = _case(pu=40.0, mux=2.0, muy=1.0, vux=4.0, tu=5.0)
        with self.assertRaises(IncompleteSectionDataError) as caught:
            HssCombinedH3_2Rule().check(case, _rect_hss_section())
        self.assertIn("c", caught.exception.details["missing_fields"])


if __name__ == "__main__":
    unittest.main()
