"""Design of one member for one LRFD load combination: one check per required strength, their interaction, status.

Pu > 0: compression (Chapter E); Pu < 0: tension (Chapter D); Mux, Muy (and Mw, Mz for single
angles about their principal axes): flexure (Chapter F); Vux, Vuy: shear (Chapter G). Axial force
and flexure acting together, or flexure about two axes, add the interaction check (Chapter H).
case.composite sends each demand to Chapter I, which uses Chapters E, F and G where it refers to them.
"""
from .domain.composite import (composite_anchor, composite_compression, composite_flexure, composite_i5, composite_method2,
                               composite_shear, composite_tension, composite_wall_interaction)
from .domain.compression import compression_strength
from .domain.coverage import (composite_obligations, discharge, flexure_obligations, interaction_obligations,
                              required_obligations, shear_obligations)
from .domain.flexure import flexure_strength
from .domain.interaction import COMBINED, amplified_cb_case, combined_strength, tension_cb_factor
from .domain.shear import shear_strength
from .domain.tension import tension_strength
from .domain.validation import section_inconsistencies, validate_case, validate_section
from .errors import IncompleteSectionDataError, RuleNotImplementedError, SectionNotFoundError
from .models import Check, DesignResult, Obligation, SteelCase, Status
from .sections.geometry import build_custom_section, build_wall_section
from .sections.models import Section
from .sections.repository import SectionRepository


class SteelDesignEngine:
    def __init__(self, repository: SectionRepository):
        self.repository = repository

    def _catalog(self, name: str) -> Section:
        section = self.repository.get(name)
        if section is None:
            raise SectionNotFoundError(f"No se encontró la sección {name} en el catálogo.", details={"section": name})
        return validate_section(section)

    def section_for(self, case: SteelCase) -> Section:
        if case.custom_section is not None:
            return validate_section(build_custom_section(case))
        if case.composite is not None and case.composite.kind == "wall":
            return validate_section(build_wall_section(case))
        return self._catalog(case.section_name)

    def _check(self, check_id, chapter, demand, unit, obligations, compute, section, inconsistent) -> Check:
        common = dict(id=check_id, chapter=chapter, demand=demand, unit=unit, obligations=obligations)
        if inconsistent:
            return Check(**common, status=Status.INCOMPLETE, errors=[{
                "code": "CATALOG_DATA_INCONSISTENT", "message": "Datos del catálogo incoherentes con su definición; "
                "revise el perfil antes de calcular.", "details": {"section": section.name, "issues": inconsistent}}])
        try:
            result = compute()
        except (RuleNotImplementedError, IncompleteSectionDataError) as exc:
            return Check(**common, status=Status.INCOMPLETE, errors=[exc.to_dict()])
        unmet = discharge(obligations, section, result)
        violated = [r for r in result["requirements"] if not r["satisfied"]]
        capacity = {"kN": result.get("available_kN"), "kN·m": result.get("available_kNm"), "–": 1.0}[unit]
        if unit == "–":
            common["demand"] = demand = result["ratio"]
        ratio = demand / capacity
        if violated or (not unmet and ratio > 1.0):
            status = Status.FAIL
        else:
            status = Status.INCOMPLETE if unmet else Status.PASS
        errors = ([{"code": "UNMET_OBLIGATION", "id": o.id, "provision": o.provision} for o in unmet]
                  + [{"code": "REQUIREMENT_NOT_MET", **r} for r in violated])
        return Check(**common, status=status, capacity=capacity, ratio=ratio, result=result, errors=errors)

    def _flexure_case(self, case: SteelCase, section: Section) -> tuple[SteelCase, dict | None]:
        """H1.2: Cb amplified by axial tension when the user asks for it."""
        if not (case.Pu < 0 and case.flexure and case.flexure.tension_cb_amplification):
            return case, None
        try:
            factor = tension_cb_factor(case, section)
        except IncompleteSectionDataError as exc:
            return case, {"applies": False, "reason": str(exc)}
        return (amplified_cb_case(case, factor) if factor["applies"] else case), factor

    def run(self, case: SteelCase) -> DesignResult:
        case = validate_case(case)
        section = self.section_for(case)
        inconsistent = section_inconsistencies(section)
        checks = []
        if case.composite:
            return self._result(section, self._composite_checks(case, section, inconsistent))
        if case.Pu:
            chapter = "E" if case.Pu > 0 else "D"
            compute = ((lambda: compression_strength(case, section, catalog=self._catalog)) if chapter == "E"
                       else (lambda: tension_strength(case, section)))
            checks.append(self._check("axial", chapter, abs(case.Pu), "kN", required_obligations(case, section),
                                      compute, section, inconsistent))
        flexure_case, cb_factor = self._flexure_case(case, section)
        for axis, moment in (("x", case.Mux), ("y", case.Muy), ("w", case.Mw), ("z", case.Mz)):
            if moment:
                check = self._check(
                    f"flexure_{axis}", "F", abs(moment), "kN·m", flexure_obligations(section, axis),
                    lambda axis=axis: flexure_strength(flexure_case, section, axis, catalog=self._catalog),
                    section, inconsistent)
                if cb_factor and check.result:
                    check.result["notes"].append(_cb_note(cb_factor))
                    check.result["inputs"]["H1_2_Cb_factor"] = cb_factor.get("factor")
                checks.append(check)
        for axis, shear in (("x", case.Vux), ("y", case.Vuy)):
            if shear:
                checks.append(self._check(f"shear_{axis}", "G", abs(shear), "kN", shear_obligations(section, axis),
                                          lambda axis=axis: shear_strength(case, section, axis),
                                          section, inconsistent))
        combined = [c for c in checks if c.id in COMBINED]
        if len(combined) > 1:
            checks.append(self._check("interaction", "H", 0.0, "–", interaction_obligations(case, section),
                                      lambda: combined_strength(case, section, combined), section, []))
        return self._result(section, checks)

    def _composite_checks(self, case: SteelCase, section: Section, inconsistent) -> list[Check]:
        """Chapter I: negative flexure of a beam is Chapter F (I3.2b); steel-only shear is Chapter G (I4.1(a), I4.3)."""
        checks = []
        kind = case.composite.kind
        if case.Pu:
            compute = ((lambda: composite_compression(case, section, lambda: compression_strength(
                case, section, catalog=self._catalog))) if case.Pu > 0 else (lambda: composite_tension(case, section)))
            checks.append(self._check("axial", "I", abs(case.Pu), "kN", composite_obligations(case, "axial"), compute,
                                      section, inconsistent))
        flexure_case, _ = self._flexure_case(case, section)
        for axis, moment in (("x", case.Mux), ("y", case.Muy), ("w", case.Mw), ("z", case.Mz)):
            if moment:
                steel = lambda axis=axis: flexure_strength(flexure_case, section, axis, catalog=self._catalog)  # noqa: E731
                negative = kind == "beam" and case.composite.beam.moment == "negative" and axis == "x"
                obligations = flexure_obligations(section, axis) if negative else composite_obligations(case, "flexure")
                checks.append(self._check(
                    f"flexure_{axis}", "F" if negative else "I", abs(moment), "kN·m", obligations,
                    lambda axis=axis, steel=steel: composite_flexure(flexure_case, section, axis, steel),
                    section, inconsistent))
        for axis, shear in (("x", case.Vux), ("y", case.Vuy)):
            if shear:
                steel = lambda axis=axis: shear_strength(case, section, axis)  # noqa: E731
                chapter_i = kind in {"filled", "wall"}
                obligations = composite_obligations(case, "shear") if chapter_i else shear_obligations(section, axis)
                checks.append(self._check(
                    f"shear_{axis}", "I" if chapter_i else "G", abs(shear), "kN", obligations,
                    lambda axis=axis, steel=steel: composite_shear(case, section, axis, steel), section, inconsistent))
        combined = [c for c in checks if c.id in COMBINED]
        if len(combined) > 1:
            method = "wall" if kind == "wall" else case.composite.interaction
            if method == "H1":
                checks.append(self._check("interaction", "H", 0.0, "–", interaction_obligations(case, section),
                                          lambda: combined_strength(case, section, combined), section, []))
            else:
                mode, provision, compute = {
                    "I5": ("I5", "I5(b)", composite_i5), "M2": ("M2", "Commentary I5", composite_method2),
                    "M2S": ("M2", "Commentary I5", composite_method2), "wall": ("I5c", "I5(c)", composite_wall_interaction)}[method]
                obligations = [Obligation(id=mode, provision=provision, reason="Interacción de fuerza axial y flexión.")]
                checks.append(self._check("interaction", "I", 0.0, "–", obligations,
                                          lambda: compute(case, section, combined), section, []))
        if case.composite.anchor:
            obligations = [Obligation(id="V" if case.composite.anchor.type == "channel" else "Q", provision="I8.3",
                                      reason="Resistencia de un anclaje de componente.")]
            checks.append(self._check("anchor", "I", 0.0, "–", obligations, lambda: composite_anchor(case, section),
                                      section, []))
        return checks

    def _result(self, section: Section, checks: list[Check]) -> DesignResult:
        statuses = {c.status for c in checks}
        if Status.FAIL in statuses:
            status = Status.FAIL                      # a known failure is never hidden by incompleteness
        elif Status.INCOMPLETE in statuses:
            status = Status.INCOMPLETE
        else:
            status = Status.PASS
        return DesignResult(section=section.name, family=section.type, status=status, checks=checks,
                            section_data=section.model_dump(mode="json", exclude_none=True))


def _cb_note(factor: dict) -> str:
    if not factor["applies"]:
        return f"H1.2 no aplicado: {factor['reason']}"
    return (f"H1.2: Cb = {factor['Cb_user']:g} · √(1 + Pr/Pey) = {factor['Cb']:.3f} "
            f"(Pey = {factor['Pey_N'] / 1000:.1f} kN, H1-2).")
