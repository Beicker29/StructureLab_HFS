"""Canonical method guards for the engine, router and direct domain calls."""
from ..design_methods import DesignMethod
from .errors import ValidationError


def require_case_method(case, *, chapter=None):
    method = case.design_method
    # A valid SteelCase contains an enum. Reject unsafe model_copy/mutation,
    # rather than allowing .value AttributeError or repairing the caller's case.
    if not isinstance(method, DesignMethod):
        raise ValidationError("Invalid case design method; validate SteelCase before calculation.",
            details={"field": "design_method", "design_method_received": method,
                     "allowed": ["LRFD", "ASD"]})
    if chapter in {"F", "I"} and method != DesignMethod.LRFD:
        scope = "flexural" if chapter == "F" else "composite"
        raise ValidationError(f"Chapter {chapter} {scope} checks are implemented only for LRFD in the current scope.",
            details={"field": "design_method", "chapter": chapter,
                     "design_method_received": method.value, "design_method_required": "LRFD"})
    return method


def validate_method_scope(case):
    """Public analysis scope; internal H1/H3 F1 conversion is not a F route."""
    require_case_method(case)
    if abs(case.loads.Mux) > 0 or abs(case.loads.Muy) > 0:
        require_case_method(case, chapter="F")
    if case.composite is not None:
        require_case_method(case, chapter="I")
