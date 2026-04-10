import math

from .models import CheckStatus, CustomSectionType, SteelCase
from .results_model import EngineResult
from .sections.models import Section
from .sections.repository import SectionRepository
from .domain.validation import validate_case
from .domain.errors import SectionNotFoundError, ValidationError
from .domain.routing.profile_router import ProfileRouter


def _build_custom_section(case: SteelCase) -> Section:
    custom = case.custom_section
    if custom is None:
        raise ValidationError("custom_section is required to build a custom section.")

    if custom.type == CustomSectionType.SOLID_CIRCULAR:
        diameter = custom.diameter or 0.0
        area = math.pi * (diameter**2) / 4.0
        inertia = math.pi * (diameter**4) / 64.0
        radius_of_gyration = diameter / 4.0
        return Section(
            name=case.section_name,
            type=custom.type.value,
            A=area,
            OD=diameter,
            Ix=inertia,
            Iy=inertia,
            rx=radius_of_gyration,
            ry=radius_of_gyration,
        )

    height = custom.H or 0.0
    width = custom.B or 0.0
    area = width * height
    inertia_x = width * (height**3) / 12.0
    inertia_y = height * (width**3) / 12.0
    radius_of_gyration_x = math.sqrt(inertia_x / area) if area > 0.0 else 0.0
    radius_of_gyration_y = math.sqrt(inertia_y / area) if area > 0.0 else 0.0
    return Section(
        name=case.section_name,
        type=custom.type.value,
        A=area,
        h=height,
        b=width,
        Ix=inertia_x,
        Iy=inertia_y,
        rx=radius_of_gyration_x,
        ry=radius_of_gyration_y,
    )


class SteelDesignEngine:
    def __init__(self, repository: SectionRepository):
        self.repository = repository
        self.router = ProfileRouter()

    def run(self, case: SteelCase) -> EngineResult:
        """
        Executes the main pipeline:
        1. Validate
        2. Fetch section
        3. Run checks
        4. Aggregate
        """
        # 1. Validation
        validate_case(case)
        
        # 2. Fetch section
        if case.custom_section is not None:
            section = _build_custom_section(case)
        else:
            section = self.repository.get(case.section_name)
            if not section:
                raise SectionNotFoundError(f"Section {case.section_name} not found in database.")

        if case.loads.Pu < 0.0:
            an = case.connection.An or 0.0
            u_factor = case.connection.U or 0.0
            ae = an * u_factor
            if ae > section.area:
                raise ValidationError(
                    "Effective net area Ae = U*An cannot exceed gross area Ag.",
                    details={
                        "section": section.name,
                        "An": an,
                        "U": u_factor,
                        "Ae": ae,
                        "Ag": section.area,
                    },
                )

        if section.type.upper() in {"SOLID_CIRCULAR", "SOLID_RECTANGULAR"} and (
            abs(case.loads.Mux) > 0.0 or abs(case.loads.Muy) > 0.0 or abs(case.loads.Vu) > 0.0
        ):
            raise ValidationError(
                "Solid custom sections currently support axial-only design (Pu).",
                details={
                    "section": section.name,
                    "profile_type": section.type,
                    "Mux": case.loads.Mux,
                    "Muy": case.loads.Muy,
                    "Vu": case.loads.Vu,
                },
            )

        if section.type.upper() == "SINGLE_ANGLE" and case.loads.Pu > 0 and case.connection.angle_compression_mode is None:
            raise ValidationError(
                "angle_compression_mode is required for single-angle compression (E5).",
                details={"section": section.name, "required_field": "connection.angle_compression_mode"},
            )
            
        # 3. Get rules dynamically
        rules = self.router.get_rules(case, section)
        
        # 4. Run checks
        checks = []
        for rule in rules:
            result = rule.check(case, section)
            checks.append(result)
            
        # 5. Aggregate overall status
        overall_status = CheckStatus.PASS
        for c in checks:
            if c.status == CheckStatus.FAIL:
                overall_status = CheckStatus.FAIL
                break
                
        return EngineResult(checks=checks, status=overall_status)
