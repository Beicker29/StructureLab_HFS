"""Chapter F: catalog profiles vs independent hand calculations, selection and blocks.

Expected values: tests/fixtures/chapter_f/reference.json from tests/oracles/chapter_f.py
(Decimal, written from a360-22w.pdf F1-F13 and B4.1b, no product import).
"""
import json
import math

import pytest
from conftest import ROOT, calculation_report

from steel_design.codes.aisc_360_22 import flexure as eq
from steel_design.domain.flexure import flexure_strength
from steel_design.errors import IncompleteSectionDataError, ValidationError
from steel_design.models import SteelCase
from steel_design.sections.geometry import built_up_i_properties, i_major_properties

REFERENCE = json.loads((ROOT / "tests/fixtures/chapter_f/reference.json").read_text(encoding="utf-8"))["cases"]
REL = 1e-9


def flexure_case(spec, moment=1.0):
    kind, axis = spec["kind"], spec.get("axis", "x")
    if kind in {"2l", "lg", "lp"}:
        flexure = {k: v for k, v in (("Cb", float(spec["Cb"]) if spec.get("Cb") else None),
                                     ("lateral_torsional_restraint", spec.get("restraint"))) if v is not None}
        lengths = {"Lx": spec["Lb"], "Ly": spec["Lb"], "Lz": spec["Lb"]} if spec.get("Lb") else None
        angle = {k: v for k, v in (("web_legs", spec.get("web_legs")), ("toe", spec.get("toe")),
                                   ("leg_in_compression", spec.get("leg"))) if v}
        moment_key = {"x": "Mux", "y": "Muy", "w": "Mw", "z": "Mz"}[axis]
        return SteelCase(tau_b=1.0, section_name=spec["name"], material={"Fy": spec["fy"]}, flexure=flexure, lengths=lengths,
                         angle_flexure=angle, **{moment_key: moment})
    flexure = {"tension_flange_holes": False}
    if spec.get("Cb"):
        flexure["Cb"] = float(spec["Cb"])
    if spec.get("holes"):
        flexure.update(tension_flange_holes=True, Afn=spec["holes"])
    data = {"material": {"Fy": spec["fy"], **({"Fu": spec["Fu"]} if spec.get("Fu") else {})},
            "Mux" if axis == "x" else "Muy": moment, "flexure": flexure}
    if spec.get("Lb"):
        data["lengths"] = {"Lx": spec["Lb"], "Ly": spec["Lb"], "Lz": spec["Lb"]}
    if kind == "bar":
        data.update(section_name="BAR", custom_section={"type": "SOLID_RECTANGULAR", "H": spec["H"], "B": spec["B"]})
    elif kind == "round":
        data.update(section_name="ROUND", custom_section={"type": "SOLID_CIRCULAR", "diameter": spec["D_"]})
    elif kind in {"bui", "buiy"}:
        data.update(section_name="PL", custom_section={
            "type": "I_BUILT_UP", "d": spec["d"], "tw": spec["tw"], "top_flange": {"b": spec["top"][0], "t": spec["top"][1]},
            "bottom_flange": {"b": spec["bottom"][0], "t": spec["bottom"][1]}})
        if spec.get("comp"):
            flexure["compression_flange"] = spec["comp"]
    else:
        data["section_name"] = spec["name"]
    return SteelCase(tau_b=1.0, **data)


@pytest.mark.parametrize("case_id", sorted(REFERENCE))
def test_catalog_profiles_match_independent_calculation(engine, case_id):
    ref = REFERENCE[case_id]
    result = engine.run(flexure_case(ref["spec"]))
    check = result.checks[0]
    r = check.result
    evaluated = {k: m for k, m in r["modes"].items() if m["applies"]}
    assert set(evaluated) == set(ref["modes_kNm"]), case_id
    for mode, value in ref["modes_kNm"].items():
        assert evaluated[mode]["Mn_kNm"] == pytest.approx(float(value), rel=REL), (case_id, mode)
    assert r["governing_mode"] == ref["governing"]
    assert check.capacity == pytest.approx(float(ref["phiMn_kNm"]), rel=REL)
    assert check.capacity == pytest.approx(0.90 * r["Mn_kNm"], rel=1e-15)        # F1(a), LRFD


def test_reference_bank_covers_sections_and_equations():
    families = {(c["spec"]["kind"], c["spec"].get("family")) for c in REFERENCE.values()}
    assert {("w", "W"), ("w", "CHANNEL"), ("rhss", None), ("chss", None), ("bar", None), ("round", None),
            ("2l", None), ("lg", None), ("lp", None), ("bui", None), ("buiy", None)} <= families
    assert {c["governing"] for c in REFERENCE.values()} >= {"Y", "LTB", "FLB", "TFR", "LB", "LLB", "TFY"}


def test_every_limit_state_is_reported_and_obligations_discharged(engine):
    result = engine.run(flexure_case(REFERENCE["W-F3-FLB"]["spec"]))
    check = result.checks[0]
    assert set(check.result["modes"]) == {"Y", "LTB", "FLB", "TFR"}
    assert all(o.satisfied_by for o in check.obligations) and check.status.value == "PASS"
    assert not check.result["modes"]["Y"]["applies"] and check.result["modes"]["Y"]["reason"]


L3000 = {"Lx": 3000, "Ly": 3000, "Lz": 3000}


@pytest.mark.parametrize("name, flexure, lengths, field", [
    ("W14X90", {}, L3000, "flexure.tension_flange_holes"),                   # F13.1 must be declared
    ("W14X90", {"tension_flange_holes": False}, None, "lengths"),            # LTB needs Lb, from the lengths
    ("IPE 100", {"tension_flange_holes": False}, L3000, None),               # catalog without Zx/Sx/J/Cw
])
def test_missing_flexure_data_is_incomplete(engine, name, flexure, lengths, field):
    check = engine.run(SteelCase(tau_b=1.0, section_name=name, material={"Fy": 345}, Mux=10, flexure=flexure, lengths=lengths)).checks[0]
    assert check.status.value == "INCOMPLETE" and check.capacity is None
    if field:
        assert field in check.errors[0]["details"]["fields"]


@pytest.mark.parametrize("name, kwargs, code", [
    ("2L4X4X1/4", {"Muy": 1, "angle_flexure": {"web_legs": "tension"}}, "FLEXURE_DOMAIN_BLOCKED"),  # not in F9
    ("L6X4X3/8", {"Mux": 1, "angle_flexure": {"toe": "compression"}}, "FLEXURE_DOMAIN_BLOCKED"),    # unequal: w/z
    ("W14X90", {"Mw": 1}, "FLEXURE_DOMAIN_BLOCKED"),                                                 # Mw only for L
    ("IPE 80", {"Muy": 1}, "CATALOG_DATA_INCONSISTENT"),                # Iy contradicts ry and Sy
])
def test_blocked_or_inconsistent_domains_never_pass(engine, name, kwargs, code):
    result = engine.run(SteelCase(tau_b=1.0, section_name=name, material={"Fy": 345},
                                  lengths={"Lx": 1000, "Ly": 1000, "Lz": 1000}, flexure={"tension_flange_holes": False,
                                           "lateral_torsional_restraint": "none"}, **kwargs))
    assert result.status.value == "INCOMPLETE" and result.errors[0]["code"] == code


@pytest.mark.parametrize(
    "name, kwargs, field",
    [
        ("2L4X4X1/4", {"Mux": 1}, "angle_flexure.web_legs"),
        ("L4X4X1/4", {"Mux": 1, "angle_flexure": {"toe": "tension"}}, "flexure.lateral_torsional_restraint"),
        (
            "L4X4X1/4",
            {"Mux": 1, "flexure": {"lateral_torsional_restraint": "none"}, "lengths": {"Lx": 1000, "Ly": 1000, "Lz": 1000}},
            "angle_flexure.toe",
        ),
        ("L6X4X3/8", {"Mw": 1, "lengths": {"Lx": 1000, "Ly": 1000, "Lz": 1000}}, "angle_flexure.leg_in_compression"),
    ],
)
def test_angle_data_must_be_explicit(engine, name, kwargs, field):
    kwargs.setdefault("lengths", {"Lx": 2000, "Ly": 2000, "Lz": 2000})
    check = engine.run(SteelCase(tau_b=1.0, section_name=name, material={"Fy": 345}, **kwargs)).checks[0]
    assert check.status.value == "INCOMPLETE" and field in check.errors[0]["details"]["fields"]


def test_beta_w_comes_from_the_catalog_with_the_sign_of_the_compressed_leg(sections):
    section = sections["L6X4X3/8"]
    beta = {}
    for leg in ("short", "long"):
        case = SteelCase(tau_b=1.0, section_name=section.name, material={"Fy": 345}, Mw=1, lengths={"Lx": 2000, "Ly": 2000, "Lz": 2000},
                         angle_flexure={"leg_in_compression": leg})
        beta[leg] = flexure_strength(case, section, "w")["modes"]["LTB"]["beta_w_mm"]
    assert beta["short"] == section.beta_w > 0 and beta["long"] == -section.beta_w        # Commentary F10
    with pytest.raises(IncompleteSectionDataError) as blocked:
        flexure_strength(case, section.model_copy(update={"beta_w": None}), "w")
    assert blocked.value.details["fields"] == ["section.beta_w"]


def test_geometric_axis_f10_rejects_axial_compression(engine):
    result = engine.run(SteelCase(tau_b=1.0, section_name="L4X4X1/4", material={"Fy": 345}, Pu=10, Mux=1,
                                  lengths={"Lx": 1000, "Ly": 1000, "Lz": 1000},
                                  single_angle_e5={"configuration": "a", "connected_leg": "long", "L": 1000,
                                                   "loaded_at_ends_through_same_leg": True,
                                                   "welded_or_two_bolts_min": True,
                                                   "no_intermediate_transverse_loads": True},
                                  flexure={"lateral_torsional_restraint": "none"},
                                  angle_flexure={"toe": "compression"}))
    assert result.check("flexure_x").errors[0]["code"] == "FLEXURE_DOMAIN_BLOCKED"


def test_a_known_failure_is_not_hidden_by_the_interaction(engine):
    result = engine.run(SteelCase(tau_b=1.0, section_name="W14X90", material={"Fy": 345}, Pu=500, Mux=5000,
                                  lengths={"Lx": 3000, "Ly": 3000, "Lz": 3000},
                                  flexure={"tension_flange_holes": False}))
    assert result.status.value == "FAIL"


def test_cb_default_is_reported(engine):
    check = engine.run(SteelCase(tau_b=1.0, section_name="W18X50", material={"Fy": 345}, Mux=100,
                                 lengths={"Lx": 4000, "Ly": 4000, "Lz": 4000}, flexure={"tension_flange_holes": False})).checks[0]
    assert check.result["inputs"]["Cb"] == 1.0 and "valor por defecto" in check.result["notes"][0]


def test_formula_properties():
    lim = eq.limits(10, 200000, 345)
    assert lim["lambda_p"] == pytest.approx(0.38 * math.sqrt(200000 / 345))
    # F2-2 is continuous with Mp at Lp and with 0.7FySx at Lr (Cb = 1)
    args = dict(E=200000, Fy=345, Sx=1e6, Zx=1.1e6, ry=50, Iy=2e7, Cw=4e11, J=4e5, ho=400, Cb=1, channel=False)
    probe = eq.f2_ltb(**args, Lb=1000)
    at_lr = eq.f2_ltb(**args, Lb=probe["Lr_mm"])
    assert at_lr["Mn"] == pytest.approx(0.7 * 345 * 1e6, rel=1e-12)
    # Se of a section without ineffective width equals I/c
    se = eq.effective_section_modulus(inertia=1e6, A=500, depth=100, t=2, b=40, be=40)
    assert se["Se"] == pytest.approx(1e6 / 50)


def test_flexure_report(engine):
    case = flexure_case(REFERENCE["RHSS-F7-3-slender-flange"]["spec"])
    text = calculation_report(case, engine.run(case))
    assert (
        "#### 9.2.2 Respecto del eje Y (Muy, Mz)" in text
        and "Flexión respecto de y (Capítulo F); case gobernante: única." in text
        and "F7-3" in text
        and "be" in text
    )
    assert "φb·Mn = 0.90 · Mn" in text and "Obligaciones del Capítulo F" in text


@pytest.mark.parametrize("lengths, axis, moment, expected", [
    ({"Lx": 9000, "Ly": 4000, "Lz": 6000}, "x", "Mux", 4000),   # min(Ly, Lz)
    ({"Lx": 9000, "Ly": 6000, "Lz": 4000}, "x", "Mux", 4000),
    ({"Lx": 4000, "Ly": 9000, "Lz": 6000}, "y", "Muy", 4000),   # min(Lx, Lz)
    ({"Lx": 6000, "Ly": 9000, "Lz": 4000}, "y", "Muy", 4000),
])
def test_lb_comes_from_the_lengths(engine, lengths, axis, moment, expected):
    case = SteelCase(
        tau_b=1.0, section_name="W18X50", material={"Fy": 345}, flexure={"tension_flange_holes": False}, lengths=lengths, **{moment: 10}
    )
    assert engine.run(case).check(f"flexure_{axis}").result["inputs"]["Lb_mm"] == expected


def test_lb_is_no_longer_an_input():
    with pytest.raises(ValueError):
        SteelCase(tau_b=1.0, section_name="W18X50", material={"Fy": 345}, Mux=10, flexure={"Lb": 3000})


def test_ltb_with_lb_from_the_lengths_matches_independent_calculation(engine):
    ref = REFERENCE["W-F2-inelastic-LTB"]                       # W18X50, Lb = 4000
    case = SteelCase(tau_b=1.0, section_name="W18X50", material={"Fy": 345}, Mux=1, flexure={"tension_flange_holes": False},
                     lengths={"Lx": 12000, "Ly": 4000, "Lz": 9000})
    assert engine.run(case).check("flexure_x").capacity == pytest.approx(float(ref["phiMn_kNm"]), rel=REL)


# --- Welded built-up I-shapes (F2 to F6, F13.2) -------------------------------------------------------------------------

def girder(d, tw, top, bottom, flexure=None, lengths=None, **demands):
    return SteelCase(section_name="PL", material={"Fy": 345, "Fu": 450}, lengths=lengths or {"Lx": 3000, "Ly": 3000, "Lz": 3000},
                     custom_section={"type": "I_BUILT_UP", "d": d, "tw": tw, "top_flange": {"b": top[0], "t": top[1]},
                                     "bottom_flange": {"b": bottom[0], "t": bottom[1]}},
                     flexure={"tension_flange_holes": False, **(flexure or {})}, **demands)


def test_plate_properties_of_a_doubly_symmetric_girder():
    p = built_up_i_properties(d=600, tw=10, bf_top=250, tf_top=20, bf_bottom=250, tf_bottom=20)
    assert p["area"] == pytest.approx(2 * 250 * 20 + 560 * 10)
    assert p["ix"] == pytest.approx(10 * 560**3 / 12 + 2 * (250 * 20**3 / 12 + 250 * 20 * 290**2))
    assert p["zx"] == pytest.approx(2 * 250 * 20 * 290 + 10 * 560**2 / 4)
    assert p["cw"] == pytest.approx((2 * 20 * 250**3 / 12) * 580**2 / 4)          # Iy(flanges)*ho^2/4
    assert p["j"] == pytest.approx((2 * 250 * 20**3 + 560 * 10**3) / 3)
    assert p["yo"] == pytest.approx(0, abs=1e-9) and p["H"] == pytest.approx(1)


def test_the_compression_flange_swaps_sxc_and_sxt(engine):
    section = engine.section_for(girder(900, 8, (350, 22), (250, 16), Mux=1))
    top, bottom = i_major_properties(section, "top"), i_major_properties(section, "bottom")
    assert top["Sxc"] == pytest.approx(bottom["Sxt"]) and top["Sxt"] == pytest.approx(bottom["Sxc"])
    assert top["Sxc"] > top["Sxt"] and top["hc"] < bottom["hc"]
    assert section.sx == pytest.approx(min(top["Sxc"], top["Sxt"]))                     # F13.1: minimum Sx


def test_unequal_flanges_need_the_compression_flange(engine):
    result = engine.run(girder(900, 8, (350, 22), (250, 16), Mux=100))
    check = result.check("flexure_x")
    assert check.status.value == "INCOMPLETE" and check.errors[0]["details"]["fields"] == ["flexure.compression_flange"]


@pytest.mark.parametrize("flange, provision, states", [
    ("top", "F4", {"CFY", "LTB", "TFY"}), ("bottom", "F4", {"CFY", "LTB"}),
])
def test_singly_symmetric_girders_use_f4_and_discharge_its_obligations(engine, flange, provision, states):
    check = engine.run(girder(900, 8, (350, 22), (250, 16), flexure={"compression_flange": flange}, Mux=100)).check("flexure_x")
    assert check.result["provisions"] == ["F1", provision, "F13.1"] and check.status.value == "PASS"
    assert {k for k, m in check.result["modes"].items() if m["applies"]} == states
    assert set(check.result["modes"]) == {"CFY", "LTB", "FLB", "TFY", "TFR"}
    assert all(o.satisfied_by for o in check.obligations)


def test_a_rolled_shape_with_a_noncompact_web_goes_to_f4(sections):
    section = sections["W18X50"].model_copy(update={"h_tw_ratio": 110.0})               # 3.76 < 110/sqrt(E/Fy) < 5.70
    case = SteelCase(section_name="W18X50", material={"Fy": 345}, Mux=1, lengths={"Lx": 1000, "Ly": 1000, "Lz": 1000},
                     flexure={"tension_flange_holes": False})
    out = flexure_strength(case, section, "x")
    rpc = out["modes"]["CFY"]
    assert out["provisions"][1] == "F4" and rpc["Rpc_equation"] == "F4-9b"
    assert 1 < rpc["Rpc"] < section.zx / section.sx and not out["modes"]["TFY"]["applies"]    # Sxt = Sxc


def test_slender_web_girder_uses_f5_with_rpg(engine):
    check = engine.run(girder(1200, 8, (400, 20), (400, 20), lengths={"Lx": 6000, "Ly": 6000, "Lz": 6000}, Mux=100)).check("flexure_x")
    modes = check.result["modes"]
    assert check.result["provisions"][1] == "F5" and modes["CFY"]["Rpg"] < 1
    assert modes["FLB"]["Fcr_equation"] == "F5-8" and modes["LTB"]["Fcr_equation"] == "F5-3"


def test_f13_2_limits_of_slender_webs_decide_the_status(engine):
    result = engine.run(girder(1500, 5, (400, 25), (400, 25), Mux=10))
    assert result.check("flexure_x").status.value == "PASS"
    failed = [e for e in result.errors if e["code"] == "TECHNICAL_REQUIREMENT_NOT_MET"]
    assert result.status.value == "FAIL" and {e["provision"] for e in failed} == {"F13.2 (F13-4)", "F13.2"}


def test_f13_2_limits_iyc_over_iy_of_singly_symmetric_girders(engine):
    result = engine.run(girder(900, 10, (500, 25), (150, 10), flexure={"compression_flange": "top"}, Mux=10))
    assert result.status.value == "FAIL"
    assert any(e["provision"] == "F13.2 (F13-2)" for e in result.errors)


@pytest.mark.parametrize("custom", [
    {"type": "I_BUILT_UP", "d": 600, "tw": 10, "top_flange": {"b": 250, "t": 20}},                         # bottom flange missing
    {"type": "I_BUILT_UP", "d": 600, "tw": 10, "H": 5, "top_flange": {"b": 250, "t": 20}, "bottom_flange": {"b": 250, "t": 20}},
    {"type": "SOLID_RECTANGULAR", "H": 100, "B": 20, "tw": 5},
])
def test_built_up_input_must_be_complete_and_exclusive(custom):
    with pytest.raises(ValueError):
        SteelCase(section_name="PL", material={"Fy": 345}, Mux=1, custom_section=custom)


def test_flanges_must_leave_a_web(engine):
    with pytest.raises(ValidationError):
        engine.run(girder(40, 10, (250, 20), (250, 20), Mux=1))


def test_built_up_girders_in_fire_use_chapter_f_not_a_4_13(engine):
    case = girder(600, 10, (250, 20), (250, 20), Mux=10).model_copy(
        update={"condition": "fire", "fire": {"steel_temperature": 500}})
    ltb = engine.run(case).check("flexure_x").result["modes"]["LTB"]
    assert ltb["equation"] == "F2-2" and "4.2.4d(e)" in ltb["provision"]


def test_cb_is_amplified_only_for_doubly_symmetric_girders(engine):
    def factor(top, bottom):
        case = girder(900, 10, top, bottom, flexure={"tension_cb_amplification": True, "compression_flange": "top"}, Pu=-200, Mux=10)
        return engine.run(case).check("flexure_x").result["inputs"]["H1_2_Cb_factor"]
    assert factor((300, 20), (300, 20)) > 1 and factor((350, 22), (250, 16)) is None
