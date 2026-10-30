from pydantic import ValidationError as PydanticValidationError

from ..models import SteelCase
from ..sections.models import Section
from ..errors import ValidationError


def validate_case(case: SteelCase) -> SteelCase:
    """Revalidate (also after model_copy/mutation) and enforce E = 200000 MPa (S22 E3)."""
    try:
        case = SteelCase.model_validate(case)
    except PydanticValidationError as exc:
        raise ValidationError("Invalid case input.", details={"fields": exc.errors(
            include_url=False, include_context=False, include_input=False)}) from exc
    if abs(case.material.E - 200000.0) > 1e-6:
        raise ValidationError("Chapter E defines E = 200000 MPa.", details={"E_received": case.material.E})
    return case


def validate_section(section: Section) -> Section:
    """Reject physically impossible records; missing properties stay None (never assumed zero)."""
    try:
        section = Section.model_validate(section)
    except PydanticValidationError as exc:
        raise ValidationError("Invalid section input.", details={"section": section.name, "fields": exc.errors(
            include_url=False, include_context=False, include_input=False)}) from exc
    zero_fields = [name for name, value in section.model_dump().items()
                   if isinstance(value, (int, float)) and value == 0
                   and name != "cw"]  # Cw = 0 is exact for round HSS
    if zero_fields:
        raise ValidationError("Selected section contains zero physical properties.",
                              details={"section": section.name, "fields": zero_fields})
    if section.H is not None and section.H > 1:
        raise ValidationError("Section.H must satisfy 0 < H <= 1.", details={"section": section.name, "value": section.H})
    if section.od is not None and any(t is not None and 2 * t >= section.od for t in (section.t, section.tdes)):
        raise ValidationError("Tube thickness must leave a positive interior diameter.", details={"section": section.name})
    if section.d is not None and section.tf is not None and 2 * section.tf >= section.d:
        raise ValidationError("Flange thickness must leave a positive web depth.", details={"section": section.name})
    return section
