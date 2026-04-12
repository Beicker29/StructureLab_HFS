from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Type

from ...codes.aisc_360_22 import axial_calc
from ...models import SteelCase
from ...sections.models import Section
from ..errors import IncompleteSectionDataError, RuleNotImplementedError
from ..rules.axial_rules import AxialE3Rule, AxialE4Rule, AxialE5Rule, AxialE7Rule
from ..rules.flexure_rule import FlexureRule
from ..rules.tension_rule import TensionRuptureRule, TensionRule


class ProfileType:
    W_SHAPE = "W"
    CHANNEL = "CHANNEL"
    DOUBLE_ANGLE = "DOUBLE_ANGLE"
    RECTANGULAR_HSS = "RECTANGULAR_HSS"
    CIRCULAR_HSS = "CIRCULAR_HSS"
    SINGLE_ANGLE = "SINGLE_ANGLE"
    SOLID_RECTANGULAR = "SOLID_RECTANGULAR"
    SOLID_CIRCULAR = "SOLID_CIRCULAR"
    FILLED_RECTANGULAR = "FILLED_RECTANGULAR"  # Backward compatibility alias
    FILLED_CIRCULAR = "FILLED_CIRCULAR"  # Backward compatibility alias


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    rule_class: Optional[Type]
    implemented: bool
    required_section_fields: Tuple[str, ...]
    applicability: Callable[[SteelCase, Section], bool]


def _has_tension(case: SteelCase, _: Section) -> bool:
    return case.loads.Pu < 0.0


def _has_compression(case: SteelCase, _: Section) -> bool:
    return case.loads.Pu > 0.0


def _has_major_flexure(case: SteelCase, _: Section) -> bool:
    return abs(case.loads.Mux) > 0.0


def _has_any_flexure(case: SteelCase, _: Section) -> bool:
    return abs(case.loads.Mux) > 0.0 or abs(case.loads.Muy) > 0.0


def _has_shear(case: SteelCase, _: Section) -> bool:
    return abs(case.loads.Vu) > 0.0


def _has_interaction(case: SteelCase, section: Section) -> bool:
    return abs(case.loads.Pu) > 0.0 and _has_any_flexure(case, section)


RULE_DEFINITIONS: Dict[str, RuleDefinition] = {
    "D2-1": RuleDefinition("D2-1", TensionRule, True, ("area",), _has_tension),
    "D2-2": RuleDefinition("D2-2", TensionRuptureRule, True, ("area",), _has_tension),
    "E3": RuleDefinition("E3", AxialE3Rule, True, ("area", "rx", "ry"), _has_compression),
    "E4": RuleDefinition("E4", AxialE4Rule, True, tuple(), _has_compression),
    "E5": RuleDefinition("E5", AxialE5Rule, True, ("area", "rx", "ry", "b_t_ratio"), _has_compression),
    "E7": RuleDefinition("E7", AxialE7Rule, True, tuple(), _has_compression),
    "F2": RuleDefinition("F2", FlexureRule, True, ("zx",), _has_major_flexure),
    "F7": RuleDefinition("F7", None, False, ("zx",), _has_any_flexure),
    "F8": RuleDefinition("F8", None, False, ("zx",), _has_any_flexure),
    "F9": RuleDefinition("F9", None, False, ("zx",), _has_any_flexure),
    "F10": RuleDefinition("F10", None, False, ("zx",), _has_any_flexure),
    "G2": RuleDefinition("G2", None, False, ("tw", "d"), _has_shear),
    "G4": RuleDefinition("G4", None, False, ("tw", "d"), _has_shear),
    "G5": RuleDefinition("G5", None, False, ("d",), _has_shear),
    "H1": RuleDefinition("H1", None, False, ("area",), _has_interaction),
    "I2": RuleDefinition("I2", None, False, ("area",), _has_interaction),
}


PROFILE_RULE_MAP = {
    ProfileType.W_SHAPE: ["D2-1", "D2-2", "E3", "E4", "E7", "F2", "G2", "H1"],
    ProfileType.CHANNEL: ["D2-1", "D2-2", "E3", "E4", "E7", "G2", "H1"],
    ProfileType.DOUBLE_ANGLE: ["D2-1", "D2-2", "E3", "E4", "E7", "F9", "G2", "H1"],
    ProfileType.RECTANGULAR_HSS: ["D2-1", "D2-2", "E3", "E4", "E7", "F7", "G4", "H1"],
    ProfileType.CIRCULAR_HSS: ["D2-1", "D2-2", "E3", "E4", "E7", "F8", "G5", "H1"],
    ProfileType.SINGLE_ANGLE: ["D2-1", "D2-2", "E3", "E5", "E7", "F10", "G2", "H1"],
    ProfileType.SOLID_RECTANGULAR: ["D2-1", "D2-2", "E3"],
    ProfileType.SOLID_CIRCULAR: ["D2-1", "D2-2", "E3"],
    ProfileType.FILLED_RECTANGULAR: ["D2-1", "D2-2", "E3"],
    ProfileType.FILLED_CIRCULAR: ["D2-1", "D2-2", "E3"],
}


def _required_fields_for_e4(profile_type: str) -> Tuple[str, ...]:
    if profile_type in {"DOUBLE_ANGLE"}:
        return ("area", "j", "cw", "ro", "ry")
    if profile_type in {"CHANNEL"}:
        return ("area", "j", "cw", "ro", "ry")
    if profile_type in {"W"}:
        return ("area", "j", "cw", "ix", "iy", "ry")
    if profile_type in {"RECTANGULAR_HSS", "CIRCULAR_HSS"}:
        return ("area", "j", "rx", "ry")
    return ("area", "j", "ry")


def _required_fields_for_e7(profile_type: str) -> Tuple[str, ...]:
    if profile_type in {"W"}:
        return ("area", "rx", "ry", "bf_2tf_ratio", "h_tw_ratio")
    if profile_type == "CHANNEL":
        return ("area", "rx", "ry", "b_t_ratio", "h_tw_ratio")
    if profile_type == "RECTANGULAR_HSS":
        return ("area", "rx", "ry", "b_tdes_ratio", "h_tdes_ratio")
    if profile_type == "CIRCULAR_HSS":
        return ("area", "rx", "ry", "d_t_ratio")
    if profile_type in {"SINGLE_ANGLE", "DOUBLE_ANGLE"}:
        return ("area", "rx", "ry", "b_t_ratio")
    return ("area", "rx", "ry")


def _section_slenderness_values(section: Section) -> Dict[str, Optional[float]]:
    return {
        "bf_2tf_ratio": section.bf_2tf_ratio,
        "b_t_ratio": section.b_t_ratio,
        "b_tdes_ratio": section.b_tdes_ratio,
        "h_tw_ratio": section.h_tw_ratio,
        "h_tdes_ratio": section.h_tdes_ratio,
        "d_t_ratio": section.d_t_ratio,
    }


class ProfileRouter:
    """
    Strict router for applicable checks.
    - A required but non-implemented rule raises RuleNotImplementedError.
    - A required implemented rule with missing section data raises IncompleteSectionDataError.
    """

    @staticmethod
    def _is_missing_numeric(value: object) -> bool:
        if value is None:
            return True
        if isinstance(value, (int, float)):
            return value <= 0.0
        return True

    @classmethod
    def _required_fields(cls, section: Section, rule_id: str, definition: RuleDefinition) -> Tuple[str, ...]:
        profile_type = section.type.upper()
        if rule_id == "E4":
            return _required_fields_for_e4(profile_type)
        if rule_id == "E7":
            return _required_fields_for_e7(profile_type)
        return definition.required_section_fields

    @classmethod
    def _validate_section_fields(cls, section: Section, rule_id: str, required_fields: Tuple[str, ...]) -> None:
        missing = [field for field in required_fields if cls._is_missing_numeric(getattr(section, field, None))]
        if missing:
            raise IncompleteSectionDataError(
                "Section data is incomplete for an applicable rule.",
                details={
                    "section": section.name,
                    "profile_type": section.type,
                    "rule_id": rule_id,
                    "missing_fields": missing,
                },
            )

    @staticmethod
    def _raise_not_implemented(rule_id: str, section: Section) -> None:
        raise RuleNotImplementedError(
            "Applicable AISC clause is not implemented.",
            details={"section": section.name, "profile_type": section.type, "rule_id": rule_id},
        )

    @classmethod
    def _is_e7_applicable(cls, case: SteelCase, section: Section) -> bool:
        """
        Returns True when section has slender compression elements and must be checked by E7.
        Missing data required for this decision triggers fail-hard.
        """
        if case.loads.Pu <= 0.0:
            return False

        profile_type = section.type.upper()
        required = _required_fields_for_e7(profile_type)
        cls._validate_section_fields(section, "E7", required)

        classification = axial_calc.classify_compression_elements(
            profile_type=profile_type,
            slenderness=_section_slenderness_values(section),
            E=case.material.E,
            Fy=case.material.Fy,
        )
        return bool(classification.get("is_slender"))

    @classmethod
    def get_rules(cls, case: SteelCase, section: Section) -> List:
        profile_type = section.type.upper()
        if profile_type not in PROFILE_RULE_MAP:
            raise RuleNotImplementedError(
                "No routing configuration exists for profile type.",
                details={"section": section.name, "profile_type": section.type},
            )

        active_rules = []
        e7_applicable = cls._is_e7_applicable(case, section)
        for rule_id in PROFILE_RULE_MAP[profile_type]:
            definition = RULE_DEFINITIONS.get(rule_id)
            if definition is None:
                cls._raise_not_implemented(rule_id, section)

            if rule_id == "E7" and not e7_applicable:
                continue

            if not definition.applicability(case, section):
                continue

            if not definition.implemented or definition.rule_class is None:
                cls._raise_not_implemented(rule_id, section)

            required_fields = cls._required_fields(section, rule_id, definition)
            cls._validate_section_fields(section, rule_id, required_fields)
            active_rules.append(definition.rule_class())

        return active_rules
