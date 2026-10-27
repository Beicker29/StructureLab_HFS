"""Implementation-to-obligation evidence, not a source of expected requirements.

Only the explicitly tested D2 solid-tie domain is qualified for discharge in v1.
Other links describe partial execution; matching a clause/name never suffices.
"""
import math

from .rules import axial_rules as axial
from .rules import flexure_rule as flexure
from .rules import shear_rules as shear
from .rules import composite_rules as composite
from .rules import combined_hss_rules as combined
from .rules.tension_rule import TensionRule, TensionRuptureRule
from ..results_model import CoverageStatus, ExecutedEvaluation


_CLAIMS = {
    TensionRule: ("N04.yielding.Pu",),
    TensionRuptureRule: ("N04.rupture.Pu",),
    axial.AxialE3Rule: ("N06.buckling.x", "N06.buckling.y"),
    axial.AxialE4Rule: ("N07.torsional_buckling",),
    axial.AxialE5Rule: ("N08.angle_alternative",),
    axial.AxialE7Rule: ("N10.effective_area",),
    combined.CombinedH1HssRule: ("N29.interaction",),
    combined.HssTorsionH3_1Rule: ("H.torsion.Tu",),
    combined.HssCombinedH3_2Rule: ("N30.interaction",),
    composite.CompositeI1Rule: ("I.eligibility",),
    composite.CompositeI2EncasedCompressionRule: ("I.axial.Pu",),
    composite.CompositeI2EncasedTensionRule: ("I.axial.Pu",),
    composite.CompositeI2FilledCompressionRule: ("I.axial.Pu",),
    composite.CompositeI2FilledTensionRule: ("I.axial.Pu",),
    composite.CompositeI5CombinedRule: ("I.interaction",),
    # I3_3/I3_4 are ratio checks; I3_1a/b/c transfer checks. None claims moment.
    composite.CompositeI3_1aRule: ("I.transfer",),
    composite.CompositeI3_1bRule: ("I.transfer",),
    composite.CompositeI3_1cRule: ("I.transfer",),
}

# Concrete classes/axes/states, not string matching against result labels.
for class_name, state, component in [
    ("FlexureF2YieldRule", "yielding", "Mux"), ("FlexureF2LtbRule", "lateral_torsional_buckling", "Mux"),
    ("FlexureF3YieldRule", "yielding", "Mux"), ("FlexureF3LtbRule", "lateral_torsional_buckling", "Mux"),
    ("FlexureF3FlbRule", "local_buckling", "Mux"),
    ("FlexureF4CompressionYieldRule", "compression_flange_yielding", "Mux"), ("FlexureF4TensionYieldRule", "tension_flange_yielding", "Mux"),
    ("FlexureF4LtbRule", "lateral_torsional_buckling", "Mux"), ("FlexureF4FlbRule", "local_buckling", "Mux"),
    ("FlexureF5CompressionYieldRule", "compression_flange_yielding", "Mux"), ("FlexureF5TensionYieldRule", "tension_flange_yielding", "Mux"),
    ("FlexureF5LtbRule", "lateral_torsional_buckling", "Mux"), ("FlexureF5FlbRule", "local_buckling", "Mux"),
    ("FlexureF6YieldRule", "yielding", "Muy"), ("FlexureF6FlbRule", "local_buckling", "Muy"),
]:
    _CLAIMS[getattr(flexure, class_name)] = (f"F.{state}.{component}",)
for number, members in {
    7: {"Yield": "yielding", "Flange": "flange_local_buckling", "Web": "web_local_buckling", "Ltb": "lateral_torsional_buckling"},
    8: {"Yield": "yielding", "LocalBuckling": "local_buckling"},
    10: {"Yield": "yielding", "LegBuckling": "local_buckling", "Ltb": "lateral_torsional_buckling"},
    11: {"Yield": "yielding", "Ltb": "lateral_torsional_buckling"},
}.items():
    for member, state in members.items():
        for axis, component in (("Mx", "Mux"), ("My", "Muy")):
            _CLAIMS[getattr(flexure, f"FlexureF{number}{member}{axis}Rule")] = (f"F.{state}.{component}",)
for cls in (shear.ShearG2VxRule, shear.ShearG3VxRule, shear.ShearG4VxRule, shear.ShearG5VxRule):
    _CLAIMS[cls] = ("G.shear.Vu", "G.shear.Vux")  # legacy route, not a physical axis transformation
for cls in (shear.ShearG3VyRule, shear.ShearG4VyRule, shear.ShearG5VyRule, shear.ShearG6VyRule):
    _CLAIMS[cls] = ("G.shear.Vuy",)
for cls in (composite.CompositeI4_1aEncasedRule, composite.CompositeI4_1bEncasedRule,
            composite.CompositeI4_1cEncasedRule, composite.CompositeI4_1EncasedGoverningRule,
            composite.CompositeI4_1FilledRule, composite.CompositeI4_3BeamDeckSteelOnlyRule):
    _CLAIMS[cls] = ("I.shear.Vu", "I.shear.Vux", "I.shear.Vuy")  # partial, never qualified by this map


def record_evaluation(report, rule, result, index, case, section):
    implementation = type(rule)
    claims = _CLAIMS.get(implementation, ())
    report.executions.append(ExecutedEvaluation(
        check_index=index, implementation=f"{implementation.__module__}.{implementation.__qualname__}",
        obligation_ids=list(claims)))
    basis = next(o for o in report.obligations if o.id == "scope.basis")
    for obligation in report.obligations:
        if obligation.id not in claims:
            continue
        obligation.executed_checks.append(index)
        if implementation not in (TensionRule, TensionRuptureRule) or basis.status != CoverageStatus.EVALUATED:
            continue
        # Defend against nominal placeholders, mismatched components or relabelled
        # outputs. Capacity equations are NOT recomputed by the coverage gate.
        clause = "D2-1" if implementation is TensionRule else "D2-2"
        memory = (result.details or {}).get("memory", {})
        inputs = memory.get("inputs", {})
        expected_inputs = ({"Fy_mpa": case.material.Fy, "Ag_mm2": section.area}
                           if implementation is TensionRule else
                           {"Fu_mpa": case.material.Fu, "An_mm2": case.connection.An,
                            "U_factor": case.connection.U,
                            "Ae_mm2": case.connection.An * case.connection.U})
        coherent = (result.clause == clause and memory.get("clause") == clause
                    and result.demand == abs(case.loads.Pu) > 0
                    and inputs.get("Pu_tension_kn") == result.demand
                    and all(inputs.get(k) == v for k, v in expected_inputs.items())
                    and math.isfinite(result.capacity) and result.capacity > 0
                    and memory.get("capacity_kn") == result.capacity
                    and result.status.value == ("PASS" if result.demand <= result.capacity else "FAIL")
                    and math.isfinite(result.dcr) and result.dcr >= 0)
        if coherent:
            obligation.status = CoverageStatus.EVALUATED
            obligation.reason = "Qualified D2 solid-tie evaluation, matching demand, properties and trace; external scope remains explicit."
            obligation.required = []
            obligation.accepted_checks.append(index)
        else:
            obligation.reason = "Executed output does not represent the required D2 demand/properties/trace; no coverage credit."
