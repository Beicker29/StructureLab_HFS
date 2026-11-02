"""Chapter I: filled, encased and composite-beam members vs independent hand calculations, selection and blocks.

Expected values: tests/fixtures/chapter_i/reference.json from tests/oracles/chapter_i.py
(Decimal, written from a360-22w.pdf I1-I5, I8.2 and Commentary Fig. C-I3.8; no product import).
"""
import json

import pytest

from steel_design.codes.aisc_360_22 import composite as eq
from steel_design.domain.compression import compression_strength
from steel_design.models import SteelCase
from steel_design.execution import execute_payload, overall_status

from conftest import ROOT, calculation_report

REFERENCE = json.loads((ROOT / "tests/fixtures/chapter_i/reference.json").read_text(encoding="utf-8"))["cases"]
REFERENCE_F = json.loads((ROOT / "tests/fixtures/chapter_f/reference.json").read_text(encoding="utf-8"))["cases"]
TIES = {"db": 10, "spacing": 300}
LENGTHS = {"Lx": 2000, "Ly": 2000, "Lz": 2000}


def concrete(spec):
    return {"fc": spec["fc"], "wc": spec.get("wc", 2320), "lightweight": False}


def anchor_case(spec, member=None, **overrides):
    """A stud or channel of I8.3 in a filled member, with the limits of I8.3 met unless overridden."""
    anchor = {"type": spec["type_"], "Qrv": spec.get("Qrv", 0), "Qrt": spec.get("Qrt", 0), "spacing": 500}
    if spec["type_"] == "stud":
        anchor.update(d=spec["d"], Fu=spec["Fu"], height=160, head_diameter=32, breakout_in_shear=False, base_thickness=10)
    else:
        anchor.update(la=spec["la"], tf=spec["tf"], tw=spec["tw"])
    anchor.update(overrides)
    return SteelCase(tau_b=1.0, section_name="PTE100X50X3MM", material={"Fy": 345},
                     composite={"kind": "filled", "concrete": {"fc": 35, "wc": 2320, "lightweight": member == "lightweight"},
                                "anchor": anchor})


DETAILING = {"longitudinal_spacing": 300, "lateral_cover": 50, "free_edge": True, "free_edge_distance": 300, "distribution": "uniform"}
WALL = {"length": 3000, "tsc": 300, "t": 10, "tf": 20, "b": 200, "st": 200, "dtie": 25}
GUIDE_KINDS = {"appendix_2_biaxial", "service_encased", "service_box", "diagram_rect", "diagram_round", "diagram_encased", "second_order", "tension_control", "box_compression", "box_flexure",
               "box_shear", "biaxial", "service_filled", "service_round", "wall_slender", "wall_stiffnesses", "c_wall_case",
               "coupling_flexure", "coupling_shear", "wall_fire_oracle"}


def wall_member(fc=35, wall=None, **demands):
    return SteelCase(tau_b=1.0, section_name="MURO", material={"Fy": 345}, **demands,
                     composite={"kind": "wall", "pour_height": 3000, "concrete": {"fc": fc, "wc": 2320, "lightweight": False},
                                "wall": {**WALL, **(wall or {})}})


def wall_case(spec):
    kind = spec["kind"]
    if kind == "wall_compression":
        lengths = {"Lx": spec["height"], "Ly": spec["height"], "Lz": spec["height"]}
        return wall_member(Pu=1, lengths=lengths), "axial", "available_kN", "phiPn_kN"
    if kind == "wall_tension":
        return wall_member(Pu=-1), "axial", "available_kN", "phiPn_kN"
    if kind == "wall_moment":
        return wall_member(Mux=1), "flexure_x", "Mn_kNm", "Mn_kNm"
    if kind == "wall_shear":
        return wall_member(Vux=1), "shear_x", "available_kN", "phiVn_kN"
    return (wall_member(Pu=spec["Pu"], Mux=spec["Mu"], lengths={"Lx": 6000, "Ly": 6000, "Lz": 6000}),
            "interaction", "ratio", "ratio")


NEW_FILLED = {"round_with_bars_compression", "round_with_bars_flexure", "rect_with_bars_flexure", "appendix_2_compression",
              "appendix_2_flexure", "appendix_2_interaction"}


def filled_extension_case(spec, data):
    """Filled members with internal bars, and rectangular filled members under Appendix 2."""
    kind = spec["kind"]
    composite = {"kind": "filled", "concrete": concrete(spec)}
    if "bars" in spec:
        composite["filled"] = {"Fysr": spec["Fysr"], "transverse": TIES,
                               "bars": [{"area": a, "db": db, "x": x, "y": y} for a, db, x, y in spec["bars"]]}
    data = {**data, "composite": composite}
    if "L" in spec:
        data["lengths"] = {"Lx": spec["L"], "Ly": spec["L"], "Lz": spec["L"]}
    if kind.endswith("compression"):
        return SteelCase(tau_b=1.0, **data, Pu=1), "axial", "Pn_kN", "Pn_kN"
    if kind.endswith("flexure"):
        return SteelCase(tau_b=1.0, **data, Mux=1), "flexure_x", "Mn_kNm", "Mn_kNm"
    return SteelCase(tau_b=1.0, **data, Pu=spec["Pu"], Mux=spec["Mu"]), "interaction", "ratio", "ratio"


def build(spec):
    """(case, check id, field of the result, expected key) from one oracle spec."""
    kind = spec["kind"]
    if kind == "anchor":
        return anchor_case(spec), "anchor", "ratio", "ratio"
    if kind.startswith("wall"):
        return wall_case(spec)
    fy = spec["fy"]
    data = {"section_name": spec["name"], "material": {"Fy": fy}}
    if kind in NEW_FILLED:
        return filled_extension_case(spec, data)
    lengths = {"Lx": spec.get("L", 1), "Ly": spec.get("L", 1), "Lz": spec.get("L", 1)}
    if "bars" in spec:
        bars = [{"area": a, "db": float(db), "x": x, "y": y} for a, db, x, y in spec["bars"]]
        encased_data = {"H": spec.get("H", 610), "B": spec.get("B", 610), "Fysr": spec["Fysr"], "bars": bars,
                        "transverse": TIES, "flexure_method": spec.get("method", "composite"), "anchors_provided": True}
        data["composite"] = {"kind": "encased", "concrete": concrete({"fc": spec.get("fc", 35)}), "encased": encased_data}
    elif kind != "beam_flexure":
        data["composite"] = {"kind": "filled", "concrete": concrete(spec)}
    if kind in {"filled_compression", "encased_compression"}:
        return SteelCase(tau_b=1.0, **data, Pu=1, lengths=lengths), "axial", "Pn_kN", "Pn_kN"
    if kind == "encased_tension":
        return SteelCase(tau_b=1.0, **data, Pu=-1), "axial", "available_kN", "phiPn_kN"
    if kind in {"filled_rect_flexure", "filled_round_flexure", "encased_flexure"}:
        moment = "Muy" if spec.get("axis") == "y" else "Mux"
        return SteelCase(tau_b=1.0, **data, **{moment: 1}), "flexure_y" if moment == "Muy" else "flexure_x", "Mn_kNm", "Mn_kNm"
    if kind == "filled_shear":
        return SteelCase(tau_b=1.0, **data, Vux=1), "shear_x", "available_kN", "phiVn_kN"
    if kind in {"i5", "method2"}:
        data["composite"]["interaction"] = "I5" if kind == "i5" else ("M2S" if spec["simplified"] else "M2")
        return SteelCase(tau_b=1.0, **data, Pu=spec["Pu"], Mux=spec["Mu"], lengths=lengths), "interaction", "ratio", "ratio"
    deck = None
    if spec["hr"]:
        deck = {"orientation": "perpendicular", "hr": spec["hr"], "wr": 150, "emid_ht_at_least_50": float(spec["Rp"]) == 0.75}
    beam_data = {"moment": "positive", "span": spec["span"], "left_beam_spacing": spec["spacing"],
                 "right_beam_spacing": spec["spacing"], "tc": spec["tc"], "deck": deck, "shored": True,
                 "studs": {"count": spec["n"], "d": spec["d"], "Fu": spec["Fu"], "length": 120, "over_web": True, "detailing": DETAILING}}
    data["composite"] = {"kind": "beam", "concrete": concrete(spec), "beam": beam_data}
    return SteelCase(tau_b=1.0, **data, Mux=1), "flexure_x", "available_kNm", "phiMn_kNm"


@pytest.mark.parametrize("case_id", sorted(c for c, v in REFERENCE.items() if v["spec"]["kind"] not in GUIDE_KINDS | {"beam_detailing", "filled_placement", "deflection_limit", "box_steel_flexure"}))
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
    return SteelCase(tau_b=1.0, section_name=name, material={"Fy": Fy}, **demands,
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


@pytest.mark.parametrize("fc, Fy", [(15, 345), (110, 345), (35, 700)])
def test_materials_outside_i13_and_appendix_2_are_blocked(engine, fc, Fy):
    result = engine.run(filled(Fy=Fy, fc=fc, Vux=1))
    assert result.status.value == "INCOMPLETE" and result.errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


@pytest.mark.parametrize("fc, Fy", [(80, 345), (35, 550)])
def test_materials_above_i13_use_appendix_2_in_rectangular_filled_members(engine, fc, Fy):
    check = engine.run(filled(Fy=Fy, fc=fc, Mux=1)).check("flexure_x")
    assert check.status.value == "PASS" and check.result["provisions"] == ["Apéndice 2"]


def test_declared_kind_must_match_the_family(engine):
    assert engine.run(filled("W14X90", Vux=1)).errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


def test_noncompact_round_filled_flexure_uses_the_guide_and_says_so(engine):
    check = engine.run(filled('PTER24"X12.70MM', Fy=500, Mux=1)).check("flexure_x")
    assert check.result["modes"]["Y"]["provision"] == "I3.4b(b)" and any("Design Guide 6" in n for n in check.result["notes"])


def test_rectangular_noncompact_filled_with_bars_is_blocked(engine):
    bars = {"Fysr": 420, "transverse": TIES, "bars": [{"area": 100, "db": 11, "x": 0, "y": 0}]}
    case = SteelCase(tau_b=1.0, section_name="PTE300X100X5MM", material={"Fy": 345}, Muy=1,
                     composite={"kind": "filled", "concrete": {"fc": 35, "wc": 2320, "lightweight": False}, "filled": bars})
    assert engine.run(case).check("flexure_y").errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


def test_bars_of_a_filled_member_meet_i22_and_i34(engine):
    bars = {"Fysr": 420, "transverse": TIES, "bars": [{"area": 10, "db": 4, "x": 0, "y": 40}]}
    case = SteelCase(tau_b=1.0, section_name="PTE200X200X7MM", material={"Fy": 345}, Mux=1,
                     composite={"kind": "filled", "concrete": {"fc": 35, "wc": 2320, "lightweight": False}, "filled": bars})
    errors = engine.run(case).check("flexure_x").errors
    assert {e.get("id") for e in errors} == {"rho_sr"}


def encased(method="steel", anchors=False, bars=None, ties=TIES, **demands):
    bars = bars or [{"area": 510, "db": 25.4, "x": x, "y": y} for x in (-241.3, 241.3) for y in (-241.3, 241.3)]
    return SteelCase(tau_b=1.0, section_name="W10X45", material={"Fy": 345}, **demands,
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
            "shored": True, "studs": {"count": 30, "d": 19, "Fu": 450, "length": 100, "over_web": True, "detailing": DETAILING}, **overrides}
    return SteelCase(tau_b=1.0, section_name="W14X30", material={"Fy": 345}, Mux=100, lengths={"Lx": 2000, "Ly": 2000, "Lz": 2000}, flexure={"tension_flange_holes": False},
                     composite={"kind": "beam", "concrete": {"fc": 28, "wc": 2320, "lightweight": False}, "beam": data})


def test_negative_flexure_is_the_steel_section_of_chapter_f(engine):
    check = engine.run(beam(moment="negative")).check("flexure_x")
    assert check.chapter == "F" and check.result["chapter"] == "F"


def test_positive_flexure_exceeds_the_steel_section(engine):
    assert engine.run(beam()).check("flexure_x").capacity > engine.run(beam(moment="negative")).check("flexure_x").capacity


def test_beam_without_connectors_is_incomplete(engine):
    check = engine.run(beam(studs=None)).check("flexure_x")
    assert check.status.value == "INCOMPLETE" and check.errors[0]["code"] == "COMPOSITE_DATA_INCOMPLETE"


def studs(**detailing):
    return {"count": 30, "d": 19, "Fu": 450, "length": 100, "over_web": True, "detailing": {**DETAILING, **detailing}}


@pytest.mark.parametrize("case_id", sorted(c for c, v in REFERENCE.items() if v["spec"]["kind"] == "beam_detailing"))
def test_anchor_detailing_limits_match_independent_calculation(engine, case_id):
    ref = REFERENCE[case_id]
    spec = ref["spec"]
    deck = None
    if spec["hr"]:
        deck = {"orientation": "perpendicular" if spec["perpendicular"] else "parallel", "hr": spec["hr"], "wr": 150,
                "emid_ht_at_least_50": False}
    case = SteelCase(tau_b=1.0, section_name="W14X30", material={"Fy": 345}, Mux=1, composite={
        "kind": "beam", "concrete": {"fc": 28, "wc": 1800 if spec["lightweight"] else 2320, "lightweight": spec["lightweight"]},
        "beam": {"moment": "positive", "span": 9000, "left_beam_spacing": 3000, "right_beam_spacing": 3000, "tc": spec["tc"], "deck": deck,
                 "shored": True, "studs": {**studs(), "length": spec["length"]}}})
    check = engine.run(case).check("flexure_x")
    assert check.status.value == "PASS", check.errors
    limits = {r["id"]: r["limit"] for r in check.result["requirements"]}
    assert float(limits["studs_s_min"].split()[1]) == pytest.approx(float(ref["s_min_mm"]))
    assert float(limits["studs_s_max"].split()[1]) == pytest.approx(float(ref["s_max_mm"]))
    assert float(limits["studs_free_edge"].split()[1]) == pytest.approx(float(ref["edge_min_mm"]))


@pytest.mark.parametrize("studs_data, field", [
    ({"count": 30, "d": 19, "Fu": 450, "length": 100, "over_web": True}, "composite.beam.studs.detailing"),
    (studs(lateral_cover=None), "composite.beam.studs.detailing.lateral_cover"),
    (studs(free_edge_distance=None), "composite.beam.studs.detailing.free_edge_distance"),
    ({**studs(), "per_rib": 2}, "composite.beam.studs.detailing.transverse_spacing"),
])
def test_beam_without_anchor_detailing_is_incomplete(engine, studs_data, field):
    result = engine.run(beam(studs=studs_data))
    check = result.check("flexure_x")
    assert check.status.value == "INCOMPLETE" and field in check.errors[0]["details"]["fields"]
    assert any(r["provision"] == "I8.2d" and r["status"] == "sin_dato" for r in result.requirements["geometry"])


@pytest.mark.parametrize("detailing, row", [
    ({"longitudinal_spacing": 100}, "studs_s_min"),
    ({"longitudinal_spacing": 901}, "studs_s_max"),
    ({"lateral_cover": 24}, "studs_cover"),
    ({"free_edge_distance": 199}, "studs_free_edge"),
    ({"transverse_spacing": 75}, "studs_s_transverse"),
])
def test_beam_fails_when_anchor_detailing_is_out_of_limits(engine, detailing, row):
    check = engine.run(beam(studs=studs(**detailing))).check("flexure_x")
    assert check.status.value == "FAIL" and any(e.get("id") == row for e in check.errors)


def test_negative_flexure_does_not_ask_for_anchor_detailing(engine):
    data = {"count": 30, "d": 19, "Fu": 450, "length": 100, "over_web": True}
    assert engine.run(beam(moment="negative", studs=data)).check("flexure_x").status.value != "INCOMPLETE"


def test_unshored_beam_needs_a_construction_case(engine):
    (_, _, result), = execute_payload({**beam(shored=False).model_dump(exclude_none=True), "material": "ASTM A572 Gr 50"}, engine)
    assert result.check("flexure_x").status.value == "INCOMPLETE" and result.status.value == "INCOMPLETE"
    assert "I3.1b" in result.check("flexure_x").errors[-1]["provision"]


def construction_bundle(Mux, shored=False):
    data = beam(shored=shored).model_dump(exclude_none=True)
    for field in ("Mux", "condition"):
        data.pop(field)
    return {**data, "material": "ASTM A572 Gr 50", "cases": [{"name": "Última", "Mux": 100}, {"name": "Vaciado", "condition": "construction", "Mux": Mux, "Vux": 10}]}


def test_unshored_beam_fails_when_the_steel_section_is_short(engine):
    executions = execute_payload(construction_bundle(5000), engine)
    assert overall_status([r for _, _, r in executions]).value == "FAIL"
    assert executions[1][2].check("flexure_x").status.value == "FAIL"


def test_construction_uses_the_steel_section_alone(engine):
    ref = REFERENCE_F["W-F2-inelastic-LTB"]             # W18X50, Lb = 4000 mm, independent calculation of Chapter F
    data = {"section_name": "W18X50", "material": "ASTM A572 Gr 50", "flexure": {"tension_flange_holes": False},
            "composite": beam().model_dump(exclude_none=True)["composite"],
            "lengths": {"ultimate": {"Lx": 9000, "Ly": 1000, "Lz": 1000}, "construction": {"Lx": 9000, "Ly": 4000, "Lz": 6000}},
            "tau_b": 1.0, "cases": [{"name": "Última", "Mux": 100}, {"name": "Vaciado", "condition": "construction", "Mux": 100, "Vux": 10}]}
    (_, _, ultimate), (_, _, construction) = execute_payload(data, engine)
    assert construction.check("flexure_x").chapter == "F" and construction.check("shear_x").chapter == "G"
    assert construction.check("flexure_x").capacity == pytest.approx(float(ref["phiMn_kNm"]), rel=1e-9)
    assert ultimate.check("flexure_x").chapter == "I"


def test_construction_case_admits_only_flexure_and_shear():
    with pytest.raises(ValueError):
        SteelCase(section_name="W18X50", material={"Fy": 345}, condition="construction", Pu=10, lengths={"Lx": 1, "Ly": 1, "Lz": 1})


def test_fire_condition_goes_with_the_fire_data():
    with pytest.raises(ValueError):
        SteelCase(section_name="W18X50", material={"Fy": 345}, condition="fire", Pu=10, lengths={"Lx": 1, "Ly": 1, "Lz": 1})


def test_lengths_are_taken_by_condition():
    nested = {"ultimate": {"Lx": 1000, "Ly": 1000, "Lz": 1000}, "construction": {"Lx": 2000, "Ly": 2000, "Lz": 2000}}
    data = {"section_name": "W18X50", "material": {"Fy": 345}, "Mux": 1, "lengths": nested}
    assert SteelCase(**data).lengths.Lx == 1000
    assert SteelCase(**data, condition="construction").lengths.Lx == 2000
    with pytest.raises(ValueError):
        SteelCase(**{**data, "lengths": {**nested, "Lx": 1}})


@pytest.mark.parametrize("case_id", sorted(c for c, v in REFERENCE.items() if v["spec"]["kind"] == "deflection_limit"))
def test_deflection_limits_match_independent_calculation(engine, case_id):
    ref = REFERENCE[case_id]
    spec = ref["spec"]
    basis = {"actual_span": spec["span"] + 100, "effective_span": spec["span"],
             "deflections": {"live_short": spec["value"], "dead_short": 0, "total_long": 0},
             "limit_divisors": {"live_short": spec["n"], "dead_short": 240, "total_long": 240}}
    case = SteelCase(section_name="W18X50", material={"Fy": 345}, Vux=1, serviceability=basis)
    row = engine.run(case).serviceability[0]
    assert row["limit_mm"] == pytest.approx(float(ref["limit_mm"]), rel=1e-9)
    assert row["satisfied"] is ref["satisfied"]


def test_exceeded_deflection_does_not_change_the_status(engine):
    basis = {"actual_span": 6000, "effective_span": 6000, "deflections": {"live_short": 500, "dead_short": 0, "total_long": 0},
             "limit_divisors": {"live_short": 360, "dead_short": 240, "total_long": 240}}
    result = engine.run(SteelCase(section_name="W18X50", material={"Fy": 345}, Vux=1, serviceability=basis))
    assert not result.serviceability[0]["satisfied"] and result.status.value == "PASS"


def test_beam_with_axial_force_is_blocked(engine):
    result = engine.run(SteelCase(**{**beam().model_dump(exclude_none=True), "Pu": 10, "lengths": LENGTHS}))
    assert result.check("axial").errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"
    assert result.status.value == "INCOMPLETE"


def test_method2_ratio_follows_the_segments():
    points = [(0.0, 100.0), (50.0, 120.0), (100.0, 100.0), (400.0, 0.0)]
    assert eq.method2_ratio(Pr=0.0, Mr=50.0, points=points) == pytest.approx(0.5)
    assert eq.method2_ratio(Pr=200.0, Mr=0.0, points=points) == pytest.approx(0.5)
    assert eq.method2_ratio(Pr=50.0, Mr=120.0, points=points) == pytest.approx(1.0)
    assert eq.method2_ratio(Pr=100.0, Mr=200.0, points=points) == pytest.approx(12 / 7)   # 2P = 140 - 0.4P on C-D


def test_method2_is_less_conservative_than_h1_on_a_stocky_member(engine):
    h1 = engine.run(encased(method="composite", anchors=True, Pu=5000, Mux=800, lengths=LENGTHS)).check("interaction").ratio
    case = encased(method="composite", anchors=True, Pu=5000, Mux=800, lengths=LENGTHS)
    data = case.model_dump(exclude_none=True)
    data["composite"]["interaction"] = "M2S"
    assert engine.run(SteelCase(**data)).check("interaction").ratio < h1


@pytest.mark.parametrize("build_case, code", [
    (lambda: filled("PTE120X60X2MM", interaction="M2", Pu=10, Mux=1, lengths=LENGTHS), "COMPOSITE_DOMAIN_BLOCKED"),
    (lambda: filled(interaction="M2", Pu=-10, Mux=1), "COMPOSITE_DOMAIN_BLOCKED"),
    (lambda: filled(interaction="M2", Mux=1, Muy=1), "COMPOSITE_DOMAIN_BLOCKED"),
    (lambda: filled(interaction="M2", Pu=10, Mux=1, Muy=1, lengths=LENGTHS), "COMPOSITE_DOMAIN_BLOCKED"),
])
def test_method2_domain(engine, build_case, code):
    assert engine.run(build_case()).check("interaction").errors[0]["code"] == code


def test_method2_simplified_admits_biaxial_flexure(engine):
    check = engine.run(filled(interaction="M2S", Mux=1, Muy=1)).check("interaction")
    flexures = engine.run(filled(Mux=1, Muy=1))
    expected = 1 / flexures.check("flexure_x").capacity + 1 / flexures.check("flexure_y").capacity
    assert check.ratio == pytest.approx(expected) and check.result["governing_equation"] == "C-I5-1a"


def test_method2_needs_the_composite_flexural_method(engine):
    data = encased(Pu=5000, Mux=800, lengths=LENGTHS).model_dump(exclude_none=True)
    data["composite"]["interaction"] = "M2"
    assert engine.run(SteelCase(**data)).check("interaction").errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


@pytest.mark.parametrize("wall, requirement", [
    ({"tsc": 600, "t": 2, "tf": 2}, "rho_s"), ({"t": 40, "dtie": 40}, "rho_s"), ({"b": 400}, "b/t"), ({"st": 400}, "st"),
    ({"t": 4, "st": 290, "dtie": 8, "b": 100}, "st/t"),
])
def test_wall_limits_of_i16_fail_the_check(engine, wall, requirement):
    check = engine.run(wall_member(wall=wall, Mux=1)).check("flexure_x")
    assert check.status.value == "FAIL" and any(e.get("id") == requirement for e in check.errors)


def test_wall_covers_only_the_plane_of_the_wall(engine):
    result = engine.run(wall_member(Muy=1, Vuy=1))
    assert {e["code"] for e in result.errors} == {"COMPOSITE_DOMAIN_BLOCKED"}


def test_wall_rejects_another_interaction_method():
    with pytest.raises(ValueError):
        SteelCase(tau_b=1.0, section_name="MURO", material={"Fy": 345}, Mux=1,
                  composite={"kind": "wall", "interaction": "M2", "concrete": {"fc": 35, "wc": 2320, "lightweight": False},
                             "wall": WALL})


def test_wall_axial_force_beyond_the_section_gives_a_failing_ratio(engine):
    result = engine.run(wall_member(Pu=-100000, Mux=1))
    assert result.check("interaction").ratio > 1 and result.status.value == "FAIL"


def test_wall_moment_reproduces_the_uniform_compression_limit():
    args = dict(Fy=345, fc=35, H=3000, t=10, tf=20, bi=280)
    squash = 345 * (2 * 10 * 3000 + 2 * 20 * 280) + 0.85 * 35 * 280 * 2960
    assert eq.wall_plastic_moment(**args, P=squash)["within_section"]
    assert not eq.wall_plastic_moment(**args, P=squash * 1.01)["within_section"]
    assert eq.wall_plastic_moment(**args, P=squash)["Mp"] == pytest.approx(0.0, abs=1e3)


STUD = dict(type_="stud", d=19, Fu=450)


@pytest.mark.parametrize("spec, overrides, requirement", [
    ({**STUD, "Qrv": 10}, {"height": 90}, "h/d"), ({**STUD, "Qrt": 10}, {"height": 140}, "h/d"),
    ({**STUD, "Qrv": 10}, {"spacing": 70}, "spacing_min"), ({**STUD, "Qrv": 10}, {"spacing": 700}, "spacing_max"),
    ({**STUD, "Qrv": 10}, {"base_thickness": 5}, "dsa_t"), ({**STUD, "Qrv": 10, "d": 22}, {"height": 160}, "dsa_max"),
])
def test_stud_limits_fail_the_check(engine, spec, overrides, requirement):
    check = engine.run(anchor_case(spec, **overrides)).check("anchor")
    assert check.status.value == "FAIL" and any(e.get("id") == requirement for e in check.errors)


@pytest.mark.parametrize("spec, overrides", [
    ({**STUD, "Qrv": 10}, {"breakout_in_shear": True}),
    ({**STUD, "Qrt": 10}, {"spacing": 200}),
    ({**STUD, "Qrt": 10}, {"edge_distance": 100}),
    ({**STUD, "Qrt": 10}, {"head_diameter": 25}),
])
def test_stud_conditions_that_send_to_aci_are_blocked(engine, spec, overrides):
    check = engine.run(anchor_case(spec, **overrides)).check("anchor")
    assert check.status.value == "INCOMPLETE" and check.errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


def test_anchor_reinforcement_limits_the_strength(engine):
    spec = {**STUD, "Qrv": 10}
    check = engine.run(anchor_case(spec, breakout_in_shear=True, reinforcement_shear=50)).check("anchor")
    assert check.result["modes"]["Q"]["Qcv_kN"] == pytest.approx(0.65 * 50)


def test_stud_in_lightweight_concrete_under_interaction_is_blocked(engine):
    check = engine.run(anchor_case({**STUD, "Qrv": 10, "Qrt": 10}, member="lightweight")).check("anchor")
    assert check.errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


def test_anchors_of_composite_beams_belong_to_i82(engine):
    data = beam().model_dump(exclude_none=True)
    data["composite"]["anchor"] = {"type": "channel", "Qrv": 1, "spacing": 300, "la": 100, "tf": 8, "tw": 6}
    assert engine.run(SteelCase(**data)).check("anchor").errors[0]["code"] == "COMPOSITE_DOMAIN_BLOCKED"


def test_each_side_of_the_slab_declares_one_limit():
    with pytest.raises(ValueError):
        beam(left_edge_distance=500)


@pytest.mark.parametrize("factory", [lambda: filled(Pu=10, Mux=1, Vux=1, lengths=LENGTHS),
                                     lambda: encased(Pu=10, Mux=1, lengths=LENGTHS), beam,
                                     lambda: wall_member(Pu=100, Mux=100, Vux=100, lengths=LENGTHS),
                                     lambda: anchor_case({**STUD, "Qrv": 10, "Qrt": 10})])
def test_reports_are_built_for_every_member_type(engine, factory):
    case = factory()
    text = calculation_report(case, engine.run(case))
    assert "Miembro compuesto" in text and "Capítulo I" in text


def placement_member(name="PTE200X100X6MM", **composite):
    return SteelCase(tau_b=1.0, section_name=name, material={"Fy": 345}, Vux=1, lengths=LENGTHS,
                     composite={"kind": "filled", "concrete": {"fc": 35, "wc": 2320, "lightweight": False}, **composite})


def placement_rows(result):
    return [r for r in result.requirements["geometry"] if "Guía 6, 4.3" in r["provision"] or "Guía 38, 2.2.1.2" in r["provision"]]


@pytest.mark.parametrize("case_id", sorted(c for c, v in REFERENCE.items() if v["spec"]["kind"] == "filled_placement"))
def test_concrete_placement_matches_independent_calculation(engine, case_id):
    ref = REFERENCE[case_id]
    spec = ref["spec"]
    case = SteelCase(tau_b=1.0, section_name=spec["name"], material={"Fy": 345}, Vux=1, lengths=LENGTHS, composite={
        "kind": "filled", "pour_height": spec["Lp"], "concrete": {"fc": 35, "wc": spec["wc"], "lightweight": False}})
    sigma, delta = placement_rows(engine.run(case))
    assert sigma["value"] == pytest.approx(float(ref["sigma_mpa"]), rel=1e-9)
    assert delta["value"] == pytest.approx(float(ref["delta_mm"]), rel=1e-9)
    assert f"p = {float(ref['p_mpa']):.4f} MPa" in sigma["description"]


def test_concrete_placement_needs_the_pour_height(engine):
    result = engine.run(placement_member())
    assert [r["status"] for r in placement_rows(result)] == ["sin_dato"]
    assert result.status.value == "INCOMPLETE"


def test_concrete_placement_is_a_recommendation_that_does_not_fail_the_member(engine):
    result = engine.run(placement_member(name="PTE120X60X2MM", pour_height=100000))
    rows = placement_rows(result)
    assert {r["status"] for r in rows} == {"no_cumple"} and not any(r["binding"] for r in rows)
    assert result.status.value != "FAIL"


def test_concrete_placement_deformation_needs_the_lengths(engine):
    data = placement_member(pour_height=3000).model_dump(exclude_none=True)
    del data["lengths"]
    assert [r["status"] for r in placement_rows(engine.run(SteelCase(**data)))] == ["cumple", "sin_dato"]


def test_concrete_placement_does_not_apply_to_round_tubes(engine):
    assert [r["status"] for r in placement_rows(engine.run(placement_member(name='PTER6"X6.00MM')))] == ["no_aplica"]


@pytest.mark.parametrize("height, wall, status", [
    (None, {}, "sin_dato"), (9144, {}, "cumple"), (9145, {}, "no_cumple"),
    (9144, {"b": 400, "st": 400, "allow_slender_plates": True}, "no_cumple"),
])
def test_wall_pour_height_of_design_guide_38(engine, height, wall, status):
    data = wall_member(wall=wall, Pu=1, lengths=LENGTHS).model_dump(exclude_none=True)
    data["composite"]["pour_height"] = height
    assert placement_rows(engine.run(SteelCase(**data)))[0]["status"] == status


def test_pour_height_is_only_for_filled_members_and_walls():
    data = beam().model_dump(exclude_none=True)
    data["composite"]["pour_height"] = 3000
    with pytest.raises(ValueError):
        SteelCase(**data)


@pytest.mark.parametrize("case_id", sorted(c for c, v in REFERENCE.items() if v["spec"]["kind"] == "box_steel_flexure"))
def test_box_in_construction_matches_independent_calculation(engine, case_id):
    ref = REFERENCE[case_id]
    spec = ref["spec"]
    lb = spec["Lb"]
    case = SteelCase(tau_b=1.0, section_name="CAJON", material={"Fy": spec["fy"]}, condition="construction", lengths={"Lx": lb, "Ly": lb, "Lz": lb},
                     **{"Mux" if spec["axis"] == "x" else "Muy": 1},
                     composite={"kind": "filled", "concrete": {"fc": 35, "wc": 2320, "lightweight": False},
                                "box": {"B": spec["B"], "H": spec["H"], "t": spec["t"]}})
    check = engine.run(case).check(f"flexure_{spec['axis']}")
    assert check.capacity == pytest.approx(float(ref["phiMn_kNm"]), rel=1e-9)
