from typing import Dict, Optional, List

from ..domain.errors import AmbiguousSectionError
from .identity import section_identity
from .models import Section


class SectionRepository:
    """Own snapshots of all records; only unique identities can be selected.

    load is additive, including repeated loads. No first/last/identical-record
    winner is inferred. get_all/get_duplicates are diagnostic, not selection.
    """

    def __init__(self):
        self._sections: Dict[str, List[Section]] = {}

    def load(self, sections: List[Section]):
        # Validate the entire batch before changing the index. Deep snapshots
        # prevent caller mutation from changing an identity or its evidence.
        batch = []
        for section in sections:
            record = Section.model_validate(section).model_copy(deep=True)
            batch.append((section_identity(record.name), record))
        for identity, record in batch:
            self._sections.setdefault(identity, []).append(record)

    def get(self, name: str) -> Optional[Section]:
        identity = section_identity(name)
        records = self._sections.get(identity, [])
        if len(records) > 1:
            raise AmbiguousSectionError(
                "Section identity is ambiguous; no catalog record was selected.",
                details={
                    "requested_name": name,
                    "identity": identity,
                    "record_count": len(records),
                    "records": [record.model_dump(mode="json") for record in records],
                },
            )
        return records[0].model_copy(deep=True) if records else None

    def get_all(self) -> List[Section]:
        """All records, including ambiguous/invalid physical data, for diagnosis.

        This is deliberately not a list of selectable or certified sections.
        Use get(name) for selection, then the engine's physical validation.
        """
        return [record.model_copy(deep=True) for records in self._sections.values() for record in records]

    def get_duplicates(self) -> Dict[str, List[Section]]:
        """Ambiguous identities and every candidate, without discarding evidence."""
        return {identity: [record.model_copy(deep=True) for record in records]
                for identity, records in self._sections.items() if len(records) > 1}
