"""Chapter I: filled, encased and composite-beam members vs independent hand calculations, selection and blocks.

Expected values: tests/fixtures/chapter_i/reference.json from tests/oracles/chapter_i.py
(Decimal, written from a360-22w.pdf I1-I5, I8.2 and Commentary Fig. C-I3.8; no product import).
"""
import json

import pytest

from steel_design.domain.compression import compression_strength
from steel_design.models import SteelCase
from steel_design.reporting import calculation_report

from conftest import ROOT

REFERENCE = json.loads((ROOT / "tests/fixtures/chapter_i/reference.json").read_text(encoding="utf-8"))["cases"]
TIES = {"db": 10, "spacing": 300}
LENGTHS = {"Lx": 2000, "Ly": 2000, "Lz": 2000}


def concrete(spec):
    return {"fc": spec["fc"], "wc": spec.get("wc", 2320), "lightweight": False}


def build(spec):
    """(case, check id, field of the result, expected key) from one oracle spec."""
    kind, fy = spec["kind"], spec["fy"]
    data = {"section_name": spec["name"], "material": {"Fy": fy}}
    lengths = {"Lx": spec.get("L", 1), "Ly": spec.get("L", 1), "Lz": spec.get("L", 1)}
    if "bars" in spec:
        bars = [{"area": a, "db": float(db), "x": x, "y": y} for a, db, x, y in spec["bars"]]
        encased_data = {"H": spec.get("H", 610), "B": spec.get("B", 610), "Fysr": spec["Fysr"], "bars": bars,
                        "transverse": TIES, "flexure_method": spec.get("method", "composite"), "anchors_provided": True}
        data["composite"] = {"kind": "encased", "concrete": concrete({"fc": spec.get("fc", 35)}), "encased": encased_data}
    elif kind != "beam_flexure":
        data["composite"] = {"kind": "filled", "concrete": concrete(spec)}
    if kind in {"filled_compression", "encased_compression"}:
        return SteelCase(**data, Pu=1, lengths=lengths), "axial", "Pn_kN", "Pn_kN"
    if kind == "encased_tension":
        return SteelCase(**data, Pu=-1), "axial", "available_kN", "phiPn_kN"
    if kind in {"filled_rect_flexure", "filled_round_flexure", "encased_flexure"}:
        moment = "Muy" if spec.get("axis") == "y" else "Mux"
        return SteelCase(**data, **{moment: 1}), "flexure_y" if moment == "Muy" else "flexure_x", "Mn_kNm", "Mn_kNm"
    if kind == "filled_shear":
        return SteelCase(**data, Vux=1), "shear_x", "available_kN", "phiVn_kN"
    if kind == "i5":
        data["composite"]["interaction"] = "I5"
        return SteelCase(**data, Pu=spec["Pu"], Mux=spec["Mu"], lengths=lengths), "interaction", "ratio", "ratio"
    deck = None
    if spec["hr"]:
        deck = {"orientation": "perpendicular", "hr": spec["hr"], "wr": 150, "emid_ht_at_least_50": float(spec["Rp"]) == 0.75}
    beam_data = {"moment": "positive", "span": spec["span"], "left_beam_spacing": spec["spacing"],
                 "right_beam_spacing": spec["spacing"], "tc": spec["tc"], "deck": deck, "shored": True,
                 "studs": {"count": spec["n"], "d": spec["d"], "Fu": spec["Fu"], "length": 120, "over_web": True}}
    data["composite"] = {"kind": "beam", "concrete": concrete(spec), "beam": beam_data}
    return SteelCase(**data, Mux=1), "flexure_x", "available_kNm", "phiMn_kNm"


@pytest.mark.parametrize("case_id", sorted(REFERENCE))
def test_profiles_match_independent_calculation(engine, case_id):
    ref = REFERENCE[case_id]
    case, check_id, field, expected = build(ref["spec"])
    check = engine.run(case).check(check_id)
    assert check.result is not None, check.errors
    assert check.result[field] == pytest.approx(float(ref[expected]), rel=1e-9), case_id


def test_reference_bank_covers_every_member_type_and_class():
    kinds = {c["spec"]["kind"] for c in REFERENCE.values()}
    assert {"filled_compression", "encased_compression", "encased_tension", "beam_flexure", "i5"} <= kinds
    assert {c["class"] for c in REFERENCE.values() if "class" in c} == {"compact", "noncompact", "slender"}


def filled(name="PTE100X50X3MM", Fy=345, fc=35, interaction="H1", **demands):
    return SteelCase(section_name=name, material={"Fy": Fy}, **demands,
                     composite={"kind": "filled", "interaction": interaction,
                                "concrete": {"fc": fc, "wc": 2320, "lightweight": False}})


def test_filled_combination_uses_h1_with_the_chapter_i_strengths(engine):
    result = engine.run(filled(Pu=100, Mux=5, lengths=LENGTHS))
    axial, flexure, interaction = result.check("axial"), result.check("flexure_x"), result.check("interaction")
    assert axial.chapter == "I" and flexure.chapter == "I" and interaction.chapter == "H"
    ratio = axial.demand / axial.capacity
    moment = flexure.demand / flexure.capacity
    assert interaction.ratio == pytest.approx(ratio + 8 / 9 * moment if ratio >= 0.2 else ratio / 2 + moment)


def test_i5_is_only_for_noncompact_or_slender_filled_sections(engine):
    result = engine.run(filled(interaction="I5", Pu=10, Mux=1, lengths=LENGTHS))
    assert result.check("interaction").errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


def test_i5_needs_flexure_about_one_axis(engine):
    result = engine.run(filled("PTE120X60X2MM", interaction="I5", Pu=10, Mux=1, Muy=1, lengths=LENGTHS))
    assert result.check("interaction").errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


@pytest.mark.parametrize("fc, Fy", [(15, 345), (80, 345), (35, 550)])
def test_materials_outside_i13_are_blocked(engine, fc, Fy):
    result = engine.run(filled(Fy=Fy, fc=fc, Vux=1))
    assert result.status.value == "INCOMPLETE" and result.errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


def test_declared_kind_must_match_the_family(engine):
    assert engine.run(filled("W14X90", Vux=1)).errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


def test_noncompact_round_filled_flexure_is_blocked(engine):
    result = engine.run(filled('PTER24"X12.70MM', Fy=500, Mux=1))
    assert result.check("flexure_x").errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


def encased(method="steel", anchors=False, bars=None, ties=TIES, **demands):
    bars = bars or [{"area": 510, "db": 25.4, "x": x, "y": y} for x in (-241.3, 241.3) for y in (-241.3, 241.3)]
    return SteelCase(section_name="W10X45", material={"Fy": 345}, **demands,
                     composite={"kind": "encased", "concrete": {"fc": 35, "wc": 2320, "lightweight": False},
                                "encased": {"H": 610, "B": 610, "Fysr": 420, "bars": bars, "transverse": ties,
                                            "flexure_method": method, "anchors_provided": anchors}})


def test_encased_flexure_default_is_the_steel_section(engine):
    assert engine.run(encased(Mux=1)).check("flexure_x").result["modes"]["Y"]["provision"] == "I3.3a(2)"


def test_encased_composite_flexure_needs_anchors(engine):
    check = engine.run(encased(method="composite", Mux=1)).check("flexure_x")
    assert check.status.value == "INCOMPLETE" and check.errors[0]["code"] == "COMPOSITE_DATA_INCOMPLETE"


def test_encased_composite_is_stronger_than_the_steel_section(engine):
    steel = engine.run(encased(Mux=1)).check("flexure_x").capacity
    assert engine.run(encased(method="composite", anchors=True, Mux=1)).check("flexure_x").capacity > steel


@pytest.mark.parametrize("kwargs", [
    {"ties": {"db": 10, "spacing": 350}},
    {"bars": [{"area": 100, "db": 11, "x": 241.3, "y": 241.3}]},
    {"bars": [{"area": 510, "db": 25.4, "x": 110, "y": 0}, {"area": 510, "db": 25.4, "x": 241.3, "y": 241.3},
              {"area": 510, "db": 25.4, "x": -241.3, "y": -241.3}]},
])
def test_encased_limitations_fail_the_check(engine, kwargs):
    check = engine.run(encased(Mux=1, **kwargs)).check("flexure_x")
    assert check.status.value == "FAIL" and any(e["code"] == "REQUIREMENT_NOT_MET" for e in check.errors)


def test_encased_shear_is_the_steel_section_of_chapter_g(engine):
    check = engine.run(encased(Vux=1)).check("shear_x")
    assert check.chapter == "G" and check.result["provisions"][0] == "G1"


def test_bare_steel_is_a_lower_bound_of_the_compressive_strength(engine, sections):
    name = "PTE100X50X3MM"
    case = filled(name, fc=21, Pu=1, lengths={"Lx": 100, "Ly": 100, "Lz": 100})
    check = engine.run(case).check("axial")
    bare = compression_strength(case, sections[name])["available_kN"]
    assert check.capacity == pytest.approx(max(0.75 * check.result["Pn_kN"], bare))


def beam(**overrides):
    data = {"moment": "positive", "span": 9000, "left_beam_spacing": 3000, "right_beam_spacing": 3000, "tc": 120,
            "shored": True, "studs": {"count": 30, "d": 19, "Fu": 450, "length": 100, "over_web": True}, **overrides}
    return SteelCase(section_name="W14X30", material={"Fy": 345}, Mux=100, flexure={"Lb": 2000, "tension_flange_holes": False},
                     composite={"kind": "beam", "concrete": {"fc": 28, "wc": 2320, "lightweight": False}, "beam": data})


def test_negative_flexure_is_the_steel_section_of_chapter_f(engine):
    check = engine.run(beam(moment="negative")).check("flexure_x")
    assert check.chapter == "F" and check.result["chapter"] == "F"


def test_positive_flexure_exceeds_the_steel_section(engine):
    assert engine.run(beam()).check("flexure_x").capacity > engine.run(beam(moment="negative")).check("flexure_x").capacity


def test_beam_without_connectors_is_incomplete(engine):
    check = engine.run(beam(studs=None)).check("flexure_x")
    assert check.status.value == "INCOMPLETE" and check.errors[0]["code"] == "COMPOSITE_DATA_INCOMPLETE"


def test_unshored_beam_needs_the_construction_moment(engine):
    assert engine.run(beam(shored=False)).check("flexure_x").status.value == "INCOMPLETE"


def test_unshored_beam_fails_when_the_steel_section_is_short(engine):
    check = engine.run(beam(shored=False, Mu_construction=5000)).check("flexure_x")
    assert check.status.value == "FAIL" and any(e.get("id") == "construction" for e in check.errors)


def test_beam_with_axial_force_is_blocked(engine):
    result = engine.run(SteelCase(**{**beam().model_dump(exclude_none=True), "Pu": 10, "lengths": LENGTHS}))
    assert result.check("axial").errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"
    assert result.status.value == "INCOMPLETE"


def test_each_side_of_the_slab_declares_one_limit():
    with pytest.raises(ValueError):
        beam(left_edge_distance=500)


@pytest.mark.parametrize("factory", [lambda: filled(Pu=10, Mux=1, Vux=1, lengths=LENGTHS),
                                     lambda: encased(Pu=10, Mux=1, lengths=LENGTHS), beam])
def test_reports_are_built_for_every_member_type(engine, factory):
    case = factory()
    text = calculation_report(case, engine.run(case))
    assert "Miembro compuesto" in text and "Capítulo I" in text
