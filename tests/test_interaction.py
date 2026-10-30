"""Chapter H: interaction of axial force and flexure (H1, H2, H4) vs independent hand calculations.

Expected values: tests/fixtures/chapter_h/reference.json from tests/oracles/chapter_h.py
(Decimal; components from the D, E and F oracles; no product import).
"""
import json
import math

import pytest

from steel_design.codes.aisc_360_22 import interaction as eq
from steel_design.models import SteelCase
from steel_design.reporting import calculation_report

from conftest import ROOT

_FIXTURE = json.loads((ROOT / "tests/fixtures/chapter_h/reference.json").read_text(encoding="utf-8"))
REFERENCE, REFERENCE_H2 = _FIXTURE["cases"], _FIXTURE["h2_cases"]


def combined_case(spec):
    data = {"section_name": spec["name"], "material": {"Fy": spec["fy"]}, "Pu": spec.get("Pu", 0),
            "Mux": spec.get("Mux", 0), "Muy": spec.get("Muy", 0)}
    flexure = {"Lb": spec["Lb"], "Cb": float(spec.get("Cb", 1))}
    if spec["family"] in {"W", "CHANNEL"}:
        flexure["tension_flange_holes"] = spec.get("holes") is not None
        if spec.get("holes") is not None:
            flexure["Afn"] = spec["holes"]
    if spec.get("cb_amplification"):
        flexure["tension_cb_amplification"] = True
    data["flexure"] = flexure
    if spec.get("L"):
        data["lengths"] = {"Lx": spec["L"], "Ly": spec["L"], "Lz": spec["L"]}
    if spec.get("tension"):
        t = spec["tension"]
        data["material"]["Fu"] = t["Fu"]
        data["tension"] = {"An": t["An"], "U": float(t["U"])}
    if spec.get("e6"):
        connectors, a = spec["e6"]
        data["double_angle_e6"] = {"connectors": connectors, "a": a, "end_connection_welded_or_pretensioned": True}
    if spec.get("web_legs"):
        data["angle_flexure"] = {"web_legs": spec["web_legs"]}
    return SteelCase(**data)


@pytest.mark.parametrize("case_id", sorted(REFERENCE))
def test_interaction_matches_independent_calculation(engine, case_id):
    ref = REFERENCE[case_id]
    result = engine.run(combined_case(ref["spec"]))
    check = result.check("interaction")
    assert check is not None and check.result is not None, result.errors
    h1 = check.result["modes"]["H1"]
    assert h1["ratio"] == pytest.approx(float(ref["H1"]), rel=1e-9)
    assert h1["equation"] == ref["H1_equation"]
    if "H4" in ref:
        assert check.result["modes"]["H4"]["ratio"] == pytest.approx(float(ref["H4"]), rel=1e-9)
    assert check.result["governing_mode"] == ref["governing"]
    assert check.ratio == pytest.approx(float(ref["ratio"]), rel=1e-9)
    assert check.status.value == ("FAIL" if float(ref["ratio"]) > 1 else "PASS")
    assert result.status == check.status or result.status.value == "FAIL"


def test_reference_bank_covers_equations():
    refs = REFERENCE.values()
    assert {r["H1_equation"] for r in refs} == {"H1-1a", "H1-1b"}
    assert any("H4" in r for r in refs) and any(r["Cb_factor"] for r in refs)
    assert any(float(r["ratio"]) > 1 for r in refs)                              # a failing combination


def test_cb_amplification_is_reported(engine):
    result = engine.run(combined_case(REFERENCE["W-H1.2-Cb-amplified"]["spec"]))
    flexure = result.check("flexure_x").result
    assert flexure["inputs"]["Cb"] == pytest.approx(1.14 * float(REFERENCE["W-H1.2-Cb-amplified"]["Cb_factor"]))
    assert any("H1.2" in n for n in flexure["notes"])


def test_cb_amplification_only_for_doubly_symmetric_members(engine):
    spec = {**REFERENCE["W-H1.2-Cb-amplified"]["spec"], "family": "CHANNEL", "name": "C15X50"}
    flexure = engine.run(combined_case(spec)).check("flexure_x").result
    assert flexure["inputs"]["Cb"] == 1.14 and any("no aplicado" in n for n in flexure["notes"])


def h2_case(spec):
    data = {"section_name": spec["name"], "material": {"Fy": spec["fy"]}, "Pu": spec.get("Pu", 0),
            "Mw": spec.get("Mw", 0), "Mz": spec.get("Mz", 0)}
    if spec.get("Lb"):
        data["flexure"] = {"Lb": spec["Lb"], "beta_w": float(spec.get("beta", 0))}
    data["angle_flexure"] = {"leg_in_compression": spec.get("leg", "long"), "toe": spec.get("toe")}
    if spec.get("L"):
        data["lengths"] = {"Lx": spec["L"], "Ly": spec["L"], "Lz": spec["L"]}
    if spec.get("tension"):
        t = spec["tension"]
        data["material"]["Fu"] = t["Fu"]
        data["tension"] = {"An": t["An"], "U": float(t["U"])}
    return SteelCase(**data)


@pytest.mark.parametrize("case_id", sorted(REFERENCE_H2))
def test_h2_matches_independent_calculation(engine, case_id):
    ref = REFERENCE_H2[case_id]
    result = engine.run(h2_case(ref["spec"]))
    check = result.check("interaction")
    assert check is not None and check.result is not None, result.errors
    assert not check.errors or float(ref["ratio"]) > 1, check.errors
    for point, expected in ref["ratios"].items():
        assert check.result["modes"][f"H2-{point}"]["ratio"] == pytest.approx(float(expected), rel=1e-9), point
    assert check.result["governing_mode"] == ref["governing"]
    assert check.ratio == pytest.approx(float(ref["ratio"]), rel=1e-9)
    assert check.status.value == ("FAIL" if float(ref["ratio"]) > 1 else "PASS")
    for key, check_id in (("Pc_kN", "axial"), ("Mcw_kNm", "flexure_w"), ("Mcz_kNm", "flexure_z")):
        if ref[key] is not None:
            assert result.check(check_id).capacity == pytest.approx(float(ref[key]), rel=1e-9), key


def test_h2_bank_covers_axial_senses_and_a_failure():
    refs = REFERENCE_H2.values()
    assert {(float(r["spec"].get("Pu", 0)) > 0) - (float(r["spec"].get("Pu", 0)) < 0) for r in refs} == {1, 0, -1}
    assert any(float(r["ratio"]) > 1 for r in refs)
    assert {r["governing"] for r in refs} >= {"H2-A", "H2-B", "H2-C"}


def test_stress_senses_reproduce_example_e14b(engine):
    # Example E.14B: Mw with the long-leg toe in compression, Mz with the toes in tension. Compression positive:
    # A (-, -), B (-, +), C (+, -).
    case = SteelCase(section_name="L8X4X1/2", material={"Fy": 345}, Mw=1, Mz=1, flexure={"Lb": 1500, "beta_w": 139.2},
                     angle_flexure={"leg_in_compression": "long", "toe": "tension"})
    modes = engine.run(case).check("interaction").result["modes"]
    signs = {p: (modes[f"H2-{p}"]["Mrw_Mcw"] > 0, modes[f"H2-{p}"]["Mrz_Mcz"] > 0) for p in "ABC"}
    assert signs == {"A": (False, False), "B": (False, True), "C": (True, False)}


def test_equal_leg_heel_has_no_major_axis_stress(engine):
    # Example F.11C: Mw causes no stress at point B of an equal-leg angle.
    case = SteelCase(section_name="L4X4X1/4", material={"Fy": 345}, Mw=1, Mz=1, flexure={"Lb": 1500},
                     angle_flexure={"toe": "compression"})
    assert engine.run(case).check("interaction").result["modes"]["H2-B"]["Mrw_Mcw"] == 0


def test_heel_lies_on_the_short_leg_side_of_w_in_every_unequal_angle(catalog):
    # Justifies the sign of Mw at B for the whole catalog (x, y, tan(alpha) of each angle).
    angles = [s for s in catalog if s.type == "SINGLE_ANGLE" and s.d != s.b]
    assert angles
    for s in angles:
        alpha, short = math.atan(s.tan_alpha), min(s.d, s.b)
        heel = s.x * math.sin(alpha) - s.y * math.cos(alpha)
        short_toe = -(short - s.x) * math.sin(alpha) - s.y * math.cos(alpha)
        assert heel < 0 and short_toe < 0, s.name


def test_h2_needs_principal_axis_moments(engine):
    result = engine.run(SteelCase(section_name="L4X4X1/4", material={"Fy": 345, "Fu": 450}, Pu=-10, Mux=1,
                                  tension={"An": 1000, "U": 0.8}, flexure={"lateral_torsional_restraint": "continuous"},
                                  angle_flexure={"toe": "tension"}))
    error = result.check("interaction").errors[0]
    assert error["code"] == "INTERACTION_DOMAIN_BLOCKED" and "DH-7" in error["message"]
    assert result.status.value == "INCOMPLETE"


def test_h2_keeps_a_missing_declaration_incomplete(engine):
    result = engine.run(SteelCase(section_name="L6X4X3/8", material={"Fy": 345}, Mw=1, Mz=1, flexure={"Lb": 1000},
                                  angle_flexure={"toe": "tension"}))                # no leg_in_compression, no beta_w
    assert result.check("interaction").errors[0]["code"] == "INTERACTION_COMPONENT_MISSING"
    assert result.status.value == "INCOMPLETE"


def test_h2_report_lists_every_point(engine):
    case = h2_case(REFERENCE_H2["L-H2-comp-long-toe"]["spec"])
    text = calculation_report(case, engine.run(case))
    assert "Ecuación H2-1 en los puntos del ángulo" in text and "segundo orden" in text
    for location in ("A (punta del ala corta)", "B (talón)", "C (punta del ala larga)"):
        assert location in text


def test_missing_component_keeps_the_interaction_incomplete(engine):
    result = engine.run(SteelCase(section_name="W14X90", material={"Fy": 345}, Pu=100, Mux=10,
                                  lengths={"Lx": 3000, "Ly": 3000, "Lz": 3000}, flexure={"Lb": 3000}))
    assert result.check("flexure_x").status.value == "INCOMPLETE"                 # F13.1 not declared
    assert result.check("interaction").errors[0]["code"] == "INTERACTION_COMPONENT_MISSING"


def test_second_order_assumption_is_stated(engine):
    result = engine.run(combined_case(REFERENCE["W-H1-1a"]["spec"]))
    assert any("segundo orden" in n for n in result.check("interaction").result["notes"])


def test_formulas_are_continuous_at_the_branch():
    a = eq.h1(Pr=0.2, Pc=1.0, Mrx=0.3, Mcx=1.0, Mry=0.0, Mcy=None)
    b = eq.h1(Pr=0.2 * (1 - 1e-12), Pc=1.0, Mrx=0.3, Mcx=1.0, Mry=0.0, Mcy=None)
    assert a["equation"] == "H1-1a" and b["equation"] == "H1-1b"
    assert a["ratio"] != pytest.approx(b["ratio"])                                  # H1-1 is not continuous


def test_interaction_report(engine):
    case = combined_case(REFERENCE["W-H4-holes"]["spec"])
    text = calculation_report(case, engine.run(case))
    assert "Interacción de fuerzas combinadas (Capítulo H)" in text and "H4-1" in text and "H1-1a" in text
