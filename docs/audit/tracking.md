# Seguimiento maestro de hallazgos — HFS-002

Fecha: 2026-10-26. Este es el registro vivo; [findings.md](findings.md) conserva el diagnóstico HFS-000 aceptado y no se reescribe. [ROADMAP](../ROADMAP.md) conserva tareas y prioridades resumidas. Actualizar ambos si cambia prioridad o asignación; no mantener una segunda copia completa del diagnóstico. Ningún hallazgo se cierra por aprobar HFS-000 o por redactar estos ADR.

Estado de todos los IDs: **abierto**. «Observado» acredita código/ejecución; «riesgo» conserva incertidumbre normativa/física. Las tareas son destinos de seguimiento, no correcciones ejecutadas. La [matriz HFS-002](../normative/hfs002-applicability.md) y su [contraste/riesgos](../normative/hfs002-implementation.md) documentan la revisión nueva, sin modificar findings HFS-000.

| ID | Prioridad | Certeza / asunto | Tarea de seguimiento | Condición mínima de cierre, además de evidencia y revisión |
|---|---|---|---|---|
| F-01 | P0 | W sin interacción reproducido; H1.1/2 local incluye familias elegibles no HSS, H2 alternativa según condiciones | HFS-010/034 | Cobertura por combinación y dominio; no copiar HSS indiscriminadamente |
| F-02 | P0 | Observado: PASS sin checks | HFS-010 | Caso vacío/incompleto nunca PASS |
| F-03 | P0 | F2 sin razones reproducido; F2/B4.1 exigen alas/alma compactas, no default | HFS-012 | Derivación con geometría fiable o bloqueo; fronteras y canal con ancho correcto |
| F-04 | P0 | Observado: campos/cargas omitidos | HFS-011 | Typos y faltantes tratados según contrato explícito |
| F-05 | P0 | Observado: resumen mezcla dimensiones | HFS-014 | Gobernante por DCR con eje/unidad y sin mínimo incompatible |
| F-06 | P0 | H3.2/H3-6 exige máximo de cocientes; max demanda/max capacidad no equivale, contraejemplo independiente 0,5 vs 0,25 | HFS-013/033/034 | Resolver ejes y capacidades con HSS real asimétrico; discrepancia algebraica confirmada, impacto físico por caso pendiente |
| F-07 | P0 | D1/E2: límites 300/200 son User Notes; E5≤200 sí condiciona alternativa | HFS-015 | Recomendaciones separadas del cumplimiento y contexto de cláusula |
| F-08 | P0 | Observado: Vu contradictorio reemplazado | HFS-011/013 | Política única de cargas/ejes sin pérdida silenciosa |
| F-09 | P0 | Observado: DCR redondeado incompatible visualmente con FAIL | HFS-015 | Valores brutos y presentación diferenciados; fronteras |
| F-10 | P0 | NaN axial confirmado; otros dominios pendientes | HFS-011/040 | Finitud/dominios comprobados por frontera de entrada |
| F-11 | P1 | Etiquetas invertidas observadas; física pendiente | HFS-013/033 | Correspondencia matemática eje/demanda/capacidad |
| F-12 | P1 | Selección ID observada; significado físico pendiente | HFS-033/040 | D/t contrastado con fuente y geometría real |
| F-13 | **P0** | Duplicados reales de geometría diferente, sobrescritura confirmada; mitigación acordada antes de G1 | HFS-016 acotada; alcance completo HFS-040 | Identidad ambigua no puede seleccionar geometría silenciosamente; catálogo contrastado; no corregido ahora |
| F-14 | P1 | Fallback de escala observado; impacto por fuente pendiente | HFS-040 | Unidades de importación inequívocas y pruebas dimensionales |
| F-15 | P1 | Geometría custom duplicada | HFS-021; DRY-05 | Un constructor consumido por cálculo y reporte, equivalencia probada |
| F-16 | P1 | CLI con responsabilidades mezcladas | HFS-021/024 | Ejecución/reportes separados con propósito, sin otro motor |
| F-17 | P1 | Reglas compuestas concentran cálculo numérico y reporte | HFS-035/036; extracción posterior justificada | Separación por dominio probado, no por longitud del archivo |
| F-18 | P1 | Parámetros fijos observados; suficiencia numérica pendiente | HFS-036 | Convergencia/equilibrio y tolerancias documentados |
| F-19 | P1 | UN F4 PDF124 describe alternativa conservadora F5; fidelidad de código y dominio siguen pendientes | HFS-032 | Fuente, dominio y conservadurismo contrastados, traza de alternativa explícita |
| F-20 | P1 | Capacidades H/I requieren auditoría | HFS-034/035 | Oráculos por trayectoria/método y origen de capacidades |
| F-21 | P1 | Resultado sin unidad/completitud/bruto dedicados | HFS-022/024 | Contrato común y traza sin inferencias de interfaz |
| F-22 | P1 | Defaults observados; hipótesis de estabilidad pendientes | HFS-022/037 | Procedencia de K/Cb/demandas y alcance explícitos |
| F-23 | P1 | Pruebas existentes insuficientes para validación exhaustiva | HFS-031–038/041/042 | Referencias independientes por dominio publicitado |
| F-24 | P1 | Sin empaquetado/CI, requisitos abiertos | HFS-020 | Instalación y tests fuera del checkout reproducibles |
| F-25 | P1 | Históricos/temporales versionados | Política HFS-001; limpieza posterior separada | Trazabilidad recuperable y justificación antes de retirar |
| F-26 | P1 | Matriz manual sin prueba de cobertura exhaustiva | HFS-023/024/030 | Registro único trazable a funciones y pruebas |
| F-27 | P1 | Procedencia de catálogo pendiente; anomalías observadas | HFS-040 | Fuente, conversiones e identidad comprobadas |
| F-28 | P2 | Permisos/erratas pendientes | HFS-030 y revisión documental | Registro verificable de edición, permisos y erratas |
| F-29 | P1 | Observado: lote vacío PASS | HFS-014 | Cardinalidad/completitud y agregación verificadas |
| F-30 | P1 | Riesgo de cobertura normativa no auditada | HFS-030–038/041 | Validación independiente; no cierre global por tests verdes |
| F-31 | **P0** | Confirmado en sonda: un check F de eje menor oculta demanda mayor sin evaluar | HFS-002/010; contraste de flexión HFS-032 | Cobertura exigida por componente; caso real y frontera además de sonda |
| F-32 | **P1** | Confirmado: FAIL con exit 0; riesgo para consumidores, no regresión | HFS-022 y documentación CLI al adaptar HFS-021 | Semántica ejecución/diseño documentada y consumidores probados; transición si cambia |
| F-33 | P0 propuesto | Biaxial sin axial omitida: sonda W y gating H/I; N29/N42 | HFS-010/034/035 | Obligaciones por combinación, incluso Pu=0; ruta por familia validada |
| F-34 | P0 propuesto | Tres roles compuestos con flexión pura 1 y 1 000 000 kNm conservan PASS sin check resistente M | HFS-010/035 | No confundir cuantía/transferencia con flexión; evaluar/bloquear M por eje y etapa |
| F-35 | P0 propuesto | E7 usa QFy/Ag; S22 E7 prescribe Fn·Ae, sin equivalencia demostrada | HFS-010/031/041 | Método por dominio/área efectiva, oráculos y revisión de consumidores H/I |
| F-36 | P0 propuesto | E5 implementa rama única y no acredita condiciones; E4 ángulo sin regla registrada | HFS-010/031/041 | Condiciones de conexión y ramas 75/80/200; flexotorsión/áreas y oráculos |
| F-37 | P1 | IDs parecen ecuaciones; H1-2 usado para interacción de tracción aunque fuente define Pey | HFS-023/024/034/035 | Separar IDs/citas; contrastar fórmula de tracción y todos consumidores |
| F-38 | P1 | Verificaciones complementarias/condiciones no acreditadas E6/F13/G7/H4/I1/I6, etapas y conexiones | HFS-010/031–038 | Alcance explícito; no omitir precondiciones ni validar por existencia de cualquier check |

Las reproducciones, archivos/símbolos y salidas de F-01 a F-32 están en [findings](findings.md). F-31 tiene `test_channel_both_axes_must_block_if_major_axis_is_unsupported`; F-32 se acredita en [examples.json](evidence-clean/examples.json) y `run.py::main`. No se inventa un xfail para F-32: el exit actual es un contrato observable cuyo cambio exige decisión explícita.

## Justificación de prioridades y discrepancias de planificación

**F-13: recomendar P0.** HFS-000 observó HEA 100 duplicado con A=2124/2534 mm² y d=96/114 mm; se retiene la última entrada según el orden, sin aviso. Esto compromete qué geometría se calcula aun con fórmulas correctas. [catalog-duplicates.json](catalog-duplicates.json) preserva ambas. No se sabe cuál nombre/fila es correcto; renombrar automáticamente sería otra hipótesis. PTEXXMM de área cero añade riesgo de calidad, pero no prueba una capacidad incorrecta en cada caso.

Acuerdo documental HFS-002: se registra **HFS-016**, fase 1, dependencias 000/001, antes de G1, como mitigación estrecha de identificación/rechazo de F-13. HFS-040 conserva importación canónica completa. No se implementa HFS-016 ahora. Rechazar duplicados globalmente podría impedir cargar ejemplos: exige diseño y prueba de transición, no un arreglo incidental. Prioridad P0 ratificada para este seguimiento por la ubicación acordada antes de G1; la solución técnica sigue pendiente.

**F-31 permanece P0:** omite una componente y puede declarar PASS; la sonda es sintética, por lo que confirmar su impacto en perfiles reales sigue pendiente. **F-32 permanece P1:** exit 0 no significa por sí mismo defecto de cálculo; preservarlo y exigir lectura del JSON es compatible con el contrato actual. Cualquier nueva semántica se revisará con sus consumidores.

HFS-002 precisó F-06 y F-07 con S22 local; sus correcciones y efectos por caso siguen pendientes. F-12/18/19/20/27/28/30 conservan incertidumbres. No se rebaja una prioridad porque falta prueba numérica ni se afirma validación física a partir de una sonda. Una solución DRY de F-15/16/17 tampoco cierra automáticamente problemas de cálculo. Evidencia F-33/34 y contraejemplo F-06: [probes.json](hfs002/probes.json); programa reproducible [probes.py](hfs002/probes.py). F-35/36/37/38 son contrastes estáticos, no nuevas pruebas normativas aprobadas.

## Cambios de estado

Para cerrar un ID registrar tarea/commit, reproducción previa, resultado posterior, prueba independiente cuando corresponda y alcance de revisión. Si solo una parte se resuelve, mantener abierto con alcance residual. Los 11 `known defect` y toda la evidencia HFS-000 permanecen intactos. HFS-001 aprobada arquitectónicamente; HFS-002 documental presentada para revisión. Ningún defecto cerrado; HFS-010/016 no ejecutadas.
