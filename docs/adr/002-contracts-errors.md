# ADR-002 — Contratos comunes, completitud y errores

Fecha: 2026-10-26. Tarea: HFS-001. Estado: arquitectura aprobada por el usuario al autorizar HFS-002, con precisiones documentales incorporadas. No cambia el JSON, los enums, errores ni códigos de salida actuales.

## Problema

`models.py` permite cargas omitidas/extra y `CheckResult` carece de unidad y completitud explícitas. `engine.py` puede producir PASS sin checks, mientras `run.py` reconstruye unidades/DCR y usa exit 0 para resultados FAIL. Resolverlo por separado en CLI/web multiplicaría contratos y decisiones contradictorias (F-02/04/05/08/09/10/21/29/31/32).

## Alternativas

1. Diccionarios y validaciones independientes en cada interfaz: cambios rápidos, múltiples fuentes de verdad; descartada.
2. Sustituir todos los modelos por entidades, DTO y esquemas separados: tipado explícito, pero duplicación y migración masiva sin necesidad; descartada.
3. Evolucionar los modelos Pydantic compartidos, conservando excepciones estructuradas y una transición explícita. **Elegida.**

## Decisión

**DRY de contratos:** `models.py`, `results_model.py` y `sections/models.py` son propietarios actuales. El CLI y la API futura deben validar y serializar esos mismos conceptos; un esquema JSON se derivará de los modelos, no será una definición editable paralela. Adaptadores pueden tener envoltorios de transporte, nunca otro significado de carga, estado o capacidad.

Distribuir responsabilidades sin repetir políticas:

| Responsabilidad | Propietario objetivo |
|---|---|
| Tipo, campos permitidos, finitud y dominio local | Modelos compartidos; reglas reutilizables pequeñas si hay consumidores reales |
| Relaciones entre entradas y compatibilidad del caso | `domain/validation.py` |
| Requisitos normativos esperados | Matriz normativa derivada de fuentes y revisada independientemente del router; no depende de reglas disponibles |
| Soporte/aplicabilidad ejecutable y campos requeridos por regla | Registro/selección de `domain/routing`, contrastado con requisitos independientes |
| Existencia, identidad, procedencia y normalización del perfil | `sections` |
| Cálculo bruto, eje, unidad y traza | Evaluación/regla propietaria; presentación no los reconstruye |
| Agregación y cobertura | Ejecución común del motor |
| Texto, formato, traducción de transporte | Adaptador CLI/HTTP o reporte |

No repetir la misma condición en tres sitios. Se permite una precondición defensiva en una función invocable directamente, pero debe usar la política canónica o documentar un dominio distinto. La validación del navegador será ayuda de interacción, nunca autoridad de ingeniería.

Decisiones para contratos futuros, a implementar solo en tareas autorizadas:

- Distinguir entrada faltante, cero explícito y valor inválido; rechazar campos extra y no finitos. La lista exacta de campos obligatorios se resolverá en HFS-011, sin imponer en este ADR que todas las cargas deban ser obligatorias.
- Una política única resolverá cargas legacy/direccionales, signos y ejes. No inventar aquí una transformación física ni legitimizar el reemplazo silencioso de Vu.
- Conservar valores brutos finitos para decisiones, dimensión/eje y método. Redondeo de presentación separado. Datos no disponibles deben tener causa explícita, no cero o infinito presentado como capacidad válida. No exigir Decimal sin necesidad demostrada.
- Resultados de check objetivo: PASS, FAIL, NOT_APPLICABLE, NOT_EVALUATED. Resultado de caso: PASS, FAIL, INCOMPLETE. Adoptar **INCOMPLETE** como nombre público objetivo; `BLOCKED` podrá describir una causa, no un segundo estado equivalente que deba manejar cada cliente.
- Criterio objetivo de agregación: cobertura incompleta -> INCOMPLETE, conservando cualquier check FAIL ya conocido; cobertura completa con algún fallo -> FAIL; cobertura completa sin fallos -> PASS. Cero checks y lote vacío nunca acreditan PASS. La definición detallada de cobertura corresponde a HFS-002/010, no se construye ahora.
- Error técnico o entrada inválida no equivale a fallo resistente. Conservar `SteelDesignError` y códigos estructurados; el adaptador traduce excepciones conocidas, y errores inesperados se registran sin inventar un resultado estructural. No añadir todavía códigos HTTP ni otro catálogo de excepciones.

**F-32:** mantener por compatibilidad el exit actual (0 si ejecutó, 1 ante excepción) mientras se revise su contrato. Consumidores actuales deben comprobar también el estado JSON. No adoptar automáticamente «FAIL implica exit no cero»: esa elección afecta scripts y requiere transición documentada. La futura API también separará éxito de transporte y resultado de diseño.

## Justificación

Precisión aprobada en HFS-002: **PASS expresa cumplimiento del alcance verificable declarado**, con hipótesis y exclusiones identificadas; nunca certificación global automática AISC 360-22. El alcance no puede definirse a posteriori como las reglas que sí se ejecutaron. La ausencia de validación independiente exigida para ese alcance impide anunciarla como obtenida. Véase la [propuesta de cobertura](../normative/hfs002-coverage-proposal.md), sin modificación del contrato actual.

Un modelo compartido reduce discrepancias de validación sin duplicar jerarquías. Separar completitud, resistencia y transporte evita usar la ausencia de error como prueba de seguridad. Unidad/eje y DCR bruto eliminan inferencias del reporte; las referencias de fuente se vinculan mediante el [ADR-003](003-traceability-testing.md).

## Consecuencias

Habrá cambios incompatibles que deben declararse: nuevos estados, campos extra rechazados y precisión de resultados pueden afectar consumidores. Versionar y documentar esas transiciones cuando se implementen HFS-010/011/015/022; no esperar al empaquetado para advertir una ruptura temprana. No mapear INCOMPLETE a PASS para conservar compatibilidad. Mantener el histórico y explicar diferencias esperadas en pruebas.

## Riesgos y verificación futura

Validación excesiva puede rechazar entradas legítimas; fijar dominios por fuente/caso. La coexistencia transitoria de formatos exige prueba de lectura/escritura y decisiones explícitas de migración. Un futuro esquema generado debe comprobarse contra el modelo, no actualizarse a mano. Cubrir fallos parciales, lotes, excepciones, límites de redondeo y paridad CLI/API. Nada de ello altera los contratos presentes en HFS-001.

## Suplemento HFS-022R — Preparación y transporte

Fecha: 2026-10-28. Decisión implementada para revisión independiente sobre
HFS-022 aprobado (`bae6463`); no modifica retrospectivamente HFS-001.

**Problema.** Contratos importaba `execution.prepare_cases`, que importaba el
motor para anotaciones. Leer JSON cargaba router, reglas y repositorio aunque
no los utilizara. Los esquemas reproducibles carecían de un consumidor validador
independiente y varios errores de integridad solo señalaban el payload completo.

**Alternativas.** A: poner el import del motor bajo TYPE_CHECKING y diferir
anotaciones: menor cambio, pero conserva contratos → ejecución y altera la
evaluación runtime de anotaciones salvo introducir otra solución para ella.
B: extraer conjuntamente cinco símbolos de preparación a un único módulo:
separa una responsabilidad real con dos consumidores, sin duplicar validación.
No se elige separar contracts por tamaño ni introducir capas genéricas.

**Decisión y justificación.** B, `steel_design.preparation`, con reexports por
identidad desde execution y fachadas vigentes de run. Preparación mantiene sus
guardas locales; contratos llama al validador de dominio original. Ejecución
conserva sus anotaciones, orden y consumo perezoso. JSON Schema se prueba con
jsonschema Draft 2020-12 solo en desarrollo; modelos/generador siguen siendo
la única fuente del esquema. Las relaciones semánticas permanecen en Python.
Los errores señalan campos/índices concretos preservando códigos y causas.

**Consecuencias y riesgos.** Un archivo adicional reduce la dependencia real
de transporte en ejecución. Cambia `__module__` de los símbolos trasladados;
se preservan imports, identidad entre reexports, firmas y comportamiento,
sin prometer persistencia pickle entre versiones. Ninguna fachada sin consumidor
se añade. La precisión del primer error puede variar si hay varios conflictos
simultáneos; no se cambia el orden de validación/ejecución legacy. Las rutas de
casos efectivos pueden referir valores heredados de la base. La interoperabilidad
no autentica resultados ni acredita AISC; F-31 sigue P0 abierto. Importar la
constante E desde axial_calc sigue siendo dependencia de la guarda canónica,
sin cálculo. Evidencia y límites en el [suplemento](../audit/hfs022/architecture-review/report.md).
