"""Compression design of one member: validate, find the section, run Chapter E, decide the status."""
from .domain.compression import compression_strength
from .domain.coverage import discharge, required_obligations
from .domain.errors import IncompleteSectionDataError, RuleNotImplementedError, SectionNotFoundError
from .domain.validation import validate_case, validate_section
from .models import DesignResult, SteelCase, Status
from .sections.geometry import build_custom_section
from .sections.identity import double_angle_label
from .sections.models import Section
from .sections.repository import SectionRepository


class SteelDesignEngine:
    def __init__(self, repository: SectionRepository):
        self.repository = repository

    def _catalog(self, name: str) -> Section:
        section = self.repository.get(name)
        if section is None:
            raise SectionNotFoundError(f"Section {name} not found in the catalog.", details={"section": name})
        return validate_section(section)

    def section_for(self, case: SteelCase) -> Section:
        if case.custom_section is not None:
            return validate_section(build_custom_section(case))
        return self._catalog(case.section_name)

    def run(self, case: SteelCase) -> DesignResult:
        case = validate_case(case)
        section = self.section_for(case)
        obligations = required_obligations(case, section)
        common = dict(section=section.name, family=section.type, design_method=case.design_method.value,
                      demand_kN=case.Pu, obligations=obligations)
        extra = {}
        if section.type.upper() == "DOUBLE_ANGLE":
            # AISC_Manual_Label: separation suffix -> separators; none -> continuous contact.
            label = double_angle_label(section.name)
            extra = {"component": self._catalog(label["component"]), "in_contact": label["in_contact"]}
        try:
            result = compression_strength(case, section, **extra)
        except (RuleNotImplementedError, IncompleteSectionDataError) as exc:
            return DesignResult(**common, status=Status.INCOMPLETE, errors=[exc.to_dict()])
        unmet = discharge(obligations, section, result)
        violated = [r for r in result["requirements"] if not r["satisfied"]]
        capacity = result["available_kN"]
        ratio = case.Pu / capacity
        if unmet:
            status = Status.INCOMPLETE
        else:
            status = Status.PASS if ratio <= 1.0 and not violated else Status.FAIL
        errors = ([{"code": "UNMET_OBLIGATION", "id": o.id, "provision": o.provision} for o in unmet]
                  + [{"code": "REQUIREMENT_NOT_MET", **r} for r in violated])
        return DesignResult(**common, status=status, capacity_kN=capacity, ratio=ratio, compression=result,
                            errors=errors)
