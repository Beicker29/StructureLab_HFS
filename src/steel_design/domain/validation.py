from ..models import SteelCase
from ..sections.models import Section
from pydantic import ValidationError as PydanticValidationError
from ..codes.aisc_360_22.axial_calc import NORMATIVE_E_MPA
from .errors import ValidationError

def validate_case(case: SteelCase):
    # Canonical local validation also covers mutated/model_copy/model_construct inputs.
    try:
        case = SteelCase.model_validate(case)
    except PydanticValidationError as exc:
        raise ValidationError("Invalid case input.", details={"fields": exc.errors(include_url=False, include_context=False, include_input=False)}) from exc
    if abs(case.material.E - NORMATIVE_E_MPA) > 1e-6:
        raise ValidationError(
            "Elastic modulus E must be 200000 MPa for normative Chapter E checks.",
            details={"E_received": case.material.E, "E_expected": NORMATIVE_E_MPA},
        )
    if case.loads.Pu < 0.0 and case.composite is None:
        if case.connection.An is None:
            raise ValidationError(
                "connection.An is required and must be > 0 for tension cases.",
                details={"required_field": "connection.An"},
            )
        if case.connection.U is None:
            raise ValidationError(
                "connection.U is required for tension cases.",
                details={"required_field": "connection.U"},
            )
    has_major_flexure = abs(case.loads.Mux) > 0.0
    has_minor_flexure = abs(case.loads.Muy) > 0.0
    if (has_major_flexure or has_minor_flexure) and case.design_method.value != "LRFD":
        raise ValidationError(
            "Chapter F flexural checks are implemented only for LRFD in the current scope.",
            details={"design_method_received": case.design_method.value, "design_method_required": "LRFD"},
        )
    if case.composite is not None:
        if case.design_method.value != "LRFD":
            raise ValidationError(
                "Chapter I composite checks are implemented only for LRFD in the current scope.",
                details={"design_method_received": case.design_method.value, "design_method_required": "LRFD"},
            )

        role = case.composite.role.value
        if role == "ENCASED_MEMBER":
            if case.composite.geometry.B is None:
                raise ValidationError(
                    "composite.geometry.B is required for ENCASED_MEMBER.",
                    details={"required_field": "composite.geometry.B"},
                )
            if case.composite.geometry.H is None:
                raise ValidationError(
                    "composite.geometry.H is required for ENCASED_MEMBER.",
                    details={"required_field": "composite.geometry.H"},
                )
            if case.composite.geometry.cover is None:
                raise ValidationError(
                    "composite.geometry.cover is required for ENCASED_MEMBER.",
                    details={"required_field": "composite.geometry.cover"},
                )
            if not case.composite.reinforcement.longitudinal_bars:
                raise ValidationError(
                    "composite.reinforcement.longitudinal_bars is required for ENCASED_MEMBER.",
                    details={"required_field": "composite.reinforcement.longitudinal_bars"},
                )
            if case.composite.reinforcement.transverse is None:
                raise ValidationError(
                    "composite.reinforcement.transverse is required for ENCASED_MEMBER.",
                    details={"required_field": "composite.reinforcement.transverse"},
                )

        if role == "COMPOSITE_BEAM":
            if case.composite.geometry.slab_effective_width is None:
                raise ValidationError(
                    "composite.geometry.slab_effective_width is required for COMPOSITE_BEAM.",
                    details={"required_field": "composite.geometry.slab_effective_width"},
                )
            if case.composite.geometry.slab_thickness is None:
                raise ValidationError(
                    "composite.geometry.slab_thickness is required for COMPOSITE_BEAM.",
                    details={"required_field": "composite.geometry.slab_thickness"},
                )

            if case.composite.geometry.deck_present is None:
                raise ValidationError("composite.geometry.deck_present must be explicit for COMPOSITE_BEAM.",
                                      details={"required_field": "composite.geometry.deck_present"})
        if role == "ENCASED_MEMBER":
            geometry = case.composite.geometry
            if 2 * geometry.cover >= min(geometry.B, geometry.H):
                raise ValidationError("Concrete cover must leave a positive interior dimension.",
                                      details={"field": "composite.geometry.cover", "B": geometry.B, "H": geometry.H, "cover": geometry.cover})
            for index, bar in enumerate(case.composite.reinforcement.longitudinal_bars):
                if (abs(bar.x) + bar.db / 2 > geometry.B / 2 or
                        abs(bar.y) + bar.db / 2 > geometry.H / 2):
                    raise ValidationError("Bar coordinate/diameter exceeds the declared concrete envelope.",
                                          details={"field": f"composite.reinforcement.longitudinal_bars.{index}", "x": bar.x, "y": bar.y, "db": bar.db})
    return case


def validate_section(section: Section) -> Section:
    """Validate a selected physical section, without selecting normative checks.

    Catalog records may retain zero placeholders for diagnosis. Those records
    cannot enter calculation. Missing properties remain None: rule-specific
    requirements and the known F-03 selection defect are not redefined here.
    Cw/Iw and signed offsets may legitimately be zero.
    """
    try:
        section = Section.model_validate(section)
    except PydanticValidationError as exc:
        raise ValidationError("Invalid section input.", details={"section": section.name,
                              "fields": exc.errors(include_url=False, include_context=False, include_input=False)}) from exc
    zero_fields = [name for name, value in section.model_dump().items()
                   if isinstance(value, (int, float)) and value == 0
                   and name not in {"cw", "iw", "x", "y", "eo", "tan_alpha"}]
    if zero_fields:
        raise ValidationError("Selected section contains zero physical properties; supply valid data.",
                              details={"section": section.name, "fields": zero_fields})
    if section.H is not None and section.H > 1:
        raise ValidationError("Section.H must satisfy 0 < H <= 1.", details={"section": section.name, "field": "H", "value": section.H})
    if section.od is not None:
        for name in ("t", "tdes"):
            value = getattr(section, name)
            if value is not None and 2 * value >= section.od:
                raise ValidationError("Tube thickness must leave a positive interior diameter.",
                                      details={"section": section.name, "field": name, "OD": section.od, "value": value})
    if section.d is not None and section.tf is not None and 2 * section.tf >= section.d:
        raise ValidationError("Flange thickness must leave a positive web depth.",
                              details={"section": section.name, "field": "tf", "d": section.d, "tf": section.tf})
    return section


def validate_case_section(case: SteelCase, section: Section) -> None:
    """Relationships requiring the selected section; no capacity evaluation."""
    if case.connection.An is not None and case.connection.An > section.area:
        raise ValidationError("Net area An cannot exceed gross area Ag.", details={
            "field": "connection.An", "section": section.name,
            "An": case.connection.An, "Ag": section.area})
    if case.composite is None:
        return
    role = case.composite.role.value
    required = []
    if case.loads.Pu > 0 or case.loads.Mux != 0 or case.loads.Muy != 0:
        required.extend(["ix", "iy"])
    if case.loads.Pu > 0:
        required.extend(["rx", "ry"])
    if case.loads.Mux != 0:
        required.extend(["sx", "zx"])
    if case.loads.Muy != 0:
        required.extend(["sy", "zy"])
    missing = [name for name in required if getattr(section, name) is None]
    if missing:
        raise ValidationError("Composite analysis requires explicit section properties.", details={
            "section": section.name, "role": role, "missing_fields": missing})
    if role == "ENCASED_MEMBER":
        geometry = case.composite.geometry
        if section.bf is None or section.d is None:
            raise ValidationError("Encased geometry requires steel bf and d.", details={
                "section": section.name, "required_fields": ["bf", "d"]})
        if geometry.B <= section.bf or geometry.H <= section.d:
            raise ValidationError("Steel core must fit inside the encased concrete envelope.", details={
                "section": section.name, "fields": ["composite.geometry.B", "composite.geometry.H"],
                "B": geometry.B, "H": geometry.H, "bf": section.bf, "d": section.d})
    if role == "FILLED_MEMBER":
        # Preserve existing dimension alternatives; do not normalize or derive new geometry.
        if section.tdes is None and section.t is None:
            raise ValidationError("Filled member requires explicit tdes or t.", details={
                "section": section.name, "required_fields": ["tdes or t"]})
        if section.type.upper() == "CIRCULAR_HSS" and section.od is None and section.d is None:
            raise ValidationError("Filled circular member requires OD or d.", details={
                "section": section.name, "required_fields": ["OD or d"]})
        if section.type.upper() == "RECTANGULAR_HSS" and (section.b is None or section.h is None):
            raise ValidationError("Filled rectangular member requires flat dimensions b and h.", details={
                "section": section.name, "required_fields": ["b", "h"]})
