import math
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Type

from ...codes.aisc_360_22 import axial_calc
from ...models import SteelCase
from ...sections.models import Section
from ..errors import IncompleteSectionDataError, RuleNotImplementedError
from ..rules.axial_rules import AxialE3Rule, AxialE4Rule, AxialE5Rule, AxialE7Rule
from ..rules.combined_hss_rules import CombinedH1HssRule, HssCombinedH3_2Rule, HssTorsionH3_1Rule
from ..rules.composite_rules import (
    CompositeI1Rule,
    CompositeI2EncasedCompressionRule,
    CompositeI2EncasedTensionRule,
    CompositeI2FilledCompressionRule,
    CompositeI2FilledTensionRule,
    CompositeI3_1aRule,
    CompositeI3_1bRule,
    CompositeI3_1cRule,
    CompositeI3_3Rule,
    CompositeI3_4Rule,
    CompositeI4_1EncasedGoverningRule,
    CompositeI4_1FilledRule,
    CompositeI4_1aEncasedRule,
    CompositeI4_1bEncasedRule,
    CompositeI4_1cEncasedRule,
    CompositeI4_3BeamDeckSteelOnlyRule,
)
from ..rules.flexure_rule import (
    FlexureF2LtbRule,
    FlexureF2YieldRule,
    FlexureF3FlbRule,
    FlexureF3LtbRule,
    FlexureF3YieldRule,
    FlexureF4CompressionYieldRule,
    FlexureF4FlbRule,
    FlexureF4LtbRule,
    FlexureF4TensionYieldRule,
    FlexureF5CompressionYieldRule,
    FlexureF5FlbRule,
    FlexureF5LtbRule,
    FlexureF5TensionYieldRule,
    FlexureF6FlbRule,
    FlexureF6YieldRule,
    FlexureF7FlangeMxRule,
    FlexureF7FlangeMyRule,
    FlexureF7LtbMxRule,
    FlexureF7LtbMyRule,
    FlexureF7WebMxRule,
    FlexureF7WebMyRule,
    FlexureF7YieldMxRule,
    FlexureF7YieldMyRule,
    FlexureF8LocalBucklingMxRule,
    FlexureF8LocalBucklingMyRule,
    FlexureF8YieldMxRule,
    FlexureF8YieldMyRule,
    FlexureF10LegBucklingMxRule,
    FlexureF10LegBucklingMyRule,
    FlexureF10LtbMxRule,
    FlexureF10LtbMyRule,
    FlexureF10YieldMxRule,
    FlexureF10YieldMyRule,
    FlexureF11LtbMxRule,
    FlexureF11LtbMyRule,
    FlexureF11YieldMxRule,
    FlexureF11YieldMyRule,
)
from ..rules.shear_rules import (
    ShearG2VxRule,
    ShearG3VxRule,
    ShearG3VyRule,
    ShearG4VxRule,
    ShearG4VyRule,
    ShearG5VxRule,
    ShearG5VyRule,
    ShearG6VyRule,
)
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


def _has_minor_flexure(case: SteelCase, _: Section) -> bool:
    return abs(case.loads.Muy) > 0.0


def _has_any_flexure(case: SteelCase, _: Section) -> bool:
    return abs(case.loads.Mux) > 0.0 or abs(case.loads.Muy) > 0.0


def _has_directional_shear(case: SteelCase) -> bool:
    return abs(case.loads.Vux) > 0.0 or abs(case.loads.Vuy) > 0.0


def _has_major_shear(case: SteelCase, _: Section) -> bool:
    if _has_directional_shear(case):
        return abs(case.loads.Vux) > 0.0
    return abs(case.loads.Vu) > 0.0


def _has_minor_shear(case: SteelCase, _: Section) -> bool:
    return _has_directional_shear(case) and abs(case.loads.Vuy) > 0.0


def _has_shear(case: SteelCase, _: Section) -> bool:
    return abs(case.loads.Vu) > 0.0 or abs(case.loads.Vux) > 0.0 or abs(case.loads.Vuy) > 0.0


def _has_torsion(case: SteelCase, _: Section) -> bool:
    return abs(case.loads.Tu) > 0.0


def _is_h1_hss_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() in {"RECTANGULAR_HSS", "CIRCULAR_HSS"} and abs(case.loads.Pu) > 0.0 and _has_any_flexure(case, section)


def _is_h3_1_hss_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() in {"RECTANGULAR_HSS", "CIRCULAR_HSS"} and _has_torsion(case, section)


def _is_h3_2_hss_applicable(case: SteelCase, section: Section) -> bool:
    if section.type.upper() not in {"RECTANGULAR_HSS", "CIRCULAR_HSS"} or not _has_torsion(case, section):
        return False
    return abs(case.loads.Pu) > 0.0 or _has_any_flexure(case, section) or _has_shear(case, section)


def _has_interaction(case: SteelCase, section: Section) -> bool:
    return False


def _safe_ratio(value: Optional[float]) -> float:
    return float(value) if isinstance(value, (int, float)) and value > 0.0 else 0.0


def _classify_element(value: float, compact_limit: float, noncompact_limit: float) -> str:
    if value <= compact_limit:
        return "compact"
    if value <= noncompact_limit:
        return "noncompact"
    return "slender"


def _w_or_channel_major_flexure_selection(case: SteelCase, section: Section) -> Optional[str]:
    if not _has_major_flexure(case, section):
        return None

    fy = case.material.Fy
    e = case.material.E
    sqrt_ratio = math.sqrt(e / fy) if min(e, fy) > 0.0 else 0.0
    flange_ratio = _safe_ratio(section.bf_2tf_ratio)
    web_ratio = _safe_ratio(section.h_tw_ratio)
    if min(flange_ratio, web_ratio) <= 0.0:
        return "F2"

    flange_class = _classify_element(flange_ratio, 0.38 * sqrt_ratio, 1.0 * sqrt_ratio)
    web_class = _classify_element(web_ratio, 3.76 * sqrt_ratio, 5.70 * sqrt_ratio)
    profile = section.type.upper()

    if profile == "CHANNEL":
        if flange_class == "compact" and web_class == "compact":
            return "F2"
        return None

    if web_class == "compact" and flange_class == "compact":
        return "F2"
    if web_class == "compact" and flange_class in {"noncompact", "slender"}:
        return "F3"
    if web_class == "noncompact":
        return "F4"
    if web_class == "slender":
        return "F5"
    return None


def _is_f2_applicable(case: SteelCase, section: Section) -> bool:
    return _w_or_channel_major_flexure_selection(case, section) == "F2"


def _is_f3_applicable(case: SteelCase, section: Section) -> bool:
    return _w_or_channel_major_flexure_selection(case, section) == "F3"


def _is_f4_applicable(case: SteelCase, section: Section) -> bool:
    return _w_or_channel_major_flexure_selection(case, section) == "F4"


def _is_f5_applicable(case: SteelCase, section: Section) -> bool:
    return _w_or_channel_major_flexure_selection(case, section) == "F5"


def _is_f6_applicable(case: SteelCase, section: Section) -> bool:
    profile = section.type.upper()
    return profile in {"W", "CHANNEL"} and _has_minor_flexure(case, section)


def _is_f7_mx_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() == "RECTANGULAR_HSS" and _has_major_flexure(case, section)


def _is_f7_my_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() == "RECTANGULAR_HSS" and _has_minor_flexure(case, section)


def _is_f8_applicable(case: SteelCase, section: Section) -> bool:
    if section.type.upper() != "CIRCULAR_HSS" or not _has_any_flexure(case, section):
        return False
    ratio = _safe_ratio(section.d_t_ratio)
    if ratio <= 0.0:
        return False
    return ratio < 0.45 * case.material.E / case.material.Fy


def _is_f8_mx_applicable(case: SteelCase, section: Section) -> bool:
    return _is_f8_applicable(case, section) and _has_major_flexure(case, section)


def _is_f8_my_applicable(case: SteelCase, section: Section) -> bool:
    return _is_f8_applicable(case, section) and _has_minor_flexure(case, section)


def _is_f10_mx_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() == "SINGLE_ANGLE" and _has_major_flexure(case, section)


def _is_f10_my_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() == "SINGLE_ANGLE" and _has_minor_flexure(case, section)


def _is_f11_mx_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() in {"SOLID_RECTANGULAR", "SOLID_CIRCULAR", "FILLED_RECTANGULAR", "FILLED_CIRCULAR"} and _has_major_flexure(case, section)


def _is_f11_my_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() in {"SOLID_RECTANGULAR", "SOLID_CIRCULAR", "FILLED_RECTANGULAR", "FILLED_CIRCULAR"} and _has_minor_flexure(case, section)


def _is_g2_vx_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() in {"W", "CHANNEL"} and _has_major_shear(case, section)


def _is_g3_vx_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() in {"SINGLE_ANGLE", "DOUBLE_ANGLE"} and _has_major_shear(case, section)


def _is_g3_vy_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() in {"SINGLE_ANGLE", "DOUBLE_ANGLE"} and _has_minor_shear(case, section)


def _is_g4_vx_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() == "RECTANGULAR_HSS" and _has_major_shear(case, section)


def _is_g4_vy_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() == "RECTANGULAR_HSS" and _has_minor_shear(case, section)


def _is_g5_vx_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() == "CIRCULAR_HSS" and _has_major_shear(case, section)


def _is_g5_vy_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() == "CIRCULAR_HSS" and _has_minor_shear(case, section)


def _is_g6_vy_applicable(case: SteelCase, section: Section) -> bool:
    return section.type.upper() in {"W", "CHANNEL"} and _has_minor_shear(case, section)


RULE_DEFINITIONS: Dict[str, RuleDefinition] = {
    "D2-1": RuleDefinition("D2-1", TensionRule, True, ("area",), _has_tension),
    "D2-2": RuleDefinition("D2-2", TensionRuptureRule, True, ("area",), _has_tension),
    "E3": RuleDefinition("E3", AxialE3Rule, True, ("area", "rx", "ry"), _has_compression),
    "E4": RuleDefinition("E4", AxialE4Rule, True, tuple(), _has_compression),
    "E5": RuleDefinition("E5", AxialE5Rule, True, ("area", "rx", "ry", "b_t_ratio"), _has_compression),
    "E7": RuleDefinition("E7", AxialE7Rule, True, tuple(), _has_compression),
    "F2-1": RuleDefinition("F2-1", FlexureF2YieldRule, True, ("zx", "sx", "iy", "cw", "ry", "j", "ho"), _is_f2_applicable),
    "F2-2": RuleDefinition("F2-2", FlexureF2LtbRule, True, ("zx", "sx", "iy", "cw", "ry", "j", "ho"), _is_f2_applicable),
    "F3-1": RuleDefinition("F3-1", FlexureF3YieldRule, True, ("zx", "sx", "iy", "cw", "ry", "j", "ho", "bf_2tf_ratio", "h_tw_ratio"), _is_f3_applicable),
    "F3-2": RuleDefinition("F3-2", FlexureF3LtbRule, True, ("zx", "sx", "iy", "cw", "ry", "j", "ho", "bf_2tf_ratio", "h_tw_ratio"), _is_f3_applicable),
    "F3-3": RuleDefinition("F3-3", FlexureF3FlbRule, True, ("zx", "sx", "iy", "cw", "ry", "j", "ho", "bf_2tf_ratio", "h_tw_ratio"), _is_f3_applicable),
    "F4-1": RuleDefinition("F4-1", FlexureF4CompressionYieldRule, True, ("sx", "bf", "tf", "tw", "h", "bf_2tf_ratio", "h_tw_ratio"), _is_f4_applicable),
    "F4-2": RuleDefinition("F4-2", FlexureF4LtbRule, True, ("sx", "bf", "tf", "tw", "h", "bf_2tf_ratio", "h_tw_ratio"), _is_f4_applicable),
    "F4-3": RuleDefinition("F4-3", FlexureF4FlbRule, True, ("sx", "bf", "tf", "tw", "h", "bf_2tf_ratio", "h_tw_ratio"), _is_f4_applicable),
    "F4-4": RuleDefinition("F4-4", FlexureF4TensionYieldRule, True, ("sx", "bf", "tf", "tw", "h", "bf_2tf_ratio", "h_tw_ratio"), _is_f4_applicable),
    "F5-1": RuleDefinition("F5-1", FlexureF5CompressionYieldRule, True, ("sx", "bf", "tf", "tw", "h", "bf_2tf_ratio", "h_tw_ratio"), _is_f5_applicable),
    "F5-2": RuleDefinition("F5-2", FlexureF5LtbRule, True, ("sx", "bf", "tf", "tw", "h", "bf_2tf_ratio", "h_tw_ratio"), _is_f5_applicable),
    "F5-3": RuleDefinition("F5-3", FlexureF5FlbRule, True, ("sx", "bf", "tf", "tw", "h", "bf_2tf_ratio", "h_tw_ratio"), _is_f5_applicable),
    "F5-4": RuleDefinition("F5-4", FlexureF5TensionYieldRule, True, ("sx", "bf", "tf", "tw", "h", "bf_2tf_ratio", "h_tw_ratio"), _is_f5_applicable),
    "F6-1": RuleDefinition("F6-1", FlexureF6YieldRule, True, ("zy", "sy", "bf_2tf_ratio"), _is_f6_applicable),
    "F6-2": RuleDefinition("F6-2", FlexureF6FlbRule, True, ("zy", "sy", "bf_2tf_ratio"), _is_f6_applicable),
    "F7-1-Mx": RuleDefinition(
        "F7-1-Mx",
        FlexureF7YieldMxRule,
        True,
        ("zx", "zy", "sx", "sy", "b", "h", "tdes", "b_tdes_ratio", "h_tdes_ratio"),
        _is_f7_mx_applicable,
    ),
    "F7-1-My": RuleDefinition(
        "F7-1-My",
        FlexureF7YieldMyRule,
        True,
        ("zx", "zy", "sx", "sy", "b", "h", "tdes", "b_tdes_ratio", "h_tdes_ratio"),
        _is_f7_my_applicable,
    ),
    "F7-2-Mx": RuleDefinition(
        "F7-2-Mx",
        FlexureF7FlangeMxRule,
        True,
        ("zx", "zy", "sx", "sy", "b", "h", "tdes", "b_tdes_ratio", "h_tdes_ratio"),
        _is_f7_mx_applicable,
    ),
    "F7-2-My": RuleDefinition(
        "F7-2-My",
        FlexureF7FlangeMyRule,
        True,
        ("zx", "zy", "sx", "sy", "b", "h", "tdes", "b_tdes_ratio", "h_tdes_ratio"),
        _is_f7_my_applicable,
    ),
    "F7-3-Mx": RuleDefinition(
        "F7-3-Mx",
        FlexureF7WebMxRule,
        True,
        ("zx", "zy", "sx", "sy", "b", "h", "tdes", "b_tdes_ratio", "h_tdes_ratio"),
        _is_f7_mx_applicable,
    ),
    "F7-3-My": RuleDefinition(
        "F7-3-My",
        FlexureF7WebMyRule,
        True,
        ("zx", "zy", "sx", "sy", "b", "h", "tdes", "b_tdes_ratio", "h_tdes_ratio"),
        _is_f7_my_applicable,
    ),
    "F7-4-Mx": RuleDefinition(
        "F7-4-Mx",
        FlexureF7LtbMxRule,
        True,
        ("zx", "zy", "sx", "sy", "b", "h", "tdes", "b_tdes_ratio", "h_tdes_ratio"),
        _is_f7_mx_applicable,
    ),
    "F7-4-My": RuleDefinition(
        "F7-4-My",
        FlexureF7LtbMyRule,
        True,
        ("zx", "zy", "sx", "sy", "b", "h", "tdes", "b_tdes_ratio", "h_tdes_ratio"),
        _is_f7_my_applicable,
    ),
    "F8-1-Mx": RuleDefinition("F8-1-Mx", FlexureF8YieldMxRule, True, ("zx", "zy", "sx", "sy", "d_t_ratio"), _is_f8_mx_applicable),
    "F8-1-My": RuleDefinition("F8-1-My", FlexureF8YieldMyRule, True, ("zx", "zy", "sx", "sy", "d_t_ratio"), _is_f8_my_applicable),
    "F8-2-Mx": RuleDefinition("F8-2-Mx", FlexureF8LocalBucklingMxRule, True, ("zx", "zy", "sx", "sy", "d_t_ratio"), _is_f8_mx_applicable),
    "F8-2-My": RuleDefinition("F8-2-My", FlexureF8LocalBucklingMyRule, True, ("zx", "zy", "sx", "sy", "d_t_ratio"), _is_f8_my_applicable),
    "F9": RuleDefinition("F9", None, False, ("zx",), _has_any_flexure),
    "F10-1-Mx": RuleDefinition("F10-1-Mx", FlexureF10YieldMxRule, True, ("b_t_ratio", "b", "t"), _is_f10_mx_applicable),
    "F10-1-My": RuleDefinition("F10-1-My", FlexureF10YieldMyRule, True, ("b_t_ratio", "b", "t"), _is_f10_my_applicable),
    "F10-2-Mx": RuleDefinition("F10-2-Mx", FlexureF10LtbMxRule, True, ("b_t_ratio", "b", "t"), _is_f10_mx_applicable),
    "F10-2-My": RuleDefinition("F10-2-My", FlexureF10LtbMyRule, True, ("b_t_ratio", "b", "t"), _is_f10_my_applicable),
    "F10-3-Mx": RuleDefinition("F10-3-Mx", FlexureF10LegBucklingMxRule, True, ("b_t_ratio", "b", "t"), _is_f10_mx_applicable),
    "F10-3-My": RuleDefinition("F10-3-My", FlexureF10LegBucklingMyRule, True, ("b_t_ratio", "b", "t"), _is_f10_my_applicable),
    "F11-1-Mx": RuleDefinition("F11-1-Mx", FlexureF11YieldMxRule, True, ("zx", "zy", "sx", "sy"), _is_f11_mx_applicable),
    "F11-1-My": RuleDefinition("F11-1-My", FlexureF11YieldMyRule, True, ("zx", "zy", "sx", "sy"), _is_f11_my_applicable),
    "F11-2-Mx": RuleDefinition("F11-2-Mx", FlexureF11LtbMxRule, True, ("zx", "zy", "sx", "sy"), _is_f11_mx_applicable),
    "F11-2-My": RuleDefinition("F11-2-My", FlexureF11LtbMyRule, True, ("zx", "zy", "sx", "sy"), _is_f11_my_applicable),
    "G2-Vx": RuleDefinition("G2-Vx", ShearG2VxRule, True, ("tw", "d"), _is_g2_vx_applicable),
    "G3-Vx": RuleDefinition("G3-Vx", ShearG3VxRule, True, ("b", "t"), _is_g3_vx_applicable),
    "G3-Vy": RuleDefinition("G3-Vy", ShearG3VyRule, True, ("b", "t"), _is_g3_vy_applicable),
    "G4-Vx": RuleDefinition("G4-Vx", ShearG4VxRule, True, ("h", "tdes"), _is_g4_vx_applicable),
    "G4-Vy": RuleDefinition("G4-Vy", ShearG4VyRule, True, ("b", "tdes"), _is_g4_vy_applicable),
    "G5-Vx": RuleDefinition("G5-Vx", ShearG5VxRule, True, ("area", "od"), _is_g5_vx_applicable),
    "G5-Vy": RuleDefinition("G5-Vy", ShearG5VyRule, True, ("area", "od"), _is_g5_vy_applicable),
    "G6-Vy": RuleDefinition("G6-Vy", ShearG6VyRule, True, ("bf", "tf"), _is_g6_vy_applicable),
    "H1": RuleDefinition("H1", CombinedH1HssRule, True, ("area",), _is_h1_hss_applicable),
    "H3-1": RuleDefinition("H3-1", HssTorsionH3_1Rule, True, tuple(), _is_h3_1_hss_applicable),
    "H3-2": RuleDefinition("H3-2", HssCombinedH3_2Rule, True, tuple(), _is_h3_2_hss_applicable),
    "I2": RuleDefinition("I2", None, False, ("area",), _has_interaction),
}


PROFILE_RULE_MAP = {
    ProfileType.W_SHAPE: [
        "D2-1",
        "D2-2",
        "E3",
        "E4",
        "E7",
        "F2-1",
        "F2-2",
        "F3-1",
        "F3-2",
        "F3-3",
        "F4-1",
        "F4-2",
        "F4-3",
        "F4-4",
        "F5-1",
        "F5-2",
        "F5-3",
        "F5-4",
        "F6-1",
        "F6-2",
        "G2-Vx",
        "G6-Vy",
    ],
    ProfileType.CHANNEL: ["D2-1", "D2-2", "E3", "E4", "E7", "F2-1", "F2-2", "F6-1", "F6-2", "G2-Vx", "G6-Vy"],
    ProfileType.DOUBLE_ANGLE: ["D2-1", "D2-2", "E3", "E4", "E7", "F9", "G3-Vx", "G3-Vy"],
    ProfileType.RECTANGULAR_HSS: [
        "D2-1",
        "D2-2",
        "E3",
        "E4",
        "E7",
        "F7-1-Mx",
        "F7-1-My",
        "F7-2-Mx",
        "F7-2-My",
        "F7-3-Mx",
        "F7-3-My",
        "F7-4-Mx",
        "F7-4-My",
        "G4-Vx",
        "G4-Vy",
        "H1",
        "H3-1",
        "H3-2",
    ],
    ProfileType.CIRCULAR_HSS: [
        "D2-1",
        "D2-2",
        "E3",
        "E4",
        "E7",
        "F8-1-Mx",
        "F8-1-My",
        "F8-2-Mx",
        "F8-2-My",
        "G5-Vx",
        "G5-Vy",
        "H1",
        "H3-1",
        "H3-2",
    ],
    ProfileType.SINGLE_ANGLE: [
        "D2-1",
        "D2-2",
        "E3",
        "E5",
        "E7",
        "F10-1-Mx",
        "F10-1-My",
        "F10-2-Mx",
        "F10-2-My",
        "F10-3-Mx",
        "F10-3-My",
        "G3-Vx",
        "G3-Vy",
    ],
    ProfileType.SOLID_RECTANGULAR: ["D2-1", "D2-2", "E3", "F11-1-Mx", "F11-1-My", "F11-2-Mx", "F11-2-My"],
    ProfileType.SOLID_CIRCULAR: ["D2-1", "D2-2", "E3", "F11-1-Mx", "F11-1-My", "F11-2-Mx", "F11-2-My"],
    ProfileType.FILLED_RECTANGULAR: ["D2-1", "D2-2", "E3", "F11-1-Mx", "F11-1-My", "F11-2-Mx", "F11-2-My"],
    ProfileType.FILLED_CIRCULAR: ["D2-1", "D2-2", "E3", "F11-1-Mx", "F11-1-My", "F11-2-Mx", "F11-2-My"],
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


def _required_fields_for_h3(profile_type: str) -> Tuple[str, ...]:
    if profile_type == "CIRCULAR_HSS":
        return ("area", "j", "od", "tdes")
    if profile_type == "RECTANGULAR_HSS":
        return ("h", "b", "tdes")
    return tuple()


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
        if rule_id in {"H3-1", "H3-2"}:
            return _required_fields_for_h3(profile_type)
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
    def _raise_not_implemented(rule_id: str, section: Section, *, extra: Optional[dict] = None) -> None:
        details = {"section": section.name, "profile_type": section.type, "rule_id": rule_id}
        if extra:
            details.update(extra)
        raise RuleNotImplementedError("Applicable AISC clause is not implemented.", details=details)

    @classmethod
    def _is_e7_applicable(cls, case: SteelCase, section: Section) -> bool:
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
    def _validate_flexure_selection(cls, case: SteelCase, section: Section, selected_rule_ids: List[str]) -> None:
        if not _has_any_flexure(case, section):
            return
        flexure_rules = {
            "F2-1",
            "F2-2",
            "F3-1",
            "F3-2",
            "F3-3",
            "F4-1",
            "F4-2",
            "F4-3",
            "F4-4",
            "F5-1",
            "F5-2",
            "F5-3",
            "F5-4",
            "F6-1",
            "F6-2",
            "F7-1-Mx",
            "F7-1-My",
            "F7-2-Mx",
            "F7-2-My",
            "F7-3-Mx",
            "F7-3-My",
            "F7-4-Mx",
            "F7-4-My",
            "F8-1-Mx",
            "F8-1-My",
            "F8-2-Mx",
            "F8-2-My",
            "F9",
            "F10-1-Mx",
            "F10-1-My",
            "F10-2-Mx",
            "F10-2-My",
            "F10-3-Mx",
            "F10-3-My",
            "F11-1-Mx",
            "F11-1-My",
            "F11-2-Mx",
            "F11-2-My",
        }
        selected_f = [rule_id for rule_id in selected_rule_ids if rule_id in flexure_rules]
        if selected_f:
            return

        profile = section.type.upper()
        if profile == "CHANNEL" and _has_major_flexure(case, section):
            cls._raise_not_implemented(
                "ChapterFSelection",
                section,
                extra={"reason": "Channel major-axis flexure outside compact F2 scope."},
            )
        if profile == "CIRCULAR_HSS":
            cls._raise_not_implemented(
                "F8",
                section,
                extra={"reason": "Round HSS exceeds F8 applicability limit D/t < 0.45E/Fy or lacks D/t."},
            )
        cls._raise_not_implemented("ChapterFSelection", section, extra={"reason": "No Chapter F rule selected."})

    @classmethod
    def _validate_composite_scope(cls, case: SteelCase, section: Section) -> None:
        composite = case.composite
        if composite is None:
            return
        role = composite.role.value
        method = composite.nominal_strength_method.value
        profile_type = section.type.upper()

        if method not in {"PLASTIC", "ELASTIC"}:
            cls._raise_not_implemented(
                "I1.2",
                section,
                extra={
                    "reason": "Only PLASTIC and ELASTIC methods are implemented in current Chapter I scope.",
                    "nominal_strength_method": method,
                },
            )

        if role == "ENCASED_MEMBER" and profile_type != "W":
            cls._raise_not_implemented(
                "I2",
                section,
                extra={"reason": "Encased member scope is limited to W steel cores.", "role": role},
            )
        if role == "FILLED_MEMBER" and profile_type not in {"RECTANGULAR_HSS", "CIRCULAR_HSS"}:
            cls._raise_not_implemented(
                "I2",
                section,
                extra={"reason": "Filled member scope is limited to rectangular and round HSS.", "role": role},
            )
        if role == "COMPOSITE_BEAM" and profile_type != "W":
            cls._raise_not_implemented(
                "I3",
                section,
                extra={"reason": "Composite beam scope is limited to W steel beams.", "role": role},
            )
        if abs(case.loads.Tu) > 0.0:
            cls._raise_not_implemented(
                "ChapterI-Torsion",
                section,
                extra={"reason": "Composite Chapter I torsion provisions are outside current scope."},
            )

    @classmethod
    def _get_composite_rules(cls, case: SteelCase, section: Section) -> List:
        cls._validate_composite_scope(case, section)
        role = case.composite.role.value
        rules: List = [CompositeI1Rule()]

        if role == "ENCASED_MEMBER":
            if case.loads.Pu > 0.0:
                rules.append(CompositeI2EncasedCompressionRule())
            elif case.loads.Pu < 0.0:
                rules.append(CompositeI2EncasedTensionRule())
            rules.append(CompositeI3_3Rule())
            if _has_shear(case, section):
                rules.extend(
                    [
                        CompositeI4_1aEncasedRule(),
                        CompositeI4_1bEncasedRule(),
                        CompositeI4_1cEncasedRule(),
                        CompositeI4_1EncasedGoverningRule(),
                    ]
                )
            return rules

        if role == "FILLED_MEMBER":
            if case.loads.Pu > 0.0:
                rules.append(CompositeI2FilledCompressionRule())
            elif case.loads.Pu < 0.0:
                rules.append(CompositeI2FilledTensionRule())
            rules.append(CompositeI3_4Rule())
            if _has_shear(case, section):
                rules.append(CompositeI4_1FilledRule())
            return rules

        if role == "COMPOSITE_BEAM":
            if case.loads.Pu != 0.0:
                cls._raise_not_implemented(
                    "I2",
                    section,
                    extra={"reason": "Composite beam axial design is outside current Chapter I implementation."},
                )
            if _has_any_flexure(case, section):
                rules.extend([CompositeI3_1aRule(), CompositeI3_1bRule(), CompositeI3_1cRule()])
            if _has_shear(case, section):
                rules.append(CompositeI4_3BeamDeckSteelOnlyRule())
            return rules

        cls._raise_not_implemented("ChapterI", section, extra={"reason": "Unknown composite role.", "role": role})
        return rules

    @classmethod
    def get_rules(cls, case: SteelCase, section: Section) -> List:
        if case.composite is not None:
            return cls._get_composite_rules(case, section)

        profile_type = section.type.upper()
        if profile_type not in PROFILE_RULE_MAP:
            raise RuleNotImplementedError(
                "No routing configuration exists for profile type.",
                details={"section": section.name, "profile_type": section.type},
            )

        active_rules = []
        active_rule_ids: List[str] = []
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
            active_rule_ids.append(rule_id)

        cls._validate_flexure_selection(case, section, active_rule_ids)
        return active_rules
