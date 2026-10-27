# Seguimiento maestro de hallazgos — HFS-012

Fecha: 2026-10-27. Este es el registro vivo; [findings.md](findings.md) conserva el diagnóstico HFS-000 aceptado y no se reescribe. [ROADMAP](../ROADMAP.md) conserva tareas y prioridades resumidas. Actualizar ambos si cambia prioridad o asignación; no mantener una segunda copia completa del diagnóstico. Ningún hallazgo se cierra por aprobar HFS-000 o por redactar estos ADR.

Entrega actual: [HFS-012](hfs012/report.md) sobre `main` con HFS-010/011/016
incorporadas. Corrección F-03 lista para revisión; F-31 sigue abierto. Cambios
locales sin publicación automática. El párrafo siguiente conserva el contexto
de aceptación y publicación de los hitos anteriores.

Estado actual: HFS-000/001/002/011/016 concluidas dentro de sus alcances por declaración del usuario. HFS-010 implementada; revisión técnica posterior a publicación/fusión autorizada. Las notas de entregas anteriores son históricas. «Observado» acredita código/ejecución; «riesgo» conserva incertidumbre normativa/física. Las tareas indican seguimiento; las correcciones ejecutadas se identifican expresamente. La [matriz HFS-002](../normative/hfs002-applicability.md) y su [contraste/riesgos](../normative/hfs002-implementation.md) conservan el diagnóstico, sin reescribir findings HFS-000.

| ID | Prioridad | Certeza / asunto | Tarea de seguimiento | Condición mínima de cierre, además de evidencia y revisión |
|---|---|---|---|---|
| F-01 | P0 | HFS-010 bloquea el PASS sin interacción; implementación/validación H pendiente. W sin interacción reproducido; H1.1/2 local incluye familias elegibles no HSS, H2 alternativa según condiciones | HFS-010/034 | Cobertura por combinación y dominio; no copiar HSS indiscriminadamente |
| F-02 | P0 | Corregido por HFS-010: cero checks/cero cargas explícitas produce INCOMPLETE; cierre demostrado para revisión. Observado: PASS sin checks | HFS-010 | Caso vacío/incompleto nunca PASS |
| F-03 | P0 | Corrección HFS-012 presentada para revisión: no se selecciona F2 con razones desconocidas, inválidas o clases contradictorias; derivación desde dimensiones B4.1 explícitas, canal con ancho completo. [Evidencia](hfs012/report.md). HFS-010 conserva pendientes y checks independientes | HFS-012; auditoría integral HFS-032/040 | Revisar límites, significado/procedencia de dimensiones y alcance declarado; no confundir corrección del fallback con validación de todas las resistencias F |
| F-04 | P0 | Corregido en contrato HFS-011 para revisión: extras/vacío rechazados, carga parcial documentada | HFS-011 | Evidencia por campo; revisión técnica del contrato/defaults pendiente |
| F-05 | P0 | Observado: resumen mezcla dimensiones | HFS-014 | Gobernante por DCR con eje/unidad y sin mínimo incompatible |
| F-06 | P0 | HFS-010 mantiene INCOMPLETE el dominio afectado sin cambiar máximos ni capacidades. H3.2/H3-6 exige máximo de cocientes; max demanda/max capacidad no equivale, contraejemplo independiente 0,5 vs 0,25 | HFS-013/033/034 | Resolver ejes y capacidades con HSS real asimétrico; discrepancia algebraica confirmada, impacto físico por caso pendiente |
| F-07 | P0 | D1/E2: límites 300/200 son User Notes; E5≤200 sí condiciona alternativa | HFS-015 | Recomendaciones separadas del cumplimiento y contexto de cláusula |
| F-08 | P0 | Parcial HFS-011: no sobrescribe/fabrica Vu; representaciones activas contradictorias rechazadas | HFS-011/013 | Física de ejes y capacidades pendiente HFS-013; no cierre global |
| F-09 | P0 | Observado: DCR redondeado incompatible visualmente con FAIL | HFS-015 | Valores brutos y presentación diferenciados; fronteras |
| F-10 | P0 | Parcial HFS-011: finitud en modelos/parser, dominios y sección seleccionada; NaN axial corregido | HFS-011/040 | Calidad/coherencia completa del catálogo y extremos numéricos pendientes; no cierre global |
| F-11 | P1 | Etiquetas invertidas observadas; física pendiente | HFS-013/033 | Correspondencia matemática eje/demanda/capacidad |
| F-12 | P1 | Selección ID observada; significado físico pendiente | HFS-033/040 | D/t contrastado con fuente y geometría real |
| F-13 | **P0** | Sobrescritura corregida en HFS-016, concluida en su alcance y fusionada en main | HFS-016 entregada; calidad integral HFS-040 | get rechaza identidades repetidas con todos los candidatos/procedencia; no se decide qué geometría es correcta. [Evidencia](hfs016/report.md) |
| F-14 | P1 | Fallback de escala observado; impacto por fuente pendiente | HFS-040 | Unidades de importación inequívocas y pruebas dimensionales |
| F-15 | P1 | Geometría custom duplicada | HFS-021; DRY-05 | Un constructor consumido por cálculo y reporte, equivalencia probada |
| F-16 | P1 | CLI con responsabilidades mezcladas | HFS-021/024 | Ejecución/reportes separados con propósito, sin otro motor |
| F-17 | P1 | Reglas compuestas concentran cálculo numérico y reporte | HFS-035/036; extracción posterior justificada | Separación por dominio probado, no por longitud del archivo |
| F-18 | P1 | Parámetros fijos observados; suficiencia numérica pendiente | HFS-036 | Convergencia/equilibrio y tolerancias documentados |
| F-19 | P1 | UN F4 PDF124 describe alternativa conservadora F5; fidelidad de código y dominio siguen pendientes | HFS-032 | Fuente, dominio y conservadurismo contrastados, traza de alternativa explícita |
| F-20 | P1 | Capacidades H/I requieren auditoría | HFS-034/035 | Oráculos por trayectoria/método y origen de capacidades |
| F-21 | P1 | Resultado sin unidad/completitud/bruto dedicados | HFS-022/024 | Contrato común y traza sin inferencias de interfaz |
| F-22 | P1 | Defaults auditados/documentados HFS-011; sin acreditación de análisis ni procedencia | HFS-011/022/037 | Procedencia de K/Cb/demandas y alcance explícitos; permanece abierto |
| F-23 | P1 | Pruebas existentes insuficientes para validación exhaustiva | HFS-031–038/041/042 | Referencias independientes por dominio publicitado |
| F-24 | P1 | Sin empaquetado/CI, requisitos abiertos | HFS-020 | Instalación y tests fuera del checkout reproducibles |
| F-25 | P1 | Históricos/temporales versionados | Política HFS-001; limpieza posterior separada | Trazabilidad recuperable y justificación antes de retirar |
| F-26 | P1 | Matriz manual sin prueba de cobertura exhaustiva | HFS-023/024/030 | Registro único trazable a funciones y pruebas |
| F-27 | P1 | Procedencia de catálogo pendiente; anomalías observadas | HFS-040 | Fuente, conversiones e identidad comprobadas |
| F-28 | P2 | Permisos/erratas pendientes | HFS-030 y revisión documental | Registro verificable de edición, permisos y erratas |
| F-29 | P1 | Observado: lote vacío PASS | HFS-014 | Cardinalidad/completitud y agregación verificadas |
| F-30 | P1 | Riesgo de cobertura normativa no auditada | HFS-030–038/041 | Validación independiente; no cierre global por tests verdes |
| F-31 | **P0** | Mitigado, no cerrado: HFS-010 mantiene Mux pendiente aunque exista F6. HFS-012 añade diagnóstico explícito de selección mayor bloqueada también en biaxial; no añade fórmulas de canal ni valida F6. [Sondas antes/después](hfs012/report.md) | HFS-002/010/012; contraste de flexión HFS-032 | Cobertura por componente, canal real y fronteras; revisar ancho completo en F6 y resistencias de canal antes de acreditar cobertura |
| F-32 | **P1** | Confirmado: FAIL con exit 0; riesgo para consumidores, no regresión | HFS-022 y documentación CLI al adaptar HFS-021 | Semántica ejecución/diseño documentada y consumidores probados; transición si cambia |
| F-33 | P0 propuesto | HFS-010 exige interacción incluso Pu=0; rutas H/I completas pendientes. Biaxial sin axial omitida: sonda W y gating H/I; N29/N42 | HFS-010/034/035 | Obligaciones por combinación, incluso Pu=0; ruta por familia validada |
| F-34 | P0 propuesto | HFS-010 exige resistencia M por eje; cuantía/transferencia no la cubren. Tres roles compuestos con flexión pura 1 y 1 000 000 kNm conservan PASS sin check resistente M | HFS-010/035 | No confundir cuantía/transferencia con flexión; evaluar/bloquear M por eje y etapa |
| F-35 | P0 propuesto | HFS-010 no acredita el dominio E7; fórmula efectiva sigue pendiente. E7 usa QFy/Ag; S22 E7 prescribe Fn·Ae, sin equivalencia demostrada | HFS-010/031/041 | Método por dominio/área efectiva, oráculos y revisión de consumidores H/I |
| F-36 | P0 propuesto | HFS-010 no acredita condiciones/ramas E5; reparación normativa pendiente. E5 implementa rama única y no acredita condiciones; E4 ángulo sin regla registrada | HFS-010/031/041 | Condiciones de conexión y ramas 75/80/200; flexotorsión/áreas y oráculos |
| F-37 | P1 | IDs parecen ecuaciones; H1-2 usado para interacción de tracción aunque fuente define Pey | HFS-023/024/034/035 | Separar IDs/citas; contrastar fórmula de tracción y todos consumidores |
| F-38 | P1 | Verificaciones complementarias/condiciones no acreditadas E6/F13/G7/H4/I1/I6, etapas y conexiones | HFS-010/031–038 | Alcance explícito; no omitir precondiciones ni validar por existencia de cualquier check |

Las reproducciones, archivos/símbolos y salidas de F-01 a F-32 están en [findings](findings.md). F-31 tiene `test_channel_both_axes_must_block_if_major_axis_is_unsupported`; F-32 se acredita en [examples.json](evidence-clean/examples.json) y `run.py::main`. No se inventa un xfail para F-32: el exit actual es un contrato observable cuyo cambio exige decisión explícita.

## Justificación de prioridades y discrepancias de planificación

**F-13: recomendar P0.** HFS-000 observó HEA 100 duplicado con A=2124/2534 mm² y d=96/114 mm; se retiene la última entrada según el orden, sin aviso. Esto compromete qué geometría se calcula aun con fórmulas correctas. [catalog-duplicates.json](catalog-duplicates.json) preserva ambas. No se sabe cuál nombre/fila es correcto; renombrar automáticamente sería otra hipótesis. PTEXXMM de área cero añade riesgo de calidad, pero no prueba una capacidad incorrecta en cada caso.

Acuerdo documental HFS-002: se registra **HFS-016**, fase 1, dependencias 000/001, antes de G1, como mitigación estrecha de identificación/rechazo de F-13. HFS-040 conserva importación canónica completa. Actualización HFS-016: implementada para revisión con rechazo por identidad al consultar, conservando el resto del catálogo. Se demuestra el cierre funcional de la sobrescritura (F-13); no se acredita cuál geometría es correcta ni la calidad integral HFS-040. Prioridad P0 histórica conservada. Ver [informe](hfs016/report.md).

**F-31 permanece P0:** omite una componente y puede declarar PASS; la sonda es sintética, por lo que confirmar su impacto en perfiles reales sigue pendiente. **F-32 permanece P1:** exit 0 no significa por sí mismo defecto de cálculo; preservarlo y exigir lectura del JSON es compatible con el contrato actual. Cualquier nueva semántica se revisará con sus consumidores.

HFS-002 precisó F-06 y F-07 con S22 local; sus correcciones y efectos por caso siguen pendientes. F-12/18/19/20/27/28/30 conservan incertidumbres. No se rebaja una prioridad porque falta prueba numérica ni se afirma validación física a partir de una sonda. Una solución DRY de F-15/16/17 tampoco cierra automáticamente problemas de cálculo. Evidencia F-33/34 y contraejemplo F-06: [probes.json](hfs002/probes.json); programa reproducible [probes.py](hfs002/probes.py). F-35/36/37/38 son contrastes estáticos, no nuevas pruebas normativas aprobadas.

## Cambios de estado

Para cerrar un ID registrar tarea/commit, reproducción previa, resultado posterior, prueba independiente cuando corresponda y alcance de revisión. Si solo una parte se resuelve, mantener abierto con alcance residual. Toda la evidencia congelada HFS-000 permanece intacta. HFS-001 aprobada arquitectónicamente; HFS-002 aceptada por el usuario como matriz documental y diagnóstico. HFS-011 presenta cambios contractuales para revisión; HFS-010/016 no ejecutadas.

### HFS-011 — correcciones demostradas y alcance residual (2026-10-27)

[Informe](hfs011/report.md), [contrato y migración](../contracts/hfs011-inputs.md). Base `5fe2c67a0d14f2541be032278d272cd85c080ecf`, cambios sin commit. Previo: 11 xfail estrictos. Primer contraste posterior: cuatro XPASS estrictos (F-04 typo, F-10 NaN, F-08 contradicción Vu y F-02 objeto loads vacío). Se confirmaron los motivos de rechazo con pruebas específicas de campo antes de retirar esas cuatro marcas; capturas y expectativas numéricas no se alteraron.

Las cuatro pruebas ahora pasan como regresión de seguridad. F-02 **no está cerrado**: se agrega reproducción explícita `loads={"Pu":0}` que sigue PASS sin checks, con xfail estricto del mismo defecto. Caracterización final: 4 aprobadas + 8 xfail (7 anteriores + esa reproducción residual). F-01/03/05/09/13/29/31 permanecen visibles. F-04 queda implementado para revisión del contrato parcial (omisión declarada=0, no desconocido). F-08/10/22 conservan los pendientes de sus filas. Ningún cierre ingenieril global aprobado.

Las dos pruebas originales de rechazo del motor para U>1 y xa<0 construyen ahora un objeto válido y lo alteran mediante model_copy: construir directamente esos valores ya falla en Pydantic. Mantienen la expectativa de rechazo en el motor; pruebas nuevas verifican también el rechazo temprano. No hay ecuaciones/capacidades/interacción modificadas ni validación ingenieril declarada.


### HFS-016 — integridad mínima, entregada para revisión

HFS-011 aprobada por el usuario antes de esta tarea; sus informes permanecen históricos.
F-13 reproducido antes: HEA 100 cambia de A=2534/d=114 a A=2124/d=96 al invertir
la carga; después ambas consultas rechazan con `AMBIGUOUS_SECTION`. Se retienen
1228 registros y 1223 identidades; 1221 son únicas recuperables. HEA 100 y PTEXXMM
quedan bloqueadas con hoja/fila/hash y todas sus propiedades. No se corrigen filas.
El test F-13 pasa sin xfail tras adaptar su expectativa al rechazo en get;
caracterización final: 5 aprobadas y 7 xfail estrictos. Las otras expectativas
congeladas y evidencias HFS-000/011 no se modifican. Los 12 ejemplos conservan
resultados exactos. [Pruebas, compatibilidad y riesgos](hfs016/report.md).
El cierre técnico de F-13 requiere revisión humana del PR; F-10/14/27 y HFS-040
siguen abiertos en su alcance residual. No se inicia HFS-010 ni otra tarea.

## Actualización HFS-010

Se separan estado resistente y global, con obligaciones independientes del router,
traza estructurada y preservación de FAIL conocidos. F-02 se corrige; F-01/03/31/33/
34/35/36 y F-06 se mitigan por INCOMPLETE, sin declarar corregidas sus fórmulas,
selectores o ramas. [Informe y reproducciones](hfs010/report.md).

Caracterización: 9 aprobadas y 3 xfail estrictos (F-05, F-09, F-29). Se retiran
cuatro xfail tras demostrar el bloqueo; las reproducciones/expectativas anteriores
permanecen en la evidencia histórica. Los 12 ejemplos conservan checks/trazas,
con 8 PASS→INCOMPLETE, 3 FAIL→INCOMPLETE (6 FAIL de check visibles) y un error previo
sin cambios. Solo tracción axial de macizos custom ordinarios con condiciones y
referencias externas explícitas puede acreditar cobertura completa en v1.

El usuario autorizó subir y fusionar esta entrega, con revisión posterior; esa
autorización no equivale a validación ingenieril ni permite iniciar otra tarea.
F-29/lote vacío sigue en HFS-014 por restricción expresa de alcance. G1 no se
declara cumplida; HFS-012/013/014 y auditorías normativas continúan pendientes.
