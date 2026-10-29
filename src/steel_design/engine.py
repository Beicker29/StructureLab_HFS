from .sections.geometry import build_custom_section as _build_custom_section
from .models import SteelCase
from .results_model import EngineResult
from .sections.models import Section
from .sections.repository import SectionRepository
from .domain.validation import validate_case, validate_section, validate_case_section
from .domain.errors import RuleNotImplementedError, SectionNotFoundError, ValidationError
from .domain.routing.profile_router import ProfileRouter
from .domain.coverage import build_coverage_plan
from .domain.coverage_evidence import record_evaluation, record_selection_errors
from .domain.errors import IncompleteSectionDataError
from .tracing import record_analysis



class SteelDesignEngine:
    def __init__(self, repository: SectionRepository):
        self.repository = repository
        self.router = ProfileRouter()

    def run(self, case: SteelCase) -> EngineResult:
        """Compatibility entry point; the context pipeline owns all validation."""
        return self.run_with_context(case)[2]

    def run_with_context(self, case: SteelCase) -> tuple[SteelCase, Section, EngineResult]:
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

        # Expected obligations are constructed BEFORE and independently of routing.
        coverage = build_coverage_plan(case, section)
        # HFS-013: absent G/H resistance is a pending component, not permission
        # to discard independent checks or to report complete coverage.
        if case.composite is None:
            unsupported = []
            if case.loads.Tu and section.type.upper() not in {"RECTANGULAR_HSS", "CIRCULAR_HSS"}:
                unsupported.append(("Tu", "H3.3 torsional stress analysis is not implemented for this family."))
            if section.type.upper() in {"SOLID_CIRCULAR", "SOLID_RECTANGULAR"}:
                unsupported.extend((component, "Solid-member shear resistance is not implemented; G5 is for hollow tubes.")
                    for component in ("Vu", "Vux", "Vuy") if getattr(case.loads, component))
            for component, reason in unsupported:
                error = RuleNotImplementedError(reason, details={"section": section.name, "component": component})
                coverage.evaluation_errors.append({"implementation": "SteelDesignEngine", "error": error.to_dict()})
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

        result = EngineResult(checks=checks, coverage=coverage)
        record_analysis(result)
        return case, section, result
