"""Chapter D: catalog profiles vs independent hand calculations, governing limit state and blocks.

Expected values: tests/fixtures/chapter_d/reference.json from tests/oracles/chapter_d.py
(Decimal, written from a360-22w.pdf D2/D3, no product import).
"""
import json
import math

import pytest

from steel_design.models import SteelCase
from steel_design.reporting import calculation_report

from conftest import ROOT

REFERENCE = json.loads((ROOT / "tests/fixtures/chapter_d/reference.json").read_text(encoding="utf-8"))["cases"]
REL = 1e-12


def tension_case(name, *, Pu=-100, Fy=345, Fu=450, An=None, U=1.0, **extra):
    tension = {"An": An, "U": U} if An is not None else None
    return SteelCase(section_name=name, material={"Fy": Fy, "Fu": Fu}, Pu=Pu,
                     tension=tension, **extra)


@pytest.mark.parametrize("case_id", sorted(REFERENCE))
def test_catalog_profiles_match_independent_calculation(engine, case_id):
    ref = REFERENCE[case_id]
    result = engine.run(tension_case(ref["section"], Fy=ref["Fy"], Fu=ref["Fu"], An=float(ref["An"]),
                                     U=float(ref["U"])))
    t = result.tension
    assert result.chapter == "D" and result.family == ref["family"]
    for mode, expected in ref["modes"].items():
        assert t["modes"][mode]["Pn_kN"] == pytest.approx(float(expected["Pn_kN"]), rel=REL)
        assert t["modes"][mode]["area_mm2"] == pytest.approx(float(expected["area_mm2"]), rel=REL)
        assert t["modes"][mode]["available_kN"] == pytest.approx(float(expected["LRFD_kN"]), rel=REL)
    assert t["available_kN"] == pytest.approx(float(ref["LRFD_kN"]), rel=REL)
    assert t["governing_mode"] == ref["governing"]
    assert result.capacity_kN == t["available_kN"]


def test_reference_bank_covers_all_catalog_families_and_both_governing_modes():
    assert {c["family"] for c in REFERENCE.values()} == {
        "W", "CHANNEL", "RECTANGULAR_HSS", "CIRCULAR_HSS", "SINGLE_ANGLE", "DOUBLE_ANGLE"}
    assert {c["governing"] for c in REFERENCE.values()} == {"TY", "TR"}


def test_governing_is_lowest_available_not_lowest_nominal(engine):
    t = engine.run(tension_case("W14X90", An=15000, U=0.9)).tension
    assert t["modes"]["TR"]["Pn_kN"] > t["modes"]["TY"]["Pn_kN"] and t["governing_mode"] == "TR"


@pytest.mark.parametrize("kwargs, field", [
    ({"An": None}, "tension.An"),               # no net-section data
    ({"An": 15000, "Fu": None}, "material.Fu"),  # rupture needs Fu
])
def test_missing_tension_data_is_incomplete(engine, kwargs, field):
    result = engine.run(tension_case("W14X90", **kwargs))
    assert result.status.value == "INCOMPLETE" and result.capacity_kN is None
    assert field in result.errors[0]["details"]["fields"]


def test_net_area_above_gross_area_is_blocked(engine):
    result = engine.run(tension_case("W14X90", An=20000))
    assert result.status.value == "INCOMPLETE" and result.errors[0]["code"] == "TENSION_DOMAIN_BLOCKED"


def test_pass_fail_boundary(engine):
    capacity = engine.run(tension_case("L4X4X1/4", An=1100, U=0.6)).capacity_kN
    assert engine.run(tension_case("L4X4X1/4", An=1100, U=0.6, Pu=-capacity)).status.value == "PASS"
    beyond = -math.nextafter(capacity, math.inf)
    assert engine.run(tension_case("L4X4X1/4", An=1100, U=0.6, Pu=beyond)).status.value == "FAIL"


def test_tension_obligations_are_yielding_and_rupture(engine):
    result = engine.run(tension_case("C15X50", An=8600, U=0.85))
    assert [(o.id, o.satisfied_by) for o in result.obligations] == [("TY", "TY"), ("TR", "TR")]


def test_d1_user_note_uses_fabricated_length_and_least_radius(engine, sections):
    case = tension_case("L4X4X1/4").model_copy(update={"tension": {"An": 1100, "U": 0.6, "fabricated_length": 7000}})
    note = engine.run(case).tension["notes"][0]
    assert f"{7000 / sections['L4X4X1/4'].rz:.1f}" in note and "supera" in note   # L/rz = 351.8 > 300
    assert "no evaluada" in engine.run(tension_case("L4X4X1/4", An=1100, U=0.6)).tension["notes"][0]


def test_tension_does_not_require_lengths_nor_e(engine):
    case = tension_case("W14X90", An=15000, U=0.9)
    assert case.lengths is None and engine.run(case).status.value == "PASS"


def test_tension_report(engine):
    case = tension_case("W14X90", An=15000, U=0.9, Pu=-2000)
    text = calculation_report(case, engine.run(case))
    assert "tracción W14X90" in text and "Ae = An·U" in text and "## 4. Estados límite (D2)" in text
    assert "Obligaciones del Capítulo D" in text and "min(φt·Pn) = 4556.250 kN (TR)" in text
