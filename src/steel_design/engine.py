"""Axial design of one member: validate, find the section, run Chapter D or E, decide the status."""
from .domain.compression import compression_strength
from .domain.coverage import discharge, required_obligations
from .domain.tension import tension_strength
from .domain.validation import validate_case, validate_section
from .errors import IncompleteSectionDataError, RuleNotImplementedError, SectionNotFoundError
from .models import DesignResult, SteelCase, Status
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

    def run(self, case: SteelCase) -> DesignResult:
        """Pu > 0: compression (Chapter E); Pu < 0: tension (Chapter D)."""
        case = validate_case(case)
        section = self.section_for(case)
        chapter = "E" if case.Pu > 0 else "D"
        obligations = required_obligations(case, section)
        common = dict(section=section.name, family=section.type, design_method=case.design_method.value,
                      chapter=chapter, demand_kN=abs(case.Pu), obligations=obligations,
                      section_data=section.model_dump(mode="json", exclude_none=True))
        try:
            result = (compression_strength(case, section, catalog=self._catalog) if chapter == "E"
                      else tension_strength(case, section))
        except (RuleNotImplementedError, IncompleteSectionDataError) as exc:
            return DesignResult(**common, status=Status.INCOMPLETE, errors=[exc.to_dict()])
        unmet = discharge(obligations, section, result)
        violated = [r for r in result["requirements"] if not r["satisfied"]]
        capacity = result["available_kN"]
        ratio = abs(case.Pu) / capacity
        if unmet:
            status = Status.INCOMPLETE
        else:
            status = Status.PASS if ratio <= 1.0 and not violated else Status.FAIL
        errors = ([{"code": "UNMET_OBLIGATION", "id": o.id, "provision": o.provision} for o in unmet]
                  + [{"code": "REQUIREMENT_NOT_MET", **r} for r in violated])
        return DesignResult(**common, status=status, capacity_kN=capacity, ratio=ratio, errors=errors,
                            **{"compression" if chapter == "E" else "tension": result})
