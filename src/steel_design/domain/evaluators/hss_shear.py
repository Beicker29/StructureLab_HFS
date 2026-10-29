"""Single unrounded G4/G5 capacity source for standalone G and H3 interaction.

No cross-axis fallback, nominal thickness fallback, or inference of shear
length from column unbraced lengths. Only demanded directions need evaluation.
"""
import math

from ..design_methods import require_case_method
from ...codes.aisc_360_22 import shear_calc
from ..actions import shear_trace
from ..errors import IncompleteSectionDataError, RuleNotImplementedError
from ...tracing import emit_step, quantity


def require_section_values(section, fields, reference):
    missing = [name for name in fields if not isinstance(getattr(section, name), (int, float))
               or isinstance(getattr(section, name), bool)
               or not math.isfinite(getattr(section, name)) or getattr(section, name) <= 0]
    if missing:
        raise IncompleteSectionDataError("Explicit positive section properties are required; no geometric fallback.",
            details={"section": section.name, "missing_fields": missing, "reference": reference})
    return tuple(getattr(section, name) for name in fields)


def round_hss_dimensions(section):
    diameter, thickness = require_section_values(section, ("od", "tdes"), "B4.2; G5/H3.1")
    if 2 * thickness >= diameter:
        raise IncompleteSectionDataError("Round HSS must have a positive interior diameter.",
                                         details={"D_mm": diameter, "t_mm": thickness})
    return diameter, thickness


def evaluate_hss_shear(case, section, axis):
    require_case_method(case)
    trace = shear_trace(case, axis)
    fy, e = case.material.Fy, case.material.E
    profile = section.type.upper()
    inputs = {"Fy_mpa": fy, "E_mpa": e, **trace}
    if profile == "RECTANGULAR_HSS":
        width, t = require_section_values(section, ("h" if axis == "x" else "b", "tdes"), "G4-1")
        cv = shear_calc.calculate_cv2_g2_2(h_over_tw=width / t, fy_mpa=fy, e_mpa=e, kv=5.0)
        area = 2 * width * t
        nominal = shear_calc.calculate_nominal_shear_strength(fy_mpa=fy, aw_mm2=area, cv=cv["Cv2"])
        inputs.update(h_resisting_mm=width, t_used_mm=t, Aw_mm2=area, h_over_t=width / t, kv=5.0)
        intermediate = {**cv, "Vn_N": nominal, "Aw_expression": "2*h_resisting*tdes"}
        clause = "G4-1"
    elif profile == "CIRCULAR_HSS":
        diameter, t = round_hss_dimensions(section)
        (area,) = require_section_values(section, ("area",), "G5-1")
        # Lx/Ly are column buckling lengths, not G5's maximum-to-zero shear distance.
        fcr = shear_calc.calculate_round_hss_fcr(e_mpa=e, fy_mpa=fy, lv_mm=None,
                                               diameter_mm=diameter, thickness_mm=t)
        if fcr["Fcr_mpa"] is None:
            raise IncompleteSectionDataError("G5 requires Lv (maximum-to-zero shear distance); Lx/Ly are not Lv.",
                details={"section": section.name, "component": trace["input_component"],
                         "reference": "G5-2a/b", "required": "Independently established Lv; input not yet represented",
                         "D_mm": diameter, "tdes_mm": t, "Fcr_G5_2b_mpa": fcr["fcr_g5_2b_mpa"]})
        nominal = shear_calc.calculate_round_hss_nominal_shear_strength(fcr_mpa=fcr["Fcr_mpa"], ag_mm2=area)
        inputs.update(D_mm=diameter, t_mm=t, Ag_mm2=area, Lv_mm=None)
        intermediate = {**fcr, "Fcr_branch": fcr["branch"], "Vn_N": nominal}
        clause = "G5-1"
    else:
        raise RuleNotImplementedError("Shared HSS shear evaluation is limited to rectangular/round HSS.")
    available = shear_calc.calculate_available_shear_strength(vn_n=nominal,
        design_method=case.design_method.value, phi_v=.90, omega_v=1.67)
    emit_step(producer=__name__+":evaluate_hss_shear", limit_state="HSS_directional_shear",
        branch=intermediate["branch"], reference=clause, equation=None, expression=None, axis=axis,
        inputs=(quantity("signed_demand", trace["signed_demand_kN"], "kN", "case.loads."+trace["input_component"]),
                quantity("Fy", fy, "MPa", "case.material.Fy"), quantity("E", e, "MPa", "case.material.E")),
        intermediates=(quantity("Vn", nominal, "N"),), outputs=(quantity("Vc", available, "kN"),),
        assumptions=(trace["axis_convention"], "Force direction: "+trace["force_direction"],
                     "Vu is a scalar alias in the x bending plane, never a vector resultant."),
        unknowns=("Branch label is emitted by coefficient evaluator; equation mapping and geometry derivation are not expanded here.",))
    return {"clause": clause, "capacity_kN": available, "inputs": inputs,
            "intermediate": intermediate, "design_factor": {"design_method": case.design_method.value,
                "phi_v": .90, "omega_v": 1.67, "capacity_expression": "phi_v*Vn (LRFD) or Vn/omega_v (ASD)"}}
