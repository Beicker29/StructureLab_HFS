# Seguimiento maestro de hallazgos — HFS-001

Fecha: 2026-10-26. Este es el registro vivo; [findings.md](findings.md) conserva el diagnóstico HFS-000 aceptado y no se reescribe. [ROADMAP](../ROADMAP.md) conserva tareas y prioridades resumidas. Actualizar ambos si cambia prioridad o asignación; no mantener una segunda copia completa del diagnóstico. Ningún hallazgo se cierra por aprobar HFS-000 o por redactar estos ADR.

Estado inicial de todos los IDs: **abierto**. «Observado» acredita código/ejecución; «riesgo» conserva incertidumbre normativa/física. Las tareas de la tabla son destinos de seguimiento, no trabajo comenzado. No se construye aquí la matriz de aplicabilidad HFS-002.

| ID | Prioridad | Certeza / asunto | Tarea de seguimiento | Condición mínima de cierre, además de evidencia y revisión |
|---|---|---|---|---|
| F-01 | P0 | Observado: W sin interacción; dominio normativo pendiente | HFS-002/010/034 | Cobertura por combinación y evaluación/bloqueo explícitos |
| F-02 | P0 | Observado: PASS sin checks | HFS-010 | Caso vacío/incompleto nunca PASS |
| F-03 | P0 | Observado: F2 sin razones de esbeltez | HFS-012 | Falta de clasificación bloquea; fronteras verificadas |
| F-04 | P0 | Observado: campos/cargas omitidos | HFS-011 | Typos y faltantes tratados según contrato explícito |
| F-05 | P0 | Observado: resumen mezcla dimensiones | HFS-014 | Gobernante por DCR con eje/unidad y sin mínimo incompatible |
| F-06 | P0 | Código observado; efecto H3 pendiente | HFS-013/033/034 | Demanda/capacidad direccionales contrastadas con fuente |
| F-07 | P0 | Presentación observada; interpretación D1/E2 pendiente | HFS-015 | Recomendaciones separadas del cumplimiento y con fuente |
| F-08 | P0 | Observado: Vu contradictorio reemplazado | HFS-011/013 | Política única de cargas/ejes sin pérdida silenciosa |
| F-09 | P0 | Observado: DCR redondeado incompatible visualmente con FAIL | HFS-015 | Valores brutos y presentación diferenciados; fronteras |
| F-10 | P0 | NaN axial confirmado; otros dominios pendientes | HFS-011/040 | Finitud/dominios comprobados por frontera de entrada |
| F-11 | P1 | Etiquetas invertidas observadas; física pendiente | HFS-013/033 | Correspondencia matemática eje/demanda/capacidad |
| F-12 | P1 | Selección ID observada; significado físico pendiente | HFS-033/040 | D/t contrastado con fuente y geometría real |
| F-13 | **P0 propuesto** | Duplicados reales de geometría diferente, sobrescritura confirmada | Corrección acotada a planificar antes de G1; alcance completo HFS-040 | Identidad ambigua no puede seleccionar geometría silenciosamente; catálogo contrastado |
| F-14 | P1 | Fallback de escala observado; impacto por fuente pendiente | HFS-040 | Unidades de importación inequívocas y pruebas dimensionales |
| F-15 | P1 | Geometría custom duplicada | HFS-021; DRY-05 | Un constructor consumido por cálculo y reporte, equivalencia probada |
| F-16 | P1 | CLI con responsabilidades mezcladas | HFS-021/024 | Ejecución/reportes separados con propósito, sin otro motor |
| F-17 | P1 | Reglas compuestas concentran cálculo numérico y reporte | HFS-035/036; extracción posterior justificada | Separación por dominio probado, no por longitud del archivo |
| F-18 | P1 | Parámetros fijos observados; suficiencia numérica pendiente | HFS-036 | Convergencia/equilibrio y tolerancias documentados |
| F-19 | P1 | F4 usa F5; admisibilidad pendiente | HFS-032 | Fuente, dominio y conservadurismo contrastados |
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

Las reproducciones, archivos/símbolos y salidas de F-01 a F-32 están en [findings](findings.md). F-31 tiene `test_channel_both_axes_must_block_if_major_axis_is_unsupported`; F-32 se acredita en [examples.json](evidence-clean/examples.json) y `run.py::main`. No se inventa un xfail para F-32: el exit actual es un contrato observable cuyo cambio exige decisión explícita.

## Justificación de prioridades y discrepancias de planificación

**F-13: recomendar P0.** HFS-000 observó HEA 100 duplicado con A=2124/2534 mm² y d=96/114 mm; se retiene la última entrada según el orden, sin aviso. Esto compromete qué geometría se calcula aun con fórmulas correctas. [catalog-duplicates.json](catalog-duplicates.json) preserva ambas. No se sabe cuál nombre/fila es correcto; renombrar automáticamente sería otra hipótesis. PTEXXMM de área cero añade riesgo de calidad, pero no prueba una capacidad incorrecta en cada caso.

Discrepancia con el roadmap: dejar todo F-13 hasta fase 4/HFS-040 es demasiado tarde para una puerta G1 de confiabilidad. Proponer una corrección estrecha de identificación/rechazo con revisión del catálogo antes de G1, manteniendo importación canónica completa en HFS-040. **No se creó ni ejecutó esa tarea en HFS-001**; falta acordar ubicación/dependencias. Rechazar duplicados globalmente hoy podría impedir cargar todos los ejemplos: exige diseño y prueba de transición, no un arreglo incidental.

**F-31 permanece P0:** omite una componente y puede declarar PASS; la sonda es sintética, por lo que confirmar su impacto en perfiles reales sigue pendiente. **F-32 permanece P1:** exit 0 no significa por sí mismo defecto de cálculo; preservarlo y exigir lectura del JSON es compatible con el contrato actual. Cualquier nueva semántica se revisará con sus consumidores.

F-06/07/12/18/19/20/27/28/30 mantienen incertidumbres explícitas. No se rebaja una prioridad porque falta prueba numérica, ni se llama defecto normativo confirmado a una hipótesis. Una solución DRY de F-15/16/17 tampoco cierra automáticamente los problemas de cálculo relacionados.

## Cambios de estado

Para cerrar un ID registrar tarea/commit, reproducción previa, resultado posterior, prueba independiente cuando corresponda y alcance de revisión. Si solo una parte se resuelve, mantener abierto con alcance residual. Los 11 `known defect` y toda la evidencia HFS-000 permanecen intactos. Aprobación de la arquitectura propuesta y priorización F-13 quedan para la revisión técnica solicitada, sin avanzar a HFS-002/010.
