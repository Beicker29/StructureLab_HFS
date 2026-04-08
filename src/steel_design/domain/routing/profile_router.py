from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Type

from ...models import SteelCase
from ...sections.models import Section
from ..errors import IncompleteSectionDataError, RuleNotImplementedError
from ..rules.axial_rules import AxialE3Rule
from ..rules.flexure_rule import FlexureRule
from ..rules.tension_rule import TensionRule


class ProfileType:
    W_SHAPE = "W"
    DOUBLE_ANGLE = "DOUBLE_ANGLE"
    RECTANGULAR_HSS = "RECTANGULAR_HSS"
    CIRCULAR_HSS = "CIRCULAR_HSS"
    SINGLE_ANGLE = "SINGLE_ANGLE"
    WT_SHAPE = "WT"
    FILLED_RECTANGULAR = "FILLED_RECTANGULAR"
    FILLED_CIRCULAR = "FILLED_CIRCULAR"


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
    "D2": RuleDefinition("D2", TensionRule, True, ("area",), _has_tension),
    "E3": RuleDefinition("E3", AxialE3Rule, True, ("area", "rx", "ry"), _has_compression),
    "E4": RuleDefinition("E4", None, False, ("area", "j", "cw"), _has_compression),
    "E5": RuleDefinition("E5", None, False, ("area",), _has_compression),
    "E7": RuleDefinition("E7", None, False, ("area",), _has_compression),
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
    ProfileType.W_SHAPE: ["D2", "E3", "E7", "F2", "G2", "H1"],
    ProfileType.DOUBLE_ANGLE: ["D2", "E3", "E4", "E7", "F9", "G2", "H1"],
    ProfileType.RECTANGULAR_HSS: ["D2", "E3", "E4", "E7", "F7", "G4", "H1"],
    ProfileType.CIRCULAR_HSS: ["D2", "E3", "E4", "E7", "F8", "G5", "H1"],
    ProfileType.SINGLE_ANGLE: ["D2", "E3", "E5", "E7", "F10", "G2", "H1"],
    ProfileType.WT_SHAPE: ["D2", "E3", "E4", "E7", "F9", "G2", "H1"],
    ProfileType.FILLED_RECTANGULAR: ["E3", "E4", "E7", "H1", "I2"],
    ProfileType.FILLED_CIRCULAR: ["E3", "E4", "E7", "H1", "I2"],
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
        return False

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
            details={
                "section": section.name,
                "profile_type": section.type,
                "rule_id": rule_id,
            },
        )

    @classmethod
    def get_rules(cls, case: SteelCase, section: Section) -> List:
        profile_type = section.type.upper()
        if profile_type not in PROFILE_RULE_MAP:
            raise RuleNotImplementedError(
                "No routing configuration exists for profile type.",
                details={"section": section.name, "profile_type": section.type},
            )

        active_rules = []
        for rule_id in PROFILE_RULE_MAP[profile_type]:
            definition = RULE_DEFINITIONS.get(rule_id)
            if definition is None:
                cls._raise_not_implemented(rule_id, section)

            if not definition.applicability(case, section):
                continue

            if not definition.implemented or definition.rule_class is None:
                cls._raise_not_implemented(rule_id, section)

            cls._validate_section_fields(section, rule_id, definition.required_section_fields)
            active_rules.append(definition.rule_class())

        return active_rules
