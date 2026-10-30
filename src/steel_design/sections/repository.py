from typing import Dict, Optional, List

from ..errors import AmbiguousSectionError
from .identity import section_identity
from .models import Section


class SectionRepository:
    """Own snapshots of all records; only unique identities can be selected.

    load is additive, including repeated loads. No first/last/identical-record
    winner is inferred.
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
                "Identidad de sección ambigua: no se seleccionó ningún registro del catálogo.",
                details={
                    "requested_name": name,
                    "identity": identity,
                    "record_count": len(records),
                    "records": [record.model_dump(mode="json") for record in records],
                },
            )
        return records[0].model_copy(deep=True) if records else None
