# ADR-003 — Trazabilidad normativa y pruebas independientes

Fecha: 2026-10-26. Tarea: HFS-001. Estado: arquitectura aprobada por el usuario al autorizar HFS-002. La matriz documental HFS-002 se entrega aparte para revisión; no se certifican reglas AISC.

## Problema

Las etiquetas de cláusula y las pruebas de positividad/routing no acreditan exactitud normativa ni cobertura. HFS-000 congela el comportamiento, incluidos defectos. El registro actual, las memorias y la matriz Markdown contienen fragmentos del conocimiento normativo; replicarlos en una web agravaría la divergencia (F-01/06/18/19/20/23/26/30/31).

## Alternativas

1. Usar snapshots del motor como prueba normativa: reproducible pero circular; descartada.
2. Crear un DSL normativo, motor de reglas y base de datos de trazas: automatización amplia, complejidad y segunda semántica de cálculo; descartada.
3. Funciones/reglas actuales con metadatos explícitos, referencias independientes y pruebas por escenarios. **Elegida.**

## Decisión

**DRY del conocimiento**, sin perder independencia de la verificación:

- La autoridad normativa es la fuente identificada por edición, artículo/ecuación y tipo documental; el código implementa una interpretación trazable, no sustituye esa autoridad.
- El registro existente `RuleDefinition` es el punto de partida de metadatos/aplicabilidad ejecutables. Ampliarlo en su tarea en lugar de crear un segundo registro para UI o reportes. Conservar condiciones complejas como funciones legibles, sin DSL ni descubrimiento dinámico.
- Por regla/método: ID estable, referencia precisa, condición y límites de aplicabilidad, entradas/unidades/ejes, función implementadora, factores, variables intermedias, resultado bruto, hipótesis, referencias de pruebas y estado de validación. Compartir el dato, no copiar textos normativos íntegros en cada reporte.
- La traza debe nacer en la evaluación que tomó la decisión. El reporte la formatea; no vuelve a calcular la capacidad, adivinar unidades por prefijo ni decidir otra rama. Mantener referencias a estados límite incluso si varias reglas reutilizan una función aritmética.
- La [matriz HFS-002](../normative/hfs002-applicability.md) tiene autoridad documental independiente del router: requisitos derivados de Specification identificada y revisión ingenieril, no de `RULE_DEFINITIONS`, `PROFILE_RULE_MAP`, predicados ni salidas. El registro ejecutable describe implementaciones y se contrasta después. Los esperados de selección tampoco se generan con el router. No es otro motor de capacidades: son requisitos y evidencia independientes.
- Specification, Commentary, User Note, manual/ejemplo auxiliar e inferencia se etiquetan separadamente. Una cita a «AISC» o a «conservador» no basta. Incertidumbre de interpretación y reglas no implementadas quedan visibles.

## Estrategia de pruebas

| Tipo | Propósito | Fuente del esperado |
|---|---|---|
| Regresión/characterization | Identificar cambios respecto a comportamiento conocido | Captura versionada, explícitamente no normativa |
| Unitarias/de contrato | Unidades, validación, selección, estados, errores | Requisito explícito y caso mínimo |
| Referencia independiente | Exactitud numérica en dominio declarado | Cálculo manual revisado o ejemplo publicado identificado; nunca la misma implementación |
| Fronteras/metamórficas | Límites, continuidad, signos/ejes y relaciones físicas | Propiedad justificada y condiciones; no sustituye un oráculo numérico |
| Integración/interfaz | Mismo cálculo y serialización desde CLI/API futura | Comparación con ejecución común y contrato |

Para una referencia numérica registrar fuente/página, fecha y autor/revisor cuando exista, entradas y conversiones, método, esperado, tolerancia absoluta/relativa y justificación. No inventar procedencia ni revisión. Para métodos iterativos incluir convergencia, equilibrio y parámetros. No copiar funciones productivas a un test y llamarlo independiente.

Un caso puede estar implementado sin estar verificado; no fundir ambos conceptos en un booleano. Un oráculo válido para un dominio no cubre automáticamente toda la familia. Cobertura de líneas sirve como diagnóstico de software, no puerta normativa. Mantener los `known defect` y sus F-ID hasta corrección demostrada; XPASS provoca revisión, no aceptación automática.

## Justificación

Se aprovecha el registro y las trazas existentes y se elimina la reconstrucción en reportes. La independencia del oráculo es una duplicación deliberada de razonamiento verificable, compatible con DRY: su finalidad es contrastar la implementación, no competir como motor de producción. Ninguna consolidación de ecuaciones con dominios distintos se admite sin equivalencia demostrada y referencias conservadas.

## Consecuencias

La matriz actual `docs/aisc_360_22_traceability.md` se conserva como inventario manual inicial de implementación; después podrá generarse desde metadatos revisados, sin mantener dos autoridades editables. Esa generación no aplica a la matriz normativa independiente: sus requisitos no provienen del router. Se adopta la [política de evidencia](../audit/evidence-policy.md) para distinguir fixtures mantenidas, capturas de aceptación e información regenerable. PASS se limita al alcance verificable declarado, nunca a certificación AISC global.

### Aplicación HFS-023 — para revisión, 2026-10-29

`RuleDefinition.metadata` materializa esa decisión en la colección existente.
El índice de implementación se genera; la tabla manual anterior queda archivada.
HFS-002, selección ejecutable, plan/evidencia HFS-010 y transporte permanecen
en sus dueños. Los descriptores incluyen reglas compuestas y vacíos, sin convertir
su registro en permiso de ejecución. Pruebas referenciadas, oráculos acotados
y acreditación normativa tienen significados distintos. Se conserva F-31 P0
abierto y F-37 explícito; no se adelanta la traza de HFS-024 ni una auditoría
normativa. [Contrato y límites](../contracts/hfs023-normative-registry.md).

## Riesgos y verificación futura

### Aplicación HFS-024 — para revisión, 2026-10-29

Se instrumentan los productores mediante observación optativa, en contexto de
ejecución, y pasos explícitos con valores locales. Identidad/citas/evidencia se
obtienen del registro HFS-023; las decisiones de cobertura se copian del resultado
canónico. La traza es un documento auxiliar y no modifica los diez esquemas JSON
1.0. Se descarta reconstruir fórmulas a partir de memorias legacy y añadir campos
silenciosamente al contrato congelado. También se descarta propagar un argumento
nuevo por todos los cálculos: el contexto optativo preserva firmas y limita el
cambio, a costa de una dependencia contextual que requiere aislamiento probado.

La frontera observada de una regla no prueba instrumentación aritmética completa.
Campos desconocidos y ramas pendientes se conservan explícitos, especialmente
F3/F4/H1/I. Las memorias existentes permanecen como formato de compatibilidad;
el exportador optativo solo consume el snapshot. No se duplican operaciones,
factores, selección ni registro. Contrato, alternativas y riesgos en
[HFS-024](../contracts/hfs024-calculation-traces.md) y su
[informe](../audit/hfs024/report.md). F-31 y acreditaciones pendientes siguen abiertos.

Metadatos desactualizados pueden aparentar trazabilidad; probar correspondencia de IDs, referencias y rutas cuando se implemente el registro. El error de un manual auxiliar o una transcripción también puede propagarse: registrar contraste y revisión. Una expectativa de regresión no debe impedir corregir un defecto. La revisión documental presente no cierra F-30 ni certifica AISC 360-22; AISC 341-22 sigue siendo alcance independiente.
