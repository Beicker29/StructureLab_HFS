from typing import Any, Dict, Optional


class SteelDesignError(Exception):
    """Base exception for steel design engine with structured context."""

    default_code = "STEEL_DESIGN_ERROR"

    def __init__(self, message: str, *, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code or self.default_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "code": self.code,
            "message": str(self),
            "details": self.details,
        }


class ValidationError(SteelDesignError):
    """Input validation error."""

    default_code = "VALIDATION_ERROR"


class SectionNotFoundError(SteelDesignError):
    """Raised when a section is not found in the repository."""

    default_code = "SECTION_NOT_FOUND"


class CatalogSchemaError(SteelDesignError):
    """Raised when catalog headers/rows are not parseable under strict policy."""

    default_code = "CATALOG_SCHEMA_ERROR"


class AmbiguousSectionError(SteelDesignError):
    """More than one catalog record has the requested identity."""

    default_code = "AMBIGUOUS_SECTION"


class RuleNotImplementedError(SteelDesignError):
    """Raised when a required AISC rule is not implemented in the engine."""

    default_code = "RULE_NOT_IMPLEMENTED"


class IncompleteSectionDataError(SteelDesignError):
    """Raised when a rule is applicable but required section properties are missing."""

    default_code = "INCOMPLETE_SECTION_DATA"
