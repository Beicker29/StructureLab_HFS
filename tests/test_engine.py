"""Engine status: PASS only when every independently required Chapter E limit state was evaluated."""
import math

import pytest

from steel_design.domain.coverage import discharge, required_obligations
from steel_design.domain.errors import AmbiguousSectionError, SectionNotFoundError
from steel_design.sections.repository import SectionRepository
from steel_design.engine import SteelDesignEngine

from conftest import steel_case


def ids(obligations):
    return {o.id for o in obligations}


@pytest.mark.parametrize("name, kwargs, expected", [
    ("W14X90", {}, {"classification", "FB-x", "FB-y"}),
    ("W14X90", {"Lz": 6000}, {"classification", "FB-x", "FB-y", "TB"}),
    ("W14X90", {"factors": {"ya": 100}}, {"classification", "FB-x", "FB-y", "TB"}),
    ("C15X50", {}, {"classification", "FB-x", "FB-y", "FTB"}),
    ("PTE100X100X4MM", {}, {"classification", "FB-x", "FB-y"}),
    ("PTE100X100X4MM", {"Lz": 6000}, {"classification", "FB-x", "FB-y", "TB"}),
    ("2L4X4X1/4", {}, {"classification", "FB-x", "FB-y", "FTB", "E6"}),
    ("L4X4X1/4", {}, {"classification", "FB"}),
    ("L4X4X1/4", {"Fy": 450}, {"classification", "FB", "FTB"}),       # b/t = 16 > 0.71*sqrt(E/Fy)
])
def test_required_obligations_follow_chapter_e_text(sections, name, kwargs, expected):
    assert ids(required_obligations(steel_case(name, **kwargs), sections[name])) == expected


def test_missing_mode_or_effective_area_keeps_obligation_open(sections):
    section = sections["C15X50"]
    obligations = required_obligations(steel_case("C15X50"), section)
    fake = {"modes": {"FB-x": {"area_basis": "Ag"}, "FB-y": {"area_basis": "Ag"}},
            "classification": {"slender": True, "elements": [{"element": "flange"}, {"element": "web"}]}}
    assert ids(discharge(obligations, section, fake)) == {"FTB", "LB"}


def test_pass_fail_boundary_is_ratio_one(engine):
    capacity = engine.run(steel_case("PTE100X100X4MM")).capacity_kN
    assert engine.run(steel_case("PTE100X100X4MM", Pu=capacity)).status.value == "PASS"
    assert engine.run(steel_case("PTE100X100X4MM", Pu=math.nextafter(capacity, math.inf))).status.value == "FAIL"


def test_asd_and_lrfd_differ_only_by_e1_factors(engine):
    lrfd = engine.run(steel_case("C15X50")).capacity_kN
    asd = engine.run(steel_case("C15X50", method="ASD")).capacity_kN
    assert lrfd == pytest.approx(asd * 0.90 * 1.67, rel=1e-12)


@pytest.mark.parametrize("name, kwargs", [
    ("2L4X4X1/4", {}), ("L4X4X1/4", {}), ("PTE100X100X4MM", {"Lz": 6000}), ("C15X50", {"factors": {"xa": 5}}),
])
def test_blocked_domains_are_incomplete_never_pass(engine, name, kwargs):
    result = engine.run(steel_case(name, **kwargs))
    assert result.status.value == "INCOMPLETE" and result.capacity_kN is None and result.errors


def test_solid_custom_section(engine):
    result = engine.run(steel_case("BAR", Fy=250, L=1000, custom_section={"type": "SOLID_RECTANGULAR", "H": 100, "B": 20}))
    ry = 20 / math.sqrt(12)
    fe = math.pi**2 * 200000 / (1000 / ry) ** 2                     # E3-4
    assert result.compression["governing_mode"] == "FB-y"
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
