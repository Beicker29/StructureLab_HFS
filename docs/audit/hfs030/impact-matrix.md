# HFS-030 — Cotejo de erratas y mapa de impactos

Fuentes y hashes: [inventario](sources.md). E25 = lista 2025-01-23; E26 = lista
2026-09-23. Las 22 filas corresponden a los grupos de página/disposición de ambas
listas; los cambios múltiples de una figura o párrafo se conservan juntos.
No son nuevos IDs de reglas ni predicados de aplicabilidad.

**HECHO VERIFICADO:** en cada fila se encontró en S22 la redacción anterior
indicada y se leyó la sustitución en la errata local. **INFERENCIA:** la prioridad
expresa el riesgo de usar esa referencia en el motor o de ampliar su alcance.
No significa defecto numérico demostrado. **PENDIENTE:** validación independiente
del cálculo y las cuestiones expresamente indicadas. No se cierran F-ID.

## Correcciones de enero de 2025

| ID / página E25 | S22 impresa / PDF | Disposición; antes → corrección | Tipo | Impacto y prioridad propuesta |
|---|---|---|---|---|
| E25-01 / 1 | 16.1-60 / 128 | F5-1: símbolo izquierdo Mp → Mn; producto Rpg·Fy·Sxc conservado | Editorial / símbolo de resultado | Directo F5 y delegación F4. P1 trazabilidad; no sustituir todas las apariciones de Mp. Grupo A abajo. |
| E25-02 / 1 | 16.1-64 / 132 | F7.4: números F7-10/11/12/13 → F7-8/9/10/11, en ese orden | Referencia | Directo F7: una referencia F7-10 resulta ambigua sin revisión documental. P1; grupo B. No cambia por sí sola la expresión. |
| E25-03 / 1 | 16.1-136 / 204 | Tabla J3.1M, Grupo 150 M12: pretensión 72 → 61 kN | Formulación / valor tabulado | J no implementado como diseño de conexiones; P2 actual, requisito antes de ampliarlo. No cambiar fuerzas de miembros. Grupo X. |
| E25-04 / 1 | 16.1-153 / 221 | J10-7: My, ksi (MPa) → kip-in. (N-mm) | Unidades | J10 sin check dedicado; P2 actual. No confundir con los momentos calculados de F. Grupo X. |
| E25-05 / 1 | 16.1-167 / 235 | Tabla K4.1, K4-2 punzonamiento bajo flexión en plano: φ 0,90 → 0,95 LRFD | Factores | K4 no implementado; P2 actual. No extrapolar a F, G o H3 ni cambiar Ω=1,58. Grupo X. |
| E25-06 / 1 | 16.1-168 / 236 | Tabla K4.1A, segundo límite de esbeltez de rama: desigualdad ≤ en el lado 0,05E/Fyb → ≥; la errata imprime 0,05E/Fy ≥ Db/tb | Aplicabilidad / referencia de variable | K4 no implementado; P1 preventivo: invertir el dominio tiene efecto de seguridad si se implementa. **PENDIENTE** aclarar además Fy frente a Fyb: se preserva exactamente la diferencia documental, sin resolverla por intuición. Grupo X. |
| E25-07 / 1 | 16.1-185 / 253 | N4.1(b), N4.2(b): AWS 8.1.4.2(4) → 8.1.4.2(5) | Referencia / alcance externo | Inspección externa, sin regla; P2. No se cotejó AWS. Grupo X. |
| E25-08 / 1 | 16.1-241 / 309 | Ap. 4.2.4d(c), después de A-4-11: referencia para Pe(T), I2-5 → I2-4 | Referencia | Incendio no implementado; P2 actual. No modifica I2-4 ni I2-5 a temperatura ordinaria. Grupo Y. |
| E25-09 / 1 | 16.1-242 / 310 | Ap. 4.2.4d(d), después de A-4-12: referencia para Pe(T), I2-5 → I2-4 | Referencia | Igual separación que E25-08; P2. Grupo Y. |
| E25-10 / 1 | 16.1-281 / 349 | Ap. 7.3.1(b), L: altura de piso → longitud lateralmente no arriostrada del miembro | Aplicabilidad / definición geométrica | Método de análisis global externo, relación `scope.N03`; P1 documental. No alterar L/Lb/K recibidos ni afirmar que el programa verifica estabilidad global. Grupo Z. |
| E25-11 / 1 | 16.1-447 / 515 | Figura C-I3.8(c): Fcr → Fn en el diagrama y expresiones asociadas | Editorial / símbolos en Commentary | Auxiliares de flexión compuesta; P1, grupo C. No equivale a corrección automática de las resistencias ni al cierre de F-34/F-35. |
| E25-12 / 2 | 16.1-477 / 545 | Figura C-J1.2, alternativas 1 y 2: enlace textual «are» → «and» entre perfiles laminados y armados | Editorial | Detalle de acceso de soldadura externo; P2. Grupo X. |
| E25-13 / 2 | 16.1-615 / 683 | Figura C-A-4.6: base 0,45 → 0,54 en la expresión de Pn(T) correspondiente a A-4-11 | Formulación en figura auxiliar | Incendio no implementado; P2 actual. **No reemplazar el 0,45 de C3**, que permanece en la figura corregida, ni constantes coincidentes de E/F. Grupo Y. |
| E25-14 / 2 | 16.1-624 / 692 | Tabla C-A-4.5: referencias A-4-23…31 → A-4-24…32 | Referencia | Incendio no implementado; P2. Grupo Y. |

## Correcciones de septiembre de 2026

Todas están en la página 1 de E26; son adicionales, no sustituyen E25.

| ID | S22 impresa / PDF | Disposición; antes → corrección | Tipo | Impacto y prioridad propuesta |
|---|---|---|---|---|
| E26-01 | 16.1-lvi / 58 | Glosario HSS: A3.1a(b) → Tabla A3.1 | Referencia | `scope.N01`, materiales/familias HSS; P2. No homologa materiales del catálogo. Grupo Z. |
| E26-02 | 16.1-83 / 151 | H1-2, unidades de Lb: in.^4 (mm^4) → in. (mm) | Unidades | H1 y consumidores I5; P1 documental. La corrección de longitud **no** transforma H1-2 en ecuación de interacción. F-37 sigue abierto. Grupo D. |
| E26-03 | 16.1-109 / 177 | I5-2: Fyr → Fysr en csr | Editorial / variable de formulación | Directo I5 método 4; P1 documental. El cálculo actual ya recibe `fysr_mpa`; concordancia de símbolo, no acreditación integral. Grupo C. |
| E26-04 | 16.1-120 / 188 | I8.4d(3), equivalencia métrica de rigidez elástica de conexión a cortante: 180 → 350000 N/mm | Unidades / criterio de aceptación | I8 no implementado, `scope.N44`; P1 preventivo por magnitud y aceptación de conexión. No modificar rigideces EI del motor. Grupo X. |
| E26-05 | 16.1-202 / 270 | Ap. 2, Fn en A-2-1/2: kips (N) → ksi (MPa) | Unidades | Compuestos de alta resistencia fuera de la implementación declarada de I ordinario; P2 actual. No ampliar límites I1.3. Grupo Y. |
| E26-06 | 16.1-603 / 671 | Commentary Ap. 4.2: D de in. (mm) a in. (m); `a` de Btu/(ft²-s-°F) a Btu/(ft-in.-s-°F), SI W/(m²-°C); SB de escalas °F⁴/°C⁴ a °R⁴/K⁴, respectivamente | Unidades | Modelo térmico no implementado; P1 preventivo por consistencia dimensional. Conservar combinaciones de unidades de la fuente, no aplicar sustituciones globales. Grupo Y. |
| E26-07 | 16.1-603 / 671 | En las dos expresiones para entradas °F: TFK=(TF+479)/1,8 y Tsk=(Ts+479)/1,8 → TF+459 y Ts+459 | Formulación / conversión de temperatura | Modelo térmico no implementado; P1 preventivo. La errata usa 459: no inventar 459,67 ni interpretar ambas ramas como kelvin; revisar conjuntamente E26-06 antes de implementar. Grupo Y. |
| E26-08 | 16.1-630 / 698 | Commentary Ap. 5.2.6: Design Guide 15, sección 1.3 → 4.3 | Referencia | Evaluación de estructuras existentes/remaches fuera del motor; P2. No se obtuvo el Design Guide. Grupo X. |

## Enlaces con código, registro, trazas y pruebas

El [snapshot de 93 entradas](evidence/registry-links.json) contiene IDs exactos,
clases responsables, módulos de cálculo, citas actuales, F-ID, pruebas de software,
referencias independientes declaradas y observaciones de trazas por ejemplo e
índice de evaluación. Se genera leyendo el registro existente y el archivo
histórico HFS-024; **no ejecuta cálculos** ni deriva requisitos normativos del
router. Es evidencia fechada, no una segunda fuente canónica editable.

| Grupo | Entradas HFS-023 / propietarios reales | Trazas HFS-024 / pruebas existentes / limitación |
|---|---|---|
| A: F5 y F4 | `F5-1`…`F5-4`, `F4-1`…`F4-4`; `codes/aisc_360_22/flexure_calc.py::evaluate_f5`, `evaluate_f4`; `domain/rules/flexure_rule.py` | F4 declara delegación a F5; conversión F1 y nominal emitidos, subramas incompletas. `test_chapter_f_rules.py`, `test_hfs012_flexure_selection.py`, `test_hfs017_design_method.py`, `test_hfs024_tracing.py`. **HECHO:** `mn_cfy = rpg * Fy * sx` se presenta como Mn. **PENDIENTE:** equivalencia de geometría/Sxc, todas las ramas y oráculos F5; F-19/30/38. |
| B: F7 | Ocho IDs `F7-{1,2,3,4}-{Mx,My}`; `flexure_calc.py::evaluate_f7`; reglas F7 | Metadatos citan numeración local antigua; no renumerar IDs internos de estados límite. Pasos de nominal/conversión no acreditan F7.4. Pruebas F, HFS-017/024; F-28/30/37. **PENDIENTE:** actualización compatible de citas con revisión explícita y auditoría HFS-032. |
| C: I3/I5 | `I3.MOMENT.FILLED`, `I3.MOMENT.ENCASED`, `I5`; `composite_calc.py::i5_strength_ratio_csr`; `domain/rules/composite_rules.py::_i5_method_4_interaction` y auxiliares de flexión de ese módulo | I5 registra método/valores; no expande todos los cálculos nominales ni I5-2 en un paso independiente. `test_chapter_i_rules.py`, HFS-017/024; referencias independientes y límites en snapshot. **HECHO:** csr usa Asr·Fysr y el llamador pasa `parts['Fysr_mpa']`. **PENDIENTE:** correspondencia de C-I3.8(c), oráculo de ese dominio, equilibrio y métodos I; F-20/23/34/37. No afirmar validación por coincidencia del símbolo. |
| D: H1 | `H1`, consumidores `I5`; `combined_hss_rules.py::CombinedH1HssRule`, `composite_rules.py` | H1 tracción conserva etiqueta legacy H1-2 pero traza `equation=null`; `test_hfs024_tracing.py`, HFS-013 de método y HFS-017 no acreditan esa fórmula. El contrato de longitudes usa mm; no se ha detectado un cálculo de Pey acreditado por esa etiqueta. F-37 persiste. |
| X: conexiones/inspección/rehabilitación | Sin regla específica J3/J10/K4/N4/Ap.5; frontera externa general `scope.N35`. I8 se relaciona con `scope.N44` | Sin productor/check específico ni oráculo numérico en el registro para estas erratas. Las pruebas HFS-010/023 verifican límites/metadatos, no estas disposiciones. No atribuir K4 a H3 por tratar ambos HSS. F-28/30/38, HFS-038/035 futuros. |
| Y: incendio/alta resistencia | No hay regla específica para estas disposiciones de Ap.2/4. I1/I2/I3/I5 ordinarios no acreditan el dominio térmico/alta resistencia | Sin trazas de las operaciones corregidas ni oráculos registrados. Pruebas I no constituyen pruebas de incendio. Similitud con I2-4 no permite trasladar factores, unidades ni dominio. F-28/30/38; mantener fuera de alcance. |
| Z: fuentes/estabilidad | `scope.N01`, `scope.N03`; preparación/materiales y demandas externas, sin cálculo propio de estabilidad global | Descriptores externos, sin regla numérica correspondiente. Ver HFS-010/023 y contratos de entradas; no validan combinaciones de carga o análisis global recibido. F-22/28/38, HFS-037 futuro. |

Los prefijos de archivo de la tabla son relativos a `src/steel_design/`; las
pruebas a `tests/`. El snapshot proporciona referencias exactas y los pasos
históricos, incluidos los casos sin observación. Todas las 93 entradas conservan
`NOT_ACCREDITED`. Los ejemplos observan 45 IDs; ninguno de esos contadores
acredita cumplimiento de una errata.

## Hallazgos documentales adicionales al cotejo de erratas

Estas observaciones se mantienen bajo F-37/F-28 y los F-ID indicados; **no se
atribuyen a una errata oficial que no las menciona**. Se conserva intacto el
registro de runtime y su índice generado para no alterar las trazas existentes.

| ID de observación | HECHO VERIFICADO en S22 / contraste | Consecuencia y pendiente |
|---|---|---|
| L30-01 | F2 está en PDF 121–123 (16.1-53–55); el rango HFS-023 118–121 no cubre F2.2 completo. F3 está en 123–124 (55–56), fuera de su rango registrado 121–122. `scope.N11` cita 118–119, pero F1(a)-(d) está en 120. | P1 F-37: corregir localizadores en una modificación explícita de metadatos/trazas, sin renumerar identidades. |
| L30-02 | A3 está en PDF 74–79 (16.1-6–11), Tabla A3.1 en 75–76; `scope.N01` conserva localizador pendiente. | P2 F-28/37: localizador resuelto documentalmente; verificar materiales no es función de este cotejo. |
| L30-03 | `I3.MOMENT.ENCASED` cita I3.3b/PDF173. I3.3b trata detalles constructivos en PDF172; resistencia nominal y métodos están en I3.3a(a), PDF171–172. | P1 F-37/F-34: referencia sustantiva incorrecta; no considerar un check de cuantía/detalle como resistencia a flexión. |
| L30-04 | E7-1, PDF116/16.1-48, usa Fn·Ae; `axial_calc.calculate_Fcr_slender` usa QFy y las reglas emplean Ag. E5, PDF111–113, exige condiciones y ramas 75/80/200; el helper actual `calculate_e5_effective_slenderness` conserva aproximación de una rama. | F-35/F-36 **P0 propuestos**, abiertos: discrepancias documentales confirmadas, efecto numérico y equivalencia no demostrados. Sin auditoría HFS-031 ni cambios. |
| L30-05 | F2 exige alas/alma compactas; B4.1a distingue ancho completo de ala de canal y semiancho de ala I (PDF88); F3/F4/F5 tienen dominios I, F6 eje menor. | F-31 **P0 abierto**; revisar canal real/resistencia mayor en HFS-032. E25/E26 no aportan una implementación ni cierran esta omisión. |
| L30-06 | H1.2 remite a H1-1a/b para interacción de tracción; H1-2 define Pey (PDF151). F3-3 no es una ecuación de F3. C-I5-1a/b es Commentary, PDF521. | P1 F-37: separar ID/etiqueta/fuente; la errata E26-02 corrige unidades, no esas correspondencias. |
| L30-07 | La User Note F4 permite alternativa F5, PDF124. H3-6, PDF154, especifica el mayor cociente Vr/Vc de ambos ejes y su umbral torsional. | F-19/06/39: respaldo documental acotado; no prueba que todas las operaciones, propiedades y condiciones del código sean correctas. No se reabre ni cierra funcionalidad por mera lectura. |

**HIPÓTESIS no aceptadas como hechos:** que la renumeración F7 cambie capacidades;
que toda aparición `Fyr` de un método auxiliar de I deba reemplazarse; que los
errores tipográficos expliquen F-35/F-36; que un test verde elimine una discrepancia
normativa. Requieren investigación en sus hitos, no búsquedas/reemplazos globales.
