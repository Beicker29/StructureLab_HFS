# HFS-010 — Cobertura y estado global, versión 1

Estado: implementación para revisión técnica. [Informe](../audit/hfs010/report.md).
El origen de requisitos sigue siendo la [matriz independiente HFS-002](../normative/hfs002-applicability.md),
derivada de S22 local, con erratas pendientes. Este documento define el contrato
operativo, no otra matriz editable ni una certificación exhaustiva de AISC.

## Qué significa el resultado

`CheckStatus` conserva PASS/FAIL para cada evaluación existente. `AnalysisStatus`
separa el resultado del análisis: PASS, FAIL o **INCOMPLETE**. No se crean checks
con demanda/capacidad ficticias para representar falta de información.

| Cobertura | Checks conocidos | Estado global |
|---|---|---|
| Completa, con resistencia evaluada | Todos satisfactorios | PASS del alcance declarado |
| Completa | Algún FAIL | FAIL |
| Pendiente o sin verificaciones resistentes | Cualquier resultado, incluido FAIL | INCOMPLETE |

`known_failures` contiene índices base cero de los checks FAIL, también cuando
el global es INCOMPLETE. Los checks conservan números y estados; un FAIL no se
convierte en PASS ni se borra por existir incertidumbre. `EngineResult` sin
cobertura, aun construido con `status="PASS"`, se agrega como INCOMPLETE.

Entrada inválida, catálogo ambiguo y error de no soporte siguen siendo errores
estructurados, distintos de FAIL resistente. Los rechazos previos del router
se conservan. Si una regla ya seleccionada lanza `RuleNotImplementedError` o
`IncompleteSectionDataError`, se registra en `coverage.evaluation_errors` y se
conservan los checks previos/siguientes; el global queda INCOMPLETE. Otros errores
no se transforman en resultados estructurales.

## Plan y evidencia

El motor crea `build_coverage_plan(case, section)` **antes** de llamar al router.
El plan no importa router, `RULE_DEFINITIONS`, clases de reglas ni sus salidas.
Es una proyección conservadora y acotada de la matriz canónica; una rama no
resuelta se mantiene pendiente. Las funciones de esa proyección no calculan
capacidades ni constituyen otra selección ejecutable.

`coverage_evidence.py` contiene únicamente vínculos desde clases concretas
ejecutadas a obligaciones parciales. No decide cuáles obligaciones existen.
Los nombres/prefijos de cláusula no otorgan cobertura: una regla de cuantía o
transferencia no acredita resistencia de momento; F6 menor no acredita Mux.
Un N-ID se descompone por estado y componente; por ejemplo N04 exige fluencia
**y** rotura, y N17 distingue fluencia, pandeo local de ala/alma y LTB por eje.
Los grupos de ramas todavía desconocidas permanecen pendientes; no se exige
simultáneamente cada alternativa permitida por la norma.

Campos de `coverage`:

| Campo | Contenido |
|---|---|
| `version`, `source` | HFS-010-v1 y fuente normativa independiente |
| `declared_scope` | Resistencia del miembro para todas las demandas suministradas; no se recorta según los checks obtenidos |
| `supported_complete_domain` | Subconjunto cuya cobertura completa puede acreditarse en esta entrega |
| `method`, `section_name`, `profile_type`, `demand_components` | Contexto de método, sección y demandas con signo; no se transforman ejes |
| `evaluation_context` | Un miembro/caso suministrado; no se infieren envolventes de posiciones, combinaciones ni etapas |
| `scope_evidence` | Declaraciones/referencias externas aportadas, sin autenticar |
| `obligations` | Registro de requisitos y condiciones por estado/componente |
| `executions` | Índice de check, clase implementadora exacta y obligaciones que declara abordar parcialmente |
| `evaluation_errors` | Fallos controlados de disponibilidad durante ejecución de reglas |
| `external_responsibilities` | Análisis global, conexiones, otros reglamentos, recomendaciones y erratas no certificadas |
| `complete` | Derivado: todas las obligaciones resueltas, al menos una resistencia acreditada y ningún error de evaluación |

Cada obligación tiene `id`, `normative_ids`, `limit_state`, `component`, `condition`,
`applicability` (TRUE/FALSE/UNKNOWN), `status` (EVALUATED/NOT_APPLICABLE/PENDING),
`reason`, `required`, `alternatives`, `selected_alternative`, `executed_checks`,
`accepted_checks` y `resistance`. Un check ejecutado es evidencia parcial; solo
`accepted_checks` acredita la obligación. Desconocido nunca se vuelve N/A.
NOT_APPLICABLE requiere una condición falsa justificada, por ejemplo ausencia de
paredes delgadas en un macizo. Un campo `required` puede pedir información o una
implementación validada: rellenar números no siempre basta para completar.

## Subconjunto que puede obtener PASS o FAIL completo

Versión 1: macizo **custom** rectangular o circular ordinario y prismático,
tracción axial concéntrica (`Pu < 0`), todos los momentos/cortantes/torsión cero,
sin compuesto, LRFD o ASD ya soportados en D2, An/U proporcionados y físicamente
admisibles por HFS-011. No se amplía el soporte de familias o métodos.

Se requiere el nuevo objeto opcional `tension_scope`; sin él los cálculos siguen
ejecutándose, pero la aplicabilidad queda pendiente. No es una opción para
desactivar requisitos ni para acotar otras demandas a posteriori.

| Campo | Declaración o evidencia requerida |
|---|---|
| `ordinary_prismatic_member` | true: miembro ordinario prismático, no armado, pasador, ojal, barra roscada ni elemento de conexión |
| `concentric_axial_force` | true: carga axial concéntrica; no hay excentricidad/momento omitido |
| `no_special_conditions` | true: no existen condiciones especiales que invaliden D2 ordinario, como fatiga, fuego o demanda sísmica específica |
| `material_reference` | Referencia externa que justifique A3/grado/norma y valores del material |
| `demand_reference` | Referencia a demanda/combinación/método y análisis global aplicable |
| `net_area_reference` | Justificación B4.3/D3 de la sección neta crítica An y U, incluidas perforaciones/transmisión |
| `connection_reference` | Revisión externa de conexión y modos locales, incluido block shear; no los evalúa D2 |
| `external_checks_reference` | Revisión de responsabilidades externas y compatibilidad de exclusiones con el caso |

Todos esos campos tienen default `None` (= desconocido). Booleanos estrictos;
referencias, cuando se aportan, deben ser strings no blancos. Un false mantiene
el dominio sin acreditar. Datos extra se rechazan. No copiar estos valores a
true ni inventar referencias para obtener PASS. Son evidencia declarada por el
responsable del caso, no documentos verificados por el programa.

La evidencia externa permite delimitar precondiciones, **no cuenta como check
resistente**. Deben ejecutarse ambas clases D2 calificadas, con demanda, áreas,
materiales y traza concordantes; placeholders, etiquetas copiadas, datos no
finitos o capacidades no positivas no acreditan cobertura. Se contrastan las
dos resistencias mediante aritmética independiente de S22 D2/D3 en las pruebas.
PASS sigue siendo condicional a la veracidad de entradas/referencias y al alcance
de S22 local; no declara validadas la conexión, el edificio ni erratas pendientes.

## Dominios que permanecen incompletos

Compresión, flexión, cortante, torsión e interacciones conservan cálculos actuales
cuando pueden ejecutarse, pero no tienen acreditación completa en v1. Tampoco
se acredita tensión de catálogo mediante la sola etiqueta de familia. En
particular: E5/E7, W con N+M, biaxialidad sin axial, canal mayor, flexión pura de
compuestos y HSS con cortante/torsión no pueden obtener PASS por omisión.

N29 conserva H1/H2 como alternativas condicionadas; N23 G2.1/campo de tracción;
N41 encasado acero/RC/acero+refuerzo; N42 rutas por clase; N30 umbral H3/H1.
No hay una alternativa acreditada automáticamente por nombre ni se resuelven
sus condiciones con el router. Alcances especiales/desconocidos siguen pendientes
o producen el error de no soporte previo. No se implementan HFS-012/013.

N01/N03/N35 separan responsabilidades externas de la resistencia evaluada. N33
no añade obligaciones resistentes a partir de recomendaciones D1/E2. El reporte
legacy de admisibilidad conserva F-07 hasta su tarea; no gobierna esta cobertura.

## Migración de consumidores

- El JSON de salida añade `coverage` y `known_failures`; `status` admite INCOMPLETE.
  Consumidores con enums/esquemas cerrados deben actualizarse. No mapearlo a PASS
  ni a FAIL: no expresa una resistencia calculada incumplida.
- Los JSON existentes siguen válidos. Sus estados pueden cambiar aun cuando todos
  sus checks sean iguales. La ausencia de `tension_scope` no se rellena por defecto.
- CLI stdout, archivos detallados y motor comparten estos campos. Exit sigue 0
  para una ejecución con resultado (PASS/FAIL/INCOMPLETE) y 1 para excepción.
- Un lote no vacío propaga INCOMPLETE si alguno de sus casos es incompleto mediante
  el agregador común; conserva los FAIL por caso. **El lote vacío sigue siendo
  el defecto F-29**, reservado expresamente a HFS-014; no se corrige aquí.
- `checks` conserva valores, nombres, cláusulas y trazas. No consumirlos aislados
  como certificación ignorando cobertura. Las clases no calificadas pueden tener
  capacidades orientativas afectadas por hallazgos pendientes.

Resultados por ejemplo, cambios de expectativas y evidencia histórica preservada
en el [informe](../audit/hfs010/report.md). La transición no exige igualdad literal
de todo el JSON: sí exige igualdad de checks y errores previos cuando no se cambian
ecuaciones, y explica cada cambio de estado por separado.
