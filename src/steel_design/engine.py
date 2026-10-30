"""Design of one member for one LRFD load combination: one check per required strength, then the status.

Pu > 0: compression (Chapter E); Pu < 0: tension (Chapter D); Mux, Muy: flexure (Chapter F).
More than one nonzero demand needs the interaction of Chapter H (not yet available).
"""
from .domain.compression import compression_strength
from .domain.coverage import discharge, flexure_obligations, required_obligations
from .domain.flexure import flexure_strength
from .domain.tension import tension_strength
from .domain.validation import section_inconsistencies, validate_case, validate_section
from .errors import IncompleteSectionDataError, RuleNotImplementedError, SectionNotFoundError
from .models import Check, DesignResult, SteelCase, Status
from .sections.geometry import build_custom_section
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
        capacity = result["available_kN"] if unit == "kN" else result["available_kNm"]
        ratio = demand / capacity
        if violated or (not unmet and ratio > 1.0):
            status = Status.FAIL
        else:
            status = Status.INCOMPLETE if unmet else Status.PASS
        errors = ([{"code": "UNMET_OBLIGATION", "id": o.id, "provision": o.provision} for o in unmet]
                  + [{"code": "REQUIREMENT_NOT_MET", **r} for r in violated])
        return Check(**common, status=status, capacity=capacity, ratio=ratio, result=result, errors=errors)

    def run(self, case: SteelCase) -> DesignResult:
        case = validate_case(case)
        section = self.section_for(case)
        inconsistent = section_inconsistencies(section)
        checks = []
        if case.Pu:
            chapter = "E" if case.Pu > 0 else "D"
            compute = ((lambda: compression_strength(case, section, catalog=self._catalog)) if chapter == "E"
                       else (lambda: tension_strength(case, section)))
            checks.append(self._check("axial", chapter, abs(case.Pu), "kN", required_obligations(case, section),
                                      compute, section, inconsistent))
        for axis, moment in (("x", case.Mux), ("y", case.Muy)):
            if moment:
                checks.append(self._check(f"flexure_{axis}", "F", abs(moment), "kN·m", flexure_obligations(section, axis),
                                          lambda axis=axis: flexure_strength(case, section, axis), section, inconsistent))
        pending = len(checks) > 1
        statuses = {c.status for c in checks}
        if Status.FAIL in statuses:
            status = Status.FAIL                      # a known failure is never hidden by incompleteness
        elif Status.INCOMPLETE in statuses or pending:
            status = Status.INCOMPLETE
        else:
            status = Status.PASS
        return DesignResult(section=section.name, family=section.type, status=status, checks=checks,
                            interaction_pending=pending,
                            section_data=section.model_dump(mode="json", exclude_none=True))
