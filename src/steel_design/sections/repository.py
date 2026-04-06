from typing import Dict, Optional, List
from .models import Section

class SectionRepository:
    """
    In-memory storage and retrieval for Section profiles.
    """
    def __init__(self):
        self._sections: Dict[str, Section] = {}
        
    def load(self, sections: List[Section]):
        """Load a list of sections into the repository."""
        for section in sections:
            # Store in uppercase for case-insensitive lookup
            self._sections[section.name.upper()] = section
            
    def get(self, name: str) -> Optional[Section]:
        """Retrieve a section by name."""
        return self._sections.get(name.upper())

    def get_all(self) -> List[Section]:
        """Retrieve all sections."""
        return list(self._sections.values())
