from enum import Enum
from typing import List, Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from .models import CheckResult, CheckStatus
from .domain.errors import ValidationError


class AnalysisStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"


class CoverageStatus(str, Enum):
    EVALUATED = "EVALUATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING = "PENDING"


class CoverageObligation(BaseModel):
    id: str
    normative_ids: List[str]
    limit_state: str
    component: str
    condition: str
    applicability: Literal["TRUE", "FALSE", "UNKNOWN"] = "TRUE"
    status: CoverageStatus = CoverageStatus.PENDING
    reason: str
    required: List[str] = Field(default_factory=list)
    alternatives: List[str] = Field(default_factory=list)
    selected_alternative: str | None = None
    executed_checks: List[int] = Field(default_factory=list)
    accepted_checks: List[int] = Field(default_factory=list)
    resistance: bool = True


class ExecutedEvaluation(BaseModel):
    check_index: int
    implementation: str
    obligation_ids: List[str] = Field(default_factory=list)


class CoverageReport(BaseModel):
    version: Literal["HFS-010-v1"] = "HFS-010-v1"
    source: str = "docs/normative/hfs002-applicability.md (S22 local; errata reconciliation pending)"
    declared_scope: str = "Member resistance for every supplied demand component; no global AISC certification"
    supported_complete_domain: str = "Ordinary prismatic custom solid in concentric axial tension, with explicit external evidence"
    method: str
    section_name: str
    profile_type: str
    scope_evidence: dict = Field(default_factory=dict)
    evaluation_context: str = "One supplied member/load case; no position, combination or construction-stage envelope is inferred"
    demand_components: dict[str, float]
    obligations: List[CoverageObligation]
    executions: List[ExecutedEvaluation] = Field(default_factory=list)
    evaluation_errors: List[dict] = Field(default_factory=list)
    external_responsibilities: List[str] = Field(default_factory=lambda: [
        "N01/N03: global analysis, combinations, material qualification and stability are supplied externally",
        "N35: connections including block shear, serviceability, fatigue, fire, fabrication and other regulations are not certified",
        "N33: D1/E2 User Note slenderness recommendations are not resistance obligations",
        "F-28: January 2025 / September 2026 AISC errata remain unreconciled with S22 local",
    ])

    @computed_field
    @property
    def complete(self) -> bool:
        return (bool(self.obligations) and not self.evaluation_errors
                and all((o.status == CoverageStatus.NOT_APPLICABLE and o.applicability == "FALSE")
                        or (o.status == CoverageStatus.EVALUATED and o.applicability == "TRUE"
                            and (not o.resistance or o.accepted_checks)) for o in self.obligations)
                and any(o.resistance and o.status == CoverageStatus.EVALUATED and o.accepted_checks
                        for o in self.obligations))


class EngineResult(BaseModel):
    checks: List[CheckResult]
    status: AnalysisStatus = AnalysisStatus.INCOMPLETE
    coverage: CoverageReport | None = None

    @computed_field
    @property
    def known_failures(self) -> List[int]:
        """Zero-based indices; incompleteness never hides known failures."""
        return [i for i, check in enumerate(self.checks) if check.status == CheckStatus.FAIL]

    @model_validator(mode="after")
    def aggregate(self):
        covered = self.coverage is not None and self.coverage.complete
        if covered:
            covered = all(0 <= index < len(self.checks)
                          for obligation in self.coverage.obligations
                          for index in obligation.accepted_checks)
        if not covered or not self.checks:
            self.status = AnalysisStatus.INCOMPLETE
        else:
            self.status = AnalysisStatus.FAIL if self.known_failures else AnalysisStatus.PASS
        return self


def aggregate_case_statuses(statuses: List[AnalysisStatus]) -> AnalysisStatus:
    """Aggregate actual cases; an empty bundle has no compliance result."""
    if not statuses:
        raise ValidationError(
            "A case bundle must contain at least one case.", code="EMPTY_CASE_BUNDLE",
            details={"field": "cases", "minimum_items": 1, "received_items": 0},
        )
    if AnalysisStatus.INCOMPLETE in statuses:
        return AnalysisStatus.INCOMPLETE
    return AnalysisStatus.FAIL if AnalysisStatus.FAIL in statuses else AnalysisStatus.PASS
