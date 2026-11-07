"""Appendix 4, Section 4.2.4d (simple method) for one fire case: material properties at temperature and what the method covers.

The temperatures are data of the case (heat transfer analysis, 4.2.2). At or below 200 deg C of steel, the strengths ignore temperature.
Each chapter applies these properties in its own domain module. Formulas live in codes/aisc_360_22/appendix_4.py.
"""
from typing import Any

from ..codes.aisc_360_22 import appendix_4 as a4
from ..codes.aisc_360_22.constants import G_STEEL
from ..errors import RuleNotImplementedError
from ..models import SteelCase

NOTES = (
    "Apéndice 4, 4.2.2 y 4.2.4: las temperaturas provienen del análisis térmico del usuario (T uniforme en la sección) y las "
    "solicitaciones de la "
    "combinación A-4-1. Las conexiones y, en miembros rellenos, los agujeros de ventilación de 4.2.4a no se revisan aquí."
)
EXTENSION = (
    "Fuera de 4.2.4d y de la Guía 38, que a temperatura solo tratan la compresión de rellenos y muros: ecuaciones de temperatura "
    "ambiente con las propiedades "
    "de 4.2.3b, como indica en general el Commentary de 4.2.4d. Es una decisión de ingeniería (DA4-8)."
)
SLENDER_BLOCK = "Apéndice 4, 4.2.4d: el método simple solo se aplica a secciones no esbeltas."
_DEMANDS = ("P", "Mx_3", "My_2", "Vy_2", "Vx_3")


def is_elevated(case: SteelCase) -> bool:
    """A fire case above 200 deg C of steel: the simple method applies."""
    return case.fire is not None and case.fire.steel_temperature > a4.SIMPLE_METHOD_MIN


def steel_at_temperature(case: SteelCase) -> dict | None:
    """Table A-4.2.1 at the steel temperature, or None when temperature does not enter the strengths."""
    if not is_elevated(case):
        return None
    Fy, T = case.material.Fy, case.fire.steel_temperature
    if Fy > a4.FY_MAX:
        raise RuleNotImplementedError(f"Apéndice 4, 4.2.3b: se aplica a aceros con Fy ≤ {a4.FY_MAX:g} MPa.", code="FIRE_DOMAIN_BLOCKED",
                                      details={"Fy_mpa": Fy})
    factors = a4.steel_factors(T)
    Fy_T = factors["ky"] * Fy
    Fu_T = a4.tensile_strength(Fu=case.material.Fu, Fy_T=Fy_T, T=T)
    return {
        "T_C": T,
        **factors,
        "Fy_T_mpa": Fy_T,
        "Fu_T_mpa": Fu_T,
        "E_T_mpa": factors["kE"] * case.material.E,
        "G_T_mpa": factors["kE"] * G_STEEL,
    }


def with_fire(result: dict, hot: dict | None, provision: str, *notes: str) -> dict:
    """The result of a chapter, with the properties and the literal of the simple method when they were used."""
    if hot:
        result["fire"] = hot
        result["provisions"].append(f"Apéndice 4, {provision}")
        result["notes"] += [NOTES, *notes]
    return result


def with_fire_extension(result: dict, hot: dict | None) -> dict:
    """with_fire for what 4.2.4d does not state: the ambient equations with the properties of 4.2.3b (DA4-8)."""
    return with_fire(result, hot, "Commentary 4.2.4d", EXTENSION)


def uncovered_demands(case: SteelCase) -> list[str]:
    """The demands of a composite member above 200 deg C that stay blocked: encased members (DA4-1) and the axial force of a
    composite beam."""
    if not is_elevated(case) or case.composite is None:
        return []
    demands = [name for name in _DEMANDS if getattr(case, name)]
    if case.composite.kind == "encased":
        return demands
    return ["P"] if case.composite.kind == "beam" and case.P else []


def fire_summary(case: SteelCase) -> dict | None:
    """Temperatures and retention factors of a fire case, for the report. Concrete only when its temperature was given."""
    if case.fire is None:
        return None
    fire = case.fire
    out: dict[str, Any] = {"T_C": fire.steel_temperature, "simple_method": is_elevated(case), "steel": None, "concrete": [], "bars": None}
    if out["simple_method"] and case.material.Fy <= a4.FY_MAX:
        out["steel"] = steel_at_temperature(case)
    if case.composite is None:
        return out
    temperatures = ([("uniforme", fire.concrete_temperature)] if fire.concrete_temperature is not None else []) + [
        ("capa", layer.T) for layer in fire.concrete_layers or []] + [("capa del alma", layer.T) for layer in fire.web_layers or []] + [
        ("capa de las alas", layer.T) for layer in fire.flange_layers or []]
    lightweight, fc = case.composite.concrete.lightweight, case.composite.concrete.fc
    for zone, T in temperatures:
        factors = a4.concrete_factors(T, lightweight=lightweight)
        out["concrete"].append({"zone": zone, "T_C": T, **factors, "fc_T_mpa": factors["kc"] * fc})
    if fire.bar_temperature is not None:
        out["bars"] = {"T_C": fire.bar_temperature, **a4.steel_factors(fire.bar_temperature)}
    return out
