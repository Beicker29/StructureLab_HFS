"""Compression preconditions, shared by E checks and axial consumers in H/I.

This is a precondition, not a selector or a resistance calculation. See
docs/audit/hfs031r0/domains.md. A permitted local mode does not discharge E1.
"""
import math

from ...codes.aisc_360_22 import axial_calc
from ...models import SteelCase
from ...sections.models import Section
from ..errors import IncompleteSectionDataError, RuleNotImplementedError


def compression_classification(case: SteelCase, section: Section) -> dict:
    return axial_calc.classify_compression_elements(
        section.type,
        {name: getattr(section, name) for name in (
            "bf_2tf_ratio", "b_t_ratio", "b_tdes_ratio", "h_tw_ratio",
            "h_tdes_ratio", "d_t_ratio")},
        case.material.E, case.material.Fy,
    )


def requires_torsional_mode(case: SteelCase, section: Section) -> bool:
    """E4 scope, shared by selection and capacity evaluation.

    Ordinary closed PTE: E1.1 E3/E7. Preserve E4's explicit special-length
    condition, comparing unbraced (not K-adjusted) lengths. Offset restraints
    cannot silently become an ordinary case. Open I/channel modes are retained.
    """
    if section.type.upper() in {"RECTANGULAR_HSS", "CIRCULAR_HSS"}:
        return (case.lengths.Lz > min(case.lengths.Lx, case.lengths.Ly)
                or case.factors.xa != 0 or case.factors.ya != 0)
    if section.type.upper() in {"SOLID_RECTANGULAR", "SOLID_CIRCULAR"}:
        return False
    if section.type.upper() == "SINGLE_ANGLE":
        ratio = section.b_t_ratio
        return ratio is None or ratio > .71*math.sqrt(case.material.E/case.material.Fy)
    return True


def require_compression_domain(case: SteelCase, section: Section, *, reference: str) -> None:
    """Reject an unjustified capacity before computing it, including direct calls.

Callers decide whether compression is active; a capacity requested by an
interaction must pass this guard even when that interaction has no axial load.
No missing Cw, principal axis, classification or connection is synthesized.
"""
    context = {"rule_id": reference, "section": section.name,
               "profile_type": section.type, "design_method": case.design_method.value,
               "milestone": "HFS-031R"}

    def blocked(reason, findings, **details):
        raise RuleNotImplementedError(
            reason, code="COMPRESSION_DOMAIN_BLOCKED",
            details={**context, "findings": findings, **details},
        )

    def incomplete(reason, **details):
        raise IncompleteSectionDataError(
            reason, code="COMPRESSION_DATA_INCOMPLETE",
            details={**context, "findings": ["F-48"], **details},
        )

    if reference == "E5":
        blocked("E5 conditions, principal axes and effective-slenderness branches are not supported.",
                ["F-36"], required="Connection conditions, configuration, connected leg and principal axes")
    if reference not in {"E3", "E4", "E7"}:
        raise ValueError(f"Unknown compression domain: {reference}")

    family = section.type.upper()
    if family == "SINGLE_ANGLE":
        blocked("Single-angle compression lacks justified principal-axis and E5/E4 conditions.", ["F-36"])
    if family == "DOUBLE_ANGLE":
        blocked("Double-angle contact, principal modes and E6 assembly conditions are not represented.",
                ["F-38", "F-48"])
    if family not in {"W", "CHANNEL", "RECTANGULAR_HSS", "CIRCULAR_HSS", "SOLID_RECTANGULAR", "SOLID_CIRCULAR"}:
        blocked("Compression family has no justified domain in this evaluator.", ["F-48"])
    torsion_required = reference == "E4" or (reference == "E7" and requires_torsional_mode(case, section))
    if torsion_required:
        if family not in {"W", "CHANNEL", "RECTANGULAR_HSS", "CIRCULAR_HSS"}:
            blocked("E4 coupling and symmetry-axis selection are not supported for this family.", ["F-46"])
        if case.factors.xa != 0 or case.factors.ya != 0:
            blocked("E4 displaced bracing requires E4-10/11/12 or analysis; offsets cannot be ignored.",
                    ["F-47"], xa=case.factors.xa, ya=case.factors.ya)
        if family != "CHANNEL" and ((section.H is not None and section.H != 1) or (section.eo is not None and section.eo != 0)):
            blocked("Supplied shear-center data contradict the supported doubly symmetric E4 domain.",
                    ["F-46"], H=section.H, eo=section.eo)

    values = {"section.area": section.area, "section.rx": section.rx, "section.ry": section.ry,
              "material.E": case.material.E, "material.Fy": case.material.Fy,
              "factors.Kx": case.factors.Kx, "factors.Ky": case.factors.Ky,
              "lengths.Lx": case.lengths.Lx, "lengths.Ly": case.lengths.Ly}
    if torsion_required:
        values.update({"section.j": section.j, "factors.Kz": case.factors.Kz, "lengths.Lz": case.lengths.Lz})
        if family == "CHANNEL":
            # E4-3 requires explicit coupling and polar radius about the shear
            # center. Neither centroidal radius nor H=1 is a missing-data fill.
            values.update({"section.ro": section.ro, "section.H": section.H})
        elif section.ro is None:
            values.update({"section.ix": section.ix, "section.iy": section.iy})
        else:
            values["section.ro"] = section.ro
    invalid = [name for name, value in values.items()
               if isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(value) or value <= 0]
    if torsion_required and (section.cw is None or not math.isfinite(section.cw) or section.cw < 0):
        invalid.append("section.cw")  # Explicit zero is meaningful; absence is not zero.
    if torsion_required and family == "CHANNEL" and section.H is not None and section.H > 1:
        invalid.append("section.H")
    if invalid:
        incomplete("Compression requires complete finite physical data for every evaluated mode.", fields=invalid)

    # Preserve the existing modulus policy also at the directly callable boundary.
    if abs(case.material.E - axial_calc.NORMATIVE_E_MPA) > 1e-6:
        incomplete("Chapter E requires E=200000 MPa.", fields=["material.E"])
    if family not in {"SOLID_RECTANGULAR", "SOLID_CIRCULAR"}:
        classification = compression_classification(case, section)
        if classification["overall"] == "unknown":
            incomplete("All compression elements must have a known classification.", classification=classification)
        if classification["is_slender"] and reference != "E7":
            blocked("Slender compression requires E7 Fn*Ae; gross-area E3/E4 cannot substitute for it.",
                    ["F-35"], classification=classification)
        if reference == "E7" and not classification["is_slender"]:
            blocked("E7 requires a section with slender compression elements.", ["F-35"], classification=classification)
    if reference == "E7":
        geometry = {
            "W": ("tf", "tw"), "CHANNEL": ("tf", "tw"),
            "RECTANGULAR_HSS": ("tdes",), "CIRCULAR_HSS": ("tdes", "od"),
        }.get(family)
        if geometry is None:
            blocked("E7 plate geometry is not implemented for this family.", ["F-35"])
        missing = ["section."+name for name in geometry
                   if getattr(section, name) is None or not math.isfinite(getattr(section, name))
                   or getattr(section, name) <= 0]
        if missing:
            incomplete("E7 needs physical thicknesses and complete B4 plate widths/ratios.", fields=missing)
