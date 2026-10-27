"""Expected obligations from HFS-002 N rows, not router-generated expectations.

D2 oracle: S22 local PDF100-103 (16.1-32..35), N04. Stipulated qualified
ordinary solid tie: Ag=1000, An=800 mm2, U=.8, Fy=345, Fu=450 MPa.
Independent arithmetic, kN: LRFD 310.5/216; ASD 345/1.67 and 144.
No complete AISC validation or verification of external declarations is claimed.
"""
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from src.steel_design.domain.coverage import build_coverage_plan
from src.steel_design.domain.errors import RuleNotImplementedError, IncompleteSectionDataError, ValidationError as DomainValidationError
from src.steel_design.domain.rules.tension_rule import TensionRule, TensionRuptureRule
from src.steel_design.engine import SteelDesignEngine, _build_custom_section
from src.steel_design.models import CheckResult, SteelCase, TensionScope
from src.steel_design.results_model import AnalysisStatus, EngineResult
from src.steel_design.sections.loader import load_sections_from_excel
from src.steel_design.sections.repository import SectionRepository

ROOT = Path(__file__).resolve().parents[1]
SCOPE = dict(ordinary_prismatic_member=True, concentric_axial_force=True, no_special_conditions=True,
             material_reference="Stipulated S22 A3 material for isolated D2 oracle",
             demand_reference="Stipulated concentric tie load, no instability amplification",
             net_area_reference="Stipulated An=800 and U=.8, D3 by external assessment",
             connection_reference="Stipulated connection/block shear checked externally; ordinary tie, not pin/eye/thread",
             external_checks_reference="Stipulated ordinary ambient/static nonseismic member; external service/detailing review")


def payload(loads, **extra):
    return dict(section_name="W12X26", material=dict(Fy=345, Fu=450), loads=loads,
                lengths=dict(Lx=1000, Ly=1000, Lz=1000, Lb=1000), **extra)


def tie(demand=-50, **extra):
    data = payload(dict(Pu=demand))
    data.update(section_name="tie", custom_section=dict(type="SOLID_RECTANGULAR", B=10, H=100),
                connection=dict(An=800, U=.8), tension_scope=SCOPE)
    data.update(extra)
    return SteelCase(**data)


@pytest.fixture(scope="module")
def repository():
    repo = SectionRepository()
    repo.load(load_sections_from_excel(str(ROOT / "data/sections.xlsx")))
    return repo


def obligations(result):
    return {o.id: o for o in result.coverage.obligations}


def example(name, loads=None):
    data = json.loads((ROOT / "examples" / f"{name}_case.json").read_text(encoding="utf-8-sig"))
    data.pop("output", None)
    if loads is not None:
        data["loads"] = loads
    return SteelCase(**data)


@pytest.mark.parametrize("method,capacities", [("LRFD", (310.5, 216)), ("ASD", (345/1.67, 144))])
@pytest.mark.parametrize("demand", [-50, -220, -350])
def test_d2_independent_capacities_and_global_pass_fail(method, capacities, demand):
    result = SteelDesignEngine(SectionRepository()).run(tie(demand, design_method=method))
    assert set(obligations(result)) == {"scope.basis", "N04.yielding.Pu", "N04.rupture.Pu"}
    assert [c.capacity for c in result.checks] == pytest.approx(capacities, rel=1e-12, abs=1e-9)
    assert all(c.demand == abs(demand) for c in result.checks)
    assert result.status.value == ("PASS" if abs(demand) <= min(capacities) else "FAIL")
    assert result.coverage.complete
    assert obligations(result)["N04.yielding.Pu"].accepted_checks == [0]
    assert obligations(result)["N04.rupture.Pu"].accepted_checks == [1]
    assert result.coverage.scope_evidence == SCOPE


def test_round_solid_tension_has_same_two_required_limit_states():
    case = tie(custom_section=dict(type="SOLID_CIRCULAR", diameter=40))
    result = SteelDesignEngine(SectionRepository()).run(case)
    # Independent geometry/units: Ag=pi*20^2; N -> kN.
    assert result.status.value == "PASS"
    assert result.checks[0].capacity == pytest.approx(.9*345*math.pi*20**2/1000, rel=1e-12, abs=1e-9)
    assert result.checks[1].capacity == pytest.approx(216, rel=1e-12, abs=1e-9)


@pytest.mark.parametrize("loads", [dict(Pu=1), dict(Pu=-1, Mux=1), dict(Mux=1, Muy=1)])
def test_tension_declarations_cannot_narrow_other_demands(loads):
    result = SteelDesignEngine(SectionRepository()).run(tie(loads=loads))
    assert result.status.value == "INCOMPLETE"
    assert obligations(result)["scope.basis"].status.value == "PENDING"


def test_declaration_cannot_qualify_net_area_larger_than_gross():
    # Existing HFS-011 guard remains the single authority for physical validity.
    with pytest.raises(DomainValidationError, match="Net area An cannot exceed"):
        SteelDesignEngine(SectionRepository()).run(tie(connection=dict(An=1200, U=.5)))


@pytest.mark.parametrize("field", list(SCOPE))
def test_missing_external_precondition_is_unknown_not_na(field):
    scope = dict(SCOPE)
    scope.pop(field)
    result = SteelDesignEngine(SectionRepository()).run(tie(tension_scope=scope))
    basis = obligations(result)["scope.basis"]
    assert basis.status.value == "PENDING" and basis.applicability == "UNKNOWN"
    assert any(field in required for required in basis.required)
    assert result.status.value == "INCOMPLETE"


@pytest.mark.parametrize("update", [{"ordinary_prismatic_member": False}, {"no_special_conditions": False},
                                    {"concentric_axial_force": False}])
def test_false_conditions_cannot_qualify_tie(update):
    assert SteelDesignEngine(SectionRepository()).run(tie(tension_scope={**SCOPE, **update})).status.value == "INCOMPLETE"


@pytest.mark.parametrize("update", [{"ordinary_prismatic_member": "true"}, {"concentric_axial_force": 1},
                                    {"material_reference": " "}, {"unknown": True}])
def test_scope_input_preserves_hfs011_contract(update):
    with pytest.raises(ValidationError):
        TensionScope(**{**SCOPE, **update})


def test_known_failure_survives_missing_obligation():
    result = SteelDesignEngine(SectionRepository()).run(tie(-350, tension_scope=None))
    assert result.status.value == "INCOMPLETE" and result.known_failures == [0, 1]
    assert all(c.status.value == "FAIL" for c in result.checks)
    assert EngineResult.model_validate_json(result.model_dump_json()).status == result.status


@pytest.mark.parametrize("keep", [[], [TensionRule()], [TensionRuptureRule()], [TensionRule(), TensionRule()]])
def test_suppress_one_or_all_rules_cannot_pass(monkeypatch, keep):
    engine = SteelDesignEngine(SectionRepository())
    monkeypatch.setattr(engine.router, "get_rules", lambda *args: keep)
    result = engine.run(tie())
    assert result.status.value == "INCOMPLETE"
    assert any(o.status.value == "PENDING" for o in result.coverage.obligations)


def test_relabelled_fake_check_cannot_cover_obligations(monkeypatch):
    class Fake:
        def check(self, *args):
            return CheckResult(name="Tension Yielding", clause="D2-1", demand=50, capacity=1000, dcr=.05, status="PASS")
    engine = SteelDesignEngine(SectionRepository())
    monkeypatch.setattr(engine.router, "get_rules", lambda *args: [Fake(), Fake()])
    result = engine.run(tie())
    assert result.status.value == "INCOMPLETE"
    assert all(not o.accepted_checks for o in result.coverage.obligations)


@pytest.mark.parametrize("mutation", [dict(demand=0, capacity=0, dcr=0), dict(clause="F2-1"), dict(details={})])
def test_placeholder_or_mismatched_real_implementation_is_not_coverage(monkeypatch, mutation):
    original = TensionRule.check
    monkeypatch.setattr(TensionRule, "check", lambda self, case, section: original(self, case, section).model_copy(update=mutation))
    result = SteelDesignEngine(SectionRepository()).run(tie())
    assert result.status.value == "INCOMPLETE"
    assert not obligations(result)["N04.yielding.Pu"].accepted_checks


@pytest.mark.parametrize("error", [RuleNotImplementedError, IncompleteSectionDataError])
def test_rule_unavailable_preserves_prior_failure(monkeypatch, error):
    def unavailable(*args):
        raise error("Deliberately unavailable rupture evaluation")
    monkeypatch.setattr(TensionRuptureRule, "check", unavailable)
    result = SteelDesignEngine(SectionRepository()).run(tie(-350))
    assert result.status.value == "INCOMPLETE" and result.known_failures == [0]
    assert result.coverage.evaluation_errors[0]["error"]["code"] == error.default_code
    assert obligations(result)["N04.rupture.Pu"].status.value == "PENDING"


def test_f02_zero_load_has_no_resistance_coverage(repository):
    result = SteelDesignEngine(repository).run(SteelCase(**payload(dict(Pu=0, Mux=0, Muy=0, Vu=0, Vux=0, Vuy=0, Tu=0))))
    assert not result.checks and result.status.value == "INCOMPLETE"
    assert obligations(result)["scope.nonempty"].status.value == "PENDING"


@pytest.mark.parametrize("loads", [dict(Pu=1, Mux=1), dict(Pu=0, Mux=1, Muy=1)])
def test_f01_f33_interaction_required_independently_of_router(repository, loads):
    result = SteelDesignEngine(repository).run(SteelCase(**payload(loads)))
    assert result.status.value == "INCOMPLETE"
    interaction = obligations(result)["N29.interaction"]
    assert interaction.normative_ids == ["N29"] and interaction.status.value == "PENDING"
    assert not interaction.executed_checks  # W isolated E/F never represents H
    assert interaction.alternatives == ["H1 for eligible symmetry/restraints", "H2 permitted general alternative"]


def test_f03_unknown_compactness_is_never_covered(repository):
    section = repository.get("W12X26").model_copy(update=dict(bf_2tf_ratio=None, h_tw_ratio=None))
    repo = SectionRepository()
    repo.load([section])
    result = SteelDesignEngine(repo).run(SteelCase(**payload(dict(Mux=1))))
    assert result.status.value == "INCOMPLETE"
    assert obligations(result)["N11.conditions.Mux"].applicability == "UNKNOWN"
    assert obligations(result)["F.yielding.Mux"].executed_checks  # old F2 computation retained, never accredited


def test_f31_minor_axis_does_not_cover_major(repository):
    section = repository.get("W12X26").model_copy(update=dict(type="CHANNEL", bf_2tf_ratio=50, h_tw_ratio=300))
    repo = SectionRepository()
    repo.load([section])
    result = SteelDesignEngine(repo).run(SteelCase(**payload(dict(Mux=1, Muy=1))))
    assert result.status.value == "INCOMPLETE"
    assert not obligations(result)["F.yielding.Mux"].executed_checks
    assert obligations(result)["F.yielding.Muy"].executed_checks


@pytest.mark.parametrize("name,nid", [("composite_encased", "N39"),
                                    ("composite_filled_rectangular_hss", "N40"), ("composite_beam", "N43")])
@pytest.mark.parametrize("moment", [1, 1000000])
def test_f34_ratio_or_transfer_is_not_moment_resistance(repository, name, nid, moment):
    result = SteelDesignEngine(repository).run(example(name, dict(Mux=moment)))
    obligation = obligations(result)["I.flexure.Mux"]
    assert result.status.value == "INCOMPLETE" and obligation.normative_ids == [nid]
    assert not obligation.executed_checks and not obligation.accepted_checks


def test_f35_e7_execution_does_not_prove_correspondence(repository):
    section = repository.get("W12X26").model_copy(update=dict(bf_2tf_ratio=100, h_tw_ratio=300))
    repo = SectionRepository()
    repo.load([section])
    result = SteelDesignEngine(repo).run(SteelCase(**payload(dict(Pu=1))))
    assert result.status.value == "INCOMPLETE"
    assert obligations(result)["N10.effective_area"].executed_checks
    assert "F-35" in obligations(result)["N10.effective_area"].reason


def test_f36_e5_conditions_and_branches_stay_pending(repository):
    result = SteelDesignEngine(repository).run(example("single_angle", dict(Pu=1)))
    assert result.status.value == "INCOMPLETE"
    assert obligations(result)["N08.angle_alternative"].executed_checks
    assert "F-36" in obligations(result)["N08.angle_alternative"].reason


def test_f06_directional_hss_combination_stays_pending(repository):
    result = SteelDesignEngine(repository).run(example("rectangular_hss"))
    assert result.status.value == "INCOMPLETE"
    assert obligations(result)["N30.interaction"].executed_checks
    assert "F-06" in obligations(result)["N30.interaction"].reason
    assert {"G.shear.Vux", "G.shear.Vuy"} <= obligations(result).keys()


def test_alternatives_are_one_required_route_not_all_branches(repository):
    result = SteelDesignEngine(repository).run(example("composite_encased", dict(Vux=1)))
    obligation = obligations(result)["I.shear.Vux"]
    assert len(obligation.alternatives) == 3
    assert obligation.selected_alternative is None and obligation.status.value == "PENDING"
    # No independent obligation requiring all three permissible alternatives.
    assert [o.id for o in result.coverage.obligations if o.limit_state == "composite_shear"] == ["I.shear.Vux"]


def test_geometric_not_applicable_requires_positive_evidence():
    case = tie(loads=dict(Muy=1), custom_section=dict(type="SOLID_CIRCULAR", diameter=30))
    plan = build_coverage_plan(case, _build_custom_section(case))
    by_id = {o.id: o for o in plan.obligations}
    assert by_id["F.local_buckling.Muy"].status.value == "NOT_APPLICABLE"
    assert by_id["F.lateral_torsional_buckling.Muy"].status.value == "NOT_APPLICABLE"
    assert by_id["F.yielding.Muy"].status.value == "PENDING"


def test_planning_does_not_call_router(monkeypatch):
    engine = SteelDesignEngine(SectionRepository())
    monkeypatch.setattr(engine.router, "get_rules", lambda *args: pytest.fail("Planner consulted routing"))
    case = tie()
    plan = build_coverage_plan(case, _build_custom_section(case))
    assert {o.id for o in plan.obligations} == {"scope.basis", "N04.yielding.Pu", "N04.rupture.Pu"}


def test_direct_empty_result_cannot_be_constructed_as_pass():
    assert EngineResult(checks=[], status="PASS").status == AnalysisStatus.INCOMPLETE


@pytest.mark.parametrize("bundle", [False, True])
def test_cli_serializes_coverage_and_propagates_incomplete(tmp_path, bundle):
    case = tie(tension_scope=None).model_dump(mode="json")
    if bundle:
        case = {**case, "cases": [{"name": "unqualified"}, {"name": "qualified", "tension_scope": SCOPE}]}
    path = tmp_path / "case.json"
    path.write_text(json.dumps(case), encoding="utf-8")
    run = subprocess.run([sys.executable, "-m", "src.steel_design.run", str(path),
                          "--results-dir", str(tmp_path / "results")], cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    data = json.loads(run.stdout)
    assert data["status"] == "INCOMPLETE"
    summary = data["cases"][0] if bundle else data
    assert summary["coverage"]["complete"] is False
    detail = json.loads(Path(summary["artifacts"]["detailed_results_json"]).read_text(encoding="utf-8"))
    assert detail["output"]["coverage"] == summary["coverage"]
    if bundle:
        assert data["cases"][1]["status"] == "PASS"
