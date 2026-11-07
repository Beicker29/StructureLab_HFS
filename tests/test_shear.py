"""Chapter G: catalog profiles vs independent hand calculations, selection and blocks.

Expected values: tests/fixtures/chapter_g/reference.json from tests/oracles/chapter_g.py
(Decimal, written from a360-22w.pdf G1-G6, no product import).
"""
import json

import pytest
from conftest import ROOT, calculation_report

from steel_design.codes.aisc_360_22 import shear as eq
from steel_design.models import SteelCase

REFERENCE = json.loads((ROOT / "tests/fixtures/chapter_g/reference.json").read_text(encoding="utf-8"))["cases"]


def shear_case(spec, shear=1.0):
    data = {"material": {"Fy": spec["fy"]}, "Vx_3" if spec.get("axis") == "x_3" else "Vy_2": shear}
    if spec["kind"] == "bar":
        data.update(section_name="BAR", custom_section={"type": "SOLID_RECTANGULAR", "H": spec["H"], "B": spec["B"]})
    elif spec["kind"] == "round":
        data.update(section_name="ROUND", custom_section={"type": "SOLID_CIRCULAR", "diameter": spec["D_"]})
    elif spec["kind"] == "bui" or (spec["kind"] == "stiff" and not spec.get("name")):
        data.update(section_name="PL", custom_section={
            "type": "I_BUILT_UP", "d": spec["d"], "tw": spec["tw"], "flange_plus2": {"b": spec["plus2"][0], "t": spec["plus2"][1]},
            "flange_minus2": {"b": spec["minus2"][0], "t": spec["minus2"][1]}})
    else:
        data["section_name"] = spec["name"]
    if spec.get("Lv"):
        data["shear"] = {"Lv": spec["Lv"]}
    if spec["kind"] == "stiff":
        data["stiffeners"] = {"a": spec["a"], **spec["stiff"], "material": {"Fy": spec["fyst"]},
                              **({"end": spec["end"]} if spec.get("end") else {})}
        data["shear"] = {"panel": spec["panel"]}
    return SteelCase(tau_b=1.0, **data)


@pytest.mark.parametrize("case_id", sorted(REFERENCE))
def test_catalog_profiles_match_independent_calculation(engine, case_id):
    ref = REFERENCE[case_id]
    check = engine.run(shear_case(ref["spec"])).checks[0]
    assert check.chapter == "G" and check.status.value == "PASS", check.errors
    assert check.result["Vn_kN"] == pytest.approx(float(ref["Vn_kN"]), rel=1e-9)
    assert check.result["phi_v"] == float(ref["phi_v"])
    assert check.capacity == pytest.approx(float(ref["phiVn_kN"]), rel=1e-9)
    if "stiffened" in ref:                      # G2.4: the stiffener limits, and both strengths of G2.1 and the tension field
        oracle, mode = ref["stiffened"], check.result["modes"]["V"]
        assert mode["kv"] == pytest.approx(float(oracle["kv"]), rel=1e-12)
        limits = {r["id"]: r for r in check.result["requirements"]}
        assert limits["G2-16"]["limit"] == pytest.approx(float(oracle["b_t_max"]), rel=1e-12)
        assert limits["G2-17"]["value"] == pytest.approx(float(oracle["Ist"]), rel=1e-12)
        assert limits["G2-17"]["limit"] == pytest.approx(float(oracle["Ist1"]), rel=1e-12)
        if "Vn_tension_field" in oracle:
            assert mode["Vn_G2_1_N"] == pytest.approx(float(oracle["Vn_G2_1"]), rel=1e-9)
            assert mode["Vn_tension_field_N"] == pytest.approx(float(oracle["Vn_tension_field"]), rel=1e-9)
        if "beta_v" in oracle:
            assert mode["beta_v"] == pytest.approx(float(oracle["beta_v"]), rel=1e-9)
            assert mode["Mpf_Nmm"] == pytest.approx(float(oracle["Mpf"]), rel=1e-9)
            assert mode["Mpst_Nmm"] == pytest.approx(float(oracle["Mpst"]), rel=1e-9)


def test_reference_bank_covers_every_section_and_coefficient():
    kinds = {c["spec"]["kind"] for c in REFERENCE.values()}
    assert kinds == {"i", "rhss", "chss", "angle", "bar", "round", "bui", "stiff"}
    assert {c["spec"].get("panel") for c in REFERENCE.values()} >= {"interior", "end"}
    assert {c["phi_v"] for c in REFERENCE.values()} == {"1.00", "0.90"}         # G2.1(a) and G1(a)


@pytest.mark.parametrize("name, field, expected", [
    ("W24X62", "Cv_equation", "G2-2"), ("W16X26", "Cv_equation", "G2-4"),
    ("PTE100X40X1.5MM", "Cv_equation", "G2-10"),
])
def test_coefficient_branches(engine, name, field, expected):
    fy = 450 if name == "W16X26" else 345
    check = engine.run(SteelCase(tau_b=1.0, section_name=name, material={"Fy": fy}, Vy_2=1)).checks[0]
    assert check.result["modes"]["V"][field] == expected


def test_round_hss_without_lv_uses_the_lower_bound():
    with_lv = eq.round_hss_strength(E=200000, Fy=1000, Ag=1000, D=500, t=2, Lv=500)
    without = eq.round_hss_strength(E=200000, Fy=1000, Ag=1000, D=500, t=2)
    assert without["Fcr_equation"] == "G5-2b" and with_lv["Fcr_equation"] == "G5-2a"
    assert without["Vn"] <= with_lv["Vn"]


def test_cv2_branches_meet_within_the_rounding_of_the_constants():
    root = (1.2 * 200000 / 345) ** 0.5
    for limit, tolerance in ((1.10 * root, 1e-9), (1.37 * root, 3e-3)):      # 1.10/1.37 vs 1.51/1.37^2
        below = eq.cv2(h_tw=limit * (1 - 1e-12), kv=1.2, E=200000, Fy=345)["Cv"]
        above = eq.cv2(h_tw=limit * (1 + 1e-12), kv=1.2, E=200000, Fy=345)["Cv"]
        assert below == pytest.approx(above, rel=tolerance)


@pytest.mark.parametrize("data, code", [
    ({"section_name": "IPE 80"}, "CATALOG_DATA_INCONSISTENT"),
])
def test_uncovered_domains_are_incomplete(engine, data, code):
    result = engine.run(SteelCase(tau_b=1.0, material={"Fy": 345}, Vy_2=1, **data))
    assert result.status.value == "INCOMPLETE" and result.errors[0]["code"] == code


# Limits at Fy = 345, kv = 5: 1.10*sqrt(kv*E/Fy) = 59.22, 1.37*sqrt(kv*E/Fy) = 73.76; d/t along the shear.
@pytest.mark.parametrize("H, B, shear, equation", [
    (590, 10, "Vy_2", "G2-9"), (600, 10, "Vy_2", "G2-10"), (740, 10, "Vy_2", "G2-11"),
    (10, 590, "Vx_3", "G2-9"), (10, 600, "Vx_3", "G2-10"), (10, 740, "Vx_3", "G2-11"),
    (740, 10, "Vx_3", "G2-9"), (10, 740, "Vy_2", "G2-9"),
])
def test_rectangular_bar_uses_cv2_with_the_ratio_along_the_shear(engine, H, B, shear, equation):
    custom = {"type": "SOLID_RECTANGULAR", "H": H, "B": B}
    check = engine.run(SteelCase(tau_b=1.0, section_name="BAR", material={"Fy": 345}, custom_section=custom, **{shear: 1})).checks[0]
    assert check.status.value == "PASS" and check.result["modes"]["V"]["Cv_equation"] == equation
    assert check.result["provisions"] == ["G1", "G4"] and check.result["classification"]["elements"][0]["kv"] == 5.0


def test_stocky_bar_uses_its_whole_gross_area(engine):
    case = SteelCase(tau_b=1.0, section_name="BAR", material={"Fy": 345}, Vy_2=1,
                     custom_section={"type": "SOLID_RECTANGULAR", "H": 100, "B": 20})
    assert engine.run(case).checks[0].result["Vn_kN"] == pytest.approx(414.0)   # 0.6*345*2000/1000, by hand
    assert "G4-1" in calculation_report(case, engine.run(case))


def test_round_bar_report_states_the_user_decision(engine):
    case = SteelCase(tau_b=1.0, section_name="ROUND", material={"Fy": 250}, Vy_2=1,
                     custom_section={"type": "SOLID_CIRCULAR", "diameter": 50})
    check = engine.run(case).checks[0]
    assert check.result["modes"]["V"]["Cv2"] == 1.0 and check.result["provisions"] == ["G1", "G4"]
    assert check.result["Vn_kN"] == pytest.approx(147.262156)                   # 0.6*250*(pi*50^2/4)/2/1000, by hand
    assert "decisión DG-4" in calculation_report(case, engine.run(case))


def test_shear_alone_or_with_flexure_needs_no_interaction(engine):
    result = engine.run(SteelCase(tau_b=1.0, section_name="W14X90", material={"Fy": 345}, Mx_3=200, Vy_2=300,
                                  lengths={"Lx_3": 3000, "Ly_2": 3000, "Lz_1": 3000}, flexure={"tension_flange_holes": False}))
    assert [c.id for c in result.checks] == ["flexure_x_3", "shear_y_2"] and result.status.value == "PASS"


def test_shear_report(engine):
    case = shear_case(REFERENCE["W-G2.1a"]["spec"])
    text = calculation_report(case, engine.run(case))
    assert "Cortante a lo largo de y, eje 2 (Vy_2) (Capítulo G)" in text and "G2-2" in text
    assert "φv·Vn = 1.00 · Vn" in text



def stiffened(panel="interior", a=1500, end=True, **extra):
    stiff = {"a": a, "b": 120, "t": 12, "arrangement": "pair", "material": {"Fy": 345, "name": "ASTM A572 Gr 50"}}
    if end:
        stiff["end"] = {"b": 150, "t": 20, "arrangement": "pair", "e": 100}
    data = dict(section_name="PL", material={"Fy": 345}, Vy_2=1,
                custom_section={"type": "I_BUILT_UP", "d": 1200, "tw": 8, "flange_plus2": {"b": 400, "t": 20},
                                "flange_minus2": {"b": 400, "t": 20}}, stiffeners=stiff, shear={"panel": panel} if panel else None)
    return SteelCase(tau_b=1.0, **{**data, **extra})


@pytest.mark.parametrize("case, field", [
    (stiffened(panel=None), "shear.panel"),                     # a/h <= 3: the panel decides G2.2 or G2.3
    (stiffened(panel="end", end=False), "stiffeners.end"),     # G2.3 needs the end stiffener
])
def test_stiffened_webs_need_the_panel_data(engine, case, field):
    check = engine.run(case).check("shear_y_2")
    assert check.status.value == "INCOMPLETE" and check.errors[0]["details"]["fields"] == [field]


def test_end_panel_of_unequal_flanges_is_by_analysis(engine):
    case = stiffened(panel="end", custom_section={"type": "I_BUILT_UP", "d": 1200, "tw": 8, "flange_plus2": {"b": 400, "t": 20},
                                                  "flange_minus2": {"b": 300, "t": 20}})
    check = engine.run(case).check("shear_y_2")
    assert check.status.value == "INCOMPLETE" and "G2.3(b)" in check.errors[0]["message"]


def test_the_larger_of_g2_1_and_the_tension_field_governs(engine):
    mode = engine.run(stiffened()).check("shear_y_2").result["modes"]["V"]
    assert mode["Vn"] == max(mode["Vn_G2_1_N"], mode["Vn_tension_field_N"]) and mode["equation"] == "G2-7"


def test_a_failed_stiffener_limit_fails_the_member(engine):
    case = stiffened(stiffeners={"a": 1500, "b": 60, "t": 4, "arrangement": "single", "material": {"Fy": 345}})
    check = engine.run(case).check("shear_y_2")
    failed = {r["id"] for r in check.result["requirements"] if not r["satisfied"]}
    assert failed == {"G2-16", "G2-17"} and check.status.value == "FAIL"


def test_end_panel_limits_the_tension_flange_stress(engine):
    check = engine.run(stiffened(panel="end", Mx_3=3000, flexure={"tension_flange_holes": False},
                                 lengths={"Lx_3": 1000, "Ly_2": 1000, "Lz_1": 1000})).check("shear_y_2")
    limit = next(r for r in check.result["requirements"] if r["id"] == "G2.3")
    assert not limit["satisfied"] and limit["limit"] == pytest.approx(0.35 * 345) and check.status.value == "FAIL"


def test_tension_field_in_fire_uses_fy_at_temperature(engine):
    ambient = engine.run(stiffened()).check("shear_y_2").result["modes"]["V"]["Vn"]
    hot = engine.run(stiffened(condition="fire", fire={"steel_temperature": 500})).check("shear_y_2").result
    assert hot["modes"]["V"]["Vn"] == pytest.approx(ambient * hot["fire"]["ky"], rel=1e-12)
    assert any("DA4-11" in n for n in hot["notes"])


def test_stiffener_material_comes_from_the_catalog():
    from steel_design.execution import prepare_cases
    payload = {"section_name": "W14X90", "material": "ASTM A36", "Vy_2": 10,
               "stiffeners": {"a": 600, "b": 100, "t": 10, "arrangement": "pair", "material": "ASTM A572 Gr 50"}}
    case = prepare_cases(payload)[0][1]
    assert case.stiffeners.material.Fy == 345 and case.stiffeners.material.name == "ASTM A572 Gr 50"
