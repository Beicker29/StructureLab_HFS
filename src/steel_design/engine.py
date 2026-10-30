"""Compression design of one member: validate, find the section, run Chapter E, decide the status."""
from .domain.compression import compression_strength
from .domain.coverage import discharge, required_obligations
from .domain.errors import IncompleteSectionDataError, RuleNotImplementedError, SectionNotFoundError
from .domain.validation import validate_case, validate_section
from .models import DesignResult, SteelCase, Status
from .sections.geometry import build_custom_section
from .sections.models import Section
from .sections.repository import SectionRepository


class SteelDesignEngine:
    def __init__(self, repository: SectionRepository):
        self.repository = repository

    def section_for(self, case: SteelCase) -> Section:
        if case.custom_section is not None:
            return validate_section(build_custom_section(case))
        section = self.repository.get(case.section_name)
        if section is None:
            raise SectionNotFoundError(f"Section {case.section_name} not found in the catalog.",
                                       details={"section": case.section_name})
        return validate_section(section)

    def run(self, case: SteelCase) -> DesignResult:
        case = validate_case(case)
        section = self.section_for(case)
        obligations = required_obligations(case, section)
        common = dict(section=section.name, family=section.type, design_method=case.design_method.value,
                      demand_kN=case.Pu, obligations=obligations)
        try:
            result = compression_strength(case, section)
        except (RuleNotImplementedError, IncompleteSectionDataError) as exc:
            return DesignResult(**common, status=Status.INCOMPLETE, errors=[exc.to_dict()])
        unmet = discharge(obligations, section, result)
        capacity = result["available_kN"]
        ratio = case.Pu / capacity
        if unmet:
            status = Status.INCOMPLETE
        else:
            status = Status.PASS if ratio <= 1.0 else Status.FAIL
        return DesignResult(**common, status=status, capacity_kN=capacity, ratio=ratio, compression=result,
                            errors=[{"code": "UNMET_OBLIGATION", "id": o.id, "provision": o.provision} for o in unmet])
