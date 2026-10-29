# HFS-031 — Confrontación ecuación, dominio y consumidor

Base `05198f06a63f8405bd96ffbe494be796cdb165e4`. La autoridad de requisitos es
[la matriz independiente](requirements.md); la evidencia cuantitativa está en
[cálculos](calculations.md) y [78 confrontaciones](evidence/probes.json).
Los cuatro estados de este documento **no** modifican CheckStatus,
AnalysisStatus, CoverageStatus, JSON 1.0 ni `NOT_ACCREDITED` del registro.

- **VERIFICADO:** coincidencia demostrada para la fórmula/dominio expresamente
  delimitado; no implica revisión humana ni acreditación de todo el capítulo.
- **INCORRECTO:** contradicción reproducible con la disposición identificada.
- **NO IMPLEMENTADO:** no existe el cálculo/dato necesario para ese requisito.
- **INDETERMINADO:** fuente, geometría, hipótesis o alcance insuficiente para
  decidir con seguridad; no significa no aplicable.

Todos los paths Python siguientes son relativos a `src/steel_design/`.

## Ecuaciones y precondiciones

| Requisitos / ecuación | Implementación responsable y selección | Dictamen acotado y evidencia |
|---|---|---|
| DE-D1 / recomendación D1 | `domain/recommendations.slenderness_recommendations` | **VERIFICADO** por lectura y regresión HFS-015: aviso, no FAIL; longitud fabricada/r mínimo y excepción rod requieren declaración. No se confunde con KL/r. |
| DE-D2Y / D2-1 | `codes/aisc_360_22/tension_calc.calculate_Pn_yielding`, `calculate_available_tensile_strength`, `tension_design_factor`; `TensionRule` | **VERIFICADO** producto FyAg, N→kN, φ=0,90/Ω=1,67 en ambos métodos; Pu<0, demanda absoluta. No prueba procedencia Fy/Ag. |
| DE-D2R / D2-2 | Mismo módulo `calculate_Pn_rupture`; `TensionRuptureRule`; `TensionEvaluator.evaluate` | **VERIFICADO** FuAe, φ=0,75/Ω=2 y mínimo de **disponibles**, no nominales. Ambos checks independientes sobreviven. An/U requeridos por validación pública; no conexión calculada. |
| DE-D3A / D3-1 | `domain/evaluators/tension_evaluator.py` | **VERIFICADO** Ae=UAn para An/U suministrados; motor limita An≤Ag, U∈(0,1]. **NO IMPLEMENTADO** cálculo de An por caminos B4.3. |
| DE-D3MIN y DE-D3T1…8 | `Connection.An/U` son entradas, no una selección de Tabla D3.1 | **NO IMPLEMENTADO** identificación del tipo de conexión, x̄/l, número de pernos, ranuras, piso por elementos conectados y factores tabulados. **INDETERMINADO** validez de An/U de un caso externo. No calificar U=.8 por observar `.8` en una prueba. |
| DE-D4C/T | Sin regla D4; `coverage.build_coverage_plan` crea N05 para doble ángulo | **NO IMPLEMENTADO** conectores/presillas. N05 permanece pendiente; D2 sobre suma de áreas no reemplaza D4. Armados genéricos no representados requieren exclusión externa. |
| DE-D5R/S/BY/DIM, DE-D6R/DIM | Sin familias/contratos de pasador o eyebar | **NO IMPLEMENTADO** D5-1/2, J7 y detalle D5/D6. Familias desconocidas rechazadas explícitamente. Un usuario que codifique un eyebar como sólido ordinario debe declarar condiciones especiales; el motor no autentica la declaración. |
| DE-E1 | `axial_calc.compression_design_factor`, `calculate_available_compressive_strength` | **VERIFICADO** 0,90/1,67 y escala. **INDETERMINADO** suficiencia del mínimo de modos por familia; checks concurrentes no demuestran selección correcta. |
| DE-E2 | `calculate_Fe_flexural`, modelos `Lengths/Factors`, recomendaciones | **VERIFICADO** KL/r para datos positivos. **NO IMPLEMENTADO** cálculo K/análisis de estabilidad C/Ap.7. La tolerancia de E=200000 es validación del motor, no evidencia de estabilidad. |
| DE-E3 / E3-1…4 | `calculate_Fe_flexural`, `calculate_Fcr`, `calculate_Pn`, `axial_rules._e3_components`, `AxialE3Rule` | **VERIFICADO** Euler, dos ramas y eje menor Fe cuando ambos ejes son principales y están completos. `Fy/Fe≤2,25` incluye igualdad. Nominales N y disponibles kN correctos; no redondeo para decidir. |
| DE-E3 selección | `ProfileRouter.get_rules`, E3 siempre si Pu>0 en familias mapeadas, incluso esbeltas | **INCORRECTO** atribuir E3 aislado a elemento esbelto: queda simultáneo a E7, sin limitar dominio. Como check adicional no subsana E7; no recibe crédito de cobertura. **INCORRECTO** E3 directo omite eje ausente usando el otro y puede dar PASS (F-48). Router sí exige rx/ry. |
| DE-B41 / clases | `axial_calc.classify_compression_elements`, `_is_e7_applicable` | **VERIFICADO** coeficientes de W laminada/canal/HSS rectangular/circular/ángulo simple con razones correctas. **INCORRECTO** doble ángulo sin distinguir contacto continuo (caso1) de separado (caso3); ausencia parcial puede etiquetarse non_slender. **NO IMPLEMENTADO** T, I armada identificada, otros rigidizados/no rigidizados. **INDETERMINADO** usar tipo W genérico para cualquier perfil fabricado. F-48. |
| DE-B42 / razones y espesores | `sections/loader.py`, `Section` | Conversión Ix/Iy ×10⁶, J ×10³, Cw ×10⁹ según encabezados del catálogo; valores en mm⁴/mm⁶ al evaluar. **INDETERMINADO** calidad/fuente de cada propiedad y espesor ASTM: no se audita todo catálogo. F-12: fallback D/t usa ID antes que OD, incompatible con E7/B4; F-14 unidades ambiguas y F-27 procedencia geométrica permanecen abiertos. |
| DE-E4A / E4-2/5/6/7/9 | `calculate_ro_for_double_symmetric`, `calculate_Fe_torsional`, `_e4_components`, `AxialE4Rule` | **VERIFICADO** aritmética en doble simetría, centro de corte=centroide, Cw/J/Lz válidos. `ro²=(Ix+Iy)/Ag` es exacto en ese dominio, no en cualquier sección. Oráculo independiente E4-symmetric. |
| DE-E4B / E4-3 | `calculate_Fe_flexural_torsional` | **VERIFICADO** raíz inferior algebraica para datos 0<H≤1 y eje de simetría correctamente elegido; contrastada con raíz racionalizada. No acredita el llamador. `H=None/≤0` se convierte a1 en helper, radicando negativo a0: **INDETERMINADO/INCORRECTO** como política para geometría desconocida; no es disposición AISC. |
| DE-E4B selección del eje | `_e4_components` y `_governing_fe_e4` | **INCORRECTO F-46**: CHANNEL usa Fey aunque el canal de ejes convencionales es simétrico respecto a x, que requiere Fex. Doble ángulo también exige orientación efectiva documentada. H no es obligatorio; fallback1 elimina acoplamiento sin fundamento. Caso consistente: capacidad de E4 se duplica. |
| DE-E4C / E4-4 | No solucionador cúbico; ángulo no tiene E4 en `PROFILE_RULE_MAP` | **NO IMPLEMENTADO** menor raíz general y ángulo que requiere E4; relacionado F-36/F-38. Banco incluye caso reducible de la cúbica con raíz independiente, sin fingir ejecución de esa ecuación. |
| DE-E4D/E/F / E4-10…12 | xa/ya se aceptan y se imprimen en memoria E4, pero no se usan al calcular | **INCORRECTO F-47** al presentar capacidad como E4 para esos datos. **NO IMPLEMENTADO** desplazamiento restringido y análisis general. Mismo resultado con offset0 y offset200, frente a reducción normativa demostrada. |
| DE-E4UN / Cw opcional | Router exige Cw>0 para doble ángulo/canal/W | **NO IMPLEMENTADO** alternativa sin término Cw para doble ángulo; rechazo de cero aun cuando permitido. Es defecto de completitud, no demostración de inseguridad por sí solo. |
| DE-E5COND / cinco condiciones | Motor exige solo `angle_compression_mode` | **NO IMPLEMENTADO** conexión por misma ala, pernos/soldadura, carga intermedia, contexto plano/espacial, ratio<1,7 y límite efectivo≤200. `both_legs` no es E5(b); etiquetas E5-1a/b son IDs legacy, no ecuaciones existentes en S22. F-36/F-37. |
| DE-E5A / E5-1 | `calculate_e5_effective_slenderness` | **VERIFICADO** solo expresión 72+0,75s si s=L/ra≤80 y se cumplen condiciones. **INDETERMINADO** regla en ese rango, porque el llamador entrega max(KxLx/rx,KyLy/ry), no L/ra acreditado. |
| DE-E5A / E5-2 | Mismo helper | **INCORRECTO F-36**: extrapola E5-1 más allá de80. A120: 162 frente a182; resistencia+26,22%. |
| DE-E5B / E5-3/4 | No selector plano/espacial | **NO IMPLEMENTADO**, uso de `one_leg` contradice ambas ramas; ensayos de75 y80 y sus lados. A s120 la extrapolación también sobrestima frente a E5-4 (+3,74%). |
| DE-E5AS/BS | No entradas bl/bs/ala conectada/contexto/ra, rz no usado | **NO IMPLEMENTADO** incremento y piso principal; no se puede corregir solo una constante. Oráculos distinguen rama/piso y límite200. |
| DE-E5MODES / ángulo concéntrico | `AxialE3Rule`, `AxialE5Rule` usan rx/ry y omiten rz | **INCORRECTO F-36** si rx/ry son geométricos como en catálogo: ángulo ideal100×100×10, principal menor19,6583mm, geométrico30,7797mm, disponible120,750 frente283,865kN. Aunque b/t<0,71√(E/Fy) permite omitir flexotorsión, no permite omitir flexión principal. |
| DE-E6END/A/B/DET1…4 | Sin regla E6; doble ángulo usa E3/E4/E7 de sección agregada | **NO IMPLEMENTADO** E6-1/2, deslizamiento y detalle. Oráculos16 configuraciones de conectores/paso; contraste E3 sin modificación difiere. N09 pendiente evita PASS global; F-38. |
| DE-E7BASE / E7-1 | `AxialE7Rule`, `calculate_q_factor`, `calculate_Fcr_slender`, `calculate_Pn` | **INCORRECTO F-35**, método QFy/Ag no demuestra FnAe. Diferencias de ambos signos; no universalmente conservador. |
| DE-E7WIDTH / E7-2…5 | No cálculo de be/de/he ni áreas por elemento | **NO IMPLEMENTADO** método prescrito; Q de cocientes de límites no lo sustituye. En W/canal Q usa primero bf/2tf incluso si canal exige ancho completo (clasificación usa b/t): otra inconsistencia del mismo F-35/F-48. |
| DE-E7ROUND / E7-6 | Rama Q=1 con D/t≤límite | **VERIFICADO** equivalencia aritmética acotada a Ae=Ag y modos correctamente evaluados. No acredita toda ruta E7. |
| DE-E7ROUND / E7-7 y límite superior | Q=0,11E/(FyD/t), sin límite0,45E/Fy | **INCORRECTO F-35** reducción y colocación dentro de curva. Fuera del límite se calcula igualmente, aunque cobertura permanece pendiente. Frontera superior abierta debe rechazarse o explicitar falta de método. |
| DE-E7BASE / selección de Fe | E7 calcula min de E3 y E4 positivos para todas las familias | **INCORRECTO** potencial para ángulo: E7 exige Fn solo de E3. Además filtra Fe=0 de una ruta incompleta en vez de acreditar que ese modo no aplica. No se valida la ruta por registrar `be=None`. |

## Aptitud por dominio y método

| Dominio | LRFD / ASD | Dictamen de esta auditoría | Uso del resultado |
|---|---|---|---|
| Tracción ordinaria, An/U externos justificados, Fy/Fu/Ag correctos | Ambos | **VERIFICADO** D2/D3-1 aritmética y factores | Solo el alcance contractual de tirante sólido concéntrico puede completar cobertura con declaraciones explícitas; no diseño de conexión ni certificación global. |
| Determinación automática An/U, D4/D5/D6 | Ambos | **NO IMPLEMENTADO** | Revisar externamente o rechazar representación impropia; no deducir del PASS D2. |
| E3 aislado, ambos ejes principales, noesbelto y K/L acreditados | Ambos | **VERIFICADO** ecuaciones y factores en banco | Aritmética apta bajo esas hipótesis; cobertura pública de compresión continúa incompleta. |
| E4 doble simetría por centro de corte, propiedades coherentes | Ambos | **VERIFICADO** fórmula acotada | Falta acreditación integral de selección/otros modos; no declarar sección verificada solo por E4. |
| E4 canal, H desconocido, desplazamientos | Ambos | **INCORRECTO** | No usar sus capacidades como demostración normativa; F-46/F-47 abiertos. |
| E4 general no simétrica / estabilidad analítica | Ambos | **NO IMPLEMENTADO** | No sustituir por torsión simple. |
| E5 completo / ángulo con radios geométricos | Ambos | **INCORRECTO** | F-36 abierto; solo subexpresión E5-1 verificada. |
| E6 completo | Ambos | **NO IMPLEMENTADO** | Exige conectores, geometría y detalle no representados. |
| E7 esbelto, todas las familias declaradas | Ambos | **INCORRECTO** | F-35 abierto; no acreditar por reducción de capacidad respecto de E3. |
| Propiedades/condiciones no autenticadas del catálogo y materiales | Ambos | **INDETERMINADO** | Muestra por familia y procedencia capturada; no corrección de datos sin fuente. |

## Seguridad, consumidores y límites de independencia

La puerta HFS-010 solo descarga D2 en el tirante sólido acotado. No se encontró
PASS **global** indebido en las ocho familias de compresión y los escenarios
dirigidos de este banco: permanecen `INCOMPLETE` o rechazo estructurado.
Sí se demuestran **PASS locales falsos** en E7/E4 cuando la demanda se sitúa
entre la resistencia normativa y la calculada. Las reglas directas entregan
`CheckResult` sin plan de cobertura; sus consumidores deben conservar este límite.
No equivale a demostrar ausencia universal de falso PASS con cualquier entrada.

La memoria E4 etiqueta `warping_term_n`, `stvenant_term_n` y
`torsional_stiffness_n`, aunque ECw/L² y GJ tienen dimensión N·mm²,
no N. El denominador Ag·ro² sí es mm⁴ y el cociente MPa es correcto.
Se registra como defecto de unidades de trazabilidad relacionado F-21/F-37;
no se renombra una clave JSON silenciosamente ni se altera el valor calculado.

Mapa de consumidores de Q y Fcr_slender: `AxialE7Rule`,
`combined_hss_rules._available_axial_strength` y
`composite_rules._bare_steel_compression_capacity_k_n`. La búsqueda de usos
establece propagación potencial; **no se ejecuta auditoría H/I ni se validan sus
interacciones**. Cualquier reparación compartida deberá medir explícitamente
ese impacto en la tarea autorizada correspondiente.

`_e3_components/_e4_components` y `_governing_fe_e3/_governing_fe_e4` duplican
parte del cálculo; no se sustituyen en este hito. No hay código retirado, ni
fachada nueva ni motor paralelo. Oráculos stdlib/Decimal son independientes
por diseño. Las muestras sintéticas estipulan propiedades/unidades; los
ejemplos reales son regresión, no calibración de los esperados.
