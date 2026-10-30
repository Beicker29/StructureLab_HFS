"""Chapter F: catalog profiles vs independent hand calculations, selection, blocks, interaction.

Expected values: tests/fixtures/chapter_f/reference.json from tests/oracles/chapter_f.py
(Decimal, written from a360-22w.pdf F1-F13 and B4.1b, no product import).
"""
import json
import math

import pytest

from steel_design.codes.aisc_360_22 import flexure as eq
from steel_design.models import SteelCase
from steel_design.reporting import calculation_report

from conftest import ROOT

REFERENCE = json.loads((ROOT / "tests/fixtures/chapter_f/reference.json").read_text(encoding="utf-8"))["cases"]
REL = 1e-9


def flexure_case(spec, moment=1.0):
    kind, axis = spec["kind"], spec.get("axis", "x")
    if kind in {"2l", "lg", "lp"}:
        flexure = {k: v for k, v in (("Lb", spec.get("Lb")), ("Cb", float(spec["Cb"]) if spec.get("Cb") else None),
                                     ("lateral_torsional_restraint", spec.get("restraint")),
                                     ("beta_w", float(spec["beta"]) if spec.get("beta") else None)) if v is not None}
        angle = {k: v for k, v in (("web_legs", spec.get("web_legs")), ("toe", spec.get("toe")),
                                   ("leg_in_compression", spec.get("leg"))) if v}
        moment_key = {"x": "Mux", "y": "Muy", "w": "Mw", "z": "Mz"}[axis]
        return SteelCase(section_name=spec["name"], material={"Fy": spec["fy"]}, flexure=flexure,
                         angle_flexure=angle, **{moment_key: moment})
    flexure = {"tension_flange_holes": False}
    if spec.get("Lb"):
        flexure["Lb"] = spec["Lb"]
    if spec.get("Cb"):
        flexure["Cb"] = float(spec["Cb"])
    if spec.get("holes"):
        flexure.update(tension_flange_holes=True, Afn=spec["holes"])
    data = {"material": {"Fy": spec["fy"], **({"Fu": spec["Fu"]} if spec.get("Fu") else {})},
            "Mux" if axis == "x" else "Muy": moment, "flexure": flexure}
    if kind == "bar":
        data.update(section_name="BAR", custom_section={"type": "SOLID_RECTANGULAR", "H": spec["H"], "B": spec["B"]})
    elif kind == "round":
        data.update(section_name="ROUND", custom_section={"type": "SOLID_CIRCULAR", "diameter": spec["D_"]})
    else:
        data["section_name"] = spec["name"]
    return SteelCase(**data)


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
            ("2l", None), ("lg", None), ("lp", None)} <= families
    assert {c["governing"] for c in REFERENCE.values()} >= {"Y", "LTB", "FLB", "TFR", "LB", "LLB"}


def test_every_limit_state_is_reported_and_obligations_discharged(engine):
    result = engine.run(flexure_case(REFERENCE["W-F3-FLB"]["spec"]))
    check = result.checks[0]
    assert set(check.result["modes"]) == {"Y", "LTB", "FLB", "TFR"}
    assert all(o.satisfied_by for o in check.obligations) and check.status.value == "PASS"
    assert not check.result["modes"]["Y"]["applies"] and check.result["modes"]["Y"]["reason"]


@pytest.mark.parametrize("name, flexure, field", [
    ("W14X90", {"Lb": 3000}, "flexure.tension_flange_holes"),          # F13.1 must be declared
    ("W14X90", {"tension_flange_holes": False}, "flexure.Lb"),          # LTB needs Lb
    ("IPE 100", {"Lb": 3000, "tension_flange_holes": False}, None),      # catalog without Zx/Sx/J/Cw
])
def test_missing_flexure_data_is_incomplete(engine, name, flexure, field):
    check = engine.run(SteelCase(section_name=name, material={"Fy": 345}, Mux=10, flexure=flexure)).checks[0]
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
    result = engine.run(SteelCase(section_name=name, material={"Fy": 345},
                                  flexure={"Lb": 1000, "tension_flange_holes": False,
                                           "lateral_torsional_restraint": "none"}, **kwargs))
    assert result.status.value == "INCOMPLETE" and result.errors[0]["code"] == code


@pytest.mark.parametrize("name, kwargs, field", [
    ("2L4X4X1/4", {"Mux": 1}, "angle_flexure.web_legs"),
    ("L4X4X1/4", {"Mux": 1, "angle_flexure": {"toe": "tension"}}, "flexure.lateral_torsional_restraint"),
    ("L4X4X1/4", {"Mux": 1, "flexure": {"lateral_torsional_restraint": "none", "Lb": 1000}}, "angle_flexure.toe"),
    ("L6X4X3/8", {"Mw": 1, "flexure": {"Lb": 1000}, "angle_flexure": {"leg_in_compression": "long"}}, "flexure.beta_w"),
    ("L6X4X3/8", {"Mw": 1, "flexure": {"Lb": 1000, "beta_w": 80}}, "angle_flexure.leg_in_compression"),
])
def test_angle_data_must_be_explicit(engine, name, kwargs, field):
    kwargs.setdefault("flexure", {"Lb": 2000})
    check = engine.run(SteelCase(section_name=name, material={"Fy": 345}, **kwargs)).checks[0]
    assert check.status.value == "INCOMPLETE" and field in check.errors[0]["details"]["fields"]


def test_geometric_axis_f10_rejects_axial_compression(engine):
    result = engine.run(SteelCase(section_name="L4X4X1/4", material={"Fy": 345}, Pu=10, Mux=1,
                                  lengths={"Lx": 1000, "Ly": 1000, "Lz": 1000},
                                  single_angle_e5={"configuration": "a", "connected_leg": "long", "L": 1000,
                                                   "loaded_at_ends_through_same_leg": True,
                                                   "welded_or_two_bolts_min": True,
                                                   "no_intermediate_transverse_loads": True},
                                  flexure={"Lb": 1000, "lateral_torsional_restraint": "none"},
                                  angle_flexure={"toe": "compression"}))
    assert result.check("flexure_x").errors[0]["code"] == "FLEXURE_DOMAIN_BLOCKED"


def test_combination_with_two_demands_waits_for_chapter_h(engine):
    result = engine.run(SteelCase(section_name="W14X90", material={"Fy": 345}, Pu=500, Mux=200,
                                  lengths={"Lx": 3000, "Ly": 3000, "Lz": 3000},
                                  flexure={"Lb": 3000, "tension_flange_holes": False}))
    assert [c.status.value for c in result.checks] == ["PASS", "PASS"]
    assert result.status.value == "INCOMPLETE" and result.errors[-1]["code"] == "INTERACTION_PENDING"


def test_a_known_failure_is_not_hidden_by_pending_interaction(engine):
    result = engine.run(SteelCase(section_name="W14X90", material={"Fy": 345}, Pu=500, Mux=5000,
                                  lengths={"Lx": 3000, "Ly": 3000, "Lz": 3000},
                                  flexure={"Lb": 3000, "tension_flange_holes": False}))
    assert result.status.value == "FAIL"


def test_cb_default_is_reported(engine):
    check = engine.run(SteelCase(section_name="W18X50", material={"Fy": 345}, Mux=100,
                                 flexure={"Lb": 4000, "tension_flange_holes": False})).checks[0]
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
    assert "## 2. Flexión respecto de y (Capítulo F)" in text and "F7-3" in text and "be" in text
    assert "φb·Mn = 0.90 · Mn" in text and "Obligaciones del Capítulo F" in text
