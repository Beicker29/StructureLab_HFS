"""Chapter G: catalog profiles vs independent hand calculations, selection and blocks.

Expected values: tests/fixtures/chapter_g/reference.json from tests/oracles/chapter_g.py
(Decimal, written from a360-22w.pdf G1-G6, no product import).
"""
import json

import pytest

from steel_design.codes.aisc_360_22 import shear as eq
from steel_design.models import SteelCase
from steel_design.reporting import calculation_report

from conftest import ROOT

REFERENCE = json.loads((ROOT / "tests/fixtures/chapter_g/reference.json").read_text(encoding="utf-8"))["cases"]


def shear_case(spec, shear=1.0):
    data = {"section_name": spec["name"], "material": {"Fy": spec["fy"]},
            "Vuy" if spec.get("axis") == "y" else "Vux": shear}
    if spec.get("Lv"):
        data["shear"] = {"Lv": spec["Lv"]}
    return SteelCase(**data)


@pytest.mark.parametrize("case_id", sorted(REFERENCE))
def test_catalog_profiles_match_independent_calculation(engine, case_id):
    ref = REFERENCE[case_id]
    check = engine.run(shear_case(ref["spec"])).checks[0]
    assert check.chapter == "G" and check.status.value == "PASS", check.errors
    assert check.result["Vn_kN"] == pytest.approx(float(ref["Vn_kN"]), rel=1e-9)
    assert check.result["phi_v"] == float(ref["phi_v"])
    assert check.capacity == pytest.approx(float(ref["phiVn_kN"]), rel=1e-9)


def test_reference_bank_covers_every_section_and_coefficient():
    kinds = {c["spec"]["kind"] for c in REFERENCE.values()}
    assert kinds == {"i", "rhss", "chss", "angle"}
    assert {c["phi_v"] for c in REFERENCE.values()} == {"1.00", "0.90"}         # G2.1(a) and G1(a)


@pytest.mark.parametrize("name, field, expected", [
    ("W24X62", "Cv_equation", "G2-2"), ("W16X26", "Cv_equation", "G2-4"),
    ("PTE100X40X1.5MM", "Cv_equation", "G2-10"),
])
def test_coefficient_branches(engine, name, field, expected):
    fy = 450 if name == "W16X26" else 345
    check = engine.run(SteelCase(section_name=name, material={"Fy": fy}, Vux=1)).checks[0]
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
    ({"section_name": "BAR", "custom_section": {"type": "SOLID_RECTANGULAR", "H": 100, "B": 20}}, "SHEAR_DOMAIN_BLOCKED"),
    ({"section_name": "IPE 80"}, "CATALOG_DATA_INCONSISTENT"),
])
def test_uncovered_domains_are_incomplete(engine, data, code):
    result = engine.run(SteelCase(material={"Fy": 345}, Vux=1, **data))
    assert result.status.value == "INCOMPLETE" and result.errors[0]["code"] == code


def test_shear_alone_or_with_flexure_needs_no_interaction(engine):
    result = engine.run(SteelCase(section_name="W14X90", material={"Fy": 345}, Mux=200, Vux=300,
                                  flexure={"Lb": 3000, "tension_flange_holes": False}))
    assert [c.id for c in result.checks] == ["flexure_x", "shear_x"] and result.status.value == "PASS"


def test_shear_report(engine):
    case = shear_case(REFERENCE["W-G2.1a"]["spec"])
    text = calculation_report(case, engine.run(case))
    assert "Cortante paralelo a y (con Mux) (Capítulo G)" in text and "G2-2" in text
    assert "φv·Vn = 1.00 · Vn" in text
