"""Engine status: PASS only when every independently required Chapter E limit state was evaluated."""
import math

import pytest
from conftest import steel_case

from steel_design.domain.coverage import discharge, required_obligations
from steel_design.engine import SteelDesignEngine
from steel_design.errors import AmbiguousSectionError, SectionNotFoundError
from steel_design.execution import execute_payload, governing, overall_status
from steel_design.models import DesignResult, Status, SteelCase, worst_status
from steel_design.sections.repository import SectionRepository


def ids(obligations):
    return {o.id for o in obligations}


@pytest.mark.parametrize("name, kwargs, expected", [
    ("W14X90", {}, {"classification", "FB-x_3", "FB-y_2"}),
    ("W14X90", {"Lz_1": 6000}, {"classification", "FB-x_3", "FB-y_2", "TB"}),
    ("W14X90", {"factors": {"ya_2": 100}}, {"classification", "FB-x_3", "FB-y_2", "TB"}),
    ("C15X50", {}, {"classification", "FB-x_3", "FB-y_2", "FTB"}),
    ("PTE100X100X4MM", {}, {"classification", "FB-x_3", "FB-y_2"}),
    ("PTE100X100X4MM", {"Lz_1": 6000}, {"classification", "FB-x_3", "FB-y_2", "TB"}),
    ("2L4X4X1/4", {}, {"classification", "FB-x_3", "FB-y_2", "FTB", "E6"}),
    ("L4X4X1/4", {}, {"classification", "FB"}),
    ("L4X4X1/4", {"Fy": 450}, {"classification", "FB", "FTB"}),       # b/t = 16 > 0.71*sqrt(E/Fy)
])
def test_required_obligations_follow_chapter_e_text(sections, name, kwargs, expected):
    assert ids(required_obligations(steel_case(name, **kwargs), sections[name])) == expected


def test_missing_mode_or_effective_area_keeps_obligation_open(sections):
    section = sections["C15X50"]
    obligations = required_obligations(steel_case("C15X50"), section)
    fake = {"modes": {"FB-x_3": {"area_basis": "Ag"}, "FB-y_2": {"area_basis": "Ag"}},
            "classification": {"slender": True, "elements": [{"element": "flange"}, {"element": "web"}]}}
    assert ids(discharge(obligations, section, fake)) == {"FTB", "LB"}


def test_pass_fail_boundary_is_ratio_one(engine):
    capacity = engine.run(steel_case("PTE100X100X4MM")).capacity_kN
    assert engine.run(steel_case("PTE100X100X4MM", P=-(capacity))).status.value == "PASS"
    assert engine.run(steel_case("PTE100X100X4MM", P=-(math.nextafter(capacity, math.inf)))).status.value == "FAIL"


def test_capacity_is_lrfd_design_strength(engine):
    result = engine.run(steel_case("C15X50"))
    assert result.capacity_kN == pytest.approx(0.90 * result.compression["Pn_kN"], rel=1e-15)


@pytest.mark.parametrize("name, kwargs", [
    ("2L4X4X1/4", {}), ("L4X4X1/4", {}), ("W14X90", {"factors": {"xa_3": 5, "ya_2": 5}}), ("C15X50", {"factors": {"xa_3": 5}}),
])
def test_blocked_domains_are_incomplete_never_pass(engine, name, kwargs):
    result = engine.run(steel_case(name, **kwargs))
    assert result.status.value == "INCOMPLETE" and result.capacity_kN is None and result.errors


def test_solid_custom_section(engine):
    result = engine.run(steel_case("BAR", Fy=250, L=1000, custom_section={"type": "SOLID_RECTANGULAR", "H": 100, "B": 20}))
    ry = 20 / math.sqrt(12)
    fe = math.pi**2 * 200000 / (1000 / ry) ** 2                     # E3-4
    assert result.compression["governing_mode"] == "FB-y_2"
    assert result.capacity_kN == pytest.approx(0.90 * 0.877 * fe * 2000 / 1000)  # E3-3 (Fy/Fe > 2.25)
    assert result.status.value == "PASS"


def test_unknown_and_ambiguous_sections(engine, sections):
    with pytest.raises(SectionNotFoundError):
        engine.run(steel_case("W99X1"))
    repo = SectionRepository()
    w = sections["W14X90"]
    repo.load([w, w.model_copy(update={"area": 1.0})])
    with pytest.raises(AmbiguousSectionError):
        SteelDesignEngine(repo).run(steel_case("w14x90"))


@pytest.mark.parametrize(
    "statuses, expected",
    [(["PASS", "PASS"], "PASS"), (["PASS", "INCOMPLETE"], "INCOMPLETE"), (["PASS", "FAIL"], "FAIL"), (["INCOMPLETE", "FAIL"], "FAIL")],
)
def test_a_known_failure_is_never_hidden_by_incompleteness(statuses, expected):
    assert worst_status(Status(s) for s in statuses).value == expected
    results = [DesignResult(section="W14X90", family="W", status=s) for s in statuses]
    assert overall_status(results).value == expected


def test_cb_amplification_without_lengths_is_reported_and_not_assumed(engine):
    flexure = {"tension_flange_holes": False, "Cb": 1.2, "tension_cb_amplification": True}
    case = SteelCase(
        section_name="W14X90", material={"Fy": 345, "Fu": 448}, P=100, Mx_3=50, tension={"An": 15000, "U": 0.9}, flexure=flexure
    )
    assert engine.run(case).check("flexure_x_3").status == Status.INCOMPLETE


def test_second_order_on_a_member_of_another_family_is_incomplete(engine):
    second_order = {
        "axis": "x_3",
        "Mnt": 1.5,
        "Mlt": 1,
        "Pnt": -40,
        "Plt": -10,
        "M1_M2": -0.5,
        "Pstory": 20000,
        "Pmf": 8000,
        "H": 500,
        "L": 2000,
        "drift": 10,
    }
    case = SteelCase(section_name="W14X90", material={"Fy": 345}, tau_b=0.8, lengths={"Lx_3": 2000, "Ly_2": 2000, "Lz_1": 2000},
                     composite={"kind": "filled", "concrete": {"fc": 35, "wc": 2320, "lightweight": False}, "second_order": second_order})
    result = engine.run(case)
    assert result.status == Status.INCOMPLETE and result.check("axial").capacity is None


def test_governing_is_the_check_with_the_largest_ratio(engine):
    data = {"section_name": "W14X90", "material": "ASTM A572 Gr 50", "lengths": {"Lx_3": 4000, "Ly_2": 4000, "Lz_1": 4000},
            "cases": [{"name": "leve", "P": -100}, {"name": "fuerte", "P": -2500}]}
    executions = execute_payload(data, engine)
    top = governing(executions)
    assert top["name"] == "fuerte" and top["check"] == "axial" and top["ratio"] == executions[1][2].check("axial").ratio
