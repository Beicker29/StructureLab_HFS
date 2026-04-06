import openpyxl
from typing import List, Dict, Any
from .models import Section

def load_sections_from_excel(filepath: str) -> List[Section]:
    """
    Loads steel sections from an Excel file and returns a list of Section models.
    """
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active
    
    sections = []
    
    # Extract headers
    headers = [cell.value for cell in ws[1]]
    
    # Iterate over rows starting from row 2
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]: # Skip empty rows
            continue
            
        row_data = dict(zip(headers, row))
        # Mapeo Inteligente del Tipo de Perfil basado en la nomenclatura
        shape_name = str(row_data.get("shape", "Unknown")).upper().strip()
        
        if shape_name.startswith("WT"):
            resolved_type = "WT"
        elif shape_name.startswith("W"):
            resolved_type = "W"
        elif shape_name.startswith("DBL_L") or shape_name.startswith("2L"):
            resolved_type = "DOUBLE_ANGLE"
        elif shape_name.startswith("L"):
            resolved_type = "SINGLE_ANGLE"
        elif "HSS" in shape_name and shape_name.count("X") == 2:
            resolved_type = "RECTANGULAR_HSS"
        elif "HSS" in shape_name:
            resolved_type = "CIRCULAR_HSS"
        else:
            resolved_type = "DOUBLE_ANGLE"  # Fallback a tu base inicial

        # Build Section object
        # Mapeando los nombres de encabezados del archivo original
        section = Section(
            name=shape_name,
            type=resolved_type,
            A=row_data.get("area [mm2]", 0.0),
            d=None,
            bf=None,
            tf=None,
            tw=None,
            Ix=row_data.get("Ix [mm4]", 0.0),
            Iy=row_data.get("Iy [mm4]", 0.0),
            Sx=row_data.get("Sx", 0.0),
            Sy=row_data.get("Sy [mm3]", 0.0),
            Zx=row_data.get("Zx", 0.0),
            Zy=row_data.get("Zy [mm3]", 0.0),
            rx=row_data.get("rx [mm]", 0.0),
            ry=row_data.get("ry [mm]", 0.0),
            J=row_data.get("J [mm4]", 0.0),
            Cw=row_data.get("Cw [mm6]", 0.0)
        )
        sections.append(section)
        
    return sections
