# HFS-024 - Matriz de instrumentacion y pendientes

Vista de los 93 descriptores HFS-023; no es una matriz normativa ni una nueva seleccion.
Generada desde `RULE_DEFINITIONS` y observaciones reales de los 12 ejemplos por `scripts/audit_hfs024.py --probe .`.
Las referencias de origen estan en `evidence/after.zip` (traces-wheel.json); los detalles y limites en [el contrato](../../contracts/hfs024-calculation-traces.md).

71 clases tienen frontera instrumentada; 22 entradas no tienen clase ejecutable. Los ejemplos ejercitan 45 IDs y emiten pasos para 26 IDs.
Esto NO significa que las otras clases esten ausentes ni que las observadas tengan trazabilidad completa. Todas conservan acreditacion normativa NOT_ACCREDITED.
El tipo de paso implementado se describe por grupo en el contrato; esta tabla registra lo observado, sin deducir ramas no ejecutadas.

| ID estable | Propietario check | Frontera | Observado en ejemplos | Productores de pasos observados / pendiente |
|---|---|---|---|---|
| D2-1 | tension_rule:TensionRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| D2-2 | tension_rule:TensionRuptureRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| E3 | axial_rules:AxialE3Rule | Si | Si | `axial_rules:AxialE3Rule.check` |
| E4 | axial_rules:AxialE4Rule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| E5 | axial_rules:AxialE5Rule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| E7 | axial_rules:AxialE7Rule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| F2-1 | flexure_rule:FlexureF2YieldRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F2-2 | flexure_rule:FlexureF2LtbRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F3-1 | flexure_rule:FlexureF3YieldRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F3-2 | flexure_rule:FlexureF3LtbRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F3-3 | flexure_rule:FlexureF3FlbRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F4-1 | flexure_rule:FlexureF4CompressionYieldRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F4-2 | flexure_rule:FlexureF4LtbRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F4-3 | flexure_rule:FlexureF4FlbRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F4-4 | flexure_rule:FlexureF4TensionYieldRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F5-1 | flexure_rule:FlexureF5CompressionYieldRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F5-2 | flexure_rule:FlexureF5LtbRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F5-3 | flexure_rule:FlexureF5FlbRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F5-4 | flexure_rule:FlexureF5TensionYieldRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F6-1 | flexure_rule:FlexureF6YieldRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F6-2 | flexure_rule:FlexureF6FlbRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F7-1-Mx | flexure_rule:FlexureF7YieldMxRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F7-1-My | flexure_rule:FlexureF7YieldMyRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F7-2-Mx | flexure_rule:FlexureF7FlangeMxRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F7-2-My | flexure_rule:FlexureF7FlangeMyRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F7-3-Mx | flexure_rule:FlexureF7WebMxRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F7-3-My | flexure_rule:FlexureF7WebMyRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F7-4-Mx | flexure_rule:FlexureF7LtbMxRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F7-4-My | flexure_rule:FlexureF7LtbMyRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F8-1-Mx | flexure_rule:FlexureF8YieldMxRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F8-1-My | flexure_rule:FlexureF8YieldMyRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F8-2-Mx | flexure_rule:FlexureF8LocalBucklingMxRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F8-2-My | flexure_rule:FlexureF8LocalBucklingMyRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F9 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| F10-1-Mx | flexure_rule:FlexureF10YieldMxRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F10-1-My | flexure_rule:FlexureF10YieldMyRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F10-2-Mx | flexure_rule:FlexureF10LtbMxRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F10-2-My | flexure_rule:FlexureF10LtbMyRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F10-3-Mx | flexure_rule:FlexureF10LegBucklingMxRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F10-3-My | flexure_rule:FlexureF10LegBucklingMyRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F11-1-Mx | flexure_rule:FlexureF11YieldMxRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F11-1-My | flexure_rule:FlexureF11YieldMyRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| F11-2-Mx | flexure_rule:FlexureF11LtbMxRule | Si | Si | `flexure_calc:available_flexural_strength`, `flexure_rule:_build_flexure_result_from_mn` |
| F11-2-My | flexure_rule:FlexureF11LtbMyRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| G2-Vx | shear_rules:ShearG2VxRule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| G3-Vx | shear_rules:ShearG3VxRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| G3-Vy | shear_rules:ShearG3VyRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| G4-Vx | shear_rules:ShearG4VxRule | Si | Si | `hss_shear:evaluate_hss_shear` |
| G4-Vy | shear_rules:ShearG4VyRule | Si | Si | `hss_shear:evaluate_hss_shear` |
| G5-Vx | shear_rules:ShearG5VxRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| G5-Vy | shear_rules:ShearG5VyRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| G6-Vy | shear_rules:ShearG6VyRule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| H1 | combined_hss_rules:CombinedH1HssRule | Si | Si | `flexure_calc:available_flexural_strength`, `combined_hss_rules:_available_flexural_strength`, `combined_hss_rules:_compute_h1_interaction` |
| H3-1 | combined_hss_rules:HssTorsionH3_1Rule | Si | Si | `combined_hss_calc:calculate_available_torsional_strength`, `combined_hss_calc:calculate_nominal_torsional_strength` |
| H3-2 | combined_hss_rules:HssCombinedH3_2Rule | Si | Si | `combined_hss_calc:calculate_available_torsional_strength`, `combined_hss_calc:calculate_h3_6_interaction`, `combined_hss_calc:calculate_nominal_torsional_strength`, `flexure_calc:available_flexural_strength`, `combined_hss_rules:HssCombinedH3_2Rule.check`, `combined_hss_rules:_available_flexural_strength` |
| I2 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| I1 | composite_rules:CompositeI1Rule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I2.ENCASED.COMPRESSION | composite_rules:CompositeI2EncasedCompressionRule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I2.ENCASED.TENSION | composite_rules:CompositeI2EncasedTensionRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| I2.FILLED.COMPRESSION | composite_rules:CompositeI2FilledCompressionRule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I2.FILLED.TENSION | composite_rules:CompositeI2FilledTensionRule | Si | No | Sin pasos; instrumentacion aritmetica pendiente |
| I3.TRANSFER.CONCRETE | composite_rules:CompositeI3_1aRule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I3.TRANSFER.STEEL | composite_rules:CompositeI3_1bRule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I3.TRANSFER.ANCHORS | composite_rules:CompositeI3_1cRule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I3.ENCASED.REINFORCEMENT | composite_rules:CompositeI3_3Rule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I3.FILLED.REINFORCEMENT | composite_rules:CompositeI3_4Rule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I4.ENCASED.STEEL | composite_rules:CompositeI4_1aEncasedRule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I4.ENCASED.RC | composite_rules:CompositeI4_1bEncasedRule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I4.ENCASED.COMBINED | composite_rules:CompositeI4_1cEncasedRule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I4.ENCASED.GOVERNING | composite_rules:CompositeI4_1EncasedGoverningRule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I4.FILLED | composite_rules:CompositeI4_1FilledRule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I4.BEAM.STEEL | composite_rules:CompositeI4_3BeamDeckSteelOnlyRule | Si | Si | Sin pasos; instrumentacion aritmetica pendiente |
| I5 | composite_rules:CompositeI5CombinedRule | Si | Si | `composite_rules:CompositeI5CombinedRule.check` |
| scope.N01 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N02 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N03 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N05 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N09 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N11 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N22 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N28 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N31 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N32 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N33 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N34 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N35 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N44 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| scope.N45 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| F.CHANNEL.MAJOR.OUTSIDE_F2 | - | No | No | Sin implementacion de check; no generar traza ficticia |
| H.INTERACTION.REMAINDER | - | No | No | Sin implementacion de check; no generar traza ficticia |
| I3.MOMENT.ENCASED | - | No | No | Sin implementacion de check; no generar traza ficticia |
| I3.MOMENT.FILLED | - | No | No | Sin implementacion de check; no generar traza ficticia |
| I3.MOMENT.BEAM | - | No | No | Sin implementacion de check; no generar traza ficticia |
