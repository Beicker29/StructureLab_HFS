"""Chapter D for one member: tensile yielding (D2-1) and tensile rupture (D2-2, D3-1).

An (B4.3b) and U (Table D3.1) are user data. Both limit states are always
evaluated; the governing one is the lowest available strength of each method,
because their resistance factors differ (D2). Formulas live in codes/aisc_360_22/tension.py.
"""
import math

from ..codes.aisc_360_22 import tension as eq
from ..errors import IncompleteSectionDataError, RuleNotImplementedError
from ..models import SteelCase
from ..sections.models import Section

_LIMITATIONS = (
    "An (B4.3b) y U (Tabla D3.1) son datos del usuario; el programa no verifica la disposición de agujeros ni la conexión.",
    "La rotura por bloque de cortante (J4.3) y la resistencia de los elementos de conexión (J4.1) quedan fuera de este cálculo.",
    "Miembros con pasador (D5) y barras de ojo (D6) no están cubiertos.",
)


def _incomplete(reason, section, fields):
    raise IncompleteSectionDataError(reason, code="TENSION_DATA_INCOMPLETE",
                                     details={"section": section.name, "profile_type": section.type, "fields": fields})


def least_radius(section: Section) -> float | None:
    """Least radius of gyration of the section (rz for single angles)."""
    radii = [r for r in (section.rx, section.ry, section.rz if section.type.upper() == "SINGLE_ANGLE" else None) if r]
    return min(radii) if radii else None


def tension_strength(case: SteelCase, section: Section) -> dict:
    """Nominal and available tensile strength of one member (Chapter D)."""
    method = case.design_method.value
    if case.tension is None:
        _incomplete("La tracción requiere tension: An (B4.3b) y U (Tabla D3.1).", section, ["tension.An", "tension.U"])
    if case.material.Fu is None:
        _incomplete("La rotura en tracción (D2-2) requiere Fu.", section, ["material.Fu"])
    ag, an, u = section.area, case.tension.An, case.tension.U
    if not (isinstance(ag, (int, float)) and math.isfinite(ag) and ag > 0):
        _incomplete("La tracción requiere el área bruta Ag.", section, ["section.area"])
    if an > ag:
        raise RuleNotImplementedError("El área neta An no puede superar el área bruta Ag (B4.3b).",
                                      code="TENSION_DOMAIN_BLOCKED",
                                      details={"section": section.name, "An_mm2": an, "Ag_mm2": ag})

    yielding = eq.yielding_strength(Fy=case.material.Fy, Ag=ag)
    net = eq.effective_net_area(An=an, U=u)
    rupture = eq.rupture_strength(Fu=case.material.Fu, Ae=net["Ae_mm2"])
    modes = {
        "TY": {"limit_state": "tensile_yielding", "provision": "D2(a)", "area_basis": "Ag", "area_mm2": ag,
               "stress_mpa": case.material.Fy, "Pn_equation": yielding["equation"], "Pn_kN": yielding["Pn_N"] / 1000.0,
               "available_kN": eq.available_strength(yielding["Pn_N"], "yielding")},
        "TR": {"limit_state": "tensile_rupture", "provision": "D2(b) + D3", "area_basis": "Ae", "area_mm2": net["Ae_mm2"],
               "An_mm2": an, "U": u, "Ae_equation": net["equation"], "stress_mpa": case.material.Fu,
               "Pn_equation": rupture["equation"], "Pn_kN": rupture["Pn_N"] / 1000.0,
               "available_kN": eq.available_strength(rupture["Pn_N"], "rupture")},
    }
    governing = {m: min(modes, key=lambda k: modes[k]["available_kN"][m]) for m in ("LRFD", "ASD")}
    available = {m: modes[governing[m]]["available_kN"][m] for m in ("LRFD", "ASD")}

    notes = []
    radius, length = least_radius(section), case.tension.fabricated_length
    if length and radius:
        ratio = length / radius
        notes.append(f"Nota de D1: L/r = {ratio:.1f} (longitud fabricada / radio de giro mínimo); se recomienda ≤ 300"
                     + (" — supera la recomendación (no es un límite de resistencia)." if ratio > 300 else "."))
    else:
        notes.append("Nota de D1 (L/r ≤ 300 recomendado) no evaluada: falta tension.fabricated_length.")
    if section.type.upper() == "DOUBLE_ANGLE":
        notes.append("D4: las placas de unión y la separación de conectores de miembros armados no se verifican "
                     "(se recomienda esbeltez de cada componente entre conectores ≤ 300).")
    return {
        "chapter": "D", "code": "ANSI/AISC 360-22",
        "section": section.name, "family": section.type.upper(), "design_method": method,
        "inputs": {"Fy_mpa": case.material.Fy, "Fu_mpa": case.material.Fu, "Ag_mm2": ag, "An_mm2": an, "U": u},
        "provisions": ["D2", "D3"],
        "modes": modes,
        "governing_mode": governing[method],
        "governing_equation": modes[governing[method]]["Pn_equation"],
        "Pn_kN": modes[governing[method]]["Pn_kN"],
        "available": available,
        "available_kN": available[method],
        "governing_by_method": governing,
        "requirements": [],
        "notes": notes,
        "limitations": list(_LIMITATIONS),
    }
