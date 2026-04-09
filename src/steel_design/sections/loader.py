import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import openpyxl

from ..domain.errors import CatalogSchemaError
from .models import Section


PLACEHOLDER_VALUES = {
    "",
    "-",
    "–",
    "—",
    "N/A",
    "NA",
    "NONE",
    "NULL",
    "#DIV/0!",
    "#N/A",
    "#VALUE!",
    "#REF!",
    "#NUM!",
    "#NAME?",
    "#NULL!",
}

UNIT_SCALE_BY_VARIABLE = {
    "Ix": 1e6,
    "Iy": 1e6,
    "Iz": 1e6,
    "Iw": 1e6,
    "Sw1": 1e6,
    "Sw2": 1e6,
    "Sw3": 1e6,
    "Zx": 1e3,
    "Zy": 1e3,
    "Sx": 1e3,
    "Sy": 1e3,
    "Sz": 1e3,
    "SwA": 1e3,
    "SwB": 1e3,
    "SwC": 1e3,
    "SzA": 1e3,
    "SzB": 1e3,
    "SzC": 1e3,
    "Qf": 1e3,
    "Qw": 1e3,
    "C": 1e3,
    "J": 1e3,
    "Cw": 1e9,
}

FIELD_HEADER_CANDIDATES: Dict[str, Sequence[str]] = {
    "shape": ("shape", "name", "section", "section_name", "designation"),
    "area": ("A", "area [mm2]", "area", "Ag"),
    "d": ("d",),
    "h": ("h",),
    "bf": ("bf",),
    "b": ("b",),
    "od": ("OD",),
    "id": ("ID",),
    "tf": ("tf",),
    "t": ("t", "tnom"),
    "tdes": ("tdes",),
    "tw": ("tw",),
    "ix": ("Ix", "Ix [mm4]"),
    "iy": ("Iy", "Iy [mm4]"),
    "sx": ("Sx", "Sx [mm3]"),
    "sy": ("Sy", "Sy [mm3]"),
    "zx": ("Zx", "Zx [mm3]"),
    "zy": ("Zy", "Zy [mm3]"),
    "rx": ("rx", "rx [mm]"),
    "ry": ("ry", "ry [mm]"),
    "j": ("J", "J [mm4]"),
    "cw": ("Cw", "Cw [mm6]"),
    "ro": ("ro", "ro [mm]"),
    "H": ("H",),
    "x": ("x", "Xc [mm]"),
    "y": ("y", "Yc [mm]"),
    "eo": ("eo",),
    "bf_2tf_ratio": ("bf/2tf",),
    "b_t_ratio": ("b/t",),
    "b_tdes_ratio": ("b/tdes",),
    "h_tw_ratio": ("h/tw",),
    "h_tdes_ratio": ("h/tdes",),
    "d_t_ratio": ("D/t",),
}


def _normalize_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


def _clean_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.upper() in PLACEHOLDER_VALUES:
            return None
        return stripped
    return value


def _build_header_indexes(headers: Iterable[object]) -> Tuple[Dict[str, int], Dict[str, int]]:
    exact: Dict[str, int] = {}
    normalized: Dict[str, int] = {}
    for idx, raw in enumerate(headers):
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            exact[text] = idx
            normalized[_normalize_header(text)] = idx
    return exact, normalized


def _find_column_index(
    exact_headers: Dict[str, int],
    normalized_headers: Dict[str, int],
    candidates: Sequence[str],
) -> Optional[int]:
    for candidate in candidates:
        if candidate in exact_headers:
            return exact_headers[candidate]
    for candidate in candidates:
        normalized = _normalize_header(candidate)
        if normalized in normalized_headers:
            return normalized_headers[normalized]
    return None


def _resolve_profile_type(shape_name: str, sheet_name: str) -> str:
    normalized_shape = shape_name.upper().strip()
    normalized_sheet = sheet_name.upper().strip()

    if normalized_sheet == "C":
        return "CHANNEL"
    if normalized_sheet == "2L":
        return "DOUBLE_ANGLE"
    if normalized_sheet == "L":
        return "SINGLE_ANGLE"
    if normalized_sheet == "PTE_RECT":
        return "RECTANGULAR_HSS"
    if normalized_sheet == "PTE_RED":
        return "CIRCULAR_HSS"

    if normalized_shape.startswith("W"):
        return "W"
    if normalized_shape.startswith("DBL_L") or normalized_shape.startswith("2L"):
        return "DOUBLE_ANGLE"
    if normalized_shape.startswith("L"):
        return "SINGLE_ANGLE"
    if normalized_shape.startswith("C"):
        return "CHANNEL"
    if "HSS" in normalized_shape or "PTE" in normalized_shape:
        if normalized_shape.count("X") >= 2:
            return "RECTANGULAR_HSS"
        return "CIRCULAR_HSS"

    raise CatalogSchemaError(
        "Cannot resolve section profile type from shape name.",
        details={"shape": shape_name, "sheet": sheet_name},
    )


def _coerce_float(
    raw_value: object,
    *,
    section_name: str,
    field_name: str,
    row_number: int,
    required: bool,
) -> Optional[float]:
    value = _clean_value(raw_value)
    if value is None:
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

    if isinstance(value, (int, float)):
        return float(value)

    try:
        return float(str(value).replace(",", ""))
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


def _scaled_float(
    row: tuple,
    *,
    column_index: Optional[int],
    section_name: str,
    field_name: str,
    row_number: int,
    required: bool,
    source_header: Optional[str],
) -> Optional[float]:
    if column_index is None:
        if required:
            raise CatalogSchemaError(
                "Required column is missing from catalog.",
                details={"section": section_name, "field": field_name},
            )
        return None

    value = _coerce_float(
        row[column_index],
        section_name=section_name,
        field_name=field_name,
        row_number=row_number,
        required=required,
    )
    if value is None:
        return None

    scale = 1.0
    if source_header is not None:
        source_header_clean = source_header.strip()
        scale = UNIT_SCALE_BY_VARIABLE.get(source_header_clean, 1.0)
    return value * scale


def load_sections_from_excel(filepath: str) -> List[Section]:
    """
    Loads sections from all profile sheets in sections.xlsx.
    Strict mode: schema and parsing issues raise CatalogSchemaError.
    """
    workbook = openpyxl.load_workbook(filepath, data_only=True)
    profile_sheets = [sheet for sheet in workbook.sheetnames if sheet.strip().upper() != "README"]
    if not profile_sheets:
        raise CatalogSchemaError(
            "No profile sheets found in catalog workbook.",
            details={"workbook": filepath, "sheetnames": workbook.sheetnames},
        )

    sections: List[Section] = []
    for sheet_name in profile_sheets:
        sheet = workbook[sheet_name]
        headers = [cell.value for cell in sheet[1]]
        exact_headers, normalized_headers = _build_header_indexes(headers)

        required_columns = {
            key: _find_column_index(exact_headers, normalized_headers, candidates)
            for key, candidates in FIELD_HEADER_CANDIDATES.items()
        }

        if required_columns["shape"] is None or required_columns["area"] is None:
            raise CatalogSchemaError(
                "Catalog sheet is missing required columns (shape/area).",
                details={"sheet": sheet_name, "headers": [str(h) for h in headers]},
            )

        for row_number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            shape_index = required_columns["shape"]
            raw_shape = _clean_value(row[shape_index]) if shape_index is not None else None
            if raw_shape is None:
                continue

            section_name = str(raw_shape).upper()
            # WT profiles are intentionally excluded from this repository scope.
            if section_name.startswith("WT"):
                continue
            section_type = _resolve_profile_type(section_name, sheet_name)

            field_values: Dict[str, Optional[float]] = {}
            for field_name, column_index in required_columns.items():
                if field_name == "shape":
                    continue
                header_name = headers[column_index] if column_index is not None else None
                field_values[field_name] = _scaled_float(
                    row,
                    column_index=column_index,
                    section_name=section_name,
                    field_name=field_name,
                    row_number=row_number,
                    required=(field_name == "area"),
                    source_header=str(header_name) if header_name is not None else None,
                )

            # Derive ratios that can be obtained from geometric properties when missing in source rows.
            if (field_values["bf_2tf_ratio"] is None) and (field_values["bf"] is not None) and (field_values["tf"] not in (None, 0.0)):
                field_values["bf_2tf_ratio"] = field_values["bf"] / (2.0 * field_values["tf"])
            if (field_values["b_t_ratio"] is None) and (field_values["b"] is not None) and (field_values["t"] not in (None, 0.0)):
                field_values["b_t_ratio"] = field_values["b"] / field_values["t"]
            if (field_values["b_tdes_ratio"] is None) and (field_values["b"] is not None) and (field_values["tdes"] not in (None, 0.0)):
                field_values["b_tdes_ratio"] = field_values["b"] / field_values["tdes"]
            if (field_values["h_tw_ratio"] is None) and (field_values["h"] is not None) and (field_values["tw"] not in (None, 0.0)):
                field_values["h_tw_ratio"] = field_values["h"] / field_values["tw"]
            if (field_values["h_tdes_ratio"] is None) and (field_values["h"] is not None) and (field_values["tdes"] not in (None, 0.0)):
                field_values["h_tdes_ratio"] = field_values["h"] / field_values["tdes"]
            if field_values["d_t_ratio"] is None:
                diameter = field_values["id"] if field_values["id"] not in (None, 0.0) else field_values["od"]
                if (diameter is not None) and (field_values["tdes"] not in (None, 0.0)):
                    field_values["d_t_ratio"] = diameter / field_values["tdes"]
                elif (diameter is not None) and (field_values["t"] not in (None, 0.0)):
                    field_values["d_t_ratio"] = diameter / field_values["t"]

            section = Section(
                name=section_name,
                type=section_type,
                A=field_values["area"],
                d=field_values["d"],
                h=field_values["h"],
                bf=field_values["bf"],
                b=field_values["b"],
                OD=field_values["od"],
                ID=field_values["id"],
                tf=field_values["tf"],
                t=field_values["t"],
                tdes=field_values["tdes"],
                tw=field_values["tw"],
                Ix=field_values["ix"],
                Iy=field_values["iy"],
                Sx=field_values["sx"],
                Sy=field_values["sy"],
                Zx=field_values["zx"],
                Zy=field_values["zy"],
                rx=field_values["rx"],
                ry=field_values["ry"],
                J=field_values["j"],
                Cw=field_values["cw"],
                ro=field_values["ro"],
                H=field_values["H"],
                x=field_values["x"],
                y=field_values["y"],
                eo=field_values["eo"],
                **{
                    "bf/2tf": field_values["bf_2tf_ratio"],
                    "b/t": field_values["b_t_ratio"],
                    "b/tdes": field_values["b_tdes_ratio"],
                    "h/tw": field_values["h_tw_ratio"],
                    "h/tdes": field_values["h_tdes_ratio"],
                    "D/t": field_values["d_t_ratio"],
                },
            )
            sections.append(section)

    return sections

