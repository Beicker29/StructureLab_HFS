# Seguimiento maestro de hallazgos — HFS-017

## Suplemento HFS-030 — 2026-10-29, cotejo local para revisión

Base `main`/`76a9086`; jobs CI HFS-024 Windows/Ubuntu SUCCESS observados.
[Informe](hfs030/report.md), [fuentes por hash](hfs030/sources.md) y
[22 grupos de erratas + contraste documental](hfs030/impact-matrix.md).
El usuario limitó las fuentes al repositorio y aportó E25/E26 durante la tarea.
No se modifican cálculos, registro, trazas, selección, cobertura ni estados.

- **F-31 permanece P0 abierto**: E25/E26 no implementan resistencia mayor de
  canal; B4/F2–F6 conserva condiciones diferenciadas por familia y eje.
- **F-35/F-36 permanecen P0 propuestos**: E7 Fn·Ae y condiciones/ramas E5
  cotejadas; ningún cierre por una errata o test. Efecto numérico pendiente.
- **F-37 permanece P1**: observaciones L30-01/03/06 documentan localizadores
  F2/F3/F1 incompletos, cita I3.3b incorrecta para resistencia de encamisados,
  H1-2=Pey y separación Commentary/Specification. E25-02 renumera F7; E26-02
  solo corrige unidades Lb. La actualización compatible de metadata/trazas
  queda pendiente, sin alterar identidades ni históricos en HFS-030.
- **F-28 permanece P2 abierto**: hashes, fuentes locales y diferencias E25/E26
  registrados; no se afirma autenticación remota, inventario editorial universal
  ni permiso de redistribución. E25-06 (Fy/Fyb), E26-04 y E26-06/07 tienen
  prioridad preventiva P1 junto con F-38 antes de implementar esos dominios.
- F-19/20/22/23/30/34/38 siguen abiertos; usar Fysr en I5-2 y llamar Mn al
  resultado F5 es concordancia documental acotada, no validación independiente.

La matriz conserva HECHO VERIFICADO / INFERENCIA / HIPÓTESIS / PENDIENTE.
No se inicia HFS-031/032 ni se cierran hallazgos por esta entrega. Los siguientes
suplementos son históricos y permanecen intactos.

## Suplemento HFS-024 — 2026-10-29, para revisión

HFS-023 fue aprobado arquitectónicamente por el usuario; su commit publicado
`93e4f8c` tiene CI SUCCESS Windows/Ubuntu. HFS-024 añade observaciones reales y
pasos progresivos, con [contrato](../contracts/hfs024-calculation-traces.md),
[matriz](hfs024/rule-matrix.md) e [informe](hfs024/report.md).

F-21/F-26: fuente estructurada optativa de valores/unidades/procedencia, enlazada
al registro único y a checks por identidad; expansión completa y transición de
memorias pendientes. F-37: F3 no se trata como ecuación, F4 declara delegación F5,
H1 tracción no atribuye su fórmula a H1-2, I5 conserva método y tipo de fuente.
No cambia la etiqueta legacy ni se acredita su expresión normativa. F-19/20/23/28/30
permanecen abiertos; observar no valida. **F-31 permanece P0 abierto**: trazar
F6 no acredita la flexión mayor de un canal. F-33–38 y restantes límites siguen
vigentes. No cambia prioridad ni se cierra una auditoría normativa por esta entrega.

## Suplemento HFS-023 — 2026-10-29

F-26 se aborda arquitectónicamente con metadatos canónicos en RuleDefinition
y un índice derivado verificable; no se cierra la validación exhaustiva ni F-30.
F-37 queda explícito separando ID, disposición y ecuación, sin cambiar etiquetas
JSON ni fórmulas. F-31 permanece **P0 abierto**; F-19/20/23/28/33–38 y límites
normativos restantes no se resuelven por registrar referencias o pasar tests.
[Informe y riesgos](hfs023/report.md), [contrato](../contracts/hfs023-normative-registry.md).
No se inicia HFS-024 ni se cambian prioridades/cierres normativos. Las entregas
anteriores y sus resultados se conservan a continuación como historia.

Fecha: 2026-10-27. Este es el registro vivo; [findings.md](findings.md) conserva el diagnóstico HFS-000 aceptado y no se reescribe. [ROADMAP](../ROADMAP.md) conserva tareas y prioridades resumidas. Actualizar ambos si cambia prioridad o asignación; no mantener una segunda copia completa del diagnóstico. Ningún hallazgo se cierra por aprobar HFS-000 o por redactar estos ADR.

Entrega actual HFS-017 sobre `main`/`7234df8`: F-44/F-45 corregidos
funcionalmente para revisión; métodos separados en reglas/evaluadores directos
y conversores, F-43 preservado, sin habilitar ASD F/I. Once suites: 1661 aprobadas y
12 subpruebas, sin xfail. Doce ejemplos/24 recorridos CLI idénticos.
[Informe](hfs017/report.md). Sin cambios de ecuaciones, cobertura ni cierre de
defectos normativos pendientes; HFS-020/039 no iniciadas. Sin commit/push.

Entrega previa HFS-015 sobre `main`/`dbd87cb`: F-09 y F-07 corregidos para
revisión técnica. Números originales y display separados; recomendaciones sin
crédito resistente; E5 no acreditado. Diez suites: 1193 aprobadas + 12 subpruebas,
sin xfail. [Informe y evidencia](hfs015/report.md). Sin cambios de fórmulas,
routing, factores F-43, catálogo o plan HFS-010. HFS-017/039 no implementadas.

Entrega previa HFS-014 sobre `main`/`d3190d4`: F-05 y F-29 corregidos, cierre
funcional demostrado para revisión. [Informe y evidencia](hfs014/report.md).
Caracterización: 11 aprobadas + 1 xfail estricto F-09. Sin cambios de resistencias,
selección, HFS-010 o F-32. HFS-017/039 quedan solo en planificación futura.
Las notas siguientes de entregas previas conservan su contexto histórico.

Revisión final HFS-013 sobre `abafdbb`: **F-43 corregido, cierre funcional
demostrado para revisión**. La función compartida H3/H1 aplica F1(a) por método;
73 pruebas nuevas y ocho suites aprobadas. El motor conserva el rechazo de
flexión ASD y no acredita nuevas obligaciones. [Suplemento](hfs013/f1-correction/report.md).

Entrega actual: [HFS-013](hfs013/report.md) sobre `main` con HFS-012 incorporada
por declaración del usuario. Correcciones G/H3 y bloqueos listos para revisión;
F-31 sigue abierto. Cambios locales sin publicación automática. El párrafo siguiente conserva el contexto
de aceptación y publicación de los hitos anteriores.

Estado actual: HFS-000/001/002/011/016 concluidas dentro de sus alcances por declaración del usuario. HFS-010 implementada; revisión técnica posterior a publicación/fusión autorizada. Las notas de entregas anteriores son históricas. «Observado» acredita código/ejecución; «riesgo» conserva incertidumbre normativa/física. Las tareas indican seguimiento; las correcciones ejecutadas se identifican expresamente. La [matriz HFS-002](../normative/hfs002-applicability.md) y su [contraste/riesgos](../normative/hfs002-implementation.md) conservan el diagnóstico, sin reescribir findings HFS-000.

| ID | Prioridad | Certeza / asunto | Tarea de seguimiento | Condición mínima de cierre, además de evidencia y revisión |
|---|---|---|---|---|
| F-01 | P0 | HFS-010 bloquea el PASS sin interacción; implementación/validación H pendiente. W sin interacción reproducido; H1.1/2 local incluye familias elegibles no HSS, H2 alternativa según condiciones | HFS-010/034 | Cobertura por combinación y dominio; no copiar HSS indiscriminadamente |
| F-02 | P0 | Corregido por HFS-010: cero checks/cero cargas explícitas produce INCOMPLETE; cierre demostrado para revisión. Observado: PASS sin checks | HFS-010 | Caso vacío/incompleto nunca PASS |
| F-03 | P0 | Corrección HFS-012 presentada para revisión: no se selecciona F2 con razones desconocidas, inválidas o clases contradictorias; derivación desde dimensiones B4.1 explícitas, canal con ancho completo. [Evidencia](hfs012/report.md). HFS-010 conserva pendientes y checks independientes | HFS-012; auditoría integral HFS-032/040 | Revisar límites, significado/procedencia de dimensiones y alcance declarado; no confundir corrección del fallback con validación de todas las resistencias F |
| F-04 | P0 | Corregido en contrato HFS-011 para revisión: extras/vacío rechazados, carga parcial documentada | HFS-011 | Evidencia por campo; revisión técnica del contrato/defaults pendiente |
| F-05 | P0 histórico | Corregido HFS-014: DCR máximo, empates trazables y fallos preservados, sin capacidad mezclada. HFS-015 publica y ordena ahora valores originales, con versión/migración explícitas | HFS-014; precisión HFS-015 para revisión; contratos HFS-022/024 pendientes | Revisar migración y límites de metadata; contraejemplo dimensional y 72 regresiones HFS-014 preservados |
| F-06 | P0 | Corregida agregación G/H3 en HFS-013 para revisión: máximo de cocientes con cada par demanda/capacidad, fuente G4/G5 única sin redondeo. Oráculo asimétrico y perfil PTE real; combinación completa 0,97→1,61 incluye también F-39. Global INCOMPLETE | HFS-013; auditoría integral HFS-033/034 | Revisar convención y casos; no acreditar todas las capacidades D/E/F, geometrías y condiciones por corregir la agregación |
| F-07 | P0 histórico | Corregido HFS-015 para revisión: avisos D1/E2 con fuente y estados propios; longitud fabricada/radio mínimo y excepción rod no inferidos. E5(4) sigue NOT_EVALUATED | HFS-015; auditoría E5 HFS-031 pendiente | Revisar migración de admisibilidad y declaraciones externas; no acreditar cobertura desde avisos |
| F-08 | P0 | HFS-011 rechazó representaciones contradictorias; HFS-013 define Vu como alias escalar Vux, asociado Mux/fuerza y local. Oráculos positivos/negativos y trazas compartidas; nunca resultante | HFS-011/013; adaptadores HFS-021/022 | Revisar entradas históricas interpretadas como fuerza x/resultante y consumidores I; no cierre de toda transformación externa |
| F-09 | P0 histórico | Corregido HFS-015 para revisión: valores originales, decisión única, display con estado/bruto, ranking original, trazas directas y JSON estricto. Xfail retirado tras XPASS investigado | HFS-015; contratos HFS-022/024 pendientes | Fronteras y consumidores pasan; revisar diferencias I4/I5 y migración, sin declarar validación normativa integral |
| F-10 | P0 | Parcial HFS-011: finitud en modelos/parser, dominios y sección seleccionada; NaN axial corregido | HFS-011/040 | Calidad/coherencia completa del catálogo y extremos numéricos pendientes; no cierre global |
| F-11 | P1 | HFS-013 aclara sufijo de plano de flexión vs dirección de fuerza; pares G/H3 y trazas explícitos. No permuta cargas. G3 y G6 canal bloqueados por dirección/reparto no acreditados | HFS-013/033 | Revisar convención de adaptadores, orientación real de ángulos y compuesto I; etiquetas solas no acreditan física |
| F-12 | P1 | Selección ID observada; significado físico pendiente | HFS-033/040 | D/t contrastado con fuente y geometría real |
| F-13 | **P0** | Sobrescritura corregida en HFS-016, concluida en su alcance y fusionada en main | HFS-016 entregada; calidad integral HFS-040 | get rechaza identidades repetidas con todos los candidatos/procedencia; no se decide qué geometría es correcta. [Evidencia](hfs016/report.md) |
| F-14 | P1 | Fallback de escala observado; impacto por fuente pendiente | HFS-040 | Unidades de importación inequívocas y pruebas dimensionales |
| F-15 | P1 | HFS-021: cierre funcional para revisión; constructor único `sections.geometry`, Section validada compartida con presentación | HFS-021; DRY-05 | [Oráculos geométricos, regresión exacta y fachadas](hfs021/report.md); sin aproximaciones HSS ni nuevas geometrías |
| F-16 | P1 | HFS-021: cierre arquitectónico acotado para revisión; ejecución en memoria y reporting separados del transporte CLI | HFS-021; trazas futuras HFS-024 | [Mapa de consumidores y compatibilidad](hfs021/preparation.md); un solo motor, mismas suites/resultados. No acredita contrato canónico de trazas futuro |
| F-17 | P1 | Reglas compuestas concentran cálculo numérico y reporte | HFS-035/036; extracción posterior justificada | Separación por dominio probado, no por longitud del archivo |
| F-18 | P1 | Parámetros fijos observados; suficiencia numérica pendiente | HFS-036 | Convergencia/equilibrio y tolerancias documentados |
| F-19 | P1 | UN F4 PDF124 describe alternativa conservadora F5; fidelidad de código y dominio siguen pendientes | HFS-032 | Fuente, dominio y conservadurismo contrastados, traza de alternativa explícita |
| F-20 | P1 | Capacidades H/I requieren auditoría | HFS-034/035 | Oráculos por trayectoria/método y origen de capacidades |
| F-21 | P1 | Resultado sin unidad/completitud/bruto dedicados | HFS-022/024 | Contrato común y traza sin inferencias de interfaz |
| F-22 | P1 | Defaults auditados/documentados HFS-011; sin acreditación de análisis ni procedencia | HFS-011/022/037 | Procedencia de K/Cb/demandas y alcance explícitos; permanece abierto |
| F-23 | P1 | Pruebas existentes insuficientes para validación exhaustiva | HFS-031–038/041/042 | Referencias independientes por dominio publicitado |
| F-24 | P1 | Sin empaquetado/CI, requisitos abiertos | HFS-020 | Instalación y tests fuera del checkout reproducibles |
| F-25 | P1 | Históricos/temporales versionados | Política HFS-001; limpieza posterior separada | Trazabilidad recuperable y justificación antes de retirar |
| F-26 | P1 | HFS-023: matriz de implementación derivada de RuleDefinition.metadata, referencias e integridad verificadas; cobertura exhaustiva no acreditada | HFS-023 para revisión; HFS-024/030 pendientes | [Registro único y riesgos](hfs023/report.md); no cierre normativo por metadatos |
| F-27 | P1 | Procedencia de catálogo pendiente; anomalías observadas | HFS-040 | Fuente, conversiones e identidad comprobadas |
| F-28 | P2 | HFS-030 coteja 22 grupos de E25/E26 locales por hash; base S22 conserva texto anterior. Permisos, autenticación remota y exhaustividad editorial pendientes; incertidumbre Fy/Fyb K4.1A explícita | HFS-030 y revisión documental | Registro verificable de edición, permisos y erratas; no cierre por inventario local |
| F-29 | P1 histórico | Corregido HFS-014 para revisión: aggregate_case_statuses([]) lanza EMPTY_CASE_BUNDLE; CLI stderr/exit 1, sin cumplimiento, ejecución de casos ni memorias. Tabla de estados no vacíos y fallos individuales preservados | HFS-014 | Revisar errores/migración; tests de lista vacía, tipos/elementos inválidos y combinaciones PASS/FAIL/INCOMPLETE. F-32 no cambia |
| F-30 | P1 | Riesgo de cobertura normativa no auditada | HFS-030–038/041 | Validación independiente; no cierre global por tests verdes |
| F-31 | **P0** | Mitigado, no cerrado: HFS-010 mantiene Mux pendiente aunque exista F6. HFS-012 añade diagnóstico explícito de selección mayor bloqueada también en biaxial; no añade fórmulas de canal ni valida F6. [Sondas antes/después](hfs012/report.md) | HFS-002/010/012; contraste de flexión HFS-032 | Cobertura por componente, canal real y fronteras; revisar ancho completo en F6 y resistencias de canal antes de acreditar cobertura |
| F-32 | **P1** | Confirmado: FAIL con exit 0; riesgo para consumidores, no regresión | HFS-022 y documentación CLI al adaptar HFS-021 | Semántica ejecución/diseño documentada y consumidores probados; transición si cambia |
| F-33 | P0 propuesto | HFS-010 exige interacción incluso Pu=0; rutas H/I completas pendientes. Biaxial sin axial omitida: sonda W y gating H/I; N29/N42 | HFS-010/034/035 | Obligaciones por combinación, incluso Pu=0; ruta por familia validada |
| F-34 | P0 propuesto | HFS-010 exige resistencia M por eje; cuantía/transferencia no la cubren. Tres roles compuestos con flexión pura 1 y 1 000 000 kNm conservan PASS sin check resistente M | HFS-010/035 | No confundir cuantía/transferencia con flexión; evaluar/bloquear M por eje y etapa |
| F-35 | P0 propuesto | HFS-010 no acredita el dominio E7; fórmula efectiva sigue pendiente. E7 usa QFy/Ag; S22 E7 prescribe Fn·Ae, sin equivalencia demostrada | HFS-010/031/041 | Método por dominio/área efectiva, oráculos y revisión de consumidores H/I |
| F-36 | P0 propuesto | HFS-010 no acredita condiciones/ramas E5; reparación normativa pendiente. E5 implementa rama única y no acredita condiciones; E4 ángulo sin regla registrada | HFS-010/031/041 | Condiciones de conexión y ramas 75/80/200; flexotorsión/áreas y oráculos |
| F-37 | P1 | IDs parecen ecuaciones; H1-2 usado para interacción de tracción aunque fuente define Pey. HFS-030: L30-01/03/06 documentan localizadores y referencia I3.3b incorrectos; E25-02 renumera F7. Traces/metadata preservadas, corrección pendiente | HFS-023/024/030/032/034/035 | Separar IDs/citas; contrastar fórmula de tracción y consumidores, actualizar referencias con revisión explícita de impacto |
| F-38 | P1 | Verificaciones complementarias/condiciones no acreditadas E6/F13/G7/H4/I1/I6, etapas y conexiones | HFS-010/031–038 | Alcance explícito; no omitir precondiciones ni validar por existencia de cualquier check |
| F-39 | P0 propuesto | Confirmado y corregido HFS-013 para revisión: H3-6 usaba cuadrado del término normal; Specification 16.1-86 exige término lineal. Oráculo normal=0,4 y corte+torsión=0,9: 0,97→1,21 | HFS-013/034 | Revisión de expresión y dominio; Pc/Mc requieren validación separada |
| F-40 | P1 propuesto | Confirmado y corregido HFS-013: H3-5 4,58→0,458π²; a h/t=100 Fcr=91,6→90,405576 MPa. Extrapolación h/t>260 bloqueada | HFS-013/034 | Revisión de fronteras y alcance del dato h plano mayor; prioridad P1 por exceso ~1,32% de rama, no significa aceptable |
| F-41 | P0 propuesto | Confirmados fallbacks no acreditados G/H3: Lv desde Lx/Ly, L desde KzLz, C desde 2J/D o exterior reconstruido con planos+3t, t nominal/otra pared. HFS-013 retira esas inferencias; prueba fluencia sin longitud solo por identidad matemática | HFS-013/022/033/034/040 | Definir datos físicos/procedencia que faltan; no completar catálogo artificialmente; revisión de C declarada y espesores |
| F-42 | P0 propuesto | Confirmado: umbral 20% de H3.2 se presentaba como check PASS y G3 reutilizaba un ala en ambos planos. G6 canal no acredita reparto. HFS-013 bloquea esas evaluaciones y conserva INCOMPLETE y checks independientes | HFS-013/033/034 | Implementar/validar alternativas H1/G y direcciones reales en tarea autorizada, no dar cobertura por presencia de regla |
| F-43 | P0 propuesto; corregido | Revisión independiente confirma Mc=0,90Mn también en ASD dentro de H3/H1. Cierre funcional HFS-013: conversión canónica F1(a), ASD=Mn/1,67, nominales y LRFD preservados. Antes 18 fallos ASD dirigidos; después 73 pruebas nuevas aprobadas. Ocho checks de sondas ASD pasan de PASS a FAIL | Corrección final HFS-013; aprobación técnica pendiente | Revisar cierre acotado al factor F1. El rechazo público de flexión ASD limita exposición, pero no legitima capacidades internas 50,3% excesivas. No habilitar ASD integral ni cerrar F-37/F-31 |
| F-44 | P0 propuesto; corregido para revisión | HFS-017 reproduce F directo ASD calculando LRFD y helpers/reglas I sin guarda de método. Ahora rechazo estructurado antes de nominales y retornos inactivos; motor/router/evaluadores comparten política | HFS-017 | [Sondas antes/después y 468 pruebas](hfs017/report.md); revisar cobertura de entradas directas. No habilitar ASD F/I ni declarar acreditadas capacidades I |
| F-45 | P1; corregido para revisión | HFS-017 reproduce métodos desconocidos tratados como ASD en conversores D/E/G/H, o cero previo a validar. Ahora ValueError explícito incluso nominal cero; casos corruptos directos dan ValidationError estructurado | HFS-017 | [Contrato y migración](../contracts/hfs017-design-method.md); verificar consumidores directos y conservar factores/aritmética válidos |

Las reproducciones, archivos/símbolos y salidas de F-01 a F-32 están en [findings](findings.md). F-31 tiene `test_channel_both_axes_must_block_if_major_axis_is_unsupported`; F-32 se acredita en [examples.json](evidence-clean/examples.json) y `run.py::main`. No se inventa un xfail para F-32: el exit actual es un contrato observable cuyo cambio exige decisión explícita.

## Justificación de prioridades y discrepancias de planificación

**F-13: recomendar P0.** HFS-000 observó HEA 100 duplicado con A=2124/2534 mm² y d=96/114 mm; se retiene la última entrada según el orden, sin aviso. Esto compromete qué geometría se calcula aun con fórmulas correctas. [catalog-duplicates.json](catalog-duplicates.json) preserva ambas. No se sabe cuál nombre/fila es correcto; renombrar automáticamente sería otra hipótesis. PTEXXMM de área cero añade riesgo de calidad, pero no prueba una capacidad incorrecta en cada caso.

Acuerdo documental HFS-002: se registra **HFS-016**, fase 1, dependencias 000/001, antes de G1, como mitigación estrecha de identificación/rechazo de F-13. HFS-040 conserva importación canónica completa. Actualización HFS-016: implementada para revisión con rechazo por identidad al consultar, conservando el resto del catálogo. Se demuestra el cierre funcional de la sobrescritura (F-13); no se acredita cuál geometría es correcta ni la calidad integral HFS-040. Prioridad P0 histórica conservada. Ver [informe](hfs016/report.md).

**F-31 permanece P0:** omite una componente y puede declarar PASS; la sonda es sintética, por lo que confirmar su impacto en perfiles reales sigue pendiente. **F-32 permanece P1:** exit 0 no significa por sí mismo defecto de cálculo; preservarlo y exigir lectura del JSON es compatible con el contrato actual. Cualquier nueva semántica se revisará con sus consumidores.

HFS-002 precisó F-06 y F-07 con S22 local; HFS-013 corrige F-06 para revisión; F-07 permanece pendiente. F-12/18/19/20/27/28/30 conservan incertidumbres. No se rebaja una prioridad porque falta prueba numérica ni se afirma validación física a partir de una sonda. Una solución DRY de F-15/16/17 tampoco cierra automáticamente problemas de cálculo. Evidencia F-33/34 y contraejemplo F-06: [probes.json](hfs002/probes.json); programa reproducible [probes.py](hfs002/probes.py). F-35/36/37/38 son contrastes estáticos, no nuevas pruebas normativas aprobadas.

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


## Actualización HFS-013

La convención documentada de planos/fuerzas conserva la asociación histórica;
F-06 se corrige con pares por eje, y H3-6/H3-5 con referencias independientes.
Los nuevos bloqueos por C/longitudes/dirección ausentes preservan checks
independientes y cobertura pendiente. No se habilita PASS global en G/H3.
[Informe y pruebas](hfs013/report.md): 961 aprobadas + 12 subpruebas, 3 xfail
estrictos F-05/09/29. F-31 sigue abierto; HFS-012 se conserva. F-39–42 son
hallazgos confirmados con correcciones/bloqueos presentados para revisión,
no cierres aprobados. Sin HFS-014/015 ni publicación automática.
