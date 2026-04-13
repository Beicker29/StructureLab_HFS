# AISC 360-22 Traceability Matrix

This matrix is the normative traceability baseline for the current P0 scope.
Reference document: `a360-22w.pdf`.

| Clause | Status | Engine entrypoint | Core calculation function(s) | Test reference |
|---|---|---|---|---|
| D2-1 / D2-2 (Tension, con `Ae = U*An` segun D3) | Implemented | `domain/rules/tension_rule.py::TensionRule.check` | `codes/aisc_360_22/tension_calc.py` | `tests/test_normative_d2_e3_f2.py::test_D2_tension_capacity_in_kN_and_clause` |
| E3-1 / E3-2 / E3-3 / E3-4 (Compression) | Implemented | `domain/rules/axial_rules.py::AxialE3Rule.check` | `codes/aisc_360_22/axial_calc.py` | `tests/test_normative_d2_e3_f2.py::test_E3_axial_rule_returns_clause_and_positive_capacity_kN` |
| F2 / F3 / F4 / F5 / F6 / F7 / F8 / F10 / F11 (Flexion, LRFD-only scope) | Implemented | `domain/rules/flexure_rule.py` | `codes/aisc_360_22/flexure_calc.py` | `tests/test_chapter_f_rules.py`, `tests/test_normative_d2_e3_f2.py::test_F2_flexure_rule_uses_kN_m_and_absolute_demand` |
| E4-1 (Torsional/Flexural-Torsional) | Implemented | `domain/rules/axial_rules.py::AxialE4Rule.check` | `codes/aisc_360_22/axial_calc.py::calculate_Fe_torsional / calculate_Fe_flexural_torsional` | `tests/test_chapter_e_rules.py::test_e4_channel_rule_returns_capacity` |
| E5-1 (Single angles, mode-dependent) | Implemented | `domain/rules/axial_rules.py::AxialE5Rule.check` | `codes/aisc_360_22/axial_calc.py::calculate_e5_effective_slenderness` | `tests/test_chapter_e_rules.py::test_e5_mode_one_leg_is_more_conservative_than_both_legs` |
| E7-1 (Slender elements in compression) | Implemented | `domain/rules/axial_rules.py::AxialE7Rule.check` | `codes/aisc_360_22/axial_calc.py::calculate_q_factor / calculate_Fcr_slender` | `tests/test_chapter_e_rules.py::test_e7_reduction_decreases_capacity_vs_e3` |
| F9 | Blocked (Not Implemented) | `domain/routing/profile_router.py` | N/A | Covered by router fail-hard policy |
| G2 / G3 / G4 / G5 / G6 (Cortante) | Implemented | `domain/rules/shear_rules.py` | `codes/aisc_360_22/shear_calc.py` | `tests/test_chapter_g_rules.py`, `tests/test_engine_cli_integration.py::test_cli_returns_json_for_supported_shear_case` |
| H1 (HSS axial+flexion) | Implemented | `domain/rules/combined_hss_rules.py::CombinedH1HssRule.check` | `codes/aisc_360_22/combined_hss_calc.py` + capacities from D/E/F | `tests/test_chapter_h_rules.py::test_router_adds_h1_h3_for_hss_combined_actions` |
| H3-1 / H3-2 (HSS torsion y combinaciones) | Implemented | `domain/rules/combined_hss_rules.py` | `codes/aisc_360_22/combined_hss_calc.py` | `tests/test_chapter_h_rules.py` |
| H3-3 (Non-HSS torsion combined stress) | Blocked (Not Implemented) | `engine.py` guard + router policy | N/A | Covered by fail-hard torsion scope |
| I2 | Blocked (Not Implemented) | `domain/routing/profile_router.py` | N/A | Covered by router fail-hard policy |
| E4 for 2L without J/Cw in catalog | Blocked by data (strict policy) | `domain/routing/profile_router.py` | N/A until catalog completion | `tests/test_chapter_e_rules.py::test_engine_reports_missing_2l_e4_properties` |
