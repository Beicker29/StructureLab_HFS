# AISC 360-22 Traceability Matrix

This is an implementation index, not proof of normative coverage or independent
validation. Requirements come from the independent HFS-002 matrix; current
G/H3 scope, equations and blocks are recorded in [HFS-013](audit/hfs013/report.md).
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
| G2 / G4 / G5 / G6 (Cortante) | Partial; G6 W without torsion; G5 unknown Lv blocks length-dependent branches | `domain/rules/shear_rules.py`, `domain/evaluators/hss_shear.py` | `codes/aisc_360_22/shear_calc.py` | `tests/test_chapter_g_rules.py`, `tests/test_hfs013_directional_h3.py` |
| G3 / G6 channel | Blocked: resisting leg/orientation or flange distribution not established | `domain/rules/shear_rules.py` | No new formulation | `tests/test_hfs013_directional_h3.py` |
| H1 (HSS axial+flexion) | Implemented | `domain/rules/combined_hss_rules.py::CombinedH1HssRule.check` | `codes/aisc_360_22/combined_hss_calc.py` + capacities from D/E/F | `tests/test_chapter_h_rules.py::test_router_adds_h1_h3_for_hss_combined_actions` |
| H3.1 / H3.2 (HSS torsion; equations H3-1 through H3-6) | Partial: rectangular C required, h/t>260 blocked; round unknown L blocks length-dependent branches; Tr/Tc<=0.20 alternative pending | `domain/rules/combined_hss_rules.py` + shared G4/G5 evaluator | `codes/aisc_360_22/combined_hss_calc.py` | `tests/test_chapter_h_rules.py`, `tests/test_hfs013_directional_h3.py` |
| H3.3 (Non-HSS combined stresses; not equation H3-3) | Blocked (Not Implemented); preserves independent checks, INCOMPLETE | `engine.py` coverage diagnostic | N/A | `tests/test_hfs013_directional_h3.py::test_unsupported_non_hss_torsion_does_not_erase_independent_shear` |
| I1 / I2 / I3-1 / I3-3 / I3-4 / I4 / I5 (Composite members, LRFD scope) | Implemented (encased + filled + composite beam; no CPSW) | `domain/routing/profile_router.py` + `domain/rules/composite_rules.py` | `codes/aisc_360_22/composite_calc.py` + Chapter E/G helpers | `tests/test_chapter_i_rules.py` |
| E4 for 2L without J/Cw in catalog | Blocked by data (strict policy) | `domain/routing/profile_router.py` | N/A until catalog completion | `tests/test_chapter_e_rules.py::test_engine_reports_missing_2l_e4_properties` |
