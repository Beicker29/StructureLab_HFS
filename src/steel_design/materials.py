"""Catalog of structural steels, data/Materiales.xlsx: name, Fy and Fu (MPa). A JSON input names its material here."""
from functools import lru_cache
from pathlib import Path

import openpyxl

from .errors import ValidationError

CATALOG = Path(__file__).resolve().parents[2] / "data" / "Materiales.xlsx"
_HEADERS = ("Material", "Fy (MPa)", "Fu (MPa)")


@lru_cache(maxsize=1)
def material_catalog() -> dict[str, dict]:
    sheet = openpyxl.load_workbook(CATALOG, data_only=True, read_only=True).worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    if tuple(next(rows)[:3]) != _HEADERS:
        raise ValidationError(f"{CATALOG.name} debe tener las columnas {', '.join(_HEADERS)}.", code="INVALID_MATERIAL_CATALOG")
    return {str(name).strip(): {"name": str(name).strip(), "Fy": float(fy), "Fu": float(fu)} for name, fy, fu in (r[:3] for r in rows) if name}


def material_by_name(name) -> dict:
    """Fy and Fu of one material of the catalog; JSON inputs give the name, never the values."""
    catalog = material_catalog()
    if not isinstance(name, str):
        raise ValidationError("material debe ser el nombre de un material de Materiales.xlsx; no indique Fy ni Fu.", code="INVALID_MATERIAL",
                              details={"available": sorted(catalog)})
    if name not in catalog:
        raise ValidationError(f"El material {name} no está en Materiales.xlsx.", code="UNKNOWN_MATERIAL", details={"available": sorted(catalog)})
    return catalog[name]
