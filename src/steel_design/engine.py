from typing import List
from .models import SteelCase, CheckStatus
from .results_model import EngineResult
from .sections.repository import SectionRepository
from .domain.validation import validate_case
from .domain.errors import SectionNotFoundError, ValidationError
from .domain.routing.profile_router import ProfileRouter

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
        section = self.repository.get(case.section_name)
        if not section:
            raise SectionNotFoundError(f"Section {case.section_name} not found in database.")

        if case.connection.Ae is not None and case.connection.Ae > section.area:
            raise ValidationError(
                "Effective net area Ae cannot exceed gross area Ag.",
                details={
                    "section": section.name,
                    "Ae": case.connection.Ae,
                    "Ag": section.area,
                },
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
