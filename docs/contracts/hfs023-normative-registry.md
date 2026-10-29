# HFS-023 — Registro normativo declarativo mínimo

Estado: implementación para revisión técnica independiente. Base `main`
`1b170929374bd590292ce3f5a17fca1e65bb79ce`. La aprobación arquitectónica HFS-022Q
fue declarada por el usuario. Este hito no realiza una auditoría normativa,
no acredita disposiciones nuevas y no asigna una calificación.

## Propietario y consumidores

La única colección canónica de reglas es
`steel_design.domain.routing.profile_router.RULE_DEFINITIONS`. Se amplía la
dataclass existente `RuleDefinition` con `metadata: RuleMetadata | None`.
El default `None` permite conservar la firma de construcción anterior, pero
el registro distribuido exige metadatos para **cada** entrada. Los modelos
Pydantic nuevos `RuleMetadata` y `Citation` son inmutables, rechazan campos
extra y validan su propia integridad; no duplican SteelCase, Section, checks,
resultados, preparación o contratos de transporte.

`registry_metadata.py` declara grupos de anotaciones que se adjuntan una vez
a las definiciones. No conserva otro diccionario público de reglas, carga
JSON/archivos, registra plugins ni evalúa casos. Agrupar contexto documental
no une ecuaciones, factores ni implementaciones.

Consumidores actuales: router, que continúa leyendo exclusivamente los campos
ejecutables anteriores; auditor `scripts/audit_hfs023.py`; pruebas de integridad;
e [índice derivado](../aisc_360_22_traceability.md). Engine, contratos, CLI,
reporting y SVG no consultan `metadata`. El contrato JSON 1.0 no incluye estos
modelos y sus diez schemas permanecen intactos. La distribución sigue en 0.2.0;
no se introduce una versión de transporte ni de cobertura nueva.

## Identidad, fuente y evidencia

| Campo / propietario | Significado |
|---|---|
| `RuleDefinition.rule_id` | ID estable del registro; **no** número de ecuación ni etiqueta de salida |
| `rule_class` | Clase Python real responsable del check; `None` si no hay clase de check para esa entrada |
| `implemented` | Existencia de esa clase, no implementación completa de la disposición |
| `applicability` | Predicado ejecutable original, o `None` para entradas descriptivas; no significa «aplica siempre» |
| `required_section_fields` | Requisitos legacy del selector; no lista exhaustiva de entradas de la disposición. Las guardas de regla y requisitos especiales del router conservan autoridad |
| `metadata.citations` | Edición, fuente S22/UN22/C22, capítulo, disposición, ecuaciones identificadas y localizador PDF 1-based; A3 conserva localizador explícitamente pendiente |
| `matrix_ids` | Vínculos a N01–N45 de la matriz independiente; no obligaciones calculadas para un caso |
| `family_scope`, `conditions` | Descripción de dominio/condiciones; no predicados nuevos ni reglas para una UI |
| `equation_note` | Distingue localizador, rango, correspondencia conocida y correspondencia pendiente; nunca deducir ecuación desde ID |
| `calculation_refs`, `selection_ref` | Módulos/símbolos canónicos de cálculo y selección existentes; el auditor comprueba resolución e identidad |
| `method_note` | Límites del soporte actual; política ejecutable única en `design_methods.validate_method_scope` |
| `implementation_state` | `PARTIAL`, `BLOCKED`, `NOT_IMPLEMENTED`, `EXTERNAL` o `ADVISORY`, siempre acompañado de límites |
| `software_verification`, `software_tests` | `TESTS_REFERENCED` o `NO_DIRECT_TEST`: describe referencias disponibles, no afirma por sí solo que pasen o cubran cada rama |
| `independent_tests`, `independent_scope` | Referencias numéricas/manuales existentes y su alcance restringido. Vacío exige explicación, no equivale a validado |
| `normative_validation` | `NOT_ACCREDITED` para la disposición completa en este hito. Ni un test ni el contador de referencias pueden promoverlo |
| `limitations`, `findings` | Vacíos y F-ID relacionados; el estado vivo/prioridad siguen en tracking, no en otro mapa mutable |

La identidad/jerarquía de fuentes permanece en
[HFS-002 fuentes](../normative/hfs002-sources.md): S22 es Specification local;
UN22 es User Note informativa; C22 es Commentary informativo. El registro puede
distinguir los tres, sin convertir una nota en obligación. Se conserva la
incertidumbre de erratas F-28. No se incorpora una transcripción de terceros
ni se afirma que el documento local incluya correcciones posteriores.

Los rangos de ecuaciones localizan la disposición; **no acreditan una
correspondencia exhaustiva rama por rama**. Se conserva explícitamente F-37:
`F3-3` es un ID interno; `H3-1`/`H3-2` identifican las reglas para H3.1/H3.2;
la etiqueta legacy `H1-2` en tracción no representa la ecuación de interacción
de S22. F4 mantiene el vínculo a su alternativa F5 y User Note, sin validar
su conservadurismo ni cambiar el cálculo. F7 conserva la numeración local
con erratas pendientes. Estos hallazgos no autorizan relabeling de resultados
en HFS-023; HFS-024 deberá tratar los cambios de traza de forma explícita.

## Extensión sin otra selección

Se conservan los 56 IDs anteriores. Los 55 predicados/bindings activos o
bloqueados originales permanecen iguales; `I2` conserva su ID como descriptor
del antiguo placeholder, sin el predicado muerto `_has_interaction` que siempre
devolvía False. `I2` no estaba en `PROFILE_RULE_MAP` y no afirma que todo I2
carezca de implementación. Las 17 clases compuestas reciben IDs descriptivos
inequívocos, sin modificar `ProfileRouter._get_composite_rules`.

Se agregan 20 registros de condiciones externas, recomendaciones y vacíos,
incluidos canal mayor fuera de F2, interacción restante y momentos compuestos
sin check independiente. Ninguna entrada nueva se añade a `PROFILE_RULE_MAP`.
Una entrada descriptiva tiene `applicability=None`; el validador rechaza que
se intente enlazarla desde un mapa de selección. Los campos de texto nunca
se interpretan como instrucciones ejecutables.

El motor puede seguir usando funciones auxiliares para I5 aunque falte el
check de flexión pura. Por eso se distingue `rule_class=None` de ausencia de
cualquier función auxiliar; `calculation_refs` identifica las funciones que
sí existen. Una comprobación I3 de cuantía/transferencia tampoco acredita M.

`coverage.build_coverage_plan` y `coverage_evidence` conservan requisitos,
enlaces a ejecuciones y guardas de acreditación HFS-010. No se mueve `_CLAIMS`
al registro, se alteran estados o se redefinen obligaciones desde reglas
disponibles. La acreditación **condicional y acotada** ya existente de D2 para
tirantes macizos se conserva: no implica acreditación integral de D2/D3.

Las familias publicadas por el auditor bajo `routed_profiles` describen código;
`family_scope` y los N-ID remiten al dominio normativo documental. No usar
`routed_profiles` para derivar aplicabilidad normativa ni generar oráculos.
F-31 permanece **P0 abierto**. ASD en F/I sigue bloqueado según HFS-017.

## Integridad y mantenimiento

Desde una instalación editable con las constraints vigentes:

```text
python scripts/audit_hfs023.py --check
python scripts/audit_hfs023.py --check --out .venv/hfs023-review-new
python -m pytest -q -p no:cacheprovider tests/test_hfs023_registry.py
python scripts/generate_hfs022_schemas.py --check
```

`--out` exige un directorio nuevo y genera inventario completo JSON, consumidores
y prueba de alcance contra el SHA base. Es un comando de auditoría de este hito,
no un formato público JSON 1.0. Para regenerar únicamente el índice derivado:

```text
python scripts/audit_hfs023.py
```

La matriz de requisitos HFS-002, su contraste histórico, fuentes y oráculos no
son salidas de ese generador. La tabla manual anterior está archivada con sus
bytes en evidencia HFS-023; la ruta vigente pasa a ser una vista derivada, de
modo que no quedan dos índices manuales de implementación que puedan divergir.

Las pruebas comprueban IDs, completitud, fuentes/N-ID/F-ID, símbolos y nodos de
tests existentes, propietarios por capítulo, inmutabilidad, herencia y bloqueo
de entradas descriptivas en routing. Las mutaciones demuestran rechazo de
referencias rotas, ausencia de campos y falsas acreditaciones. No prueban la
verdad de una cita ni la suficiencia ingenieril de un oráculo.

Compatibilidad interna: iterar `RULE_DEFINITIONS` ahora incluye descriptores
sin predicado; no ejecutar todas sus entradas. El router sigue usando su mapa
explícito y su rama I original. La firma del constructor solo añade un campo
opcional; se retira un helper privado sin consumidores operativos. No cambia
la API pública HFS-021A, el CLI, las memorias, los SVG ni los JSON legacy/1.0.
