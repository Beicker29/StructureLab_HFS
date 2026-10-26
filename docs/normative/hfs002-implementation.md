# HFS-002 — Norma frente a implementación

Base inspeccionada: `2b96da7cfa160932f78f9501de80d573a6704786`. Los N-ID remiten a la [matriz independiente](hfs002-applicability.md); esta tabla es un contraste del código, no la autoridad para decidir lo requerido. Rutas de código relativas a `src/steel_design/`.

## Superficie aceptada actualmente

| Familia/configuración | Entrada y evidencia | Limitación observable |
|---|---|---|
| W (incluye hoja W/IPE/HEA/HEB) | `sections/loader.py`, `ProfileType`, 319 filas cargadas | La etiqueta no prueba simetría/fabricación ni validez ASTM de toda fila |
| CHANNEL | 32 filas | F2 mayor solo si clasificado compacto; F6 menor puede ocultar mayor no soportado |
| DOUBLE_ANGLE | 639 filas | F9 declarado no implementado; ejemplo bloqueado por falta J/Cw para E4; no prueba que toda la familia esté bloqueada |
| SINGLE_ANGLE | 137 filas | E5 requiere modo `one_leg/both_legs`; opciones F10 de eje/restricción/toe no acreditan por sí mismas condiciones normativas |
| RECTANGULAR_HSS / CIRCULAR_HSS | 80 / 21 filas | Clasificación/geometría de catálogo pendientes; circular F8 bloqueado si D/t ausente o ≥0,45E/Fy |
| SOLID_RECTANGULAR / SOLID_CIRCULAR | `custom_section` B/H o diámetro | D/E/F11; cortante custom y torsión no HSS rechazados |
| FILLED_RECTANGULAR / FILLED_CIRCULAR | Alias legacy en `PROFILE_RULE_MAP` | En esa tabla remiten a **macizos F11**, no al rol compuesto `FILLED_MEMBER`; no contar como otras dos familias físicas |
| ENCASED_MEMBER | `composite.role`, núcleo W únicamente | LRFD, métodos nominales PLASTIC/ELASTIC; otras secciones rechazadas |
| FILLED_MEMBER | Rol compuesto con HSS rectangular/circular | LRFD; PLASTIC/ELASTIC; no confundir con alias legacy |
| COMPOSITE_BEAM | Rol compuesto con W+losa | LRFD; axial distinto de cero rechazado; chequeos ejecutados no comprueban resistencia a M |

Catálogo HFS-000: 1228 registros cargados, 1223 retenidos tras sobrescritura; las cantidades de familia son **antes** de deduplicar. Fuente preservada: [catalog.json](../audit/evidence-clean/catalog.json), hash Excel `5aaaf953a32e77e6d9985e9f91db82702d70b3ee0930a2eb6e695e297a5f1359`. No se reimportó a otro formato ni se modificó. Nombres repetidos/propiedades dudosas siguen F-13/27.

`Section.type` es string, pero el router rechaza tipos sin mapa. Acero solo admite LRFD/ASD en D/E/G y torsión HSS sin flexión; `validate_case` rechaza toda flexión ASD. Todo compuesto ASD y métodos STRAIN_COMPAT/EFFECTIVE_STRAIN se rechazan. Son límites de software, **no prohibiciones de AISC**. Los métodos I5 tienen además selección propia; un enum nominal PLASTIC/ELASTIC no valida todas sus rutas. No hay web/API nuevas.

## Leyenda de evidencia

- **P**: existe implementación parcial o candidata; no significa validada ni completa.
- **A**: no se identificó evaluación correspondiente en el flujo inspeccionado.
- **B**: rechazo explícito de ese alcance; conservarlo hasta tener soporte validado.
- **R**: regresión original/HFS-000. **K**: caracterización de defecto, no aceptación del resultado. **L**: contraste documental independiente con S22 local. **O-limitada**: constante/aritmética independiente acotada; no cubre todas las ramas.

La columna de validación responde si se dispone de evidencia independiente para **toda la verificación**: ninguna fila alcanza ese estado en esta tarea. No se borran pruebas útiles: D2 y conversión de momento tienen valores esperados explícitos. Positividad, selección de IDs y ejemplos smoke no validan el capítulo. Los tests se localizan en `tests/test_*.py`; reproducibilidad nueva en [informe](../audit/hfs002/report.md).

| N-ID | Implementación actual / evidencia de código | Estado y validación independiente disponible | Vacío / seguimiento |
|---|---|---|---|
| N01 | `models.py`, `domain/validation.py`; cargas recibidas, no combinadas | P; R/K; no validación de procedencia | F-04/10/22; alcance y combinación externa |
| N02 | `axial_calc.classify_compression_elements`, selector W/canal, `composite_calc.filled_section_classification_i1_4`, loader | P; R/K/L; sin oráculos completos por tabla | F-03/12/14/27; fabricación, tablas distintas y máximo permitido no se deducen del tipo |
| N03 | K/L/Cb y offsets aportados; `axial_rules._e4_components` | P como datos; A análisis global; no validación C | F-22; defaults no prueban análisis ni arriostramiento |
| N04 | `tension_rule`, `tension_calc`, `TensionEvaluator`; An/U aportados y Ae≤Ag en engine | P; R y O-limitada: `test_normative_d2_e3_f2` 310,5 kN para fluencia LRFD; D3 producto comprobado | Derivación An/U y todas configuraciones/conexiones no auditadas; F-23 |
| N05 | Sin regla D4 ni detalle armado en selección | A; L | F-38; no ignorar en 2L traccionado |
| N06 | `AxialE3Rule`, `calculate_Fe_flexural/calculate_Fcr` | P; R, sin oráculo completo; test E3 citado exige positividad | F-23/30; también se selecciona junto a E7 sin representar dominio por estado |
| N07 | `AxialE4Rule`, `_e4_components`; requisitos por familia del router | P; R; sin validación completa de ejes/offsets/simetría | Ángulo no tiene E4 registrado; E7 puede llamar componentes E4. No equiparar ausencia de check con ausencia de cálculo ni con cobertura; F-36 |
| N08 | `AxialE5Rule`, `calculate_e5_effective_slenderness` | P; L confirma rama única `72+0.75*slenderness` para one_leg; no oráculo independiente de conjunto | F-36: no ramas >80/espacial ni cinco condiciones E5 acreditadas |
| N09 | Sin regla E6 ni contrato de conectores a/ri/apriete | A; L | F-38; E3/E4/E7 de 2L no acreditan E6 |
| N10 | `AxialE7Rule`, `calculate_q_factor/calculate_Fcr_slender` | P **discrepante**; L: QFy y Ag frente Fn·Ae E7-1; memoria declara be no modelado | F-35; no se prueba conservadurismo ni equivalencia; no validar por etiqueta E7-1 |
| N11 | `Factors.Cb`, selección y reglas F | P; R; sin verificación independiente de apoyos/diagrama y ejes | F-22/30/38 |
| N12 | `FlexureF2YieldRule/LtbRule`, `flexure_calc.evaluate_f2` | P LRFD, B ASD; R y O-limitada de conversión 310,5 kNm; no oráculo de LTB | F-03; datos ausentes no prueban compacto |
| N13 | F3 Yield/Ltb/Flb y `evaluate_f3` | P LRFD/B ASD; R, no validación completa | ID interno F3-3 no es ecuación F3-3 de S22; F-37 |
| N14 | Reglas F4 delegan a `evaluate_f4_conservative` que usa F5 | P; L: UN F4 PDF124 sí describe alternativa conservadora, no equivale a validar implementación | F-19 permanece: comprobar dominio, factores y traza de alternativa, no reemplazar automáticamente |
| N15 | F5 cuatro reglas y `evaluate_f5` | P LRFD/B ASD; R; no validación completa | N22 ausente; F-30/38 |
| N16 | F6 Yield/Flb; toma `bf_2tf_ratio` también para canal | P; R/K/L; ancho de canal requiere contraste catálogo/código | F-31 y F-03; no atribuir toda selección válida por tener F6 |
| N17 | F7 Yield/Flange/Web/Ltb por x/y | P LRFD/B ASD; R; no oráculos completos | Intercambio de ejes/clasificación y geometría HSS/caja pendientes; F-30; no extender a cajas arbitrarias |
| N18 | F8 Yield/Local por x/y; guard D/t | P/B por límite/método; R; no validación completa | F-12 y combinación sin axial F-33 |
| N19 | F9 `implemented=False` en router | B para flexión 2L; L | Conservar bloqueo, no usar F10 completo por parecido; otro eje no cubierto |
| N20 | F10 Yield/Ltb/Leg por x/y; opciones de conexión | P LRFD/B ASD; R; no evidencia completa de transformación/signos | H2 ausente; F-01/33/30 |
| N21 | F11 Yield/Ltb por x/y y geometría custom | P LRFD/B ASD; R; no validación completa | F-15; interacción N29 ausente |
| N22 | Sin reglas F13 | A; L | F-38; no presumir sin agujeros/rigidizadores por falta de campos |
| N23 | `ShearG2VxRule`, `shear_calc` | P; R; no auditoría independiente de todas ramas G2.1/2/3/4 | No presentar G2 como cobertura de paneles/extremos/rigidizadores; F-30/38 |
| N24 | `ShearG3VxRule/VyRule` para L y 2L | P; R; no oráculo del reparto 2L | F-30/38; G3 nombra ángulo individual/tee, no prueba automática de 2L |
| N25 | `ShearG4VxRule/VyRule`, copia en H | P; R; sin validación física de ejes | F-06/08/11; DRY-04 |
| N26 | `ShearG5VxRule/VyRule`; H usa Lx/Ly para Lv | P; R; sin procedencia de Lv ni geometría acreditada | F-12/22/30; Lv normativo no es longitud de pandeo necesariamente |
| N27 | `ShearG6VyRule` | P; R; sin validación por cada elemento | F-11/30; contexto de torsión y suma/reparto pendientes |
| N28 | Sin regla G7 ni geometría de abertura | A; L | F-38; software no determina si condición está ausente |
| N29 | `CombinedH1HssRule`, solo HSS y Pu≠0 + M; no H2/H1 para W/canal/macizos/ángulos | P HSS; A demás/biaxial sin N; K/L | F-01/33; rama tracción usa suma lineal llamada H1-2, distinta referencia S22: F-37 |
| N30 | `HssTorsionH3_1Rule/HssCombinedH3_2Rule`, `combined_hss_rules` | P; R/L/O-limitada algebraica F-06, no capacidad física validada | F-06 máximo cocientes; revisar umbral y límites sin suponer resto correcto |
| N31 | `engine.run` rechaza torsión no HSS | B; R/L | Sin H3.3 ni análisis de alabeo; preservar rechazo |
| N32 | Sin H4 | A; L | F-38, áreas/perforaciones/posición faltantes |
| N33 | `run.py` admisibilidad D1/E2 | P reporte; L diferencia Specification/UN confirmada | F-07; separar recomendación de condición de E5 |
| N34 | Sin soporte explícito D5/D6/F12 | A/B según tipo | Fuera del alcance; datos insuficientes no deben degradarse a barra común |
| N35 | Sin evaluaciones completas de remisiones externas | A; solo delimitación L | HFS-038; ninguna certificación de miembro/edificio completo |
| N36 | `CompositeI1Rule`, validación de positivos y geometría; retorna demanda=capacidad=1 | P; R/L; sin revisión íntegra I1/materiales/detallado | F-38: I1 PASS no demuestra límites I1.3 ni proporciones/ACI; clasificación no equivale a elegibilidad |
| N37 | `CompositeI2EncasedCompressionRule/TensionRule` | P LRFD/B ASD; R; sin validación independiente completa | F-18/20/30; N44 ausente |
| N38 | `CompositeI2FilledCompressionRule/TensionRule` | P LRFD/B ASD; R; sin validación completa | Clasificación por demanda y piso acero requieren contraste; F-20/35 |
| N39 | `_encased_steel_only_flexural_capacity_axis` usado por I5; `CompositeI3_3Rule` solo cuantía | A check de M puro; P capacidad interna acero solo | F-34: no se ejecuta verificación resistente de flexión pura |
| N40 | `_filled_flexural_capacity_i3_axis` consumido por I5; `CompositeI3_4Rule` solo cuantía | A check de M puro; P capacidad interna | F-34; ausencia de check aunque la función exista |
| N41 | Reglas I4 encasado (alternativas/agregador), relleno y viga | P LRFD/B ASD; R; no validación completa de ejes/ACI/Kc | F-20/38; no requerir que pasen todas las alternativas I4.1 simultáneamente sin justificación |
| N42 | `CompositeI5CombinedRule`; se activa solo Pu≠0 + M | P; R, sin validación independiente completa; A biaxial sin N | F-20/33/37; método 2 y biaxialidad requieren interpretación y oráculos, no aprobación por nombre |
| N43 | `CompositeI3_1a/b/cRule` compara cortantes horizontales; no resistencia M I3.2 | P transferencia; A momento/etapa/ancho efectivo comprobado | F-34/38; demanda horizontal es min(0,85fcAc,FyAs), independiente de M |
| N44 | `_sum_anchor_qn` calcula candidatos I8; no reglas I6 de introducción de fuerzas en columnas | P anclajes viga; A I6 completo; sin validación independiente completa | F-38; no confundir transferencia de viga I3.2d y columna I6 |
| N45 | Roles no presentes y métodos bloqueados; otras configuraciones no modeladas | B/A; sin validación | Fuera del alcance o pendiente; no habilitadas por este documento |

## Revisión explícita de hallazgos críticos

**F-01:** S22 H1.1/2 PDF150–151 admite doble simetría y monosimetría restringida a ejes geométricos; no limita a HSS. C-H1 PDF472 confirma ejemplos de familias, pero la obligación viene de Specification. La sonda W de HFS-000 vuelve a xfail. Solución abierta: H1 o alternativa H2 debidamente implementada, o bloqueo por cobertura; no copiar la regla HSS sin revisar origen de capacidades y dominio. No añadir la antigua restricción Iyc/Iy a H1.1: C-H1 explica su eliminación; H1.3 mantiene condiciones distintas.

**F-03:** F2 exige alma y alas compactas según B4.1. `_w_or_channel_major_flexure_selection` retorna F2 si falta cualquiera de las razones; eso no establece compactación. Resolver mediante geometría confiable que permita derivar razones o error de datos, no con default compacto. En canal, revisar ancho completo frente `bf/2tf` antes de consolidar clasificador. No se modifica catálogo.

**F-06:** H3.2/H3-6, PDF154 / 16.1-86, prescribe el mayor **Vr/Vc por eje**. `_required_shear_demand` devuelve max demandas y `_available_shear_strength` max capacidades por separado. Discrepancia algebraica confirmada con fuente: demandas (50,0) kN, capacidades estipuladas (100,200) kN → requerido 0,5, emparejamiento actual 0,25. No es un oráculo de capacidad física ni prueba de todas las salidas. [probes.json](../audit/hfs002/probes.json) conserva cálculo independiente. La corrección futura requiere además cerrar F-08/11 y comparar H/G con HSS asimétrico real; no basta cambiar un `max` aislado.

**F-31:** el xfail sintético se reprodujo: cualquier F menor hace retornar `_validate_flexure_selection` antes del rechazo mayor. F6 cubre únicamente eje menor; F2 no cubre canal mayor no compacto. Solución de cobertura por componente inequívoca; solución normativa para el canal fuera de F2 permanece pendiente de análisis, no se asigna F3/F4 automáticamente. La sonda no es un canal físico validado; no se inventó un caso real para cerrar el riesgo.

## Nuevos vacíos y riesgos priorizados

Los IDs siguen abiertos en [tracking](../audit/tracking.md). «Confirmado» se acota al contraste/evidencia descrita, no a la magnitud global de error resistente.

| ID / prioridad propuesta | Evidencia / causa | Impacto y propuesta futura |
|---|---|---|
| F-33 / P0 | N29/N42; gating Pu≠0. Sonda W Pu=0, Mx=My=1 → PASS solo F2/F6; F10 exige H2 para biaxial incluso sin axial | Falta interacción biaxial pura. HFS-010 debe bloquear ausencia por combinación; HFS-034/035 resolver ruta por familia, sin motor nuevo |
| F-34 / P0 | N39/40/43; sondas basadas en 3 ejemplos reales, sustituyendo cargas por Pu=0, Mx=1 y luego 1 000 000 kNm | Los tres roles siguen PASS con los mismos checks de cuantía/transferencia. Omisión de demanda M confirmada; no se determina capacidad correcta aquí. HFS-010 cierre/bloqueo; HFS-035 implementación revisada |
| F-35 / P0 | N10; E7-1 requiere Fn·Ae y E7.1/2 determina Ae. Código QFy/Ag no calcula anchos efectivos y memoria lo admite | Discrepancia de método confirmada, conservadurismo/errores por familia pendientes. HFS-010 no anunciar dominio validado; HFS-031+041 oráculos antes de sustitución. Afecta consumidores H/I; no refactorizar copias ahora |
| F-36 / P0 | N07/08; E5 contiene ramas y cinco condiciones, función one_leg solo 72+0,75·esbeltez; E4 no registrado para L | Dominio E5 y flexotorsión no acreditados. Corregir solo tras casos de conexión, fronteras 75/80/200 y relación alas; HFS-031, bloqueo de desconocido HFS-010 |
| F-37 / P1 | N13/29/42: IDs internos parecen ecuaciones; H1 tracción calcula suma y etiqueta H1-2, que en PDF es Pey; I5 repite rama | Trazabilidad y método de tracción pendientes. Es necesario separar ID interno, sección y ecuación; HFS-023/024/034/035. No concluir que suma conservadora equivale a la ecuación citada ni que es insegura en todos los casos |
| F-38 / P1 | N05/09/22/28/32/36/44: faltan condiciones/conexiones/etapas y evaluaciones detalladas; evidencia estática de tablas anteriores | Riesgo de alcance incompleto aunque existan capacidades. HFS-010 debe impedir PASS del alcance solicitado que dependa de ellas; HFS-031/032/033/035/037/038 resuelven detalle. Si reproducción demuestra falso PASS específico, elevar ese subcaso a P0 |

F-35/36 son diagnósticos estáticos contrastados con fuente, **no nuevos xfail** ni ensayos numéricos independientes completos. F-33/34 sí tienen capturas nuevas; F-06 tiene contraejemplo algebraico acotado. La evidencia de HFS-000 no se reescribe.
