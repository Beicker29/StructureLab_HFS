import math

from .models import CustomSectionType, SteelCase
from .results_model import EngineResult
from .sections.models import Section
from .sections.repository import SectionRepository
from .domain.validation import validate_case, validate_section, validate_case_section
from .domain.errors import RuleNotImplementedError, SectionNotFoundError, ValidationError
from .domain.routing.profile_router import ProfileRouter
from .domain.coverage import build_coverage_plan
from .domain.coverage_evidence import record_evaluation, record_selection_errors
from .domain.errors import IncompleteSectionDataError


def _build_custom_section(case: SteelCase) -> Section:
    custom = case.custom_section
    if custom is None:
        raise ValidationError("custom_section is required to build a custom section.")

    if custom.type == CustomSectionType.SOLID_CIRCULAR:
        diameter = custom.diameter or 0.0
        area = math.pi * (diameter**2) / 4.0
        inertia = math.pi * (diameter**4) / 64.0
        radius_of_gyration = diameter / 4.0
        elastic_modulus = math.pi * (diameter**3) / 32.0
        plastic_modulus = (diameter**3) / 6.0
        return Section(
            name=case.section_name,
            type=custom.type.value,
            A=area,
            OD=diameter,
            Ix=inertia,
            Iy=inertia,
            Sx=elastic_modulus,
            Sy=elastic_modulus,
            Zx=plastic_modulus,
            Zy=plastic_modulus,
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
    section_modulus_x = width * (height**2) / 6.0
    section_modulus_y = height * (width**2) / 6.0
    plastic_modulus_x = width * (height**2) / 4.0
    plastic_modulus_y = height * (width**2) / 4.0
    return Section(
        name=case.section_name,
        type=custom.type.value,
        A=area,
        h=height,
        b=width,
        Ix=inertia_x,
        Iy=inertia_y,
        Sx=section_modulus_x,
        Sy=section_modulus_y,
        Zx=plastic_modulus_x,
        Zy=plastic_modulus_y,
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
        case = validate_case(case)
        
        # 2. Fetch section
        if case.custom_section is not None:
            try:
                section = _build_custom_section(case)
            except (OverflowError, ZeroDivisionError) as exc:
                raise ValidationError("Custom dimensions exceed the supported floating-point range.",
                                      details={"field": "custom_section"}) from exc
        else:
            section = self.repository.get(case.section_name)
            if not section:
                raise SectionNotFoundError(f"Section {case.section_name} not found in database.")

        section = validate_section(section)
        validate_case_section(case, section)

        if case.loads.Pu < 0.0 and case.composite is None:
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
            abs(case.loads.Vu) > 0.0 or abs(case.loads.Vux) > 0.0 or abs(case.loads.Vuy) > 0.0
        ):
            raise ValidationError(
                "Solid custom sections currently do not support shear checks (Vu).",
                details={
                    "section": section.name,
                    "profile_type": section.type,
                    "Mux": case.loads.Mux,
                    "Muy": case.loads.Muy,
                    "Vu": case.loads.Vu,
                    "Vux": case.loads.Vux,
                    "Vuy": case.loads.Vuy,
                },
            )

        if (
            section.type.upper() == "SINGLE_ANGLE"
            and case.loads.Pu > 0
            and case.connection.angle_compression_mode is None
            and case.composite is None
        ):
            raise ValidationError(
                "angle_compression_mode is required for single-angle compression (E5).",
                details={"section": section.name, "required_field": "connection.angle_compression_mode"},
            )

        if abs(case.loads.Tu) > 0.0 and section.type.upper() not in {"RECTANGULAR_HSS", "CIRCULAR_HSS"} and case.composite is None:
            raise RuleNotImplementedError(
                "Torsion is implemented only for round and rectangular HSS in current scope (H3.1/H3.2).",
                details={"section": section.name, "profile_type": section.type, "requested_clause": "H3.3"},
            )
            
        # Expected obligations are constructed BEFORE and independently of routing.
        coverage = build_coverage_plan(case, section)
        # 3. Get rules dynamically
        selection_errors = []
        rules = self.router.get_rules(case, section, selection_errors)
        record_selection_errors(coverage, selection_errors)
        
        # 4. Run checks
        checks = []
        for rule in rules:
            try:
                result = rule.check(case, section)
            except (RuleNotImplementedError, IncompleteSectionDataError) as exc:
                coverage.evaluation_errors.append({"implementation": type(rule).__name__, "error": exc.to_dict()})
                continue
            checks.append(result)
            record_evaluation(coverage, rule, result, len(checks) - 1, case, section)

        return EngineResult(checks=checks, coverage=coverage)
