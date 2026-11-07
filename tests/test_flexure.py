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
    """The program input of one oracle spec: ETABS axes and signs; angles carry their heel."""
    kind, axis = spec["kind"], spec.get("axis", "x_3")
    if kind in {"2l", "lg", "lp"}:
        flexure = {k: v for k, v in (("Cb", float(spec["Cb"]) if spec.get("Cb") else None),
                                     ("lateral_torsional_restraint", spec.get("restraint"))) if v is not None}
        lengths = {"Lx_3": spec["Lb"], "Ly_2": spec["Lb"], "Lz_1": spec["Lb"]} if spec.get("Lb") else None
        if kind == "2l":
            moments = {"Mx_3": moment * spec["Mx_3"]}
        elif kind == "lg":
            moments = {"Mx_3" if axis == "x_3" else "My_2": moment * spec["M"]}
        else:                               # principal axes: the geometric moments written by the oracle
            moments = {"Mx_3": moment * float(spec["Mx_3"]), "My_2": moment * float(spec["My_2"])}
        return SteelCase(tau_b=1.0, section_name=spec["name"], material={"Fy": spec["fy"]}, flexure=flexure, lengths=lengths,
                         heel=spec["heel"], **moments)
    flexure = {"tension_flange_holes": False}
    if spec.get("Cb"):
        flexure["Cb"] = float(spec["Cb"])
    if spec.get("holes"):
        flexure.update(tension_flange_holes=True, Afn=spec["holes"])
    sign = spec.get("Mx_3", 1)              # built-up I: Mx_3 < 0 compresses the -2 flange
    data = {"material": {"Fy": spec["fy"], **({"Fu": spec["Fu"]} if spec.get("Fu") else {})},
            "Mx_3" if axis == "x_3" else "My_2": sign * moment, "flexure": flexure}
    if spec.get("Lb"):
        data["lengths"] = {"Lx_3": spec["Lb"], "Ly_2": spec["Lb"], "Lz_1": spec["Lb"]}
    if kind == "bar":
        data.update(section_name="BAR", custom_section={"type": "SOLID_RECTANGULAR", "H": spec["H"], "B": spec["B"]})
    elif kind == "round":
        data.update(section_name="ROUND", custom_section={"type": "SOLID_CIRCULAR", "diameter": spec["D_"]})
    elif kind in {"bui", "buiy"}:
        data.update(section_name="PL", custom_section={
            "type": "I_BUILT_UP", "d": spec["d"], "tw": spec["tw"], "flange_plus2": {"b": spec["plus2"][0], "t": spec["plus2"][1]},
            "flange_minus2": {"b": spec["minus2"][0], "t": spec["minus2"][1]}})
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


L3000 = {"Lx_3": 3000, "Ly_2": 3000, "Lz_1": 3000}


@pytest.mark.parametrize("name, flexure, lengths, field", [
    ("W14X90", {}, L3000, "flexure.tension_flange_holes"),                   # F13.1 must be declared
    ("W14X90", {"tension_flange_holes": False}, None, "lengths"),            # LTB needs Lb, from the lengths
    ("IPE 100", {"tension_flange_holes": False}, L3000, None),               # catalog without Zx/Sx/J/Cw
])
def test_missing_flexure_data_is_incomplete(engine, name, flexure, lengths, field):
    check = engine.run(SteelCase(tau_b=1.0, section_name=name, material={"Fy": 345}, Mx_3=10, flexure=flexure, lengths=lengths)).checks[0]
    assert check.status.value == "INCOMPLETE" and check.capacity is None
    if field:
        assert field in check.errors[0]["details"]["fields"]


HEEL = {"axis_2": "-", "axis_3": "-"}        # long leg toward +2, short leg toward +3


@pytest.mark.parametrize("name, kwargs, code", [
    ("2L4X4X1/4", {"My_2": 1, "heel": {"axis_2": "+"}}, "FLEXURE_DOMAIN_BLOCKED"),                   # not in F9
    ("IPE 80", {"My_2": 1}, "CATALOG_DATA_INCONSISTENT"),                # Iy contradicts ry and Sy
])
def test_blocked_or_inconsistent_domains_never_pass(engine, name, kwargs, code):
    result = engine.run(SteelCase(tau_b=1.0, section_name=name, material={"Fy": 345},
                                  lengths={"Lx_3": 1000, "Ly_2": 1000, "Lz_1": 1000}, flexure={"tension_flange_holes": False,
                                           "lateral_torsional_restraint": "none"}, **kwargs))
    assert result.status.value == "INCOMPLETE" and result.errors[0]["code"] == code


@pytest.mark.parametrize("name, heel, field", [
    ("2L4X4X1/4", None, "heel.axis_2"),
    ("L4X4X1/4", None, "heel.axis_2"),
    ("L4X4X1/4", {"axis_2": "-"}, "heel.axis_3"),
])
def test_angles_need_their_heel(engine, name, heel, field):
    check = engine.run(SteelCase(tau_b=1.0, section_name=name, material={"Fy": 345}, Mx_3=1, heel=heel,
                                 lengths={"Lx_3": 2000, "Ly_2": 2000, "Lz_1": 2000})).checks[0]
    assert check.status.value == "INCOMPLETE" and field in check.errors[0]["details"]["fields"]


@pytest.mark.parametrize("restraint, legs, axial, axes", [
    ("none", "L4X4X1/4", 0, {"flexure_x_3"}),                     # F10.2(2): one geometric moment, equal legs
    ("continuous", "L6X4X3/8", 0, {"flexure_x_3"}),               # F10.2(2): continuous restraint
    ("none", "L6X4X3/8", 0, {"flexure_w", "flexure_z"}),          # unequal legs without restraint: principal axes
    (None, "L4X4X1/4", 0, {"flexure_w", "flexure_z"}),            # no restraint declared: principal axes
    ("none", "L4X4X1/4", 10, {"flexure_w", "flexure_z"}),         # with axial force: principal axes and H2
])
def test_single_angle_moments_go_to_the_principal_axes_when_f10_needs_them(engine, restraint, legs, axial, axes):
    flexure = {"lateral_torsional_restraint": restraint} if restraint else None
    tension = {"tension": {"An": 1000, "U": 1.0}, "material": {"Fy": 345, "Fu": 450}} if axial else {"material": {"Fy": 345}}
    result = engine.run(SteelCase(tau_b=1.0, section_name=legs, P=axial, Mx_3=1, heel=HEEL, flexure=flexure,
                                  lengths={"Lx_3": 2000, "Ly_2": 2000, "Lz_1": 2000}, **tension))
    assert {c.id for c in result.checks if c.id.startswith("flexure")} == axes


@pytest.mark.parametrize("heel, moment, toe", [
    ({"axis_2": "-", "axis_3": "-"}, 1, "compression"),     # long-leg toe at +2: Mx_3 > 0 compresses it
    ({"axis_2": "-", "axis_3": "-"}, -1, "tension"),
    ({"axis_2": "+", "axis_3": "-"}, -1, "compression"),    # toe at -2
])
def test_the_sign_of_the_moment_gives_the_compressed_toe(sections, heel, moment, toe):
    section = sections["L4X4X1/4"]
    case = SteelCase(tau_b=1.0, section_name=section.name, material={"Fy": 345}, Mx_3=moment, heel=heel,
                     flexure={"lateral_torsional_restraint": "none"}, lengths={"Lx_3": 2000, "Ly_2": 2000, "Lz_1": 2000})
    ltb = flexure_strength(case, section, "x_3")["modes"]["LTB"]
    assert ltb["Mcr_equation"] == ("F10-5a" if toe == "compression" else "F10-5b")


def test_beta_w_comes_from_the_catalog_with_the_sign_of_the_compressed_leg(sections):
    section = sections["L6X4X3/8"]
    beta = {}
    # Heel at (-2, -3): Mx_3 > 0 compresses the +2 face, where the long-leg toe lies; My_2 > 0 compresses +3 (short-leg toe).
    for leg, moments in (("long", {"Mx_3": 1}), ("short", {"My_2": 1})):
        case = SteelCase(tau_b=1.0, section_name=section.name, material={"Fy": 345}, heel=HEEL,
                         lengths={"Lx_3": 2000, "Ly_2": 2000, "Lz_1": 2000}, **moments)
        beta[leg] = flexure_strength(case, section, "w")["modes"]["LTB"]["beta_w_mm"]
    assert beta["short"] == section.beta_w > 0 and beta["long"] == -section.beta_w        # Commentary F10
    with pytest.raises(IncompleteSectionDataError) as blocked:
        flexure_strength(case, section.model_copy(update={"beta_w": None}), "w")
    assert blocked.value.details["fields"] == ["section.beta_w"]


def test_single_angle_e5_with_moments_is_blocked(engine):
    result = engine.run(SteelCase(tau_b=1.0, section_name="L4X4X1/4", material={"Fy": 345}, P=-10, Mx_3=1, heel=HEEL,
                                  lengths={"Lx_3": 1000, "Ly_2": 1000, "Lz_1": 1000},
                                  single_angle_e5={"configuration": "a", "connected_leg": "long", "L": 1000,
                                                   "loaded_at_ends_through_same_leg": True,
                                                   "welded_or_two_bolts_min": True,
                                                   "no_intermediate_transverse_loads": True},
                                  flexure={"lateral_torsional_restraint": "none"}))
    assert result.check("axial").errors[0]["code"] == "COMPRESSION_DOMAIN_BLOCKED"


def test_a_known_failure_is_not_hidden_by_the_interaction(engine):
    result = engine.run(SteelCase(tau_b=1.0, section_name="W14X90", material={"Fy": 345}, P=-500, Mx_3=5000,
                                  lengths={"Lx_3": 3000, "Ly_2": 3000, "Lz_1": 3000},
                                  flexure={"tension_flange_holes": False}))
    assert result.status.value == "FAIL"


def test_cb_default_is_reported(engine):
    check = engine.run(SteelCase(tau_b=1.0, section_name="W18X50", material={"Fy": 345}, Mx_3=100,
                                 lengths={"Lx_3": 4000, "Ly_2": 4000, "Lz_1": 4000}, flexure={"tension_flange_holes": False})).checks[0]
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
        "#### 9.2.2 Respecto de y, eje 2 (My_2; en ángulos simples, eje principal z)" in text
        and "Flexión respecto de y (eje 2) (Capítulo F); case gobernante: única." in text
        and "F7-3" in text
        and "be" in text
    )
    assert "φb·Mn = 0.90 · Mn" in text and "Obligaciones del Capítulo F" in text


@pytest.mark.parametrize("lengths, axis, moment, expected", [
    ({"Lx_3": 9000, "Ly_2": 4000, "Lz_1": 6000}, "x_3", "Mx_3", 4000),   # min(Ly_2, Lz_1)
    ({"Lx_3": 9000, "Ly_2": 6000, "Lz_1": 4000}, "x_3", "Mx_3", 4000),
    ({"Lx_3": 4000, "Ly_2": 9000, "Lz_1": 6000}, "y_2", "My_2", 4000),   # min(Lx_3, Lz_1)
    ({"Lx_3": 6000, "Ly_2": 9000, "Lz_1": 4000}, "y_2", "My_2", 4000),
])
def test_lb_comes_from_the_lengths(engine, lengths, axis, moment, expected):
    case = SteelCase(
        tau_b=1.0, section_name="W18X50", material={"Fy": 345}, flexure={"tension_flange_holes": False}, lengths=lengths, **{moment: 10}
    )
    assert engine.run(case).check(f"flexure_{axis}").result["inputs"]["Lb_mm"] == expected


def test_lb_is_no_longer_an_input():
    with pytest.raises(ValueError):
        SteelCase(tau_b=1.0, section_name="W18X50", material={"Fy": 345}, Mx_3=10, flexure={"Lb": 3000})


def test_ltb_with_lb_from_the_lengths_matches_independent_calculation(engine):
    ref = REFERENCE["W-F2-inelastic-LTB"]                       # W18X50, Lb = 4000
    case = SteelCase(tau_b=1.0, section_name="W18X50", material={"Fy": 345}, Mx_3=1, flexure={"tension_flange_holes": False},
                     lengths={"Lx_3": 12000, "Ly_2": 4000, "Lz_1": 9000})
    assert engine.run(case).check("flexure_x_3").capacity == pytest.approx(float(ref["phiMn_kNm"]), rel=REL)


# --- Welded built-up I-shapes (F2 to F6, F13.2) -------------------------------------------------------------------------

def girder(d, tw, plus2, minus2, flexure=None, lengths=None, **demands):
    return SteelCase(section_name="PL", material={"Fy": 345, "Fu": 450}, lengths=lengths or {"Lx_3": 3000, "Ly_2": 3000, "Lz_1": 3000},
                     custom_section={"type": "I_BUILT_UP", "d": d, "tw": tw, "flange_plus2": {"b": plus2[0], "t": plus2[1]},
                                     "flange_minus2": {"b": minus2[0], "t": minus2[1]}},
                     flexure={"tension_flange_holes": False, **(flexure or {})}, **demands)


def test_plate_properties_of_a_doubly_symmetric_girder():
    p = built_up_i_properties(d=600, tw=10, bf_plus2=250, tf_plus2=20, bf_minus2=250, tf_minus2=20)
    assert p["area"] == pytest.approx(2 * 250 * 20 + 560 * 10)
    assert p["ix"] == pytest.approx(10 * 560**3 / 12 + 2 * (250 * 20**3 / 12 + 250 * 20 * 290**2))
    assert p["zx"] == pytest.approx(2 * 250 * 20 * 290 + 10 * 560**2 / 4)
    assert p["cw"] == pytest.approx((2 * 20 * 250**3 / 12) * 580**2 / 4)          # Iy(flanges)*ho^2/4
    assert p["j"] == pytest.approx((2 * 250 * 20**3 + 560 * 10**3) / 3)
    assert p["yo"] == pytest.approx(0, abs=1e-9) and p["H"] == pytest.approx(1)


def test_the_compression_flange_swaps_sxc_and_sxt(engine):
    section = engine.section_for(girder(900, 8, (350, 22), (250, 16), Mx_3=1))
    plus2, minus2 = i_major_properties(section, "plus2"), i_major_properties(section, "minus2")
    assert plus2["Sxc"] == pytest.approx(minus2["Sxt"]) and plus2["Sxt"] == pytest.approx(minus2["Sxc"])
    assert plus2["Sxc"] > plus2["Sxt"] and plus2["hc"] < minus2["hc"]
    assert section.sx == pytest.approx(min(plus2["Sxc"], plus2["Sxt"]))                 # F13.1: minimum Sx


def test_the_sign_of_mx_3_gives_the_compressed_flange(engine):
    sxc = {}
    for sign in (1, -1):
        check = engine.run(girder(900, 8, (350, 22), (250, 16), Mx_3=100 * sign)).check("flexure_x_3")
        sxc[sign] = check.result["modes"]["CFY"]["Sxc"]
        assert ("cara +2" if sign > 0 else "cara −2") in " ".join(check.result["notes"])
    assert sxc[1] > sxc[-1]                     # the wide flange (+2) is compressed by Mx_3 > 0


@pytest.mark.parametrize("flange, provision, states", [
    (1, "F4", {"CFY", "LTB", "TFY"}), (-1, "F4", {"CFY", "LTB"}),          # Mx_3 > 0 compresses the wide +2 flange
])
def test_singly_symmetric_girders_use_f4_and_discharge_its_obligations(engine, flange, provision, states):
    check = engine.run(girder(900, 8, (350, 22), (250, 16), Mx_3=100 * flange)).check("flexure_x_3")
    assert check.result["provisions"] == ["F1", provision, "F13.1"] and check.status.value == "PASS"
    assert {k for k, m in check.result["modes"].items() if m["applies"]} == states
    assert set(check.result["modes"]) == {"CFY", "LTB", "FLB", "TFY", "TFR"}
    assert all(o.satisfied_by for o in check.obligations)


def test_a_rolled_shape_with_a_noncompact_web_goes_to_f4(sections):
    section = sections["W18X50"].model_copy(update={"h_tw_ratio": 110.0})               # 3.76 < 110/sqrt(E/Fy) < 5.70
    case = SteelCase(section_name="W18X50", material={"Fy": 345}, Mx_3=1, lengths={"Lx_3": 1000, "Ly_2": 1000, "Lz_1": 1000},
                     flexure={"tension_flange_holes": False})
    out = flexure_strength(case, section, "x_3")
    rpc = out["modes"]["CFY"]
    assert out["provisions"][1] == "F4" and rpc["Rpc_equation"] == "F4-9b"
    assert 1 < rpc["Rpc"] < section.zx / section.sx and not out["modes"]["TFY"]["applies"]    # Sxt = Sxc


def test_slender_web_girder_uses_f5_with_rpg(engine):
    lengths = {"Lx_3": 6000, "Ly_2": 6000, "Lz_1": 6000}
    check = engine.run(girder(1200, 8, (400, 20), (400, 20), lengths=lengths, Mx_3=100)).check("flexure_x_3")
    modes = check.result["modes"]
    assert check.result["provisions"][1] == "F5" and modes["CFY"]["Rpg"] < 1
    assert modes["FLB"]["Fcr_equation"] == "F5-8" and modes["LTB"]["Fcr_equation"] == "F5-3"


def test_f13_2_limits_of_slender_webs_decide_the_status(engine):
    result = engine.run(girder(1500, 5, (400, 25), (400, 25), Mx_3=10))
    assert result.check("flexure_x_3").status.value == "PASS"
    failed = [e for e in result.errors if e["code"] == "TECHNICAL_REQUIREMENT_NOT_MET"]
    assert result.status.value == "FAIL" and {e["provision"] for e in failed} == {"F13.2 (F13-4)", "F13.2"}


def test_f13_2_limits_iyc_over_iy_of_singly_symmetric_girders(engine):
    result = engine.run(girder(900, 10, (500, 25), (150, 10), Mx_3=10))
    assert result.status.value == "FAIL"
    assert any(e["provision"] == "F13.2 (F13-2)" for e in result.errors)


@pytest.mark.parametrize("custom", [
    {"type": "I_BUILT_UP", "d": 600, "tw": 10, "flange_plus2": {"b": 250, "t": 20}},                       # -2 flange missing
    {"type": "I_BUILT_UP", "d": 600, "tw": 10, "H": 5, "flange_plus2": {"b": 250, "t": 20}, "flange_minus2": {"b": 250, "t": 20}},
    {"type": "SOLID_RECTANGULAR", "H": 100, "B": 20, "tw": 5},
])
def test_built_up_input_must_be_complete_and_exclusive(custom):
    with pytest.raises(ValueError):
        SteelCase(section_name="PL", material={"Fy": 345}, Mx_3=1, custom_section=custom)


def test_flanges_must_leave_a_web(engine):
    with pytest.raises(ValidationError):
        engine.run(girder(40, 10, (250, 20), (250, 20), Mx_3=1))


def test_built_up_girders_in_fire_use_chapter_f_not_a_4_13(engine):
    case = girder(600, 10, (250, 20), (250, 20), Mx_3=10).model_copy(
        update={"condition": "fire", "fire": {"steel_temperature": 500}})
    ltb = engine.run(case).check("flexure_x_3").result["modes"]["LTB"]
    assert ltb["equation"] == "F2-2" and "4.2.4d(e)" in ltb["provision"]


def test_cb_is_amplified_only_for_doubly_symmetric_girders(engine):
    def factor(plus2, minus2):
        case = girder(900, 10, plus2, minus2, flexure={"tension_cb_amplification": True}, P=200, Mx_3=10)
        return engine.run(case).check("flexure_x_3").result["inputs"]["H1_2_Cb_factor"]
    assert factor((300, 20), (300, 20)) > 1 and factor((350, 22), (250, 16)) is None


def test_f13_3_replaces_f13_4_with_stiffeners_at_a_over_h_up_to_1_5(engine):
    stiffeners = {"a": 1500, "b": 120, "t": 12, "arrangement": "pair", "material": {"Fy": 345}}
    # h/tw = 1450/6 = 241.7: within 12.0*sqrt(E/Fy) = 288.9 (F13-3), beyond 0.40E/Fy = 231.9 (F13-4)
    rows = engine.run(girder(1500, 6, (400, 25), (400, 25), Mx_3=10, stiffeners=stiffeners)).requirements["geometry"]
    provisions = {r["provision"]: r for r in rows if r["provision"].startswith("F13.2")}
    assert provisions["F13.2 (F13-3)"]["status"] == "cumple" and "F13.2" not in provisions        # 260 is for unstiffened girders
