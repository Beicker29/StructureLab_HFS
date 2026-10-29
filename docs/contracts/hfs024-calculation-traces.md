# HFS-024 — Contrato de traza de ejecución

Estado: implementación progresiva para revisión técnica. Base HFS-023 aprobada
arquitectónicamente por el usuario: `93e4f8cd523148c8cb3ccff1d94caafb4cfa8af1`.
No acredita nuevas disposiciones AISC. No cambia JSON 1.0, resultados ni cobertura.

## Decisión y propietarios

`steel_design.tracing` observa la ejecución optativamente. No selecciona reglas,
calcula capacidades, interpreta expresiones ni asigna cumplimiento. El registro
[HFS-023](hfs023-normative-registry.md) sigue siendo la única colección de IDs,
citas y evidencia. Los productores conservan cálculos y decisiones; HFS-010
conserva obligaciones y acreditación condicional. `reporting` solo proyecta datos.

El decorador `traced_rule` se declara en los 57 métodos `check` propietarios y
alcanza por herencia las 71 clases registradas. Registra entrada, retorno o
excepción de la llamada real. `emit_step`/`observed_value` reciben los valores
locales en el punto ejecutado. `observed_value` retorna el mismo objeto recibido;
no vuelve a evaluar la expresión. Las cadenas de expresión son descripciones,
nunca código ejecutable ni fuente para reconstruir ramas.

No todos los cálculos están instrumentados: una frontera observada **no es una
traza aritmética completa**. El campo `unknowns` conserva esa distinción incluso
si hay pasos. Una llamada sin pasos publica entradas/salida y desconocimiento,
no inventa una ecuación. El inventario de 93 entradas y las observaciones de los
ejemplos están en la [matriz](../audit/hfs024/rule-matrix.md).

## API optativa y compatibilidad

```python
from steel_design.tracing import capture_trace
from steel_design.reporting import calculation_trace_document

with capture_trace(provenance={"analysis_reference": "referencia externa"}) as capture:
    result = engine.run(case)  # mismo pipeline, resultado y excepciones

trace = capture.snapshot()
document = calculation_trace_document(trace)
```

`capture_trace`, `TraceCapture.snapshot`, `CalculationTrace` y
`calculation_trace_document` son la superficie optativa de HFS-024. Los helpers
de instrumentación son internos. También se observan llamadas directas a reglas
dentro del contexto; una función numérica aislada sin regla activa no crea una
regla ficticia. El contexto no hace I/O. Para excepciones, conservar la variable
`capture` y tomar el snapshot después de capturar la excepción original.

`trace_version="HFS-024-v1"` identifica este documento auxiliar. **No es un
`kind` nuevo de `contracts`**, ni cambia `contract_version="1.0"`, la versión
HFS-010-v1 o la distribución 0.2.0. El resultado no contiene la traza y sus
serializadores/esquemas permanecen intactos. No hay migración automática desde
`details.memory`, ni reconstrucción de trazas al leer resultados antiguos.

La serialización es reproducible para las mismas observaciones y procedencia
suministrada, sin timestamps automáticos. No constituye autenticación de un
resultado recibido ni una firma del código ejecutado. El archivo de evidencia
debe aportar SHA, fuentes, entorno y hash de entradas: el cálculo no consulta Git.

## Contrato formal

Los modelos Pydantic en `tracing.py` son la definición ejecutable: campos extra
rechazados, campos de modelo congelados y snapshots separados por copia profunda.
Los diccionarios de contexto son copias serializables; el consumidor puede editar
su copia sin alterar el buffer ni el resultado. No se añaden esquemas a JSON 1.0.

| Modelo/campo | Semántica y procedencia |
|---|---|
| `CalculationTrace.evaluations` | Intentos reales de reglas, en orden de entrada, incluyendo llamadas internas anidadas |
| `trace_version`, `normative_accreditation` | Identidad de documento y constante `NO_NEW_ACCREDITATION` |
| `analyses` | Estados, fallos conocidos y cobertura **copiados** del EngineResult final; enlaces check→evaluación por identidad de objeto |
| `unhandled_errors` | Excepciones que escaparon del contexto; etapa no inferida. Puede haber un error previo a selección sin ninguna regla ejecutada |
| `supplied_provenance` | Referencias aportadas por el consumidor, no verificadas por el capturador |
| `RuleTrace.rule_id`, `metadata` | Clase real enlazada a RuleDefinition; herencia inequívoca para fachadas. Ambigüedad/desconocido produce null con diagnóstico, nunca búsqueda por etiqueta |
| `implementation`, `evaluation_index`, `parent_evaluation` | Implementación invocada, identidad local del intento y padre de llamadas internas; no ID de ecuación |
| `design_method` | Método del caso recibido, también si una guarda lo rechaza; no afirma compatibilidad de combinaciones externas |
| `inputs.case`, `explicit_case_fields`, `section` | Snapshot del modelo recibido, campos declarados según Pydantic y propiedades de sección. No son los bytes JSON originales ni acreditan su fuente externa |
| `outcome` | `RETURNED`, `BLOCKED` para RuleNotImplemented/IncompleteSectionData, o `ERROR`; no estado resistente nuevo |
| `check_values`, `check_status` | Demanda/capacidad/DCR originales y decisión del check devuelto; null/ausente si no retornó |
| `CalculationStep.producer`, `limit_state`, `branch` | Símbolo propietario, responsabilidad declarada y rama emitida desde el productor; null si no instrumentada |
| `reference`, `equation`, `expression` | Disposición/subreferencia y expresión emitidas por el productor; la edición, jerarquía de fuentes y evidencia permanecen en metadata HFS-023 |
| `inputs`, `intermediates`, `outputs`, `factors` | Tuplas de `TraceValue`; valores usados/obtenidos, sin recálculo. Factores de capítulos distintos no se fusionan |
| `axis`, `assumptions`, `unknowns` | Eje declarado, condiciones y límites explícitos; no deducidos por nombres de variables o de checks |
| `TraceValue` | Nombre, valor bruto, unidad, procedencia y diagnóstico. Ausencia de valor/unidad exige explicación; no finito se representa como null diagnosticado, nunca capacidad infinita válida |

No se modifican los valores del motor al serializar no finitos en la traza.
Los textos no acreditados no se elevan a citas normativas revisadas. El estado
`NOT_ACCREDITED` del registro permanece separado de las pruebas de software y
de la acreditación condicional preexistente y acotada de HFS-010.

## Alcance de instrumentación y ambigüedades preservadas

- D2/D3: área efectiva, nominales y conversión LRFD/ASD desde las operaciones
  reales. Cada regla ejecuta actualmente ambas nominales mediante TensionEvaluator;
  la traza muestra ambas sin afirmar que ambas sean su salida seleccionada.
- E3: Fe/Fcr/Pn/capacidad y eje gobernante del evaluador. La rama de tensión
  crítica y sus factores permanecen sin expansión; no se reconstruyen desde Fy/Fe.
- F: nominal seleccionado por el constructor común y conversión canónica F1.
  La mayor parte de subramas nominales sigue pendiente. F3-3 permanece ID interno,
  no ecuación. F4 emite su delegación real a F5 y User Note, sin acreditar F-19.
- G4/G5: evaluación direccional compartida, demanda firmada, componente y rama
  producida por el evaluador. No se infieren unidades desde sufijos. Vu es alias
  escalar del plano x; Vux corresponde a fuerza local y, Vuy a fuerza local x.
- H1: rama ejecutada explícita. Compresión distingue H1-1a/b; en tracción
  `equation=null` y F-37 visible, aunque la salida legacy conserve H1-2.
- H3: nominal torsional/conversión, capacidades flexionales por eje, pares de
  cortante, sumas y operación H3-6; umbral ≤0,20 conserva BLOCKED. Las ramas
  completas de Fcr y capacidades auxiliares siguen pendientes de instrumentación.
- I: las 17 identidades registradas observan sus checks reales; I5 emite método,
  rama, capacidades y cociente existente. Método 2 sigue identificado como
  auxiliar/Commentary; no se inventa una ecuación Specification. Iteración,
  convergencia, subramas I1–I4 y factores internos quedan pendientes. Las llamadas
  internas I4 tienen padre y no reciben automáticamente enlaces de cobertura.

PASS/FAIL del check se conserva, incluso en un check inactivo legacy con cero y
unidad ausente; no acredita nada por sí solo. INCOMPLETE viene del agregador.
BLOCKED describe una ejecución impedida, nunca se convierte en FAIL resistente
ni PASS. Los errores de selección anteriores a una regla se conservan en la
cobertura o excepción original; no crean una ejecución que no ocurrió.

## Memorias y ciclo de vida

`calculation_trace_document` consume exclusivamente el snapshot. Un exportador
debe recorrer valores/unidades/expresiones existentes y mostrar los desconocidos;
puede redondear una columna de presentación, pero preserva el valor bruto y la
decisión original. No debe invocar el motor, convertir fórmulas en código,
reclasificar, adivinar ejes o sustituir null por cero.

Las memorias y SVG legacy siguen disponibles con idéntico formato. Su transición
a una presentación basada enteramente en estos pasos es pendiente explícito:
reemplazarlas ahora con instrumentación parcial perdería información o exigiría
inferencias. No se añaden fachadas de compatibilidad ni implementaciones
sustituidas; no hay eliminaciones de históricos o productores legacy.

Un contexto puede capturar varios casos secuenciales. Contextos anidados son
aislados; cada hilo/request debe abrir su propio contexto. No se promete compartir
el mismo buffer entre tareas concurrentes. La captura completa guarda entradas y
metadata por intento y tiene costo de memoria; permanece optativa. Snapshot y
exportación se realizan tras terminar la captura, no durante una evaluación.
