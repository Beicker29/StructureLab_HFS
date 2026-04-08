import re
from typing import Dict, List, Optional

import openpyxl

from ..domain.errors import CatalogSchemaError
from .models import Section


def _normalize_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(header or "").strip().lower())


CANONICAL_HEADER_ALIASES = {
    "shape": {"shape", "name", "section", "sectionname", "designation"},
    "area": {"a", "ag", "area", "areamm2"},
    "ix": {"ix", "ixmm4"},
    "iy": {"iy", "iymm4"},
    "sx": {"sx", "sxmm3"},
    "sy": {"sy", "symm3"},
    "zx": {"zx", "zxmm3"},
    "zy": {"zy", "zymm3"},
    "rx": {"rx", "rxmm"},
    "ry": {"ry", "rymm"},
    "j": {"j", "jmm4"},
    "cw": {"cw", "cwmm6"},
}


def _build_header_index(headers: List[object]) -> Dict[str, int]:
    normalized_to_index = {_normalize_header(h): i for i, h in enumerate(headers) if h is not None}
    canonical_to_index: Dict[str, int] = {}

    for canonical, aliases in CANONICAL_HEADER_ALIASES.items():
        for alias in aliases:
            if alias in normalized_to_index:
                canonical_to_index[canonical] = normalized_to_index[alias]
                break

    missing_required = [k for k in ("shape", "area") if k not in canonical_to_index]
    if missing_required:
        raise CatalogSchemaError(
            "Catalog is missing required headers for strict loading.",
            details={"missing_headers": missing_required, "headers": [str(h) for h in headers]},
        )

    return canonical_to_index


def _coerce_float(
    value: object,
    *,
    field_name: str,
    section_name: str,
    required: bool,
    row_number: int,
) -> Optional[float]:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if required:
            raise CatalogSchemaError(
                "Required numeric value is missing in catalog row.",
                details={
                    "section": section_name,
                    "field": field_name,
                    "row_number": row_number,
                },
            )
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        raise CatalogSchemaError(
            "Catalog value cannot be parsed as float.",
            details={
                "section": section_name,
                "field": field_name,
                "value": value,
                "row_number": row_number,
            },
        )


def _resolve_profile_type(shape_name: str) -> str:
    normalized = shape_name.upper().strip()

    if normalized.startswith("WT"):
        return "WT"
    if normalized.startswith("W"):
        return "W"
    if normalized.startswith("DBL_L") or normalized.startswith("2L"):
        return "DOUBLE_ANGLE"
    if normalized.startswith("L"):
        return "SINGLE_ANGLE"

    is_tube = ("HSS" in normalized) or ("PTE" in normalized)
    if is_tube and normalized.count("X") >= 2:
        return "RECTANGULAR_HSS"
    if is_tube:
        return "CIRCULAR_HSS"

    raise CatalogSchemaError(
        "Cannot resolve section profile type from shape name.",
        details={"shape": shape_name},
    )


def _get_optional_float(
    row: tuple,
    header_index: Dict[str, int],
    canonical_key: str,
    section_name: str,
    row_number: int,
) -> Optional[float]:
    if canonical_key not in header_index:
        return None
    return _coerce_float(
        row[header_index[canonical_key]],
        field_name=canonical_key,
        section_name=section_name,
        required=False,
        row_number=row_number,
    )


def load_sections_from_excel(filepath: str) -> List[Section]:
    """
    Loads steel sections from an Excel file and returns a list of Section models.
    Strict mode: schema issues are raised as CatalogSchemaError.
    """
    workbook = openpyxl.load_workbook(filepath, data_only=True)
    sheet = workbook.active
    headers = [cell.value for cell in sheet[1]]
    header_index = _build_header_index(headers)

    sections: List[Section] = []
    for row_number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        shape_raw = row[header_index["shape"]]
        if shape_raw is None or str(shape_raw).strip() == "":
            continue

        section_name = str(shape_raw).strip().upper()
        section_type = _resolve_profile_type(section_name)

        area = _coerce_float(
            row[header_index["area"]],
            field_name="area",
            section_name=section_name,
            required=True,
            row_number=row_number,
        )

        section = Section(
            name=section_name,
            type=section_type,
            A=area,
            d=None,
            bf=None,
            tf=None,
            tw=None,
            Ix=_get_optional_float(row, header_index, "ix", section_name, row_number),
            Iy=_get_optional_float(row, header_index, "iy", section_name, row_number),
            Sx=_get_optional_float(row, header_index, "sx", section_name, row_number),
            Sy=_get_optional_float(row, header_index, "sy", section_name, row_number),
            Zx=_get_optional_float(row, header_index, "zx", section_name, row_number),
            Zy=_get_optional_float(row, header_index, "zy", section_name, row_number),
            rx=_get_optional_float(row, header_index, "rx", section_name, row_number),
            ry=_get_optional_float(row, header_index, "ry", section_name, row_number),
            J=_get_optional_float(row, header_index, "j", section_name, row_number),
            Cw=_get_optional_float(row, header_index, "cw", section_name, row_number),
        )
        sections.append(section)

    return sections
