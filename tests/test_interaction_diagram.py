"""I5: which interaction applies to each composite member, and the diagrams of Manual Tables 6-2a, 6-2b, 6-3 and 6-4.

Expected values: tests/fixtures/chapter_i/reference.json from tests/oracles/chapter_i.py, and the points printed in
Design Examples I.6 and I.11 and Design Guide 6, Example 2.4.
"""
import json

import pytest
from conftest import ROOT, calculation_report
from test_design_examples import EXTRA, KIP, KIPFT, encased_member, filled_member
from test_design_guides import encased_w14x211

from steel_design.engine import SteelDesignEngine
from steel_design.models import SteelCase
from steel_design.reporting.document import report_blocks
from steel_design.reporting.pdf import pdf_bytes
from steel_design.sections.repository import SectionRepository

REFERENCE = json.loads((ROOT / "tests/fixtures/chapter_i/reference.json").read_text(encoding="utf-8"))["cases"]
DIAGRAMS = sorted(c for c, v in REFERENCE.items() if v["spec"]["kind"].startswith("diagram_"))
LENGTHS = {"Lx": 3000, "Ly": 3000, "Lz": 3000}
CONCRETE = {"fc": 35, "wc": 2320, "lightweight": False}
TIES = {"db": 10, "spacing": 300}


@pytest.fixture(scope="module")
def examples_engine(catalog):
    repository = SectionRepository()
    repository.load([*catalog, *EXTRA])
    return SteelDesignEngine(repository)


def points_of(diagram):
    return {p["point"]: p for p in diagram["points"]}


def oracle_case(spec):
    axis_moment = {"Muy" if spec.get("axis") == "y" else "Mux": 1.0}
    if spec["kind"] in {"diagram_rect", "diagram_round"}:
        return SteelCase(section_name=spec["name"], material={"Fy": spec["fy"]}, tau_b=0.8, Pu=1.0, lengths=LENGTHS, **axis_moment,
                         composite={"kind": "filled", "interaction": "H1", "concrete": CONCRETE})
    bars = [{"area": float(a), "db": float(db), "x": x, "y": y} for a, db, x, y in spec["bars"]]
    return SteelCase(section_name=spec["name"], material={"Fy": spec["fy"]}, tau_b=0.8, Pu=1.0, lengths=LENGTHS, **axis_moment,
                     composite={"kind": "encased", "concrete": CONCRETE,
                                "encased": {"H": spec["H"], "B": spec["B"], "Fysr": spec["Fysr"], "bars": bars, "transverse": TIES,
                                            "flexure_method": "composite", "anchors_provided": True}})


@pytest.mark.parametrize("case_id", DIAGRAMS)
def test_points_match_independent_calculation(engine, case_id):
    ref = REFERENCE[case_id]
    diagram = engine.run(oracle_case(ref["spec"])).interaction_diagrams[0]
    assert "reason" not in diagram, diagram
    points = points_of(diagram)
    assert set(points) == set(ref["points"])
    for name, (P, M) in ref["points"].items():
        assert points[name]["P_kN"] == pytest.approx(float(P), rel=1e-9, abs=1e-9), (case_id, name)
        assert points[name]["M_kNm"] == pytest.approx(float(M), rel=1e-9, abs=1e-9), (case_id, name)


def test_design_points_apply_lambda_and_phi(engine):
    diagram = engine.run(oracle_case(REFERENCE[DIAGRAMS[0]]["spec"])).interaction_diagrams[0]
    for p in diagram["points"]:
        assert p["design_P_kN"] == pytest.approx(0.75 * diagram["lambda"] * p["P_kN"]) and p["design_M_kNm"] == pytest.approx(0.9 * p["M_kNm"])
    assert 0 < diagram["lambda"] < 1


def test_table_6_3_reproduces_example_i6(examples_engine):
    # Design Examples I.6, Step 1: HSS10X6X3/8, f'c = 5 ksi, Fy = 50 ksi
    data = filled_member("HSS10X6X3/8", 5, L=14, Pu=129 * KIP, Mux=120 * KIPFT)
    points = points_of(examples_engine.run(SteelCase(tau_b=0.8, **data)).interaction_diagrams[0])
    for name, P, M in (("A", 729, 0), ("D", 105, 161), ("B", 0, 156), ("C", 209, 156)):
        assert points[name]["P_kN"] / KIP == pytest.approx(P, rel=0.015, abs=0.01), name
        assert points[name]["M_kNm"] / KIPFT == pytest.approx(M, rel=0.015, abs=0.01), name
    assert points["E"]["P_kN"] / KIP == pytest.approx(388, rel=0.015)


def test_table_6_2a_reproduces_example_i11(examples_engine):
    # Design Examples I.11, Step 1: W10X45 in 24 x 24 in, eight No. 8 bars
    data = encased_member(L=14, method="composite", Pu=1170 * KIP, Mux=670 * KIPFT)
    diagram = examples_engine.run(SteelCase(tau_b=0.8, **data)).interaction_diagrams[0]
    points = points_of(diagram)
    for name, P, M in (("A", 3410, 0), ("D", 1180, 1050), ("B", 0, 748), ("C", 2360, 748)):
        assert points[name]["P_kN"] / KIP == pytest.approx(P, rel=0.015, abs=0.01), name
        assert points[name]["M_kNm"] / KIPFT == pytest.approx(M, rel=0.015, abs=0.01), name
    assert diagram["lambda"] == pytest.approx(0.924, rel=0.015) and "6-2a" in diagram["table"]


def test_table_6_2b_reproduces_example_24(catalog):
    # Design Guide 6, Example 2.4, about y: MD = 62,800 kip-in, PC = 10,500 kips
    repository = SectionRepository()
    repository.load(catalog)
    data = encased_w14x211("eight", Pu=1000 * KIP, Muy=1000 * KIPFT)
    diagram = SteelDesignEngine(repository).run(SteelCase(tau_b=0.8, **data)).interaction_diagrams[0]
    points = points_of(diagram)
    assert "6-2b" in diagram["table"]
    assert points["D"]["M_kNm"] / (KIPFT / 12) == pytest.approx(62800, rel=0.015)
    assert points["C"]["P_kN"] / KIP == pytest.approx(10500, rel=0.015)


def filled(name="PTE200X200X7MM", **demands):
    return SteelCase(section_name=name, material={"Fy": 345}, tau_b=0.8, composite={"kind": "filled", "concrete": CONCRETE}, **demands)


def test_compact_filled_member_uses_h1_1_with_diagram(engine):
    result = engine.run(filled(Pu=100, Mux=10, lengths=LENGTHS))
    assert result.check("interaction").chapter == "H" and "6-3" in result.interaction_diagrams[0]["table"]


def test_noncompact_filled_member_uses_i5_in_compression_with_one_axis(engine):
    result = engine.run(filled("PTE120X60X2MM", Pu=10, Mux=1, lengths=LENGTHS))
    check = result.check("interaction")
    assert check.result["governing_mode"] == "I5" and "no compacta" in result.interaction_diagrams[0]["reason"]


@pytest.mark.parametrize("demands", [{"Pu": 10, "Mux": 1, "Muy": 1, "lengths": LENGTHS}, {"Pu": -10, "Mux": 1, "tension": {"An": 500, "U": 1.0}}])
def test_noncompact_filled_member_falls_back_to_h1_1_where_i5_does_not_cover(engine, demands):
    assert engine.run(filled("PTE120X60X2MM", **demands)).check("interaction").chapter == "H"


def test_bars_in_a_filled_member_remove_the_diagram_and_keep_h1_1(engine):
    bars = [{"area": 200, "db": 16, "x": x, "y": y} for x, y in ((55, 55), (55, -55), (-55, 55), (-55, -55))]
    case = SteelCase(section_name="PTE200X200X7MM", material={"Fy": 345}, tau_b=0.8, Pu=100, Mux=10, lengths=LENGTHS,
                     composite={"kind": "filled", "concrete": CONCRETE, "filled": {"Fysr": 420, "bars": bars, "transverse": TIES}})
    result = engine.run(case)
    assert result.check("interaction").chapter == "H" and "Asr ≠ 0" in result.interaction_diagrams[0]["reason"]
    assert "Asr ≠ 0" in calculation_report(case, result)


def test_encased_bars_out_of_the_table_arrangement_have_no_diagram(engine):
    bars = [{"area": 510, "db": 25.4, "x": x, "y": y} for x, y in ((240, 240), (240, 100), (240, -240), (-240, 240), (-240, 100), (-240, -240))]
    case = SteelCase(section_name="W10X45", material={"Fy": 345}, tau_b=0.8, Pu=100, Mux=10, lengths=LENGTHS,
                     composite={"kind": "encased", "concrete": CONCRETE,
                                "encased": {"H": 610, "B": 610, "Fysr": 420, "bars": bars, "transverse": TIES}})
    assert "disposición" in engine.run(case).interaction_diagrams[0]["reason"]


@pytest.mark.parametrize("method", ["M2", "M2S"])
def test_method_2_is_replaced_by_h1_1_in_filled_members_with_bars(engine, method):
    bars = [{"area": 200, "db": 16, "x": x, "y": y} for x, y in ((55, 55), (55, -55), (-55, 55), (-55, -55))]
    case = SteelCase(section_name="PTE200X200X7MM", material={"Fy": 345}, tau_b=0.8, Pu=100, Mux=10, lengths=LENGTHS,
                     composite={"kind": "filled", "interaction": method, "concrete": CONCRETE,
                                "filled": {"Fysr": 420, "bars": bars, "transverse": TIES}})
    result = engine.run(case)
    check = result.check("interaction")
    assert check.chapter == "H" and check.result["governing_mode"] == "H1"
    assert any(f"Se pidió {method}" in n for n in check.result["notes"])
    assert f"Se pidió {method}" in calculation_report(case, result)


def test_method_2_stays_optional_in_encased_members(engine):
    bars = [{"area": 510, "db": 25.4, "x": x, "y": y} for x, y in ((241.3, 241.3), (241.3, -241.3), (-241.3, 241.3), (-241.3, -241.3))]
    case = SteelCase(section_name="W10X45", material={"Fy": 345}, tau_b=0.8, Pu=500, Mux=100, lengths=LENGTHS,
                     composite={"kind": "encased", "interaction": "M2S", "concrete": CONCRETE,
                                "encased": {"H": 610, "B": 610, "Fysr": 420, "bars": bars, "transverse": TIES,
                                            "flexure_method": "composite", "anchors_provided": True}})
    assert engine.run(case).check("interaction").chapter == "I"


@pytest.mark.parametrize("method, chapter", [("M2S", "I"), ("H1", "H")])
def test_method_2_stays_optional(engine, method, chapter):
    case = SteelCase(section_name="PTE200X200X7MM", material={"Fy": 345}, tau_b=0.8, Pu=100, Mux=10, lengths=LENGTHS,
                     composite={"kind": "filled", "interaction": method, "concrete": CONCRETE})
    assert engine.run(case).check("interaction").chapter == chapter


def test_high_strength_uses_appendix_2_without_diagram(engine):
    case = SteelCase(section_name="PTE200X200X7MM", material={"Fy": 345}, tau_b=0.8, Pu=100, Mux=10, lengths=LENGTHS,
                     composite={"kind": "filled", "concrete": {**CONCRETE, "fc": 80}})
    result = engine.run(case)
    assert result.check("interaction").result["governing_mode"] == "A2" and "Apéndice 2" in result.interaction_diagrams[0]["reason"]


def test_single_demand_has_no_diagram(engine):
    assert engine.run(filled(Mux=1)).interaction_diagrams == []


def test_report_shows_the_table_and_the_figure_is_in_the_pdf(engine):
    case = filled(Pu=100, Mux=10, lengths=LENGTHS)
    result = engine.run(case)
    text = calculation_report(case, result)
    section = text[text.index("### 11.2"):text.index("### 11.3")]
    assert "Tabla 6-3" in section and "Punto" in section and "no decide el estado" in section
    blocks = report_blocks([(None, case, result)])
    assert any(b["kind"] == "chart" for b in blocks)
    assert pdf_bytes([blocks]).startswith(b"%PDF")


def high_strength(name="PTE200X100X6MM", interaction=None, **demands):
    return SteelCase(section_name=name, material={"Fy": 345}, tau_b=0.8, lengths=LENGTHS,
                     composite={"kind": "filled", "interaction": interaction, "concrete": {**CONCRETE, "fc": 80}}, **demands)


@pytest.mark.parametrize("case_id", ["a2-biaxial-low-axial", "a2-biaxial-high-axial"])
def test_high_strength_biaxial_matches_independent_calculation(engine, case_id):
    ref = REFERENCE[case_id]
    spec = ref["spec"]
    check = engine.run(high_strength(spec["name"], Pu=spec["Pu"], Mux=spec["Mux"], Muy=spec["Muy"])).check("interaction")
    assert check.status.value in {"PASS", "FAIL"} and check.chapter == "I"
    assert check.ratio == pytest.approx(float(ref["ratio"]), rel=1e-9)
    modes = check.result["modes"]
    by_axis = {modes[k]["coefficients_axis"]: modes[k]["ratio"] for k in ("A2", "A2-otro")}
    assert by_axis["x"] == pytest.approx(float(ref["ratio_x"]), rel=1e-9) and by_axis["y"] == pytest.approx(float(ref["ratio_y"]), rel=1e-9)
    assert modes["A2"]["ratio"] >= modes["A2-otro"]["ratio"]


def test_reference_bank_reaches_both_i5_equations():
    # A non-square section, so that the two sets of cp and cm differ
    assert all(REFERENCE[c]["ratio_x"] != REFERENCE[c]["ratio_y"] for c in ("a2-biaxial-low-axial", "a2-biaxial-high-axial"))


def test_high_strength_biaxial_is_reported_with_both_sets_of_coefficients(engine):
    case = high_strength(Pu=100, Mux=10, Muy=5)
    text = calculation_report(case, engine.run(case))
    for words in ("Revisión con cp y cm del otro eje", "extendida a dos ejes (DI-22)", "Mrx/Mcx + Mry/Mcy", "Extensión a dos ejes"):
        assert words in text


def test_high_strength_uniaxial_keeps_one_set_of_coefficients(engine):
    check = engine.run(high_strength(Pu=100, Mux=10)).check("interaction")
    assert set(check.result["modes"]) == {"A2"} and "dos ejes" not in check.result["modes"]["A2"]["provision"]


@pytest.mark.parametrize("requested", ["H1", "I5", "M2", "M2S"])
def test_requested_method_in_high_strength_is_replaced_and_reported(engine, requested):
    check = engine.run(high_strength(interaction=requested, Pu=100, Mux=10)).check("interaction")
    assert check.result["governing_mode"] == "A2" and any(f"Se pidió {requested}, pero rige el Apéndice 2" in n for n in check.result["notes"])


def test_high_strength_without_compression_uses_h1_1_and_says_so(engine):
    case = high_strength(Pu=-100, Mux=10, tension={"An": 3000, "U": 1.0})
    result = engine.run(case)
    check = result.check("interaction")
    assert check.chapter == "H" and any("Apéndice 2, 2.1.4, solo trata compresión" in n for n in check.result["notes"])
    assert "solo trata compresión" in calculation_report(case, result)


def test_walls_keep_their_own_interaction(engine):
    wall = {"length": 3000, "tsc": 400, "t": 12, "tf": 12, "b": 200, "st": 200, "dtie": 25}
    case = SteelCase(section_name="MURO", material={"Fy": 345}, tau_b=1.0, Pu=1000, Mux=100, lengths=LENGTHS,
                     composite={"kind": "wall", "concrete": CONCRETE, "wall": wall})
    assert engine.run(case).check("interaction").result["governing_mode"] == "I5c"
