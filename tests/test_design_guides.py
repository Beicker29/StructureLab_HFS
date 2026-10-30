"""Product vs AISC Design Guide 6, 2nd ed. (2025) and Design Guide 38 (2023) numerical examples, LRFD.

The guides use US units, E = 29000 ksi and properties rounded to three figures; the program uses E = 200000 MPa and
the metric concrete modulus of the Specification. Agreement is checked with a tolerance, as in test_design_examples.
Sections absent from the catalog are built from the properties printed in the example.
"""
import json
from pathlib import Path

import pytest

from steel_design.engine import SteelDesignEngine
from steel_design.models import SteelCase
from steel_design.sections.models import Section
from steel_design.sections.repository import SectionRepository

from test_composite import GUIDE_KINDS
from test_design_examples import FT, FY50, IN, KIP, KIPFT, KSI, TOL, filled_member

WC = 2323.0        # 145 lb/ft3
KIPIN = KIPFT / 12


EXTRA = [
    # Design Guide 6, Example 2.7.
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


def box_25_fc(fc, **demands):
    L = demands.pop("L", None)
    interaction = demands.pop("interaction", "H1")
    data = filled_member("BOX25", fc, L=L, interaction=interaction, **demands)
    data["composite"]["box"] = {"B": 25 * IN, "H": 25 * IN, "t": 0.5 * IN}
    return data


def box_25(**demands):
    return box_25_fc(6, **demands)


def wall(length, tsc, t, fc=6.0, b=12.0, st=12.0, dtie=0.625, Lc=None, **demands):
    """Planar SpeedCore wall. The flange plates have the thickness of the web plates (Fig. 2-11 of the guide)."""
    data = dict(section_name="MURO", material={"Fy": FY50}, **demands,
                composite={"kind": "wall", "concrete": {"fc": fc * KSI, "wc": WC, "lightweight": False},
                           "wall": {"length": length * IN, "tsc": tsc * IN, "t": t * IN, "tf": t * IN, "b": b * IN,
                                    "st": st * IN, "dtie": dtie * IN}})
    if Lc:
        data["lengths"] = {"Lx": Lc * FT, "Ly": Lc * FT, "Lz": Lc * FT}
    return data


def round_hss_16(L=None, interaction="H1", **demands):
    """Design Guide 6, Example 2.7: HSS16.000X0.250, f'c = 8 ksi, four No. 7 bars at 5.5 in from the center."""
    e = 5.5 * IN
    positions = [(0.0, e), (0.0, -e), (e, 0.0), (-e, 0.0)]
    data = dict(section_name="HSS16.000X0.250", material={"Fy": FY50}, **demands,
                composite={"kind": "filled", "interaction": interaction,
                           "concrete": {"fc": 8 * KSI, "wc": WC, "lightweight": False},
                           "filled": {"Fysr": 60 * KSI, "transverse": {"db": 10, "spacing": 300},
                                      "bars": [{"area": 0.60 * IN**2, "db": 0.875 * IN, "x": x, "y": y} for x, y in positions]}})
    if L:
        data["lengths"] = {"Lx": L * FT, "Ly": L * FT, "Lz": L * FT}
    return data


GUIDES = {
    "DG6-2.7-Pc": ("HSS16.000X0.250 relleno con 4 barras No. 7, Lc = 20 ft", round_hss_16(L=20, Pu=1.0), "axial", 1230, "kip"),
    "DG6-2.7-Mc": ("Igual, no compacta, Mp y My (I3-5b)", round_hss_16(Mux=1.0), "flexure_x", 318, "kip-ft"),
    "DG6-2.7-I5": ("Igual, Pu = 680 kips, Mux = 264 kip-ft, I5-1a",
                   round_hss_16(L=20, interaction="I5", Pu=680 * KIP, Mux=264 * KIPFT), "interaction", 0.994, "ratio"),
    "DG6-2.7-Vb": ("Igual, cortante I4-1 con el concreto neto de barras", round_hss_16(Vux=1.0), "shear_x", 226, "kip"),
    "DG6-2.6-Pc": ("Cajón 25 x 25 x 1/2 in, f'c = 12 ksi, Lc = 30 ft (Apéndice 2)", box_25_fc(12, Pu=1.0, L=30), "axial", 5030, "kip"),
    "DG6-2.6-Mc": ("Igual, flexión, 90 % de la distribución (Apéndice 2)", box_25_fc(12, Mux=1.0), "flexure_x", 1840, "kip-ft"),
    "DG6-2.6-A2": ("Igual, Pu = 2750 kips, Mux = 740 kip-ft, I5-1a con A-2-3 y A-2-4",
                   box_25_fc(12, Pu=2750 * KIP, Mux=740 * KIPFT, L=30), "interaction", 0.757, "ratio"),
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


@pytest.mark.parametrize("key", sorted(GUIDES))
def test_program_matches_design_guide(guides_engine, key):
    assert value_of(guides_engine, key) == pytest.approx(GUIDES[key][3], rel=TOL), key


def second_order_example(**over):
    """Design Guide 6, Example 2.4: Pu = 1000 kips, Hu = 190 kips, cantilever of 15 ft, Mlt = 2850 kip-ft about y."""
    data = encased_w14x211("six", L=15, Vuy=1.0)
    data["lengths"] = {"Lx": 15 * FT, "Ly": 15 * FT, "Lz": 15 * FT}
    data["composite"]["interaction"] = "M2S"
    data["composite"]["second_order"] = {"axis": "y", "Mnt": 0.0, "Mlt": 2850 * KIPFT, "Pnt": 1000 * KIP, "Plt": 0.0, "M1_M2": 0.0,
                                         "Pstory": 2000 * KIP, "Pmf": 1000 * KIP, "H": 190 * KIP, "L": 15 * FT, "drift": 1.55 * IN,
                                         **over}
    return data


def test_appendix_8_reproduces_example_24(guides_engine):
    result = guides_engine.run(SteelCase(**second_order_example()))
    flexure = result.check("flexure_y")
    info = flexure.result["second_order"]
    assert info["B1"] == pytest.approx(1.00, rel=TOL) and info["B2"] == pytest.approx(1.11, rel=TOL)
    # The LRFD column prints 21,400 kips, but its own data give 0.925(190)(180)/1.55 = 20,410 and its own B2 = 1.11 needs that
    # value (21,400 would give 1.10). The ASD column prints 20,400 kips: it is the comparison used, and the misprint is declared.
    assert info["Pe_story_kN"] / KIP == pytest.approx(20400, rel=TOL)
    # EI* = 239,000,000 kip-in2 in the guide, with Ec = wc^1.5*sqrt(f'c) = 5520 ksi. The program uses the SI form of the Specification
    # (0.043*wc^1.5*sqrt(f'c)), 5% stiffer in the concrete: Pe1 comes out 3.4% higher, which does not move B1 = 1.00.
    pe1 = flexure.result["second_order"]["Pe1_kN"] / KIP
    assert 1.0 < pe1 / (3.141592653589793**2 * 239e6 / 180**2) < 1.04
    assert flexure.demand / KIPFT == pytest.approx(3160, rel=TOL)
    assert result.check("interaction").ratio == pytest.approx(0.949, rel=TOL)


def test_tension_control_of_example_24(guides_engine):
    # eps_t = 0.00695 >= 0.00507, with hn = 7.86 in and the outermost bars at 15.5 in.
    mode = guides_engine.run(SteelCase(**encased_w14x211("six", Muy=1.0))).check("flexure_y").result["modes"]["Y"]
    assert mode["epsilon_t"] == pytest.approx(0.00695, rel=0.02)
    assert mode["epsilon_limit"] == pytest.approx(0.00507, rel=TOL)


def test_tension_control_is_required_only_for_declared_beams(guides_engine):
    data = encased_w14x211("eight", Mux=1.0)
    data["composite"]["flexural_member"] = True
    check = guides_engine.run(SteelCase(**data)).check("flexure_x")
    assert any(r["id"] == "tension_controlled" for r in check.result["requirements"])
    assert not any(r["id"] == "tension_controlled" for r in guides_engine.run(SteelCase(**encased_w14x211("eight", Mux=1.0))).check(
        "flexure_x").result["requirements"])


def test_biaxial_shape_factor_gives_more_strength_than_c_i5_1(guides_engine):
    # Design Guide 6, Section 2.3.2: alpha does not change uniaxial bending and raises the biaxial strength.
    plain = box_25(Mux=900 * KIPFT, Muy=900 * KIPFT, interaction="M2S")
    shaped = box_25(Mux=900 * KIPFT, Muy=900 * KIPFT, interaction="M2S")
    shaped["composite"]["biaxial_shape_factor"] = True
    r_plain = guides_engine.run(SteelCase(**plain)).check("interaction")
    r_shaped = guides_engine.run(SteelCase(**shaped)).check("interaction")
    x = 900 * KIPFT / guides_engine.run(SteelCase(**box_25(Mux=1.0))).check("flexure_x").capacity
    assert r_plain.ratio == pytest.approx(2 * x)
    assert r_shaped.ratio == pytest.approx(2 * x**1.5)
    assert r_shaped.result["governing_equation"] == "DG6 Ec. 2-2a"


def test_service_stiffness_follows_section_28(guides_engine):
    mode = guides_engine.run(SteelCase(**box_25(Pu=1.0, L=30))).check("axial").result["modes"]["FB-x"]
    ec_ic = (mode["EI_eff"] - 200000.0 * (25**4 - 24**4) / 12 * IN**4) / mode["C3"]
    assert mode["EI_service"] == pytest.approx(200000.0 * (25**4 - 24**4) / 12 * IN**4 + 0.4 * mode["C3"] * ec_ic)


def wall_21(**over):
    data = wall(300, 18, 0.5, Pu=1.0, Lc=17)
    data["composite"]["wall"].update(over)
    return data


def test_wall_stiffnesses_of_example_21(guides_engine):
    mode = guides_engine.run(SteelCase(**wall_21())).check("axial").result["modes"]["FB-x"]
    assert mode["EI_eff"] / (KIP * 1000 * IN**2) == pytest.approx(1.36e11, rel=TOL)
    assert mode["EA_eff"] / (KIP * 1000) == pytest.approx(1.95e7, rel=TOL)
    assert mode["GA_eff"] / (KIP * 1000) == pytest.approx(1.25e7, rel=TOL)


def test_slender_plate_alternative_of_commentary_i16a(guides_engine):
    # b/t = 40 > 28.9: Fcr = pi^2*E/(12*0.8^2*1600) with Pno = As*Fcr + 0.7*f'c*Ac (C-I1-1, C-I1-2; DG38 Eqs. 2-2, 2-3).
    strict = guides_engine.run(SteelCase(**wall_21(b=20 * IN, st=12 * IN))).check("axial")
    assert strict.status.value == "FAIL"
    allowed = guides_engine.run(SteelCase(**wall_21(b=20 * IN, allow_slender_plates=True))).check("axial")
    assert allowed.status.value == "PASS"
    mode = allowed.result["modes"]["FB-x"]
    assert mode["Pno_equation"] == "C-I1-2"
    fcr = 3.141592653589793**2 * 200000.0 / (12 * 0.8**2 * 40**2)
    assert mode["Pno_kN"] == pytest.approx((317.0 * IN**2 * fcr + 0.7 * 6 * KSI * 299 * 17 * IN**2) / 1000.0, rel=TOL)


def coupling(b, h, tf, tw, fc=6.0, **demands):
    return dict(section_name="CB", material={"Fy": FY50}, **demands,
                composite={"kind": "coupling_beam", "concrete": {"fc": fc * KSI, "wc": WC, "lightweight": False},
                           "coupling_beam": {"b": b * IN, "h": h * IN, "tf": tf * IN, "tw": tw * IN}})


@pytest.mark.parametrize("b, phi_mn, phi_vn", [(18, 22500, 698), (24, 0.9 * 30700, 716)])
def test_coupling_beams_of_examples_22_and_23(guides_engine, b, phi_mn, phi_vn):
    result = guides_engine.run(SteelCase(**coupling(b, 24, 0.75, 0.5, Mux=1.0, Vux=1.0)))
    assert result.check("flexure_x").capacity / KIPIN == pytest.approx(phi_mn, rel=TOL)
    assert result.check("shear_x").capacity / KIP == pytest.approx(phi_vn, rel=TOL)


def test_coupling_beam_blocks_what_the_guide_does_not_cover(guides_engine):
    axial = coupling(18, 24, 0.75, 0.5, Pu=1.0, lengths={"Lx": 3000, "Ly": 3000, "Lz": 3000})
    assert guides_engine.run(SteelCase(**axial)).status.value == "INCOMPLETE"
    assert guides_engine.run(SteelCase(**coupling(60, 24, 0.5, 0.5, Mux=1.0))).status.value == "INCOMPLETE"       # noncompact


def c_wall(minor="flange_tips", **demands):
    """Design Guide 38, Example 2.3: L = 360, W = 168, tsc_w = 14, tsc_f = 24, tp = 1/2 in, f'c = 6 ksi, ties 12 in."""
    data = dict(section_name="MURO-C", material={"Fy": FY50}, **demands,
                composite={"kind": "c_wall", "concrete": {"fc": 6 * KSI, "wc": WC, "lightweight": False},
                           "c_wall": {"L": 360 * IN, "W": 168 * IN, "tsc_w": 14 * IN, "tsc_f": 24 * IN, "tp": 0.5 * IN,
                                      "b": 12 * IN, "st": 12 * IN, "dtie": 1 * IN, "minor_axis_compression": minor}})
    if demands.get("Pu", 0) > 0:
        data["lengths"] = {"Lx": 17 * FT, "Ly": 17 * FT, "Lz": 17 * FT}
    return data


def test_c_wall_flexure_with_axial_force_of_example_23(guides_engine):
    tension = guides_engine.run(SteelCase(**c_wall(Pu=-12300 * KIP, Muy=722000 * KIPIN))).check("interaction").result["modes"]["I5c"]
    assert tension["equation"] == "DG38 A.2.3"
    assert tension["C_mm"] / IN == pytest.approx(119, rel=TOL)
    assert tension["Mn_at_Pr_kNm"] / KIPIN == pytest.approx(2380000, rel=TOL)
    compression = guides_engine.run(SteelCase(**c_wall("web", Pu=12300 * KIP, Muy=722000 * KIPIN))).check("interaction").result["modes"]["I5c"]
    assert compression["equation"] == "DG38 A.2.5"
    assert compression["C_mm"] / IN == pytest.approx(13.6, rel=TOL)
    assert compression["Mn_at_Pr_kNm"] / KIPIN == pytest.approx(2160000, rel=TOL)


def test_c_wall_properties_and_shear_of_example_23(guides_engine):
    mode = guides_engine.run(SteelCase(**c_wall("web", Pu=1.0))).check("axial").result["modes"]["FB-y"]
    assert mode["EI_eff"] / (KIP * 1000 * IN**2) == pytest.approx(1.17e11, rel=0.03)            # Ec is 5% stiffer in SI
    assert mode["EA_eff"] / (KIP * 1000) == pytest.approx(4.45e7, rel=0.03)
    assert guides_engine.run(SteelCase(**c_wall(Vuy=1.0))).check("shear_y").capacity / KIP == pytest.approx(0.9 * 16100, rel=TOL)


def test_c_wall_blocks_what_the_guide_does_not_cover(guides_engine):
    assert guides_engine.run(SteelCase(**c_wall(Pu=12300 * KIP, Muy=1.0))).check("interaction").status.value == "INCOMPLETE"
    assert guides_engine.run(SteelCase(**c_wall("web", Pu=1000 * KIP, Mux=1.0))).check("interaction").status.value == "INCOMPLETE"
    assert guides_engine.run(SteelCase(**c_wall(Vux=1.0))).check("shear_x").status.value == "INCOMPLETE"


FIRE_F = [1450, 927, 694, 533, 406, 305, 229, 173, 134, 108, 92, 83, 79]


def fire_wall(temperatures=True, **over):
    """Design Guide 38, Example 6.1: L = 11 ft, tsc = 24, t = 9/16 in, st = 12 in, story 17 ft, Pu = 3600 kips, Table 6-1."""
    data = wall(132, 24, 0.5625, Pu=3600 * KIP, Lc=17)
    fire = {"required_rating_hours": 3.0}
    if temperatures:
        fire.update(plate_temperature=(1840 - 32) / 1.8, element_thicknesses=[0.88 * IN] * 13,
                    element_temperatures=[(f - 32) / 1.8 for f in FIRE_F])
    data["composite"]["fire"] = {**fire, **over}
    return data


def test_fire_rating_and_strength_of_example_61(guides_engine):
    mode = guides_engine.run(SteelCase(**fire_wall())).check("fire").result["modes"]["FIRE"]
    assert mode["Pu_unit_kN"] / KIP == pytest.approx(327, rel=TOL)
    assert mode["Pn_kN"] / KIP == pytest.approx(1970, rel=TOL)
    assert mode["R_hours"] == pytest.approx(8.0)                          # 10.1 hours, limited to 8 by Equation 6-5
    assert mode["Pno_T_kN"] / KIP == pytest.approx(1220, rel=TOL)
    assert mode["Pe_T_kN"] / KIP == pytest.approx(2680, rel=0.05)         # Ec is 5% stiffer in SI
    assert mode["Pn_T_kN"] / KIP == pytest.approx(496, rel=TOL)
    assert mode["phi_Pn_T_wall_kN"] / KIP == pytest.approx(4910, rel=TOL)


def test_vent_holes_of_example_61(guides_engine):
    vent = {"s1": 10 * FT, "s2": 10 * FT, "diameter": 1 * IN, "dry_thickness": 1.5 * IN, "heating_time": 1790.0, "water_content": 0.15,
            "water_density": 62.5 * 16.018463, "pour_height": 14 * FT}
    check = guides_engine.run(SteelCase(**fire_wall(vent=vent))).check("fire")
    mode = check.result["modes"]["FIRE"]
    assert mode["vent_area_mm2"] / IN**2 == pytest.approx(0.539, rel=TOL)
    assert all(r["satisfied"] for r in check.result["requirements"])


def test_fire_rating_outside_its_limits_needs_the_temperatures(guides_engine):
    data = fire_wall(temperatures=False)
    data["Pu"] = 8000 * KIP
    assert guides_engine.run(SteelCase(**data)).check("fire").status.value == "INCOMPLETE"


def path_of(result, dotted):
    """A field of the result, of its governing mode, or of an explicit modes.<id>.<field> or second_order.<field>."""
    parts = dotted.split(".")
    node = result
    for part in parts[:-1]:
        node = node[part]
    if parts[-1] in node:
        return node[parts[-1]]
    return result["modes"][result["governing_mode"]][parts[-1]]


REFERENCE = json.loads((Path(__file__).parent / "fixtures/chapter_i/reference.json").read_text(encoding="utf-8"))["cases"]
TIES = {"db": 10, "spacing": 300}


def _bars(spec):
    return [{"area": a, "db": float(db), "x": x, "y": y} for a, db, x, y in spec["bars"]]


def _concrete(spec):
    return {"fc": spec["fc"], "wc": spec.get("wc", 2320), "lightweight": False}


def _filled(spec, **extra):
    return dict(section_name=spec["name"], material={"Fy": spec["fy"]}, composite={"kind": "filled", "concrete": _concrete(spec), **extra})


def _encased(spec, **extra):
    return dict(section_name=spec["name"], material={"Fy": spec.get("fy", 345)},
                composite={"kind": "encased", "concrete": _concrete(spec),
                           "encased": {"H": spec["H"], "B": spec["B"], "Fysr": spec["Fysr"], "bars": _bars(spec), "transverse": TIES,
                                       "flexure_method": "composite", "anchors_provided": True}, **extra})


def _length(L):
    return {"Lx": L, "Ly": L, "Lz": L}


def _box(spec, **demands):
    return SteelCase(section_name="BOX", material={"Fy": spec["fy"]}, **demands,
                     composite={"kind": "filled", "concrete": _concrete(spec), "box": {"B": spec["B"], "H": spec["H"], "t": spec["t"]}})


def _guide_case(spec):
    """(case, check id, {field of the result: oracle key}) from one oracle spec."""
    kind = spec["kind"]
    if kind == "second_order":
        so = {k: spec[k] for k in ("Pnt", "Plt", "Mnt", "Mlt", "M1_M2", "Pstory", "Pmf", "H", "drift")}
        data = _filled(spec, second_order={**so, "axis": "x", "L": spec["story"]})
        return SteelCase(**data, lengths=_length(spec["L"])), "axial", {f"second_order.{k}": k for k in ("B1", "B2", "Pr_kN", "Mr_kNm")}
    if kind.startswith("load_transfer"):
        transfer = {"Pr": spec["Pr"], "applied_to": spec["applied_to"]}
        if spec.get("A1"):
            transfer["bearing_area"] = spec["A1"]
        if spec.get("Lin"):
            transfer.update(bond_length=spec["Lin"], bond_slip_controlled=True)
        if spec.get("steel_fraction") is not None:
            transfer["steel_fraction"] = spec["steel_fraction"]
        data = (_filled if kind.endswith("filled") else _encased)(spec, load_transfer=transfer)
        expected = {"modes.LT.Vr_kN": "Vr_kN"}
        expected.update({f"modes.LT.{k}": k for k in ("bearing_kN", "bond_kN") if k in REFERENCE_KEYS[kind]})
        return SteelCase(**data, Vux=1.0), "load_transfer", expected
    if kind == "tension_control":
        return SteelCase(**_encased(spec), Mux=1.0), "flexure_x", {"epsilon_t": "epsilon_t", "epsilon_limit": "epsilon_limit"}
    if kind == "box_compression":
        return _box(spec, Pu=1.0, lengths=_length(spec["L"])), "axial", {"Pn_kN": "Pn_kN"}
    if kind == "box_flexure":
        return _box(spec, Mux=1.0), "flexure_x", {"Mn_kNm": "Mn_kNm"}
    if kind == "box_shear":
        return _box(spec, Vux=1.0), "shear_x", {"available_kN": "phiVn_kN"}
    if kind == "biaxial":
        data = (_filled if spec["member"] == "filled" else _encased)(spec, interaction="M2S", biaxial_shape_factor=True)
        return SteelCase(**data, Pu=spec["Pu"], Mux=spec["Mux"], Muy=spec["Muy"], lengths=_length(spec["L"])), "interaction", {"ratio": "ratio"}
    if kind in {"service_filled", "service_round"}:
        keys = ("EI_service", "EA_service", "GA_service") if kind == "service_filled" else ("GJ_service",)
        return (SteelCase(**_filled(spec), Pu=spec["Pu"], lengths=_length(spec["L"])), "axial", {f"modes.FB-x.{k}": k for k in keys})
    if kind in {"wall_slender", "wall_stiffnesses"}:
        over = {"b": spec["b"], "allow_slender_plates": True} if kind == "wall_slender" else {"b": 200}
        data = dict(section_name="MURO", material={"Fy": spec.get("fy", 345)}, Pu=1.0, lengths=_length(6000),
                    composite={"kind": "wall", "concrete": _concrete(spec) if "wc" in spec else {"fc": spec["fc"], "wc": 2320, "lightweight": False},
                               "wall": {"length": spec["L"], "tsc": spec["tsc"], "t": spec["t"], "tf": spec["tf"], "st": 200, "dtie": 25, **over}})
        keys = ("Pno_kN",) if kind == "wall_slender" else ("EI_eff", "EA_eff", "GA_eff")
        return SteelCase(**data), "axial", {f"modes.FB-x.{k}": k for k in keys}
    if kind == "c_wall_case":
        mode, P = spec["mode"], spec.get("P", 0)
        wall_ = {k: spec[k] for k in ("L", "W", "tsc_w", "tsc_f", "tp")}
        wall_.update(b=200, st=200, dtie=25, minor_axis_compression="web" if mode == "web" else "flange_tips")
        data = dict(section_name="MURO-C", material={"Fy": spec["fy"]}, composite={"kind": "c_wall", "concrete": _concrete(spec), "c_wall": wall_})
        if mode == "major":
            return SteelCase(**data, Mux=1.0), "flexure_x", {"Mn_kNm": "Mn_kNm", "modes.Y.C_mm": "C_mm"}
        if not P:
            return SteelCase(**data, Muy=1.0), "flexure_y", {"Mn_kNm": "Mn_kNm", "modes.Y.C_mm": "C_mm"}
        lengths = {"lengths": _length(6000)} if P > 0 else {}
        return SteelCase(**data, Pu=P, Muy=1.0, **lengths), "interaction", {"modes.I5c.Mn_at_Pr_kNm": "Mn_kNm", "modes.I5c.C_mm": "C_mm"}
    if kind in {"coupling_flexure", "coupling_shear"}:
        data = dict(section_name="CB", material={"Fy": spec["fy"]},
                    composite={"kind": "coupling_beam", "concrete": {"fc": spec["fc"], "wc": 2320, "lightweight": False},
                               "coupling_beam": {k: spec[k] for k in ("b", "h", "tf", "tw")}})
        if kind == "coupling_flexure":
            return SteelCase(**data, Mux=1.0), "flexure_x", {"Mn_kNm": "Mn_kNm", "modes.Y.C_mm": "C_mm"}
        return SteelCase(**data, Vux=1.0), "shear_x", {"available_kN": "phiVn_kN"}
    if kind == "wall_fire_oracle":
        data = dict(section_name="MURO", material={"Fy": spec["fy"]}, Pu=spec["Pu"], lengths=_length(spec["height"]),
                    composite={"kind": "wall", "concrete": _concrete(spec),
                               "wall": {"length": spec["wall_length"], "tsc": spec["tsc"], "t": spec["t"], "tf": spec["t"], "b": 200,
                                        "st": spec["st"], "dtie": 25},
                               "fire": {"required_rating_hours": spec["required"], "plate_temperature": spec["plate_T"],
                                        "element_thicknesses": spec["thicknesses"], "element_temperatures": spec["temperatures"]}})
        keys = ("R_hours", "Pn_kN", "Pno_T_kN", "Pn_T_kN", "phi_Pn_T_wall_kN")
        return SteelCase(**data), "fire", {"ratio": "ratio", **{f"modes.FIRE.{k}": k for k in keys}}


GUIDE_CASE_IDS = sorted(c for c, v in REFERENCE.items() if v["spec"]["kind"] in GUIDE_KINDS)
REFERENCE_KEYS = {"load_transfer_filled": ("bearing_kN", "bond_kN"), "load_transfer_encased": ("bearing_kN",)}


@pytest.mark.parametrize("case_id", GUIDE_CASE_IDS)
def test_guide_contents_match_independent_calculation(guides_engine, case_id):
    ref = REFERENCE[case_id]
    case, check_id, fields = _guide_case(ref["spec"])
    check = guides_engine.run(case).check(check_id)
    assert check.result is not None, check.errors
    for field, key in fields.items():
        if key not in ref:
            continue
        assert path_of(check.result, field) == pytest.approx(float(ref[key]), rel=1e-9), (case_id, field)


def i3_case(applied_to, **transfer):
    """Design Examples I.3: HSS10X6X3/8, f'c = 5 ksi, Pr = 173 kips; catalog of EXTRA in test_design_examples."""
    data = filled_member("HSS10X6X3/8", 5, Vux=1.0)
    data["composite"]["load_transfer"] = {"Pr": 173 * KIP, "applied_to": applied_to, **transfer}
    return data


@pytest.fixture(scope="module")
def i3_engine(catalog):
    from test_design_examples import EXTRA as EXAMPLES_EXTRA
    repository = SectionRepository()
    repository.load([*catalog, *EXAMPLES_EXTRA, *EXTRA])
    return SteelDesignEngine(repository)


@pytest.mark.parametrize("applied_to, extra, vr", [
    ("steel", {"bearing_area": 25.1 * IN**2}, 49.7), ("concrete", {"bearing_area": 25.1 * IN**2}, 123),
    ("both", {"bearing_area": 25.1 * IN**2, "steel_fraction": 0.611}, 17.6),
])
def test_force_allocation_of_example_i3(i3_engine, applied_to, extra, vr):
    check = i3_engine.run(SteelCase(**i3_case(applied_to, **extra))).check("load_transfer")
    mode = check.result["modes"]["LT"]
    assert mode["Vr_kN"] / KIP == pytest.approx(vr, rel=TOL)
    assert mode["bearing_kN"] / KIP == pytest.approx(138, rel=TOL)


def test_direct_bond_of_example_i3(i3_engine):
    check = i3_engine.run(SteelCase(**i3_case("steel", bond_length=12 * IN, bond_slip_controlled=True))).check("load_transfer")
    assert check.result["modes"]["LT"]["bond_kN"] / KIP == pytest.approx(7.19, rel=TOL)
    assert check.status.value == "FAIL"                                    # the example also finds 7.19 < 49.7 kips


def test_direct_bond_needs_the_declaration_of_i63(i3_engine):
    check = i3_engine.run(SteelCase(**i3_case("steel", bond_length=12 * IN))).check("load_transfer")
    assert check.status.value == "INCOMPLETE"


def test_load_transfer_of_encased_example_i8(i3_engine):
    from test_design_examples import encased_member
    data = encased_member(Vux=1.0)
    anchor = {"type": "stud", "Qrv": 1.0, "spacing": 300, "d": 0.75 * IN, "Fu": 65 * KSI, "height": 6 * IN, "breakout_in_shear": False,
              "base_thickness": 1 * IN}
    data["composite"]["anchor"] = anchor
    data["composite"]["load_transfer"] = {"Pr": 1560 * KIP, "applied_to": "steel", "bearing_area": 134 * IN**2, "anchor_count": 20}
    mode = i3_engine.run(SteelCase(**data)).check("load_transfer").result["modes"]["LT"]
    assert mode["Vr_kN"] / KIP == pytest.approx(1260, rel=TOL)
    assert mode["bearing_kN"] / KIP == pytest.approx(741, rel=TOL)
    assert mode["anchors_kN"] / KIP == pytest.approx(20 * 18.7, rel=TOL)
    bond = encased_member(Vux=1.0)
    bond["composite"]["load_transfer"] = {"Pr": 1.0, "applied_to": "steel", "bond_length": 300, "bond_slip_controlled": True}
    assert i3_engine.run(SteelCase(**bond)).check("load_transfer").errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


def test_uncoupled_wall_of_example_21_meets_every_limit(guides_engine):
    # Example 2.1: b/t = 24 <= 28.9 and S/tp = 24 <= 24.5, with tie bars of 5/8 in at 12 in.
    result = guides_engine.run(SteelCase(**wall(300, 18, 0.5, Mux=695000 * KIPIN, Vux=490 * KIP)))
    assert result.status.value == "PASS", result.errors


def test_wall_steel_matches_the_area_and_inertia_of_example_21(guides_engine):
    section = guides_engine.section_for(SteelCase(**wall(300, 18, 0.5, Mux=1.0)))
    assert section.area / IN**2 == pytest.approx(317, rel=TOL)
    assert section.ix / IN**4 == pytest.approx(2.63e6, rel=TOL)


def test_mp_and_my_of_example_27(guides_engine):
    # Printed by the composite column program of the guide: Mp = 364, My = 281 kip-ft, PNA at 4.01 in, NA at 2.04 in.
    mode = guides_engine.run(SteelCase(**round_hss_16(Mux=1.0))).check("flexure_x").result["modes"]["Y"]
    assert mode["Mp_kNm"] / KIPFT == pytest.approx(364, rel=TOL)
    assert mode["My_kNm"] / KIPFT == pytest.approx(281, rel=TOL)
    assert mode["yn_mm"] / IN == pytest.approx(2.04, rel=0.03)


def test_appendix_2_does_not_cover_lightweight_or_round_members(guides_engine):
    data = box_25_fc(12, Vux=1.0)
    data["composite"]["concrete"]["lightweight"] = True
    assert guides_engine.run(SteelCase(**data)).errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"
    assert guides_engine.run(SteelCase(**filled_member("HSS16.000X0.250", 12, Vux=1.0))).errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


def test_appendix_2_only_applies_above_the_limits_of_i13(guides_engine):
    # f'c = 6 ksi is within I1.3: Chapter I, not Appendix 2.
    check = guides_engine.run(SteelCase(**box_25(Mux=1.0))).check("flexure_x")
    assert check.result["modes"]["Y"]["provision"] == "I3.4b(a)"
