# HFS-022 — Contratos JSON optativos, versión 1.0

Estado: implementación para revisión independiente; cierre condicionado a CI
remota Windows/Ubuntu sobre la publicación final. No certificación AISC.
Base `main c91e55d5a194dfb8e80777d9e41efa1ee4b7fe02`.

## Diagnóstico y decisión

El JSON vigente no tiene versión de transporte. `SteelCase` valida entradas;
`execution` prepara casos/bundles; los modelos de salida tienen serializadores,
campos calculados y un agregador que puede sustituir un `status` recibido.
Pydantic permite ignorar extras en salidas. Leerlas directamente no comprueba
que el estado, `known_failures`, `complete` o `display` declarados coincidan.
`CheckResult` puede proyectar no finitos a null con diagnóstico. Un resumen CLI
excluye details; una memoria los reorganiza. No son intercambiables con el JSON
completo de `EngineResult`.

Se elige un solo módulo `steel_design.contracts`, sin motor, registro normativo,
plugins ni DTO de ingeniería nuevos. `ContractDocument` es una dataclass de
transporte: contiene el modelo canónico, no otra representación de sus campos.
Alternativas descartadas: versionar todos los modelos (rompe legacy), activar
migración desde CLI (cambia su contrato), duplicar modelos por versión (dos
fuentes de verdad), aplanar bundles (pierde overrides/ausencias).

Los nuevos consumidores usan explícitamente esta API; el CLI, las memorias,
`model_dump` y los ejemplos conservan sus formatos y códigos de salida.

## Cuatro versiones distintas

| Concepto | Valor / autoridad |
|---|---|
| Distribución instalable | `structurelab-hfs` **0.2.0**, `pyproject.toml` |
| Contrato JSON optativo | `contract_version: "1.0"`, `contracts.CONTRACT_VERSION` |
| Cobertura normativa operativa | `CoverageReport.version: "HFS-010-v1"`, sin cambios |
| Edición normativa del motor | ANSI/AISC 360-22; no se infiere desde una versión de software |

Se conserva 0.2.0 durante esta entrega para revisión, sin publicación ni decisión
de release. Añadir una API justifica evaluar una versión de distribución nueva
al publicarla; no se utiliza 1.0 de transporte como versión del paquete. El
manifiesto de evidencia identifica el código probado, no solo la distribución.

## Envoltura y tipos

```json
{
  "contract_version": "1.0",
  "kind": "engine_result",
  "payload": {}
}
```

El payload vacío anterior es ilustrativo, no un resultado válido.

| kind | payload devuelto | Autoridad / alcance |
|---|---|---|
| `case_input` | `SteelCase` | Campos, defaults, restricciones y enums canónicos; validación local y `domain.validation.validate_case` |
| `case_bundle` | `dict[str, Any]` | Fragmentos originales, `cases` y opciones; merge/validación local por `execution.prepare_cases`, guardas de caso compartidas |
| `coverage_report` | `CoverageReport` | Plan/evidencia, incluyendo `CoverageObligation` y `ExecutedEvaluation`; no se reconstruye un plan |
| `check_result` | `CheckResult` | Valores originales y decisión, unidades, details, diagnóstico y display canónicos |
| `engine_result` | `EngineResult` | Checks completos, cobertura, estado agregado y fallos conocidos |

Solo `case_input` permite `output` **en la envoltura**, opcional, con
`OutputOptions` canónico. Es preferencia de transporte, no campo ingenieril ni
orden de escritura. Así no se añade otro objeto `payload.case`. Ausente se
conserva ausente; `output: null` no se admite. En JSON versionado su clave es
`write_results_json`. La migración acepta los tres aliases legacy, normaliza
solo el nombre de la opción y conserva su valor. Los bundles mantienen aliases
en sus fragmentos y los resuelven en el propietario vigente después del merge.

## API pública por módulo

```python
from steel_design.contracts import (
    ContractDocument, ContractError, validate_document, load_json,
    dump_json, migrate_legacy, get_schema,
)
from steel_design.models import SteelCase

# legacy_payload es el dict de entrada ya disponible en memoria.
document = migrate_legacy(legacy_payload, kind="case_input")
versioned_json = dump_json(document)
restored = load_json(versioned_json, expected_kind="case_input")
assert isinstance(restored.payload, SteelCase)
# engine.run(restored.payload) es una acción explícita posterior del consumidor.
# restored.output no ejecuta exportación.

result_json = dump_json(ContractDocument(kind="engine_result", payload=result))
schema = get_schema("engine_result", version="1.0", mode="validation")
```

| Función | Contrato |
|---|---|
| `validate_document(data: dict, *, expected_kind=None) -> ContractDocument` | Valida documento versionado completo; devuelve modelos canónicos, nueva copia para bundle |
| `load_json(data: str | bytes, *, expected_kind=None) -> ContractDocument` | Decodifica JSON, rechaza claves duplicadas/no finitos y delega en la validación común |
| `dump_json(document: ContractDocument) -> str` | Revalida, rechaza pérdida/inconsistencia, emite UTF-8 conceptual, keys ordenadas, indent 2 y LF final; no escribe archivos |
| `migrate_legacy(data: str | bytes | dict, *, kind) -> ContractDocument` | Migración explícita del tipo declarado; rechaza cualquier `contract_version` presente |
| `get_schema(kind, *, version="1.0", mode="validation") -> dict` | Esquema nuevo en cada llamada; modo validation o serialization; sin I/O |

Crear `ContractDocument` no valida. Sus payloads pueden ser mutables;
`dump_json` vuelve a comprobarlos y nunca repara el objeto del llamador.
Para serializar un modelo se entrega ese modelo como payload. No se admiten
subclases arbitrarias ni objetos que aparenten el mismo tipo.

`ContractError(ValueError)` expone `code` y `path` (JSON Pointer cuando se conoce;
vacío significa documento completo). Códigos: `INVALID_JSON`,
`INVALID_DOCUMENT`, `UNSUPPORTED_VERSION`, `UNKNOWN_KIND`, `KIND_MISMATCH`,
`EXTRA_FIELD`, `INVALID_PAYLOAD`, `NONFINITE_NUMBER`, `LOSSY_JSON`,
`INCONSISTENT_PAYLOAD`, `COVERAGE_CONFLICT`, `CHECK_CONFLICT`,
`ALREADY_VERSIONED`, `INVALID_SCHEMA_MODE`. Los errores Pydantic/de dominio
quedan encadenados como causa, con sus diagnósticos de campos. No son FAIL
resistente ni sustituyen el contrato de errores legacy del CLI.

## Migración, defaults y límites de entradas

Tres recorridos distintos: CLI legacy actual, `migrate_legacy` explícito y
`load_json` versionado. Nunca intentar migración como fallback a una versión
desconocida. Se rechazan 0.2.0, HFS-010-v1, ediciones AISC y versiones futuras
en `contract_version`.

La entrada individual usa `exclude_unset=True` recursivo, conservando
`model_fields_set`, defaults explícitos, null opcionales y ceros suministrados.
El valor efectivo omitido sigue siendo el default actual, incluido LRFD y
las componentes de carga cero. No significa demanda desconocida. Pu positivo
es compresión; los signos, unidades y ejes son los de HFS-011/013/017.
No se transforma Vu en resultante ni se convierten combinaciones LRFD/ASD.
Un entero que no pueda representarse exactamente en el float canónico de una
entrada individual o de un caso efectivo del bundle se rechaza en lugar de
redondearlo silenciosamente.

Bundles: se conserva el dict original, orden, `name`, opciones, base y overrides.
Se valida cada caso efectivo con el **mismo** merge profundo existente. Un
fragmento puede ser inválido aisladamente y válido tras un override, como antes.
No se reemplaza el bundle por casos expandidos. `cases=[]` sigue inválido; las
guardas no ejecutan motor, catálogo, selección o geometría. Validar el contrato
examina todos los casos, mientras la ejecución legacy conserva su iteración
perezosa y puede fallar después de ejecutar casos previos. Esa diferencia es
intencional: validación optativa sin efectos frente a ejecución secuencial.

La validación no certifica existencia/propiedades del perfil ni relaciones que
requieren Section, selección o capacidades. El motor deberá repetir sus
guardas al ejecutar. Los bloqueos ASD F/I de `validate_case` se conservan;
no se implementa HFS-039 ni validación de combinaciones externas.

## Integridad de salidas

- La versión 1.0 exige snapshots completos de los modelos de salida, incluidos
  defaults y campos calculados. La migración puede completar defaults omitidos
  compatibles, pero compara **cada valor aportado** contra el modelo resultante.
- Antes de validar se retiran exclusivamente los computed fields declarados
  por Pydantic, conservando el original para cotejo posterior. Extras anidados
  de modelos tipados se rechazan. `status`, `numeric_issue`, `known_failures`,
  `complete` y `display` discrepantes nunca se aceptan tras una corrección silenciosa.
- Para comprobar coherencia aritmética de un check se reutiliza
  `CheckResult.from_values`, único constructor de DCR/decisión; no se calcula
  resistencia ni se ejecuta fórmula AISC. Se conserva el placeholder histórico
  PASS 0/0, DCR 0; no recibe por eso cobertura. Los valores serializados proceden
  del productor, no del objeto temporal de comprobación. No hay tolerancias ni
  redondeos nuevos. Una representación antigua redondeada puede ser incompatible;
  se rechaza sin reescribir su evidencia.
- La agregación sigue exclusivamente en `EngineResult.aggregate` y
  `CoverageReport.complete`. El contrato compara su resultado con el declarado.
- Integridad referencial: IDs de obligaciones únicos, ejecuciones únicas con
  índices contiguos desde cero; accepted sin duplicados y subconjunto de executed;
  referencias ejecutadas existentes; correspondencia bidireccional para las
  obligaciones presentes; estados/aplicabilidad/aceptación coherentes. En un
  EngineResult la lista de ejecuciones debe corresponder a todos sus checks;
  una resistencia aceptada no puede referenciar un placeholder con capacidad cero.
- El productor puede registrar claims de obligaciones **ausentes** del plan
  (por ejemplo Vu/Vux alternativos). Se conservan: no se crean obligaciones a
  partir de ese texto. Una cobertura aislada no prueba que existan checks
  externos con resistencias válidas; solo permite comprobar su propio grafo.
- `implementation: "src.steel_design..."` es texto histórico, nunca importación.
  No se consulta el router ni se acredita una regla por nombre o cláusula.

La comprobación de integridad **no autentica** documentos ni detecta una
falsificación coherente de todos sus campos. Tampoco valida fórmulas, capacidades,
dominios, referencias externas o completitud de la matriz normativa. PASS conserva
su alcance verificable declarado; F-31 sigue P0 abierto y F-32 sigue vigente.

### Casos no migrables sin pérdida

Los scalars no finitos se rechazan en JSON y antes de serializar modelos,
incluidos values dentro de details. Las proyecciones legacy con `dcr:null` y
`nonfinite_values` no reconstruyen un CheckResult finito: error explícito,
archivo original intacto. No se convierten null en cero/infinito ni FAIL en PASS.

`details`, `scope_evidence` y `evaluation_errors` tienen contenido dinámico;
solo se garantiza JSON finito sin pérdida de claves/valores, no una estructura
normativa fina. Se rechazan objetos Python arbitrarios, tuplas y claves no string
cuando su transformación perdería información. Diagnósticos ya representados como
JSON dentro de estos mapas se conservan como JSON; no se recupera un original
no finito a partir de sus cadenas. Esa tipificación corresponde a tareas futuras.

Resúmenes CLI, archivos de memoria y errores de ejecución no son ninguno de
los contratos completos de salida. Se rechazan sus envolturas/campos extra;
no se extraen capacidades ni se reconstruye details desde textos de memoria.

## Esquemas y reproducción

Ubicación canónica: [docs/schemas/contracts/1.0](../schemas/contracts/1.0/).
Diez esquemas: cinco tipos por dos modos; manifiesto con versiones efectivas
de Pydantic/core y hashes. Fuente: `get_schema` y modelos Pydantic, nunca edición
manual. JSON Schema Draft 2020-12 y generación por modelos están descritos en
la [documentación oficial de Pydantic](https://pydantic.dev/docs/validation/latest/concepts/json_schema/).

```powershell
python -m pip install -c requirements/ci-constraints.txt -e ".[dev]"
python scripts/generate_hfs022_schemas.py
python scripts/generate_hfs022_schemas.py --check
python scripts/verify_hfs020.py --out .venv/hfs022-review
```

Dependencias de generación fijadas por las constraints existentes: Pydantic
2.14.1/core 2.50.1. `--check` compara bytes, incluidos nombres/archivos ausentes
o sobrantes, sin escribir; exit 1 ante deriva. UTF-8, orden estable y LF; la
regla Git eol=lf se limita a los nuevos esquemas para que Windows no introduzca
otra deriva de finales de línea. No normaliza JSON ni gráficos históricos.

En entradas se expone el modo solicitado. En salidas ambos modos describen
el snapshot serializado completo porque sus computed fields son obligatorios
también al leer; se genera desde el modo serialization de Pydantic. Las únicas
restricciones adicionales son las de la envoltura/snapshot de transporte:
campos cerrados y presencia de las propiedades publicadas, sin copiar sus tipos.

Los fragmentos de bundles no reciben prematuramente restricciones del caso
efectivo. Sus claves se derivan de SteelCase y se incluye el esquema canónico
EffectiveSteelCase en `$defs`; las validaciones posteriores al merge necesitan
Python. Tampoco JSON Schema expresa todas las relaciones de modelos,
integridad de índices o comparación de campos derivados. Un validador genérico
de JSON Schema no sustituye `validate_document`. No se añade otra dependencia
de validación ni un segundo sistema de reglas.

Inventario, consumidores, eliminación de copias y evidencia real:
[informe](../audit/hfs022/report.md), [inventario](../audit/hfs022/inventory.md).
