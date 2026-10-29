"""Execution provenance, not new AISC accreditation.

D2 arithmetic: stipulated HFS-010 tie (Ag=1000, An=800, U=.8 mm/mm2).
H3/F1: reuse only geometric INPUT fixtures from HFS-013; manual dimensionless
ratios below are independent of production. No historical oracle is modified.
"""
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import inspect
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from steel_design.codes.aisc_360_22 import tension_calc
from steel_design.codes.aisc_360_22 import axial_calc, flexure_calc, shear_calc, combined_hss_calc, composite_calc
from steel_design.domain.errors import RuleNotImplementedError
from steel_design.domain.routing.profile_router import RULE_DEFINITIONS
from steel_design.domain.rules.combined_hss_rules import CombinedH1HssRule, HssCombinedH3_2Rule
from steel_design.domain.rules.shear_rules import ShearG3VxRule, ShearG4VxRule, ShearG4VyRule
from steel_design.domain.rules.tension_rule import TensionRule
from steel_design.engine import SteelDesignEngine
from steel_design.models import SteelCase
from steel_design.reporting import calculation_trace_document
from steel_design.sections.loader import load_sections_from_excel
from steel_design.sections.repository import SectionRepository
from steel_design.tracing import CalculationStep, CalculationTrace, capture_trace, quantity

from test_hfs010_coverage import tie
from test_hfs012_flexure_selection import section as w_section, case as w_case
from test_hfs013_design_method import load_case
from test_hfs013_directional_h3 import box, case as box_case

ROOT = Path(__file__).resolve().parents[1]


def values(items):
    return {item.name: item.value for item in items}


def execute(case, section=None):
    repository = SectionRepository()
    if section is not None:
        repository.load([section])
    return SteelDesignEngine(repository).run(case)


@pytest.mark.parametrize("rid", [rid for rid, r in RULE_DEFINITIONS.items() if r.rule_class])
def test_every_registered_check_has_one_transparent_observer(rid):
    check = RULE_DEFINITIONS[rid].rule_class.check
    assert hasattr(check, "__wrapped__")
    assert not hasattr(check.__wrapped__, "__wrapped__")
    assert inspect.signature(check) == inspect.signature(check.__wrapped__)
    assert check.__module__ == check.__wrapped__.__module__


@pytest.mark.parametrize("method,expected", [("LRFD", [310.5, 216.0]), ("ASD", [345/1.67, 144.0])])
@pytest.mark.parametrize("demand,status", [(-50, "PASS"), (-350, "FAIL")])
def test_d2_trace_values_oracle_and_existing_coverage(method, expected, demand, status, monkeypatch):
    c = tie(demand, design_method=method)
    counts = []
    original = tension_calc.calculate_Pn_yielding

    def observed(*args, **kwargs):
        counts.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(tension_calc, "calculate_Pn_yielding", observed)
    plain = execute(c)
    previous_count = len(counts)
    counts.clear()
    with capture_trace() as capture:
        result = execute(c)
    assert len(counts) == previous_count  # no new evaluation, including pre-existing repeated D2 work
    assert result.model_dump(mode="json") == plain.model_dump(mode="json")
    trace = capture.snapshot()
    assert trace.analyses[0]["status"] == status
    assert trace.analyses[0]["coverage"] == result.coverage.model_dump(mode="json")
    assert [e.rule_id for e in trace.evaluations] == ["D2-1", "D2-2"]
    assert [values(e.check_values)["capacity"] for e in trace.evaluations] == pytest.approx(expected, rel=1e-12)
    for i, event in enumerate(trace.evaluations):
        assert event.metadata.normative_validation == "NOT_ACCREDITED"
        assert event.design_method == method
        assert values(event.check_values)["dcr"] == result.checks[i].dcr
        assert values(event.steps[0].outputs) == {"Ae": 640}
        assert {s.equation for s in event.steps} >= {"D3-1", "D2-1", "D2-2"}
        factor_steps = [s for s in event.steps if s.factors]
        assert {s.branch for s in factor_steps} == {method}
        assert {q.name for s in factor_steps for q in s.factors} == ({"phi"} if method == "LRFD" else {"omega"})
    exported = calculation_trace_document(trace)
    assert CalculationTrace.model_validate_json(json.dumps(exported, allow_nan=False)) == trace
    before = list(counts)
    calculation_trace_document(trace)
    assert counts == before  # exporter never invokes calculation


@pytest.mark.parametrize("family", ["rectangular", "round"])
@pytest.mark.parametrize("method", ["LRFD", "ASD"])
@pytest.mark.parametrize("moments", ["x", "y", "both"])
def test_h3_real_axes_factors_and_independent_final_ratio(family, method, moments):
    section, c, _ = load_case(family, method, moments, shear=True)
    with capture_trace() as capture:
        result = HssCombinedH3_2Rule().check(c, section)
    event, = capture.snapshot().evaluations
    assert event.rule_id == "H3-2"
    assert event.outcome == "RETURNED"
    scale = 1 if method == "LRFD" else .9*1.67
    expected = ((.4 if moments in {"x", "both"} else 0) + (.2 if moments in {"y", "both"} else 0))*scale + (.5*scale)**2
    final = event.steps[-1]
    assert final.equation == "H3-6"
    assert values(final.outputs)["interaction"] == pytest.approx(expected, abs=1e-12)
    assert values(event.check_values)["dcr"] == result.dcr
    flex = [s for s in event.steps if s.limit_state == "interaction_flexural_capacity"]
    assert {s.axis for s in flex} == ({"x", "y"} if moments == "both" else {moments})
    assert {s.branch for s in event.steps if s.limit_state == "available_flexural_strength"} == {method}
    pairs = [s for s in event.steps if s.limit_state == "directional_shear_ratio"]
    assert [s.axis for s in pairs] == ["x", "y"]
    assert [values(s.outputs)["ratio"] for s in pairs] == pytest.approx([.1*scale, .15*scale])


@pytest.mark.parametrize("axial,branch,equation", [("tension", "tension", None),
    ("low", "compression_low_axial", "H1-1b"), ("high", "compression_high_axial", "H1-1a")])
def test_h1_equation_is_not_guessed_from_legacy_clause(axial, branch, equation):
    section, c, _ = load_case("rectangular", "LRFD", axial=axial, torsion=False)
    with capture_trace() as capture:
        result = CombinedH1HssRule().check(c, section)
    event, = capture.snapshot().evaluations
    step = event.steps[-1]
    assert event.rule_id == "H1"
    assert step.branch == branch and step.equation == equation
    assert values(step.outputs)["interaction"] == result.demand
    if axial == "tension":
        assert result.clause == "H1-2"  # historical label unchanged, not used as normative identity
        assert any("F-37" in reason for reason in step.unknowns)


@pytest.mark.parametrize("loads,rule,axis,component", [({"Vux": -40}, ShearG4VxRule, "x", "Vux"),
    ({"Vuy": -20}, ShearG4VyRule, "y", "Vuy"), ({"Vu": -40}, ShearG4VxRule, "x", "Vu")])
def test_g_direction_and_signed_input_not_inferred(loads, rule, axis, component):
    with capture_trace() as capture:
        rule().check(box_case(**loads), box())
    step, = capture.snapshot().evaluations[0].steps
    assert step.axis == axis
    assert step.inputs[0].source == "case.loads."+component
    assert step.inputs[0].value == loads[component]
    assert any(("local_y" if axis == "x" else "local_x") in text for text in step.assumptions)


def test_blocked_attempt_keeps_exception_without_fabricated_check():
    c, section = box_case(Vux=1), box()
    with capture_trace() as capture, pytest.raises(RuleNotImplementedError) as caught:
        ShearG3VxRule().check(c, section)
    event, = capture.snapshot().evaluations
    assert event.outcome == "BLOCKED" and event.rule_id == "G3-Vx"
    assert event.error == caught.value.to_dict()
    assert not event.check_values and event.check_status is None
    with capture_trace() as next_capture:
        ShearG4VxRule().check(c, section)
    assert next_capture.snapshot().evaluations[0].parent_evaluation is None


def test_h3_threshold_block_is_not_capacity_pass():
    section, c, _ = load_case("rectangular", "LRFD", shear=True)
    c.loads.Tu = .001
    with capture_trace() as capture, pytest.raises(RuleNotImplementedError):
        HssCombinedH3_2Rule().check(c, section)
    event, = capture.snapshot().evaluations
    assert event.outcome == "BLOCKED"
    assert event.steps[-1].branch == "Tr_at_or_below_0.2Tc_BLOCKED"


@pytest.mark.parametrize("flange,web,ids", [(30, 40, {"F3-1", "F3-2", "F3-3"}),
    (8, 120, {"F4-1", "F4-2", "F4-3", "F4-4"})])
def test_f3_f4_identity_never_becomes_equation(flange, web, ids):
    with capture_trace() as capture:
        result = execute(w_case(Mux=1), w_section(flange, web))
    events = capture.snapshot().evaluations
    assert {e.rule_id for e in events} == ids
    assert result.status.value == "INCOMPLETE"
    assert not any(s.equation in ids for e in events for s in e.steps)
    if web == 120:
        assert all(any(s.branch == "delegate_to_evaluate_f5" for s in e.steps) for e in events)


def test_channel_gap_f31_remains_pending_with_independent_minor_check():
    c = w_case(Mux=1, Muy=1)
    with capture_trace() as capture:
        result = execute(c, w_section(30, 40, profile="CHANNEL"))
    trace = capture.snapshot()
    assert result.status.value == "INCOMPLETE"
    assert result.coverage.evaluation_errors
    assert {e.rule_id for e in trace.evaluations} == {"F6-1", "F6-2"}
    assert trace.analyses[0]["coverage"] == result.coverage.model_dump(mode="json")


@pytest.mark.parametrize("name", sorted(p.name for p in (ROOT / "examples").glob("*.json")))
def test_examples_trace_does_not_change_results_or_add_calculations(name, monkeypatch):
    calls = []

    def observe_call(function):
        @wraps(function)
        def recorded(*args, **kwargs):
            calls.append(function.__module__+":"+function.__name__)
            return function(*args, **kwargs)
        return recorded

    for module in (tension_calc, axial_calc, flexure_calc, shear_calc, combined_hss_calc, composite_calc):
        for key, function in inspect.getmembers(module, inspect.isfunction):
            if function.__module__ == module.__name__:
                monkeypatch.setattr(module, key, observe_call(function))
    data = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8-sig"))
    data.pop("output", None)
    c = SteelCase(**data)
    repository = SectionRepository()
    repository.load(load_sections_from_excel(str(ROOT / "data/sections.xlsx")))
    engine = SteelDesignEngine(repository)
    try:
        plain = engine.run(c)
    except Exception as expected:
        prior_calls = calls.copy()
        calls.clear()
        with capture_trace() as capture, pytest.raises(type(expected)) as actual:
            engine.run(c)
        assert str(actual.value) == str(expected)
        assert calls == prior_calls
        return
    prior_calls = calls.copy()
    calls.clear()
    with capture_trace() as capture:
        traced = engine.run(c)
    assert calls == prior_calls
    assert traced.model_dump(mode="json") == plain.model_dump(mode="json")
    trace = capture.snapshot()
    assert len(trace.analyses[0]["checks"]) == len(traced.checks)
    for link in trace.analyses[0]["checks"]:
        event = trace.evaluations[link["evaluation_index"]]
        check = traced.checks[link["check_index"]]
        assert event.outcome == "RETURNED"
        assert values(event.check_values)["capacity"] == check.capacity
        assert event.check_status == check.status.value
    json.dumps(calculation_trace_document(trace), allow_nan=False)


def test_capture_isolation_and_detached_snapshot():
    def worker(demand):
        with capture_trace() as capture:
            execute(tie(demand))
        return capture.snapshot()
    with capture_trace() as outer:
        execute(tie(-20))
        with capture_trace() as inner:
            execute(tie(-30))
        execute(tie(-40))
    assert len(outer.snapshot().evaluations) == 4
    assert len(inner.snapshot().evaluations) == 2
    snapshot = outer.snapshot()
    snapshot.evaluations[0].inputs.clear()
    assert outer.snapshot().evaluations[0].inputs
    with ThreadPoolExecutor(2) as pool:
        traces = list(pool.map(worker, [-10, -350]))
    assert [t.analyses[0]["status"] for t in traces] == ["PASS", "FAIL"]


def test_unknown_nonfinite_and_partial_contracts_are_explicit():
    q = quantity("inactive_capacity", float("inf"), "kN")
    assert q.value is None and "inf" in q.diagnostic
    q.model_dump_json()
    with pytest.raises(ValidationError):
        CalculationStep(producer="p", limit_state="l", branch=None, reference=None, equation=None, expression=None)


def test_inactive_direct_check_does_not_invent_a_resistance_step():
    section, c, _ = load_case("rectangular", "LRFD", axial=None)
    with capture_trace() as capture:
        check = TensionRule().check(c, section)
    event, = capture.snapshot().evaluations
    assert check.status.value == "PASS" and event.check_status == "PASS"
    assert event.steps == () and event.unknowns
    assert event.check_values[0].unit is None
    assert not capture.snapshot().analyses  # direct check alone grants no global PASS


def test_exception_before_rule_execution_has_no_invented_rule():
    c = w_case(Mux=1).model_copy(update={"design_method": "INVALID"})
    capture = None
    with pytest.raises(Exception):
        with capture_trace(provenance={"source": "stipulated test input"}) as capture:
            execute(c, w_section())
    trace = capture.snapshot()
    assert not trace.evaluations and not trace.analyses
    assert trace.unhandled_errors
    assert trace.supplied_provenance == {"source": "stipulated test input"}
