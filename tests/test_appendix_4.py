"""Appendix 4, Section 4.2.4d: fire cases vs independent hand calculations, selection and blocks.

Expected values: tests/fixtures/chapter_a4/reference.json from tests/oracles/chapter_a4.py
(Decimal, written from a360-22w.pdf Appendix 4 and the errata, no product import).
"""
import json

import pytest
from conftest import ROOT

from steel_design.codes.aisc_360_22 import appendix_4 as a4
from steel_design.execution import execute_payload, member_groups
from steel_design.models import SteelCase
from steel_design.reporting.document import report_blocks
from steel_design.reporting.text import render_text

REFERENCE = json.loads((ROOT / "tests/fixtures/chapter_a4/reference.json").read_text(encoding="utf-8"))["cases"]
HOLES = {"tension_flange_holes": False}
CONCRETE = {"fc": 35, "wc": 2320, "lightweight": False}
STUDS = {
    "count": 44,
    "d": 19,
    "Fu": 450,
    "length": 120,
    "over_web": True,
    "detailing": {
        "longitudinal_spacing": 300,
        "lateral_cover": 50,
        "free_edge": True,
        "free_edge_distance": 300,
        "distribution": "uniform",
    },
}
TIES = {"db": 10, "spacing": 300}


def fire_case(T, *, name="W12X72", L=4000, fire=None, **data):
    lengths = {"lengths": {"Lx": L, "Ly": L, "Lz": L}} if L else {}
    return SteelCase(
        **{
            "section_name": name,
            "material": {"Fy": 345, "Fu": 448},
            "condition": "fire",
            "fire": {"steel_temperature": T, **(fire or {})},
            "flexure": HOLES,
            **lengths,
            **data,
        }
    )


def beam_data(**over):
    return {
        "kind": "beam",
        "concrete": {"fc": 28, "wc": 2320, "lightweight": False},
        "beam": {
            "moment": "positive",
            "span": 13716,
            "left_beam_spacing": 3048,
            "right_beam_spacing": 3048,
            "tc": 114,
            "shored": True,
            "studs": STUDS,
            **over,
        },
    }


def composite_fire(name, composite, temperatures, L=None, fy=345, tau_b=1.0, **demand):
    lengths = {"lengths": {"Lx": L, "Ly": L, "Lz": L}} if L else {}
    return SteelCase(
        section_name=name, material={"Fy": fy}, condition="fire", fire=temperatures, tau_b=tau_b, composite=composite, **lengths, **demand
    )


def _layers(layers):
    return [{"thickness": h, "T": t} for h, t in layers]


def _bars(spec):
    return {"Fysr": spec["Fysr"], "transverse": TIES, "bars": [{"area": a, "db": db, "x": x, "y": y} for a, db, x, y in spec["bars"]]}


def _wall(spec):
    return {"kind": "wall", "concrete": {"fc": spec["fc"], "wc": spec.get("wc", 2320), "lightweight": False},
            "wall": {"length": spec["L"], "tsc": spec["tsc"], "t": spec["t"], "tf": spec["tf"], "b": 200, "st": 300, "dtie": 25}}


def _c_wall(spec, compression="flange_tips"):
    return {
        "kind": "c_wall",
        "concrete": {"fc": spec.get("fc", 35), "wc": 2320, "lightweight": False},
        "c_wall": {
            "L": spec["L"],
            "W": spec["W"],
            "tsc_w": spec.get("tsc_w", 400),
            "tsc_f": spec["tsc_f"],
            "tp": spec["tp"],
            "b": 300,
            "st": 300,
            "dtie": 25,
            "minor_axis_compression": compression,
        },
    }


def _coupling(spec):
    return {"kind": "coupling_beam", "concrete": {"fc": spec["fc"], "wc": 2320, "lightweight": False},
            "coupling_beam": {k: spec[k] for k in ("b", "h", "tf", "tw")}}


def _steel_case_of(spec, kind, T):
    if kind == "tension":
        return (
            fire_case(T, name=spec["name"], L=None, Pu=-1, tension={"An": spec["An"], "U": spec["U"]}),
            "axial",
            {"available_kN": "phiPn_kN"},
        )
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
    assert kind == "interaction"
    return fire_case(T, name=spec["name"], L=spec["L"], Pu=spec["Pu"], Mux=spec["Mu"]), "interaction", {"ratio": "ratio"}


def _case_of(ref):
    spec = ref["spec"]
    kind, T = spec["kind"], spec["T"]
    if kind in {"tension", "compression", "ltb_compact_w", "noncompact_w", "minor_axis_w", "shear_w", "interaction"}:
        return _steel_case_of(spec, kind, T)
    if kind == "beam":
        case = fire_case(T, name=spec["name"], Mux=1, L=None, composite=beam_data(), tau_b=1.0, fire={"concrete_temperature": 300})
        return case, "flexure_x", {"modes.Y.kcb": "kcb", "Mn_kNm": "Mn_kNm", "available_kNm": "phiMn_kNm"}
    fire = {"steel_temperature": T}
    if kind.startswith("filled"):
        return _filled_case(spec, kind, fire)
    if kind == "wall_uniform":
        composite = {
            "kind": "wall",
            "concrete": {"fc": spec["fc"], "wc": spec["wc"], "lightweight": False},
            "wall": {
                "length": spec["wall_length"],
                "tsc": spec["tsc"],
                "t": spec["t"],
                "tf": spec["t"],
                "b": 200,
                "st": spec["st"],
                "dtie": 25,
            },
        }
        return (composite_fire("MURO", composite, {**fire, "concrete_temperature": spec["Tc"]}, L=spec["height"], Pu=1),
                "axial", {"modes.FB.Pno_T_kN": "Pno_T_kN", "modes.FB.Pn_T_kN": "Pn_T_kN", "available_kN": "phiPn_kN"})
    if kind == "wall_tension":
        return (
            composite_fire("MURO", _wall({**spec, "fc": 40}), {**fire, "concrete_temperature": 200}, Pu=-1),
            "axial",
            {"available_kN": "phiPn_kN"},
        )
    if kind == "wall_flexure":
        temperatures = {**fire, "concrete_layers": _layers(spec["layers"])}
        if spec.get("P"):
            return (
                composite_fire("MURO", _wall(spec), temperatures, L=5000, Pu=spec["P"], Mux=1),
                "interaction",
                {"modes.I5c.Mc_at_Pr_kNm": "Mc_kNm"},
            )
        return composite_fire("MURO", _wall(spec), temperatures, Mux=1), "flexure_x", {"Mn_kNm": "Mn_kNm"}
    if kind == "wall_shear":
        return (
            composite_fire("MURO", _wall(spec), {**fire, "concrete_layers": _layers(spec["layers"])}, Vux=1),
            "shear_x",
            {"available_kN": "phiVn_kN"},
        )
    return _c_wall_or_coupling(spec, kind, fire)


def _filled_case(spec, kind, fire):
    filled = {"kind": "filled", "concrete": {**CONCRETE, "fc": spec.get("fc", 35)}}
    fire["concrete_temperature"] = spec.get("Tc", 300)
    if "bars" in spec:
        fire["bar_temperature"] = spec["bar_T"]
        filled["filled"] = _bars({"Fysr": 420, **spec})
    common = dict(name=spec["name"], composite=filled, temperatures=fire, fy=spec["fy"], tau_b=0.8)
    if kind in {"filled_uniform", "filled_round_bars"}:
        return composite_fire(L=spec["L"], Pu=1, **common), "axial", {"Pn_kN": "Pn_kN", "available_kN": "phiPn_kN"}
    if kind == "filled_tension":
        return composite_fire(Pu=-1, **common), "axial", {"available_kN": "phiPn_kN"}
    if kind in {"filled_flexure", "filled_round_bars_flexure"}:
        axis = spec.get("axis", "x")
        return composite_fire(**common, **{"Mux" if axis == "x" else "Muy": 1}), f"flexure_{axis}", {"Mn_kNm": "Mn_kNm"}
    if kind == "filled_shear":
        return composite_fire(Vux=1, **common), "shear_x", {"available_kN": "phiVn_kN"}
    if kind == "filled_h1":
        return composite_fire(L=spec["L"], Pu=spec["Pu"], Mux=spec["Mu"], **common), "interaction", {"ratio": "ratio"}
    assert kind == "filled_m2s"
    filled["interaction"] = "M2S"
    return (
        composite_fire(L=spec["L"], Pu=spec["Pu"], Mux=spec["Mu"], **common),
        "interaction",
        {"ratio": "ratio", "modes.M2.PA_kN": "PA_kN", "modes.M2.PC_kN": "PC_kN"},
    )


def _c_wall_or_coupling(spec, kind, fire):
    profiles = {"web_layers": _layers(spec["web"]), "flange_layers": _layers(spec["flange"])} if "web" in spec else {}
    if kind == "c_wall_compression":
        return (
            composite_fire("MURO-C", _c_wall(spec), {**fire, **profiles}, L=spec["height"], Pu=1),
            "axial",
            {
                "modes.FB.Pn_T_web_kN": "Pn_T_web_kN",
                "modes.FB.Pn_T_flange_kN": "Pn_T_flange_kN",
                "Pn_kN": "Pn_kN",
                "available_kN": "phiPn_kN",
            },
        )
    if kind == "c_wall_tension":
        return composite_fire("MURO-C", _c_wall(spec), {**fire, "concrete_temperature": 200}, Pu=-1), "axial", {"available_kN": "phiPn_kN"}
    if kind == "c_wall_flexure":
        moment = {"Mux": 1} if spec["mode"] == "major" else {"Muy": 1}
        return (
            composite_fire("MURO-C", _c_wall(spec), {**fire, "concrete_temperature": spec["Tc"]}, **moment),
            "flexure_x" if spec["mode"] == "major" else "flexure_y",
            {"Mn_kNm": "Mn_kNm"},
        )
    if kind == "c_wall_major_profiles":
        return composite_fire("MURO-C", _c_wall(spec), {**fire, **profiles}, Mux=1), "flexure_x", {"Mn_kNm": "Mn_kNm"}
    if kind == "c_wall_shear":
        temperatures = {**fire, "web_layers": _layers(((184, 300),)), "flange_layers": _layers(spec["flange"])}
        return composite_fire("MURO-C", _c_wall({**spec, "L": 6000}), temperatures, Vuy=1), "shear_y", {"available_kN": "phiVn_kN"}
    temperatures = {**fire, "concrete_layers": _layers(spec["layers"])}
    if kind == "coupling_m":
        return composite_fire("CB", _coupling(spec), temperatures, Mux=1), "flexure_x", {"Mn_kNm": "Mn_kNm"}
    assert kind == "coupling_v"
    return composite_fire("CB", _coupling(spec), temperatures, Vux=1), "shear_x", {"available_kN": "phiVn_kN"}


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


def test_composite_member_at_200_degrees_ignores_the_temperature_of_its_concrete(engine):
    composite = {"kind": "filled", "concrete": CONCRETE}
    hot = composite_fire("PTE100X50X3MM", composite, {"steel_temperature": 150, "concrete_temperature": 900}, tau_b=0.8, Mux=1)
    ambient = hot.model_copy(update={"condition": "ultimate", "fire": None})
    assert engine.run(hot).check("flexure_x").capacity == engine.run(ambient).check("flexure_x").capacity


def test_classification_stays_at_ambient_temperature(engine):
    # W14X90 has a noncompact flange at ambient temperature and at any temperature: F3-1 with lambda from E and Fy, not E(T), Fy(T)
    result = engine.run(fire_case(650, name="W14X90", L=100, Mux=1)).check("flexure_x").result
    rows = result["classification"]["elements"]
    assert rows[0]["lambda_p"] == pytest.approx(0.38 * (200000 / 345) ** 0.5)
    assert result["modes"]["FLB"]["equation"] == "F3-1"


def test_noncompact_filled_flexure_keeps_its_ambient_class_at_temperature(engine):
    composite = {"kind": "filled", "concrete": CONCRETE}
    temperatures = {"steel_temperature": 700, "concrete_temperature": 300}
    result = engine.run(composite_fire("PTE300X100X5MM", composite, temperatures, tau_b=0.8, Muy=1)).check("flexure_y").result
    ambient = (
        engine.run(SteelCase(section_name="PTE300X100X5MM", material={"Fy": 345}, tau_b=0.8, composite=composite, Muy=1))
        .check("flexure_y")
        .result
    )
    assert [r["class"] for r in result["classification"]["elements"]] == [r["class"] for r in ambient["classification"]["elements"]]
    mode = result["modes"]["Y"]
    assert mode["equation"] == "I3-5b" and mode["My_kNm"] <= mode["Mn_kNm"] <= mode["Mp_kNm"]


def test_instability_by_chapter_f_warns_of_the_commentary(engine):
    result = engine.run(fire_case(550, name="W14X90", L=9000, Mux=1)).check("flexure_x").result
    assert result["governing_mode"] == "LTB" and any("Commentary" in n and "DA4-3" in n for n in result["notes"])


def test_composite_extensions_say_they_are_outside_the_standard(engine):
    composite = {"kind": "filled", "concrete": CONCRETE}
    result = (
        engine.run(composite_fire("PTE100X50X3MM", composite, {"steel_temperature": 600, "concrete_temperature": 300}, tau_b=0.8, Mux=1))
        .check("flexure_x")
        .result
    )
    assert any("DA4-8" in n for n in result["notes"])


def test_interaction_diagram_uses_the_materials_at_temperature(engine):
    composite = {"kind": "filled", "concrete": CONCRETE}
    data = dict(
        section_name="PTE100X50X3MM",
        material={"Fy": 345},
        tau_b=0.8,
        composite=composite,
        Pu=5,
        Mux=0.5,
        lengths={"Lx": 2000, "Ly": 2000, "Lz": 2000},
    )
    ambient = engine.run(SteelCase(**data)).interaction_diagrams[0]
    hot = engine.run(
        SteelCase(**data, condition="fire", fire={"steel_temperature": 600, "concrete_temperature": 300})
    ).interaction_diagrams[0]
    point = {p["point"]: p for p in hot["points"]}
    assert point["A"]["P_kN"] < {p["point"]: p for p in ambient["points"]}["A"]["P_kN"] and "DA4-8" in hot["note"]


@pytest.mark.parametrize("build", [
    lambda: fire_case(550, name="PTE100X40X1.5MM", material={"Fy": 500}, L=1000, Pu=1),
    lambda: fire_case(550, name="W14X90", material={"Fy": 500, "Fu": 600}, Pu=1),
])
def test_what_the_simple_method_excludes_is_incomplete(engine, build):
    check = engine.run(build()).check("axial")
    assert check.status.value == "INCOMPLETE" and check.result is None


def test_slender_compression_elements_are_blocked(engine):
    result = engine.run(fire_case(550, name="PTE300X100X5MM", L=1000, Pu=1)).check("axial")
    assert result.status.value == "INCOMPLETE" and "elementos esbeltos" in result.errors[0]["message"]


def test_shear_buckling_is_blocked(engine):
    # Plate 500 x 5: d/t = 100 > 1.10*sqrt(5*E/Fy) = 59.2, so Cv2 < 1 (G4). No rectangular HSS of the catalog reaches it.
    case = fire_case(550, name="PLATINA", L=None, Vux=1, custom_section={"type": "SOLID_RECTANGULAR", "H": 500, "B": 5})
    assert (
        engine.run(case.model_copy(update={"condition": "ultimate", "fire": None}))
        .check("shear_x")
        .result["classification"]["elements"][0]["Cv"]
        < 1
    )
    check = engine.run(case).check("shear_x")
    assert check.status.value == "INCOMPLETE" and "pandeo por cortante" in check.errors[0]["message"]


def test_cb_is_not_amplified_in_fire(engine):
    flexure = {**HOLES, "Cb": 1.2, "tension_cb_amplification": True}
    result = engine.run(fire_case(550, Pu=-100, Mux=50, flexure=flexure, tension={"An": 8000, "U": 0.9})).check("flexure_x").result
    assert result["inputs"]["Cb"] == 1.2 and any("DA4-6" in n for n in result["notes"])


def _encased(**demand):
    encased = {"H": 610, "B": 610, "Fysr": 420, "transverse": TIES,
               "bars": [{"area": 510, "db": 25.4, "x": x, "y": y} for x, y in ((241, 241), (241, -241), (-241, 241), (-241, -241))]}
    temperatures = {"steel_temperature": 500, "concrete_temperature": 200, "bar_temperature": 300}
    return composite_fire(
        "W10X45", {"kind": "encased", "concrete": CONCRETE, "encased": encased}, temperatures, L=3000, tau_b=0.8, **demand
    )


@pytest.mark.parametrize("demand, check_id", [({"Pu": 1}, "axial"), ({"Mux": 1}, "flexure_x"), ({"Vux": 1}, "shear_x")])
def test_encased_column_stays_incomplete_above_200_degrees(engine, demand, check_id):
    result = engine.run(_encased(**demand))
    assert result.status.value == "INCOMPLETE" and result.check(check_id).errors[0]["code"] == "FIRE_NOT_COVERED"


@pytest.mark.parametrize(
    "build",
    [
        lambda: composite_fire("PTE100X50X3MM", {"kind": "filled", "concrete": CONCRETE}, {"steel_temperature": 500}, tau_b=0.8, Mux=1),
        lambda: composite_fire("W21X50", beam_data(), {"steel_temperature": 500}, Mux=1),
        lambda: composite_fire("MURO", _wall({"fc": 40, "L": 3300, "tsc": 600, "t": 14, "tf": 14}), {"steel_temperature": 500}, Mux=1),
        lambda: composite_fire(
            'PTER8"X5.00MM',
            {"kind": "filled", "concrete": CONCRETE, "filled": _bars({"Fysr": 420, "bars": [(200, 16, 0, 55), (200, 16, 0, -55)]})},
            {"steel_temperature": 500, "concrete_temperature": 300},
            tau_b=0.8,
            Mux=1,
        ),
        lambda: composite_fire(
            "PTE100X50X3MM",
            {"kind": "filled", "concrete": CONCRETE},
            {"steel_temperature": 500, "concrete_temperature": 300, "bar_temperature": 300},
            tau_b=0.8,
            Mux=1,
        ),
        lambda: composite_fire(
            "PTE100X50X3MM",
            {"kind": "filled", "concrete": CONCRETE},
            {"steel_temperature": 500, "concrete_layers": [{"thickness": 10, "T": 300}]},
            tau_b=0.8,
            Mux=1,
        ),
        lambda: composite_fire(
            "MURO-C",
            _c_wall({"L": 6000, "W": 2500, "tsc_f": 500, "tp": 16}),
            {"steel_temperature": 500, "concrete_layers": [{"thickness": 10, "T": 300}]},
            Mux=1,
        ),
        lambda: composite_fire(
            "MURO-C",
            _c_wall({"L": 6000, "W": 2500, "tsc_f": 500, "tp": 16}),
            {"steel_temperature": 500, "web_layers": [{"thickness": 10, "T": 300}]},
            Mux=1,
        ),
    ],
)
def test_each_material_needs_its_temperature_and_only_where_it_applies(build):
    with pytest.raises(ValueError):
        build()


def test_layers_must_add_up_to_half_the_concrete(engine):
    case = composite_fire(
        "MURO",
        _wall({"fc": 40, "L": 3300, "tsc": 600, "t": 14, "tf": 14}),
        {"steel_temperature": 500, "concrete_layers": [{"thickness": 100, "T": 300}]},
        Mux=1,
    )
    check = engine.run(case).check("flexure_x")
    assert check.status.value == "INCOMPLETE" and "fire.concrete_layers" in check.errors[0]["details"]["fields"]


def test_c_wall_whose_neutral_axis_leaves_the_web_at_temperature_is_blocked(engine):
    # A.2.6 assumes the neutral axis in the web. At 700 deg C the steel loses so much that the concrete of the flanges balances
    # it: no equation of the guide applies.
    spec = {"L": 6000, "W": 2500, "tsc_f": 500, "tp": 16}
    check = engine.run(composite_fire("MURO-C", _c_wall(spec), {"steel_temperature": 700, "concrete_temperature": 250}, Mux=1)).check(
        "flexure_x"
    )
    assert check.status.value == "INCOMPLETE" and "eje neutro" in check.errors[0]["message"]


def test_coupling_beam_axial_stays_blocked(engine):
    spec = {"fc": 40, "b": 450, "h": 600, "tf": 20, "tw": 12}
    check = engine.run(composite_fire("CB", _coupling(spec), {"steel_temperature": 500, "concrete_temperature": 200}, L=2000, Pu=1)).check(
        "axial"
    )
    assert check.status.value == "INCOMPLETE"


def test_concrete_above_55_mpa_is_outside_the_tables(engine):
    case = composite_fire(
        "PTE100X50X3MM",
        {"kind": "filled", "concrete": {**CONCRETE, "fc": 60}},
        {"steel_temperature": 500, "concrete_temperature": 200},
        L=2000,
        tau_b=0.8,
        Pu=1,
    )
    assert "55" in engine.run(case).check("axial").errors[0]["message"]


def test_beam_above_1100_degrees_is_blocked(engine):
    check = engine.run(
        fire_case(1100, Mux=1, L=None, name="W21X50", composite=beam_data(), tau_b=1.0, fire={"concrete_temperature": 300})
    ).check("flexure_x")
    assert check.status.value == "INCOMPLETE" and "1100" in check.errors[0]["message"]


def test_negative_flexure_of_a_beam_is_chapter_f_at_temperature(engine):
    case = fire_case(
        600, name="W21X50", Mux=1, L=2000, composite=beam_data(moment="negative"), tau_b=1.0, fire={"concrete_temperature": 300}
    )
    check = engine.run(case).check("flexure_x")
    assert check.chapter == "F" and check.result["governing_equation"].startswith("A-4")


@pytest.mark.parametrize(
    "data",
    [
        {"condition": "fire", "Vux": 1},
        {"fire": {"steel_temperature": 500}, "Vux": 1},
        {"condition": "fire", "fire": {"steel_temperature": 1200}, "Vux": 1},
        {"condition": "fire", "fire": {"steel_temperature": 10}, "Vux": 1},
        {"condition": "fire", "fire": {"steel_temperature": 500, "concrete_temperature": 200}, "Vux": 1},
        {
            "condition": "fire",
            "fire": {"steel_temperature": 500, "concrete_temperature": 200, "concrete_layers": [{"thickness": 1, "T": 100}]},
            "Vux": 1,
        },
    ],
)
def test_rejected_inputs(data):
    with pytest.raises(ValueError):
        SteelCase(section_name="W18X50", material={"Fy": 345}, **data)


def test_report_of_a_fire_case(engine):
    data = json.loads((ROOT / "examples/w_shape.json").read_text(encoding="utf-8"))
    (group,) = member_groups(execute_payload(data, engine))
    text = render_text(report_blocks(group))
    for sentence in (
        "### 1.4 Propiedades a temperatura elevada",
        "T del acero (°C)",
        "Tabla A-4.2.1",
        "Incendio a 550 °C — flexocompresión",
        "sin efecto",
        "### 6.2 Compresión (Capítulo E), condiciones de incendio; case gobernante: Incendio a 550 °C — flexocompresión",
        "### 7.2 Tracción (Capítulo D), condiciones de incendio",
        "Apéndice 4, 4.2.4d",
        "A-4-9",
        "### 9.3 Condiciones de incendio",
        "combinación A-4-1",
    ):
        assert sentence in text, sentence
    assert "esta resistencia en incendio no está programada" not in text


def test_report_shows_the_three_temperatures(engine):
    data = json.loads((ROOT / "examples/composite_filled_bars.json").read_text(encoding="utf-8"))
    (group,) = member_groups(execute_payload(data, engine))
    text = render_text(report_blocks(group))
    for sentence in ("T del acero (°C)", "T del concreto (°C)", "T de las barras (°C)", "A-4-11", "DA4-8"):
        assert sentence in text, sentence


def test_a_steel_member_rejects_the_concrete_temperature_through_the_json(engine):
    with pytest.raises(ValueError):
        execute_payload(
            {
                "section_name": "W14X90",
                "material": "ASTM A36",
                "condition": "fire",
                "fire": {"steel_temperature": 500, "bar_temperature": 300},
                "Vux": 1,
            },
            engine,
        )


def test_one_json_mixes_the_conditions_and_at_180_degrees_gives_the_ambient_result(engine):
    data = json.loads((ROOT / "examples/w_shape.json").read_text(encoding="utf-8"))
    results = {tag: result for tag, _, result in execute_payload(data, engine)}
    assert {r.condition for r in results.values()} == {"ultimate", "construction", "fire"}
    hot, ambient = results["Incendio a 180 °C — sin efecto de temperatura"], results["Combinación 5 — flexocompresión biaxial y cortante"]
    assert [(c.id, c.capacity, c.ratio) for c in hot.checks] == [(c.id, c.capacity, c.ratio) for c in ambient.checks]
