"""Technical requirements of the member, and the stiffnesses for the direct analysis method (C2.3, I1.5).

Noncomposite stiffnesses: tests/fixtures/chapter_c/reference.json from tests/oracles/chapter_c.py. Composite ones: chapter_i oracle.
"""
import json

import pytest

from steel_design.models import SteelCase
from steel_design.reporting import calculation_report

from conftest import ROOT, steel_case

REFERENCE = json.loads((ROOT / "tests/fixtures/chapter_c/reference.json").read_text(encoding="utf-8"))["cases"]
CONCRETE = {"fc": 35, "wc": 2320, "lightweight": False}
LENGTHS = {"Lx": 3000, "Ly": 3000, "Lz": 3000}
WALL = {"length": 3000, "tsc": 400, "t": 12, "tf": 12, "b": 200, "st": 200, "dtie": 25}


def rows_of(result, group):
    return {r["symbol"]: r for r in result.stiffness[group]}


def requirement(result, group, words):
    return next(r for r in result.requirements[group] if words in r["description"])


def filled(name="PTE200X200X7MM", fc=35, fy=345, **demands):
    return SteelCase(section_name=name, material={"Fy": fy}, composite={"kind": "filled", "concrete": {**CONCRETE, "fc": fc}}, **demands)


def declared(**demands):
    """filled() with the tau_b of I1.5(d)."""
    return filled(**{"tau_b": 0.8, **demands})


@pytest.mark.parametrize("case_id", sorted(REFERENCE))
@pytest.mark.parametrize("demand", [{"Vux": 1}, {"Pu": 100, "lengths": LENGTHS}])
def test_noncomposite_stiffness_matches_independent_calculation(engine, case_id, demand):
    ref = REFERENCE[case_id]
    spec = ref["spec"]
    result = engine.run(SteelCase(section_name=spec["name"], material={"Fy": 345}, **demand))
    rows = rows_of(result, "direct_analysis")
    assert rows["τb"]["value"] == 1.0 and "C2.3(c)" in rows["τb"]["source"]
    assert result.status.value != "INCOMPLETE"                                 # tau_b is not a datum here
    for symbol, key in (("EA*", "EA_star"), ("EI*x", "EI_star_x"), ("EI*y", "EI_star_y"), ("GJ*", "GJ_star")):
        assert rows[symbol]["value"] == pytest.approx(float(ref[key]), rel=1e-9), (case_id, symbol)


def test_tau_b_does_not_depend_on_the_axial_force(engine):
    low = engine.run(SteelCase(section_name="W14X90", material={"Fy": 345}, Pu=100, lengths=LENGTHS))
    high = engine.run(SteelCase(section_name="W14X90", material={"Fy": 345}, Pu=4720, lengths=LENGTHS))
    assert rows_of(high, "direct_analysis")["EI*x"]["value"] == rows_of(low, "direct_analysis")["EI*x"]["value"]


@pytest.mark.parametrize("build", [lambda: filled(Pu=100, lengths=LENGTHS)])
def test_missing_tau_b_is_incomplete_and_keeps_the_strengths(engine, build):
    case = build()
    result = engine.run(case)
    rows = rows_of(result, "direct_analysis")
    assert result.status.value == "INCOMPLETE" and any(e["code"] == "TECHNICAL_REQUIREMENT_MISSING" for e in result.errors)
    assert rows["τb"]["status"] == "sin_dato" and rows["EI*x"]["status"] == "sin_dato" and rows["EA*"]["status"] == "calculada"
    assert result.checks[0].capacity is not None and "Indique tau_b" in calculation_report(case, result)


@pytest.mark.parametrize("value", [0, -0.5, 1.1])
def test_tau_b_must_be_between_zero_and_one(value):
    with pytest.raises(ValueError):
        filled(Vux=1, tau_b=value)


@pytest.mark.parametrize("value", [0.5, 0.8])
def test_noncomposite_members_only_accept_tau_b_of_one(value):
    with pytest.raises(ValueError, match="siempre 1.0"):
        SteelCase(section_name="W14X90", material={"Fy": 345}, Vux=1, tau_b=value)
    assert SteelCase(section_name="W14X90", material={"Fy": 345}, Vux=1, tau_b=1.0).tau_b == 1.0


def test_tau_b_and_c2_3_c_are_reported_in_the_direct_analysis_subchapter(engine):
    case = SteelCase(section_name="W14X90", material={"Fy": 345}, Vux=1)
    text = calculation_report(case, engine.run(case))
    section = text[text.index("### 2.4 Rigideces para método directo"):text.index("## 3. Solicitaciones")]
    assert "Parámetro de reducción de rigidez (τb)" in section and "fijo en 1.0 para miembros no compuestos" in section
    assert "C2.3(c): se permite τb = 1.0" in section and "0.001·Yi" in section


@pytest.mark.parametrize("build, value, provision", [
    (lambda tau: filled(Pu=100, lengths=LENGTHS, tau_b=tau), 0.8, "I1.5(d)"),
    (lambda tau: filled(Pu=-10, tension={"An": 5000, "U": 1.0}, tau_b=tau), 1.0, "I1.5(c), C2.3(c)"),
    (lambda tau: SteelCase(section_name="MURO", material={"Fy": 345}, Vux=1, tau_b=tau, composite={"kind": "wall", "concrete": CONCRETE, "wall": WALL}), 1.0, "I1.5(f)"),
])
def test_tau_b_check_reports_compliance_and_does_not_change_the_status(engine, build, value, provision):
    good, bad = engine.run(build(value)), engine.run(build(0.5))
    row = requirement(good, "geometry", "τb")
    assert row["status"] == "cumple" and row["provision"] == provision and row["limit"] == f"= {value:g}"
    other = requirement(bad, "geometry", "τb")
    assert other["status"] == "no_cumple" and other["value"] == 0.5 and bad.status == good.status


def test_noncomposite_tau_b_check_is_always_met(engine):
    row = requirement(engine.run(SteelCase(section_name="W14X90", material={"Fy": 345}, Vux=1)), "geometry", "τb")
    assert (row["value"], row["limit"], row["provision"], row["status"]) == (1.0, "= 1", "C2.3(c)", "cumple")


def test_entered_tau_b_is_applied_to_composite_members(engine):
    rows, effective = rows_of(engine.run(filled(Pu=100, lengths=LENGTHS, tau_b=0.5)), "direct_analysis"), rows_of(engine.run(filled(Pu=100, lengths=LENGTHS, tau_b=0.5)), "effective")
    assert rows["EI*x"]["value"] == pytest.approx(0.8 * 0.5 * effective["(EI)eff,x"]["value"])


def test_composite_in_compression_uses_0_64_with_the_tau_b_of_i1_5(engine):
    result = engine.run(filled(Pu=100, lengths=LENGTHS, tau_b=0.8))
    rows, effective = rows_of(result, "direct_analysis"), rows_of(result, "effective")
    assert rows["EI*x"]["value"] == pytest.approx(0.64 * effective["(EI)eff,x"]["value"])
    assert rows["EA*"]["value"] == pytest.approx(0.8 * effective["(EA)eff"]["value"])
    assert rows["GA*"]["value"] == pytest.approx(0.8 * effective["(GA)eff"]["value"])
    assert rows["GJ*"]["value"] == pytest.approx(0.8 * effective["GJ"]["value"])


def test_effective_shear_stiffness_is_gc_ac_except_in_walls(engine, sections):
    result = engine.run(filled(Pu=100, lengths=LENGTHS, tau_b=0.8))
    Ec = result.stiffness["Ec_mpa"]
    Ac = result.stiffness["geometry"]["Ac_mm2"]
    assert rows_of(result, "effective")["(GA)eff"]["value"] == pytest.approx(0.4 * Ec * Ac)


def test_round_filled_reports_each_component_alone(engine, sections):
    section = sections['PTER6"X6.00MM']
    case = SteelCase(section_name='PTER6"X6.00MM', material={"Fy": 345}, Pu=10, lengths=LENGTHS, tau_b=0.8, composite={"kind": "filled", "concrete": CONCRETE})
    elastic = rows_of(engine.run(case), "elastic")
    assert "GA" not in elastic and elastic["GAs"]["value"] == pytest.approx(77200 * section.area) and elastic["GAc"]["status"] == "calculada"


def test_composite_in_net_tension_uses_the_bare_steel_of_chapter_c(engine, sections):
    # I1.5(c), then C2.3
    rows = rows_of(engine.run(filled(Pu=-10, tension={"An": 5000, "U": 1.0}, tau_b=0.9)), "direct_analysis")
    section = sections["PTE200X200X7MM"]
    assert rows["τb"]["value"] == 0.9 and rows["EI*x"]["value"] == pytest.approx(0.8 * 0.9 * 200000 * section.ix)
    assert "I1.5(c)" in rows["EI*x"]["source"]


# --- requirements ------------------------------------------------------------------------------------

def test_image_limits_of_i1_3_are_reported_with_their_literals(engine):
    result = engine.run(declared(Pu=100, lengths=LENGTHS))
    concrete = requirement(result, "materials", "Resistencia del concreto de peso normal")
    steel = requirement(result, "materials", "Fluencia del acero estructural")
    assert (concrete["provision"], concrete["limit"], concrete["status"]) == ("I1.3(a)", "21 a 69 MPa", "cumple")
    assert (steel["provision"], steel["limit"], steel["status"]) == ("I1.3(b)", "≤ 525 MPa", "cumple")
    assert requirement(result, "materials", "barras")["status"] == "no_aplica"


@pytest.mark.parametrize("fc, status", [(21, "cumple"), (41, "cumple"), (42, "no_cumple"), (20, "no_cumple")])
def test_lightweight_concrete_limit(engine, fc, status):
    filled_case = SteelCase(tau_b=1.0, section_name="PTER6\"X6.00MM", material={"Fy": 345}, Pu=10, lengths=LENGTHS,
                            composite={"kind": "filled", "concrete": {"fc": fc, "wc": 1800, "lightweight": True}})
    assert requirement(engine.run(filled_case), "materials", "liviano")["status"] == status


def test_materials_above_i1_3_go_to_appendix_2_in_rectangular_filled_members(engine):
    result = engine.run(declared(fc=80, Pu=100, lengths=LENGTHS))
    assert requirement(result, "materials", "Límites de materiales de I1.3")["status"] == "no_aplica"
    assert requirement(result, "materials", "Apéndice 2")["provision"] == "Apéndice 2, 2.1.1(b)"


def test_materials_out_of_every_limit_are_not_met_and_never_pass(engine):
    result = engine.run(declared(fc=15, Pu=100, lengths=LENGTHS))
    assert requirement(result, "materials", "Resistencia del concreto")["status"] == "no_cumple"
    assert result.status.value != "PASS"


def test_recommendations_do_not_decide_the_status(engine):
    result = engine.run(steel_case("W14X90", Pu=1, L=30000))
    row = requirement(result, "geometry", "Esbeltez efectiva")
    assert row["status"] == "no_cumple" and row["binding"] is False and row["provision"] == "Nota de E2"
    assert result.status.value == "PASS"


def test_unmet_binding_requirement_is_never_a_pass(engine):
    wall = {"length": 3000, "tsc": 400, "t": 1.0, "tf": 1.0, "b": 200, "st": 200, "dtie": 25}
    result = engine.run(SteelCase(tau_b=1.0, section_name="MURO", material={"Fy": 345}, Vux=1,
                                  composite={"kind": "wall", "concrete": CONCRETE, "wall": wall}))
    assert requirement(result, "geometry", "1 % y 10 %")["status"] == "no_cumple"
    assert result.status.value == "FAIL" and any(e["code"] == "TECHNICAL_REQUIREMENT_NOT_MET" for e in result.errors)


def test_composite_tension_does_not_ask_for_fu(engine):
    # I2.2c: Pn = Fy*As + Fysr*Asr
    result = engine.run(declared(Pu=-10, tension={"An": 5000, "U": 1.0}))
    assert not [r for r in result.requirements["materials"] if "Fu" in r["description"]]
    assert result.status.value == "PASS"


def test_section_ratio_of_filled_members(engine):
    result = engine.run(declared(Pu=100, lengths=LENGTHS))
    row = requirement(result, "geometry", "Relación ancho-espesor de la pared")
    assert row["provision"] == "I1.4, Tabla I1.1a" and row["status"] == "cumple"


def test_shear_only_does_not_apply_the_requirements_of_compression_and_flexure(engine):
    assert requirement(engine.run(declared(Vux=1)), "geometry", "Cuantías")["status"] == "no_aplica"


def test_tension_net_area_requirement(engine):
    result = engine.run(SteelCase(tau_b=1.0, section_name="W14X90", material={"Fy": 345, "Fu": 450}, Pu=-10, tension={"An": 15000, "U": 0.9}))
    assert requirement(result, "geometry", "Área neta")["status"] == "cumple"
    assert requirement(result, "materials", "Resistencia a tracción")["status"] == "cumple"


def test_chapters_of_the_report(engine):
    case = declared(Pu=100, lengths=LENGTHS)
    text = calculation_report(case, engine.run(case))
    for heading in ("### 2.4 Rigideces para método directo", "## 4. Revisión de requerimientos técnicos",
                    "### 4.1 Propiedades mecánicas de los materiales", "### 4.2 Propiedades geométricas",
                    "## 5. Revisión de capacidad a carga de compresión"):
        assert heading in text
    assert text.index("## 4. Revisión de requerimientos") < text.index("## 5. Revisión de capacidad a carga de compresión")
    assert "I1.3(a)" in text and "CUMPLE" in text and "Parámetro de reducción de rigidez (τb)" in text
