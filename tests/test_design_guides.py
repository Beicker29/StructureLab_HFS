"""Product vs AISC Design Guide 6, 2nd ed. (2025) and Design Guide 38 (2023) numerical examples, LRFD.

The guides use US units, E = 29000 ksi and properties rounded to three figures; the program uses E = 200000 MPa and
the metric concrete modulus of the Specification. Agreement is checked with a tolerance, as in test_design_examples.
Sections absent from the catalog are built from the properties printed in the example.
"""
import pytest

from steel_design.engine import SteelDesignEngine
from steel_design.models import SteelCase
from steel_design.sections.models import Section
from steel_design.sections.repository import SectionRepository

from test_design_examples import FT, FY50, IN, KIP, KIPFT, KSI, TOL, filled_member, rect_hss

WC = 2323.0        # 145 lb/ft3
KIPIN = KIPFT / 12


EXTRA = [
    # Design Guide 6, Examples 2.5: welded box 25 x 25 x 1/2 in; Zs and Is printed in the example.
    rect_hss("BOX25X25X1/2", A=49.0, t=0.5, B=25, H=25, b_t=48, h_t=48, Sx=4950 / 12.5, Zx=450, Iy=4950, Zy=450),
    # Design Guide 6, Example 2.7, without the bars for shear.
    Section(name="HSS16.000X0.250", type="CIRCULAR_HSS", OD=16 * IN, tdes=0.233 * IN, A=11.5 * IN**2, Ix=359 * IN**4,
            Iy=359 * IN**4, **{"D/t": 68.7}),
]


def encased_w14x211(bars="eight", L=15, **demands):
    """Design Guide 6, Example 2.4: W14X211 in 36 x 36 in, f'c = 10 ksi, No. 8 bars, No. 4 ties at 16 in."""
    e = 15.5 * IN
    faces = [(e, e), (e, 0.0), (e, -e), (-e, e), (-e, 0.0), (-e, -e)]
    positions = faces + ([(0.0, e), (0.0, -e)] if bars == "eight" else [])
    data = dict(section_name="W14X211", material={"Fy": FY50}, **demands,
                composite={"kind": "encased", "interaction": "M2S" if demands.get("Pu") and demands.get("Muy") else "H1",
                           "concrete": {"fc": 10 * KSI, "wc": WC, "lightweight": False},
                           "encased": {"H": 36 * IN, "B": 36 * IN, "Fysr": 60 * KSI,
                                       "bars": [{"area": 0.79 * IN**2, "db": 1.0 * IN, "x": x, "y": y} for x, y in positions],
                                       "transverse": {"db": 13, "spacing": 400}, "flexure_method": "composite",
                                       "anchors_provided": True}})
    if demands.get("Pu"):
        data["lengths"] = {"Lx": L * FT, "Ly": L * FT, "Lz": L * FT}
    return data


def box_25(**demands):
    L = demands.pop("L", None)
    interaction = demands.pop("interaction", "H1")
    return filled_member("BOX25X25X1/2", 6, L=L, interaction=interaction, **demands)


def wall(length, tsc, t, fc=6.0, b=12.0, st=12.0, dtie=0.625, Lc=None, **demands):
    """Planar SpeedCore wall. The flange plates have the thickness of the web plates (Fig. 2-11 of the guide)."""
    data = dict(section_name="MURO", material={"Fy": FY50}, **demands,
                composite={"kind": "wall", "concrete": {"fc": fc * KSI, "wc": WC, "lightweight": False},
                           "wall": {"length": length * IN, "tsc": tsc * IN, "t": t * IN, "tf": t * IN, "b": b * IN,
                                    "st": st * IN, "dtie": dtie * IN}})
    if Lc:
        data["lengths"] = {"Lx": Lc * FT, "Ly": Lc * FT, "Lz": Lc * FT}
    return data


GUIDES = {
    "DG6-2.4-Pc": ("W14X211 embebido, Lc = 15 ft", encased_w14x211(Pu=1.0), "axial", 9900, "kip"),
    "DG6-2.4-Mcy": ("W14X211 embebido, eje y, I3.3a(3), solo las 6 barras de las caras",
                    encased_w14x211("six", Muy=1.0), "flexure_y", 3330, "kip-ft"),
    "DG6-2.4-M2S": ("W14X211 embebido, Pu = 1000 kips, Muy = 3160 kip-ft, C-I5-1a",
                    encased_w14x211("six", Pu=1000 * KIP, Muy=3160 * KIPFT), "interaction", 0.949, "ratio"),
    "DG6-2.4-Vcy": ("W14X211 embebido, cortante del acero en el eje menor (G6)", encased_w14x211(Vuy=1.0), "shear_y", 1330, "kip"),
    "DG6-2.5-Pc": ("Cajón 25 x 25 x 1/2 in relleno, f'c = 6 ksi, Lc = 30 ft", box_25(Pu=1.0, L=30), "axial", 3540, "kip"),
    "DG6-2.5-Mc": ("Cajón 25 x 25 x 1/2 in relleno, flexión compacta", box_25(Mux=1.0), "flexure_x", 1980, "kip-ft"),
    "DG6-2.5-M2S": ("Cajón relleno, Pu = 1500 kips, Mux = 1800 kip-ft, C-I5-1a",
                    box_25(Pu=1500 * KIP, Mux=1800 * KIPFT, L=30, interaction="M2S"), "interaction", 0.909, "ratio"),
    "DG6-2.5-Vc": ("Cajón relleno, cortante I4-1", box_25(Vux=1.0), "shear_x", 751, "kip"),
    "DG6-2.7-Vc": ("HSS16.000X0.250 relleno, cortante I4-1", filled_member("HSS16.000X0.250", 8, Vux=1.0), "shear_x", 226, "kip"),
    "DG38-2.1-Mc": ("Muro L = 300, tsc = 18, t = 1/2 in, flexión", wall(300, 18, 0.5, Mux=1.0), "flexure_x", 1590000, "kip-in"),
    "DG38-2.1-Vc": ("Igual, cortante I4-2", wall(300, 18, 0.5, Vux=1.0), "shear_x", 12300, "kip"),
    "DG38-2.2-T": ("Muro L = 150, tsc = 18, t = 1/2 in, tracción", wall(150, 18, 0.5, Pu=-1.0), "axial", 7520, "kip"),
    "DG38-2.2-Pc": ("Igual, compresión, Lc = 17 ft", wall(150, 18, 0.5, Pu=1.0, Lc=17), "axial", 17600, "kip"),
    "DG38-2.2-Vc": ("Igual, cortante I4-2", wall(150, 18, 0.5, Vux=1.0), "shear_x", 6170, "kip"),
    "DG38-2.2-MT": ("Igual, Tr = 1310 kips, Mr = 147000 kip-in (A.1.2)",
                    wall(150, 18, 0.5, Pu=-1310 * KIP, Mux=147000 * KIPIN), "interaction", 0.385, "ratio"),
    "DG38-2.2-MC": ("Igual, Pr = 6110 kips, Mr = 147000 kip-in (A.1.3)",
                    wall(150, 18, 0.5, Pu=6110 * KIP, Mux=147000 * KIPIN, Lc=17), "interaction", 0.279, "ratio"),
    "DG38-3.1-Mc": ("Muro L = 300, tsc = 16, t = 5/16 in, flexión", wall(300, 16, 0.3125, Mux=1.0), "flexure_x", 1040000, "kip-in"),
    "DG38-3.1-Vc": ("Igual, cortante I4-2", wall(300, 16, 0.3125, Vux=1.0), "shear_x", 8190, "kip"),
    "DG38-4.1-T": ("Muro L = 132, tsc = 24, t = 9/16 in, tracción", wall(132, 24, 0.5625, Pu=-1.0), "axial", 7830, "kip"),
    "DG38-4.1-Pc": ("Igual, compresión, Lc = 17 ft", wall(132, 24, 0.5625, Pu=1.0, Lc=17), "axial", 20400, "kip"),
    "DG38-4.1-Vc": ("Igual, cortante I4-2", wall(132, 24, 0.5625, Vux=1.0), "shear_x", 6310, "kip"),
    "DG38-4.1-MT": ("Igual, Tr = 4900 kips, Mr = 166000 kip-in (A.1.2)",
                    wall(132, 24, 0.5625, Pu=-4900 * KIP, Mux=166000 * KIPIN), "interaction", 166 / 213, "ratio"),
    "DG38-4.1-MC": ("Igual, Pr = 4900 kips, Mr = 166000 kip-in (A.1.3)",
                    wall(132, 24, 0.5625, Pu=4900 * KIP, Mux=166000 * KIPIN, Lc=17), "interaction", 166 / 507, "ratio"),
}
# The program is below the guide, on the safe side, for a declared reason.
EXPECTED_BELOW = {
    "DG6-2.5-Vc": "la guía toma Av = 2·H·t con el ancho total en el cajón; el programa usa 2·h·t con h plano, como I.6 en HSS",
}
UNITS = {"kip": KIP, "kip-ft": KIPFT, "kip-in": KIPIN}


@pytest.fixture(scope="module")
def guides_engine(catalog):
    repository = SectionRepository()
    repository.load([*catalog, *EXTRA])
    return SteelDesignEngine(repository)


def value_of(engine, key):
    _, data, check_id, _, unit = GUIDES[key]
    check = engine.run(SteelCase(**data)).check(check_id)
    assert check.capacity is not None, check.errors
    return check.ratio if unit == "ratio" else check.capacity / UNITS[unit]


@pytest.mark.parametrize("key", sorted(set(GUIDES) - set(EXPECTED_BELOW)))
def test_program_matches_design_guide(guides_engine, key):
    assert value_of(guides_engine, key) == pytest.approx(GUIDES[key][3], rel=TOL), key


@pytest.mark.parametrize("key", sorted(EXPECTED_BELOW))
def test_program_is_below_a_declared_guide_value(guides_engine, key):
    assert 0.90 * GUIDES[key][3] < value_of(guides_engine, key) < GUIDES[key][3], key


def test_uncoupled_wall_of_example_21_meets_every_limit(guides_engine):
    # Example 2.1: b/t = 24 <= 28.9 and S/tp = 24 <= 24.5, with tie bars of 5/8 in at 12 in.
    result = guides_engine.run(SteelCase(**wall(300, 18, 0.5, Mux=695000 * KIPIN, Vux=490 * KIP)))
    assert result.status.value == "PASS", result.errors


def test_wall_steel_matches_the_area_and_inertia_of_example_21(guides_engine):
    section = guides_engine.section_for(SteelCase(**wall(300, 18, 0.5, Mux=1.0)))
    assert section.area / IN**2 == pytest.approx(317, rel=TOL)
    assert section.ix / IN**4 == pytest.approx(2.63e6, rel=TOL)


def test_round_filled_noncompact_flexure_of_example_27_stays_blocked(guides_engine):
    # Example 2.7 needs My of the composite column program of the guide (D/t = 68.7 > 52.2): not computed here.
    check = guides_engine.run(SteelCase(**filled_member("HSS16.000X0.250", 8, Mux=1.0))).check("flexure_x")
    assert check.status.value == "INCOMPLETE" and check.errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


def test_high_strength_materials_of_example_26_stay_blocked(guides_engine):
    # Example 2.6: f'c = 12 ksi (83 MPa) needs Appendix 2, not implemented.
    result = guides_engine.run(SteelCase(**filled_member("BOX25X25X1/2", 12, Vux=1.0)))
    assert result.errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"
