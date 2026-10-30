from pydantic import ValidationError as PydanticValidationError

from ..models import SteelCase
from ..sections.models import Section
from ..errors import ValidationError


def validate_case(case: SteelCase) -> SteelCase:
    """Revalidate (also after model_copy/mutation); compression requires E = 200000 MPa (S22 E3)."""
    try:
        case = SteelCase.model_validate(case)
    except PydanticValidationError as exc:
        raise ValidationError("Entrada del caso no válida.", details={"fields": exc.errors(
            include_url=False, include_context=False, include_input=False)}) from exc
    if case.Pu > 0 and abs(case.material.E - 200000.0) > 1e-6:
        raise ValidationError("El Capítulo E define E = 200000 MPa.", details={"E_received": case.material.E})
    return case


def validate_section(section: Section) -> Section:
    """Reject physically impossible records; missing properties stay None (never assumed zero)."""
    try:
        section = Section.model_validate(section)
    except PydanticValidationError as exc:
        raise ValidationError("Sección no válida.", details={"section": section.name, "fields": exc.errors(
            include_url=False, include_context=False, include_input=False)}) from exc
    zero_fields = [name for name, value in section.model_dump().items()
                   if isinstance(value, (int, float)) and value == 0
                   and name != "cw"]  # Cw = 0 is exact for round HSS
    if zero_fields:
        raise ValidationError("La sección seleccionada tiene propiedades físicas nulas.",
                              details={"section": section.name, "fields": zero_fields})
    if section.H is not None and section.H > 1:
        raise ValidationError("H de la sección debe cumplir 0 < H ≤ 1.", details={"section": section.name, "value": section.H})
    if section.od is not None and any(t is not None and 2 * t >= section.od for t in (section.t, section.tdes)):
        raise ValidationError("El espesor del tubo debe dejar un diámetro interior positivo.", details={"section": section.name})
    if section.d is not None and section.tf is not None and 2 * section.tf >= section.d:
        raise ValidationError("El espesor del ala debe dejar una altura de alma positiva.", details={"section": section.name})
    return section
