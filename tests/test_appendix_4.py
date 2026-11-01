"""Appendix 4, Section 4.2.4d: fire cases vs independent hand calculations, selection and blocks.

Expected values: tests/fixtures/chapter_a4/reference.json from tests/oracles/chapter_a4.py
(Decimal, written from a360-22w.pdf Appendix 4 and the errata, no product import).
"""
import json

import pytest

from steel_design.codes.aisc_360_22 import appendix_4 as a4
from steel_design.execution import execute_payload, member_groups
from steel_design.models import SteelCase
from steel_design.reporting import render_text, report_blocks

from conftest import ROOT

REFERENCE = json.loads((ROOT / "tests/fixtures/chapter_a4/reference.json").read_text(encoding="utf-8"))["cases"]
HOLES = {"tension_flange_holes": False}
CONCRETE = {"fc": 35, "wc": 2320, "lightweight": False}
STUDS = {"count": 44, "d": 19, "Fu": 450, "length": 120, "over_web": True,
         "detailing": {"longitudinal_spacing": 300, "lateral_cover": 50, "free_edge": True, "free_edge_distance": 300, "distribution": "uniform"}}


def fire_case(T, *, name="W12X72", L=4000, fire=None, **data):
    lengths = {"lengths": {"Lx": L, "Ly": L, "Lz": L}} if L else {}
    return SteelCase(**{"section_name": name, "material": {"Fy": 345, "Fu": 448}, "condition": "fire", "fire": {"steel_temperature": T, **(fire or {})},
                        "flexure": HOLES, **lengths, **data})


def beam_data(**over):
    return {"kind": "beam", "concrete": {"fc": 28, "wc": 2320, "lightweight": False},
            "beam": {"moment": "positive", "span": 13716, "left_beam_spacing": 3048, "right_beam_spacing": 3048, "tc": 114, "shored": True, "studs": STUDS, **over}}


def _case_of(ref):
    spec = ref["spec"]
    kind, T = spec["kind"], spec["T"]
    if kind == "tension":
        return fire_case(T, name=spec["name"], L=None, Pu=-1, tension={"An": spec["An"], "U": spec["U"]}), "axial", {"available_kN": "phiPn_kN"}
    if kind == "compression":
        data = {"section_name": spec["name"], "material": {"Fy": spec["fy"]}, "condition": "fire", "fire": {"steel_temperature": T},
                "Pu": 1, "lengths": {k: spec[k] for k in ("Lx", "Ly", "Lz")}}
        return SteelCase(**data), "axial", {"Pn_kN": "Pn_kN", "available_kN": "phiPn_kN"}
    if kind == "ltb_compact_w":
        flexure = {**HOLES, "Cb": spec.get("Cb", 1.0)}
        case = fire_case(T, name=spec["name"], Mux=1, flexure=flexure, lengths={"Lx": 9000, "Ly": spec["Lb"], "Lz": spec["Lb"]}, L=None)
        return case, "flexure_x", {"Mn_kNm": "Mn_kNm", "available_kNm": "phiMn_kNm"}
    if kind == "noncompact_w":
        return fire_case(T, name=spec["name"], L=spec["Lb"], Mux=1), "flexure_x", {"Mn_kNm": "Mn_kNm"}
    if kind == "minor_axis_w":
        return fire_case(T, name=spec["name"], L=4000, Muy=1), "flexure_y", {"Mn_kNm": "Mn_kNm"}
    if kind == "shear_w":
        moment = {"Vux": 1} if spec["axis"] == "x" else {"Vuy": 1}
        return fire_case(T, name=spec["name"], L=None, **moment), f"shear_{spec['axis']}", {"available_kN": "phiVn_kN"}
    if kind == "interaction":
        return fire_case(T, name=spec["name"], L=spec["L"], Pu=spec["Pu"], Mux=spec["Mu"]), "interaction", {"ratio": "ratio"}
    length = {"Lx": spec.get("L", 1), "Ly": spec.get("L", 1), "Lz": spec.get("L", 1)}
    if kind in {"filled_uniform", "filled_elements", "filled_round_bars"}:
        composite = {"kind": "filled", "concrete": CONCRETE}
        temperatures = {"steel_temperature": T}
        if kind == "filled_uniform":
            temperatures["concrete_temperature"] = spec["Tc"]
        elif kind == "filled_round_bars":
            temperatures.update(concrete_temperature=spec["Tc"], bar_temperature=spec["bar_T"])
            composite["filled"] = {"Fysr": 420, "transverse": {"db": 10, "spacing": 300},
                                   "bars": [{"area": a, "db": db, "x": x, "y": y} for a, db, x, y in spec["bars"]]}
        else:
            temperatures["concrete_elements"] = [{"A": float(a), "Ix": float(x), "Iy": float(y), "T": t} for a, x, y, t in ref["elements"]]
        return (SteelCase(section_name=spec["name"], material={"Fy": spec["fy"]}, condition="fire", fire=temperatures, Pu=1, lengths=length, tau_b=0.8, composite=composite),
                "axial", {"Pn_kN": "Pn_kN", "available_kN": "phiPn_kN"})
    if kind == "wall_uniform":
        composite = {"kind": "wall", "concrete": {"fc": spec["fc"], "wc": spec["wc"], "lightweight": False},
                     "wall": {"length": spec["wall_length"], "tsc": spec["tsc"], "t": spec["t"], "tf": spec["t"], "b": 200, "st": spec["st"], "dtie": 25}}
        height = {"Lx": spec["height"], "Ly": spec["height"], "Lz": spec["height"]}
        return (SteelCase(section_name="MURO", material={"Fy": spec["fy"]}, condition="fire", fire={"steel_temperature": T, "concrete_temperature": spec["Tc"]},
                          Pu=1, lengths=height, tau_b=1.0, composite=composite),
                "axial", {"modes.FB.Pno_T_kN": "Pno_T_kN", "modes.FB.Pn_T_kN": "Pn_T_kN", "available_kN": "phiPn_kN"})
    assert kind == "beam"
    return (fire_case(T, name=spec["name"], Mux=1, L=None, composite=beam_data(), tau_b=1.0), "flexure_x",
            {"modes.Y.kcb": "kcb", "Mn_kNm": "Mn_kNm", "available_kNm": "phiMn_kNm"})


def _path(result, dotted):
    node = result
    for part in dotted.split("."):
        node = node[part]
    return node


@pytest.mark.parametrize("case_id", sorted(REFERENCE))
def test_simple_method_matches_the_independent_calculation(engine, case_id):
    ref = REFERENCE[case_id]
    case, check_id, fields = _case_of(ref)
    check = engine.run(case).check(check_id)
    assert check.result is not None, check.errors
    for field, key in fields.items():
        assert _path(check.result, field) == pytest.approx(float(ref[key]), rel=1e-9), (case_id, field)
    assert check.result["fire"]["T_C"] == ref["spec"]["T"]


@pytest.mark.parametrize("case_id, equation", [("M-W-A413", "A-4-13"), ("M-W-A413-Cb", "A-4-13"), ("M-W-A414", "A-4-14")])
def test_the_equation_of_lateral_torsional_buckling(engine, case_id, equation):
    ref = REFERENCE[case_id]
    assert ref["equation"] == equation
    case, check_id, _ = _case_of(ref)
    assert engine.run(case).check(check_id).result["modes"]["LTB"]["equation"] == equation


def test_retention_tables_by_hand():
    assert a4.steel_factors(540) == {"kE": 0.49, "kp": 0.29, "ky": 0.66}
    assert a4.steel_factors(485)["ky"] == pytest.approx(0.94 + (0.66 - 0.94) * 55 / 110)
    assert a4.concrete_factors(650, lightweight=False) == {"kc": 0.38, "kEc": 0.092}
    assert a4.concrete_factors(650, lightweight=True)["kc"] == 0.58
    assert a4.composite_beam_factor(650) == 0.49


def test_a_4_19m_is_capped_at_three():
    assert a4.ltb(E_T=1e5, Fy=345, kp=0.04, ky=0.07, T=870, Sx=1e6, Zx=1.1e6, rts=50, J=1e5, c=1, ho=400, Lb=1000, Cb=1)["cx"] == 3.0


@pytest.mark.parametrize("build", [
    lambda T: fire_case(T, Pu=500),
    lambda T: fire_case(T, Mux=100),
    lambda T: fire_case(T, Vux=100),
])
def test_at_200_degrees_or_less_the_strength_is_the_ambient_one(engine, build):
    hot, ambient = build(200), build(200).model_copy(update={"condition": "ultimate", "fire": None})
    assert engine.run(hot).checks[0].capacity == engine.run(ambient).checks[0].capacity
    assert engine.run(hot).checks[0].result.get("fire") is None
    assert engine.run(build(200.1)).checks[0].result["fire"]["T_C"] == 200.1


def test_filled_flexure_at_200_degrees_uses_chapter_i(engine):
    case = SteelCase(section_name="PTE100X50X3MM", material={"Fy": 345}, condition="fire", fire={"steel_temperature": 150}, Mux=1, tau_b=0.8,
                     composite={"kind": "filled", "concrete": CONCRETE})
    assert engine.run(case).check("flexure_x").capacity is not None


def test_classification_stays_at_ambient_temperature(engine):
    # W14X90 has a noncompact flange at ambient temperature and at any temperature: F3-1 with lambda from E and Fy, not E(T), Fy(T)
    result = engine.run(fire_case(650, name="W14X90", L=100, Mux=1)).check("flexure_x").result
    rows = result["classification"]["elements"]
    assert rows[0]["lambda_p"] == pytest.approx(0.38 * (200000 / 345) ** 0.5)
    assert result["modes"]["FLB"]["equation"] == "F3-1"


def test_instability_by_chapter_f_warns_of_the_commentary(engine):
    result = engine.run(fire_case(550, name="W14X90", L=9000, Mux=1)).check("flexure_x").result
    assert result["governing_mode"] == "LTB" and any("Commentary" in n and "DA4-3" in n for n in result["notes"])


@pytest.mark.parametrize("build", [
    lambda: fire_case(550, name="PTE100X40X1.5MM", material={"Fy": 500}, L=1000, Pu=1),
    lambda: fire_case(550, name="W14X90", material={"Fy": 500, "Fu": 600}, Pu=1),
])
def test_what_the_simple_method_excludes_is_incomplete(engine, build):
    check = engine.run(build()).check("axial")
    assert check.status.value == "INCOMPLETE" and check.result is None


def test_slender_compression_elements_are_blocked(engine):
    case = fire_case(550, name="PTE300X100X5MM", L=1000, Pu=1)
    result = engine.run(case).check("axial")
    assert result.status.value == "INCOMPLETE" and "elementos esbeltos" in result.errors[0]["message"]


def test_shear_buckling_is_blocked(engine):
    # Plate 500 x 5: d/t = 100 > 1.10*sqrt(5*E/Fy) = 59.2, so Cv2 < 1 (G4). No rectangular HSS of the catalog reaches it.
    case = fire_case(550, name="PLATINA", L=None, Vux=1, custom_section={"type": "SOLID_RECTANGULAR", "H": 500, "B": 5})
    assert engine.run(case.model_copy(update={"condition": "ultimate", "fire": None})).check("shear_x").result["classification"]["elements"][0]["Cv"] < 1
    check = engine.run(case).check("shear_x")
    assert check.status.value == "INCOMPLETE" and "pandeo por cortante" in check.errors[0]["message"]


def test_cb_is_not_amplified_in_fire(engine):
    flexure = {**HOLES, "Cb": 1.2, "tension_cb_amplification": True}
    result = engine.run(fire_case(550, Pu=-100, Mux=50, flexure=flexure, tension={"An": 8000, "U": 0.9})).check("flexure_x").result
    assert result["inputs"]["Cb"] == 1.2 and any("DA4-6" in n for n in result["notes"])


@pytest.mark.parametrize("composite, demand, check_id", [
    ({"kind": "filled", "concrete": CONCRETE}, {"Mux": 1}, "flexure_x"),
    ({"kind": "filled", "concrete": CONCRETE}, {"Vux": 1}, "shear_x"),
    ({"kind": "filled", "concrete": CONCRETE}, {"Pu": -1}, "axial"),
])
def test_filled_demands_without_a_rule_stay_incomplete(engine, composite, demand, check_id):
    case = SteelCase(section_name="PTE100X50X3MM", material={"Fy": 345}, condition="fire", fire={"steel_temperature": 500, "concrete_temperature": 200},
                     tau_b=0.8, composite=composite, **demand)
    check = engine.run(case).check(check_id)
    assert check.status.value == "INCOMPLETE" and check.errors[0]["code"] == "FIRE_NOT_COVERED"


def test_encased_column_stays_incomplete(engine):
    encased = {"H": 610, "B": 610, "Fysr": 420, "transverse": {"db": 10, "spacing": 300},
               "bars": [{"area": 510, "db": 25.4, "x": x, "y": y} for x, y in ((241, 241), (241, -241), (-241, 241), (-241, -241))]}
    case = SteelCase(section_name="W10X45", material={"Fy": 345}, condition="fire", fire={"steel_temperature": 500}, Pu=1, tau_b=0.8,
                     lengths={"Lx": 3000, "Ly": 3000, "Lz": 3000}, composite={"kind": "encased", "concrete": CONCRETE, "encased": encased})
    result = engine.run(case)
    assert result.status.value == "INCOMPLETE" and result.check("axial").errors[0]["code"] == "FIRE_NOT_COVERED"


@pytest.mark.parametrize("fire, field", [
    ({}, "fire.concrete_temperature"),
    ({"concrete_elements": [{"A": 1000, "Ix": 1e6, "Iy": 1e6, "T": 300}]}, "fire.concrete_elements"),
])
def test_filled_needs_the_concrete_temperature_and_elements_that_add_up(engine, fire, field):
    case = SteelCase(section_name="PTE100X50X3MM", material={"Fy": 345}, condition="fire", fire={"steel_temperature": 500, **fire}, Pu=1, tau_b=0.8,
                     lengths={"Lx": 2000, "Ly": 2000, "Lz": 2000}, composite={"kind": "filled", "concrete": CONCRETE})
    check = engine.run(case).check("axial")
    assert check.status.value == "INCOMPLETE" and field in check.errors[0]["details"]["fields"]


def test_filled_with_bars_needs_their_temperature(engine):
    filled = {"Fysr": 420, "transverse": {"db": 10, "spacing": 300}, "bars": [{"area": 200, "db": 16, "x": x, "y": y} for x, y in ((0, 55), (0, -55), (55, 0), (-55, 0))]}
    case = SteelCase(section_name='PTER8"X5.00MM', material={"Fy": 345}, condition="fire", fire={"steel_temperature": 500, "concrete_temperature": 300}, Pu=1, tau_b=0.8,
                     lengths={"Lx": 3000, "Ly": 3000, "Lz": 3000}, composite={"kind": "filled", "concrete": CONCRETE, "filled": filled})
    assert "fire.bar_temperature" in engine.run(case).check("axial").errors[0]["details"]["fields"]


def test_concrete_above_55_mpa_is_outside_the_tables(engine):
    case = SteelCase(section_name="PTE100X50X3MM", material={"Fy": 345}, condition="fire", fire={"steel_temperature": 500, "concrete_temperature": 200}, Pu=1, tau_b=0.8,
                     lengths={"Lx": 2000, "Ly": 2000, "Lz": 2000}, composite={"kind": "filled", "concrete": {**CONCRETE, "fc": 60}})
    assert "55" in engine.run(case).check("axial").errors[0]["message"]


def test_beam_above_1100_degrees_is_blocked(engine):
    check = engine.run(fire_case(1100, Mux=1, L=None, name="W21X50", composite=beam_data(), tau_b=1.0)).check("flexure_x")
    assert check.status.value == "INCOMPLETE" and "1100" in check.errors[0]["message"]


def test_negative_flexure_of_a_beam_is_chapter_f_at_temperature(engine):
    case = fire_case(600, name="W21X50", Mux=1, L=2000, composite=beam_data(moment="negative"), tau_b=1.0)
    check = engine.run(case).check("flexure_x")
    assert check.chapter == "F" and check.result["governing_equation"].startswith("A-4")


@pytest.mark.parametrize("data", [
    {"condition": "fire", "Vux": 1},
    {"fire": {"steel_temperature": 500}, "Vux": 1},
    {"condition": "fire", "fire": {"steel_temperature": 1200}, "Vux": 1},
    {"condition": "fire", "fire": {"steel_temperature": 10}, "Vux": 1},
    {"condition": "fire", "fire": {"steel_temperature": 500, "concrete_temperature": 200}, "Vux": 1},
    {"condition": "fire", "fire": {"steel_temperature": 500, "concrete_temperature": 200, "concrete_layers": [{"thickness": 1, "T": 1}]}, "Vux": 1},
])
def test_rejected_inputs(data):
    with pytest.raises(ValueError):
        SteelCase(section_name="W18X50", material={"Fy": 345}, **data)


def test_report_of_a_fire_case(engine):
    data = json.loads((ROOT / "examples/w_shape.json").read_text(encoding="utf-8"))
    (group,) = member_groups(execute_payload(data, engine))
    text = render_text(report_blocks(group))
    for sentence in ("### 1.4 Propiedades a temperatura elevada", "T del acero (°C)", "Tabla A-4.2.1", "Incendio a 550 °C — flexocompresión", "sin efecto",
                     "### 6.2 Compresión (Capítulo E), condiciones de incendio; case gobernante: Incendio a 550 °C — flexocompresión",
                     "### 7.2 Tracción (Capítulo D), condiciones de incendio", "Apéndice 4, 4.2.4d", "A-4-9", "### 9.3 Condiciones de incendio", "combinación A-4-1"):
        assert sentence in text, sentence
    assert "esta resistencia en incendio no está programada" not in text


def test_a_steel_member_rejects_the_concrete_temperature_through_the_json(engine):
    with pytest.raises(ValueError):
        execute_payload({"section_name": "W14X90", "material": "ASTM A36", "condition": "fire", "fire": {"steel_temperature": 500, "bar_temperature": 300}, "Vux": 1}, engine)


def test_one_json_mixes_the_conditions_and_at_180_degrees_gives_the_ambient_result(engine):
    data = json.loads((ROOT / "examples/w_shape.json").read_text(encoding="utf-8"))
    results = {tag: result for tag, _, result in execute_payload(data, engine)}
    assert {r.condition for r in results.values()} == {"ultimate", "construction", "fire"}
    hot, ambient = results["Incendio a 180 °C — sin efecto de temperatura"], results["Combinación 5 — flexocompresión biaxial y cortante"]
    assert [(c.id, c.capacity, c.ratio) for c in hot.checks] == [(c.id, c.capacity, c.ratio) for c in ambient.checks]
