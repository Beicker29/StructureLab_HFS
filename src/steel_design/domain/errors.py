class SteelDesignError(Exception):
    """Base exception for steel design engine."""
    pass

class ValidationError(SteelDesignError):
    """Input validation error."""
    pass

class SectionNotFoundError(SteelDesignError):
    """Raised when a section is not found in the repository."""
    pass
