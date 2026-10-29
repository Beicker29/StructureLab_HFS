"""Opt-in observations of actual execution, separate from JSON contract 1.0.

No selection, equation evaluation, accreditation or reconstruction from labels.
The context is local to the caller; decorators execute the producer exactly once.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .domain.routing.registry_metadata import RuleMetadata
from .models import finite_json_payload


class TraceValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(min_length=1)
    value: float | None
    unit: str | None
    source: str = Field(min_length=1)
    diagnostic: str | None = None

    @model_validator(mode="after")
    def explicit_unknowns(self):
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("Nonfinite observations require null and a diagnostic")
        if (self.value is None or self.unit is None) and not self.diagnostic:
            raise ValueError("Unknown value/unit requires a diagnostic")
        return self


def quantity(name, value, unit, source="producer local value"):
    """Record a value without recomputing, rounding or replacing missing data."""
    diagnostic = None
    if value is None:
        diagnostic = "Value not available from producer"
    elif not math.isfinite(value):
        diagnostic = f"Producer nonfinite value: {value!r}; not a finite capacity"
        value = None
    if unit is None:
        diagnostic = (diagnostic + "; " if diagnostic else "") + "Unit not supplied by producer"
    return TraceValue(name=name, value=value, unit=unit, source=source, diagnostic=diagnostic)


class CalculationStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    producer: str = Field(min_length=1)
    limit_state: str = Field(min_length=1)
    branch: str | None
    reference: str | None
    equation: str | None
    expression: str | None
    axis: str | None = None
    inputs: tuple[TraceValue, ...] = ()
    intermediates: tuple[TraceValue, ...] = ()
    outputs: tuple[TraceValue, ...] = ()
    factors: tuple[TraceValue, ...] = ()
    assumptions: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()

    @model_validator(mode="after")
    def explain_partial(self):
        if any(getattr(self, key) is None for key in ("branch", "reference", "equation", "expression")) and not self.unknowns:
            raise ValueError("Partial steps must identify unknown or unaccredited information")
        return self


class RuleTrace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    evaluation_index: int
    parent_evaluation: int | None
    rule_id: str | None
    implementation: str
    metadata: RuleMetadata | None
    design_method: str
    outcome: Literal["RETURNED", "BLOCKED", "ERROR"]
    inputs: dict
    steps: tuple[CalculationStep, ...]
    check_values: tuple[TraceValue, ...] = ()
    check_status: str | None = None
    error: dict | None = None
    unknowns: tuple[str, ...]


class CalculationTrace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    trace_version: Literal["HFS-024-v1"] = "HFS-024-v1"
    evaluations: tuple[RuleTrace, ...]
    analyses: tuple[dict, ...]
    unhandled_errors: tuple[dict, ...] = ()
    supplied_provenance: dict = Field(default_factory=dict)
    normative_accreditation: Literal["NO_NEW_ACCREDITATION"] = "NO_NEW_ACCREDITATION"


_session = ContextVar("hfs_calculation_trace", default=None)
_active = ContextVar("hfs_rule_evaluation", default=None)


class TraceCapture:
    """Mutable execution buffer. Use snapshot() for a detached, serializable view."""

    def __init__(self, provenance=None):
        self._evaluations = []
        self._checks = []
        self._analyses = []
        self._errors = []
        self._provenance = finite_json_payload(provenance or {})

    def snapshot(self) -> CalculationTrace:
        return CalculationTrace(evaluations=tuple(e for e in self._evaluations if e is not None),
                                analyses=tuple(self._analyses), unhandled_errors=tuple(self._errors),
                                supplied_provenance=self._provenance).model_copy(deep=True)


@contextmanager
def capture_trace(*, provenance=None):
    """Capture any engine or direct rule calls in this context, without I/O.

    Nested captures are isolated. Exceptions propagate unchanged; completed and
    blocked attempts remain available through the buffer after context exit.
    """
    capture = TraceCapture(provenance)
    session_token = _session.set(capture)
    active_token = _active.set(None)
    try:
        yield capture
    except Exception as exc:
        error = exc.to_dict() if hasattr(exc, "to_dict") else {"type": type(exc).__name__, "message": str(exc)}
        capture._errors.append(finite_json_payload(error))
        raise
    finally:
        _active.reset(active_token)
        _session.reset(session_token)


def emit_step(**fields):
    """Called at the producer, with values it actually used; never evaluates text."""
    active = _active.get()
    if active is not None:
        active["steps"].append(CalculationStep(**fields))


def observed_value(value, *, name, unit, **fields):
    """Return the very value just calculated; observing adds no arithmetic."""
    if _active.get() is not None:
        emit_step(outputs=(quantity(name, value, unit),), **fields)
    return value


def traced_rule(function):
    """Observe the check boundary and preserve its signature, result and exception."""
    @wraps(function)
    def observed(self, case, section):
        capture = _session.get()
        if capture is None:
            return function(self, case, section)
        # One canonical registry. Exact identity, then inherited implementation;
        # never clause/name parsing. Ambiguous/unregistered classes stay unknown.
        from .domain.routing.profile_router import RULE_DEFINITIONS
        matches = [r for r in RULE_DEFINITIONS.values() if r.rule_class is type(self)]
        if not matches:
            matches = [r for r in RULE_DEFINITIONS.values() if r.rule_class in type(self).__mro__
                       and r.rule_class.check is type(self).check]
        definition = matches[0] if len(matches) == 1 else None
        parent = _active.get()
        index = len(capture._evaluations)
        capture._evaluations.append(None)
        inputs = finite_json_payload({"case": case.model_dump(mode="json"),
                                      "explicit_case_fields": case.model_dump(mode="json", exclude_unset=True),
                                      "section": section.model_dump(mode="json")})
        frame = {"index": index, "steps": []}
        token = _active.set(frame)
        fields = dict(evaluation_index=index, parent_evaluation=parent["index"] if parent else None,
                      rule_id=definition.rule_id if definition else None,
                      implementation=f"{type(self).__module__}:{type(self).__qualname__}.check",
                      metadata=definition.metadata if definition else None,
                      design_method=str(getattr(case.design_method, "value", case.design_method)), inputs=inputs)
        try:
            result = function(self, case, section)
        except Exception as exc:
            from .domain.errors import IncompleteSectionDataError, RuleNotImplementedError
            error = exc.to_dict() if hasattr(exc, "to_dict") else {"type": type(exc).__name__, "message": str(exc)}
            capture._evaluations[index] = RuleTrace(**fields, steps=tuple(frame["steps"]),
                outcome="BLOCKED" if isinstance(exc, (IncompleteSectionDataError, RuleNotImplementedError)) else "ERROR",
                error=finite_json_payload(error), unknowns=("No completed check; no resistance or coverage credited.",))
            raise
        else:
            capture._checks.append((result, index))
            capture._evaluations[index] = RuleTrace(**fields, steps=tuple(frame["steps"]), outcome="RETURNED",
                check_status=result.status.value,
                check_values=(quantity("demand", result.demand, result.unit, "CheckResult.demand"),
                              quantity("capacity", result.capacity, result.unit, "CheckResult.capacity"),
                              quantity("dcr", result.dcr, "ratio", "CheckResult.dcr")),
                unknowns=("Instrumentation is progressive; steps do not assert complete arithmetic provenance.",
                          "Unrecorded branches, intermediate values and equation mappings remain unknown.",
                          *(() if definition else ("No unique HFS-023 rule identity for this class.",))))
            return result
        finally:
            _active.reset(token)
    return observed


def record_analysis(result):
    """Copy existing coverage/decisions and link checks by identity, not by labels."""
    capture = _session.get()
    if capture is None:
        return
    links = [{"check_index": i, "evaluation_index": index}
             for i, check in enumerate(result.checks) for returned, index in capture._checks if returned is check]
    capture._analyses.append(finite_json_payload({"status": result.status.value,
        "known_failures": result.known_failures, "checks": links,
        "coverage": result.coverage.model_dump(mode="json") if result.coverage is not None else None}))
