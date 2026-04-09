# AISC 360-22 Traceability Matrix

This matrix is the normative traceability baseline for the current P0 scope.
Reference document: `a360-22w.pdf`.

| Clause | Status | Engine entrypoint | Core calculation function(s) | Test reference |
|---|---|---|---|---|
| D2-1 / D2-2 (Tension) | Implemented | `domain/rules/tension_rule.py::TensionRule.check` | `codes/aisc_360_22/tension_calc.py` | `tests/test_normative_d2_e3_f2.py::test_D2_tension_capacity_in_kN_and_clause` |
| E3-1 / E3-2 / E3-3 / E3-4 (Compression) | Implemented | `domain/rules/axial_rules.py::AxialE3Rule.check` | `codes/aisc_360_22/axial_calc.py` | `tests/test_normative_d2_e3_f2.py::test_E3_axial_rule_returns_clause_and_positive_capacity_kN` |
| F2-1 (Major flexure, current simplified scope) | Implemented | `domain/rules/flexure_rule.py::FlexureRule.check` | `codes/aisc_360_22/flexure_calc.py` | `tests/test_normative_d2_e3_f2.py::test_F2_flexure_rule_uses_kN_m_and_absolute_demand` |
| E4-1 (Torsional/Flexural-Torsional) | Implemented | `domain/rules/axial_rules.py::AxialE4Rule.check` | `codes/aisc_360_22/axial_calc.py::calculate_Fe_torsional / calculate_Fe_flexural_torsional` | `tests/test_chapter_e_rules.py::test_e4_channel_rule_returns_capacity` |
| E5-1 (Single angles, mode-dependent) | Implemented | `domain/rules/axial_rules.py::AxialE5Rule.check` | `codes/aisc_360_22/axial_calc.py::calculate_e5_effective_slenderness` | `tests/test_chapter_e_rules.py::test_e5_mode_one_leg_is_more_conservative_than_both_legs` |
| E7-1 (Slender elements in compression) | Implemented | `domain/rules/axial_rules.py::AxialE7Rule.check` | `codes/aisc_360_22/axial_calc.py::calculate_q_factor / calculate_Fcr_slender` | `tests/test_chapter_e_rules.py::test_e7_reduction_decreases_capacity_vs_e3` |
| F7 / F8 / F9 / F10 | Blocked (Not Implemented) | `domain/routing/profile_router.py` | N/A | Covered by router fail-hard policy |
| G2 / G4 / G5 | Blocked (Not Implemented) | `domain/routing/profile_router.py` | N/A | `tests/test_profile_router.py::test_router_fails_hard_when_non_implemented_rule_is_required` |
| H1 / I2 | Blocked (Not Implemented) | `domain/routing/profile_router.py` | N/A | Covered by router fail-hard policy |
| E4 for 2L without J/Cw in catalog | Blocked by data (strict policy) | `domain/routing/profile_router.py` | N/A until catalog completion | `tests/test_chapter_e_rules.py::test_engine_reports_missing_2l_e4_properties` |
