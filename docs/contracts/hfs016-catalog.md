# HFS-016 — Identidad y consulta del catálogo

Estado: implementación para revisión. HFS-011 aprobada por el usuario. Esta tarea no valida propiedades contra una fuente normativa ni modifica ecuaciones. [Informe y evidencia](../audit/hfs016/report.md), [ADR-001](../adr/001-engine-architecture.md), [ADR-002](../adr/002-contracts-errors.md).

## Identidad formal

Dentro de una instancia de `SectionRepository`, la clave es exclusivamente `section_identity(name)` de `sections/identity.py`:

1. Exigir string no vacío después de normalizar.
2. Sustituir cada secuencia de espacios ASCII (`U+0020`, tabulación, CR, LF, form feed y vertical tab) por un espacio ordinario; retirar espacios de los extremos.
3. Convertir únicamente letras ASCII a–z a A–Z.

`" hea  100 "`, `"HEA\t100"` y `"HEA 100"` comparten identidad. `HEA100`, `HEA-100`, `HEA_100`, `HEA 0100` y `HEA 100MM` son distintos. No se eliminan espacios internos, puntuación, unidades ni sufijos. No se convierten fracciones ni dimensiones. Los caracteres no ASCII permanecen significativos (incluido espacio no separable); no hay transliteración, normalización Unicode, equivalencia de comillas o conversión global `ß→SS`.

El nombre no identifica globalmente una sección física acreditada: es una clave de búsqueda dentro del catálogo cargado. Fuente, hoja, fila, tipo y geometría son datos de registro, **no desempates automáticos**. Cargar distintas fuentes bajo la misma identidad produce ambigüedad. La diferencia de tipo tampoco crea dos identidades seleccionables con el mismo nombre.

El loader usa esa función para el nombre importado; load/get/get_duplicates usan la misma política. Las conversiones de cadenas para clasificar familias y generar nombres de archivos de reporte conservan su propósito y no seleccionan identidades. Motor y CLI no implementan otra política de consulta.

## Procedencia sin corregir la fuente

`Section.source` es un nuevo campo opcional `SectionSource`:

| Campo | Significado |
|---|---|
| `file` | Ruta absoluta del archivo leído |
| `sha256` | Hash de los mismos bytes que parsea openpyxl; 64 caracteres hexadecimales |
| `sheet` | Nombre exacto de hoja |
| `row` | Fila Excel, base 1; incluye encabezado en fila 1 |
| `original_name` | Texto de celda antes de normalizar mayúsculas/espacios |

Las propiedades de `Section` siguen siendo las magnitudes normalizadas por el loader existente (mm y potencias correspondientes), con sus conversiones y derivaciones anteriores. El error conserva todas esas propiedades y source por candidato. No copia toda la hoja ni afirma acreditar las conversiones; hash+hoja+fila permiten rastrear el dato original en el archivo preservado. Un dato construido en Python tiene `source=None` por defecto: procedencia desconocida explícita, sin inventar archivo o fila. Una procedencia aportada por código cliente es una declaración, no una firma autenticada.

Se conserva el Excel sin renombrar filas ni escoger cuál HEA 100 es correcta. No se introduce una clave pública por fila que permita eludir el bloqueo. Resolver nombres/propiedades exige una fuente verificable y otra revisión.

## Contrato del repositorio y migración

| Operación | Antes | HFS-016 |
|---|---|---|
| `load(List[Section]) -> None` | Acumulaba; último registro sobrescribía nombre repetido | Acumula **todos** los registros, duplicados incluidos. Valida el lote antes de insertarlo; un lote estructuralmente inválido no se inserta parcialmente |
| `get(name) -> Optional[Section]` | Último registro o None; búsqueda uppercase sin tolerancia a espacios | Copia del único registro, None si no existe, `AmbiguousSectionError` si hay más de uno |
| `get_all() -> List[Section]` | Un registro por nombre, con pérdida silenciosa de anteriores | Todos los registros para diagnóstico; puede contener ambiguos y datos físicamente inválidos. No es una lista de perfiles certificados/seleccionables |
| `get_duplicates() -> Dict[str,List[Section]]` | No existía | Solo identidades repetidas, con todos los candidatos y procedencia |
| Mutación de objetos | Referencias compartidas podían cambiar datos almacenados | Snapshots profundos al cargar y copias profundas al consultar/listar; mutar objetos externos o detalles del error no cambia el índice ni sus registros |

No se deduplican registros idénticos: repetir una identidad es una ambigüedad de origen, aunque las propiedades coincidan. Cargar dos veces el mismo lote añade registros y bloquea sus identidades. No hay reemplazo implícito ni modo de elegir primero/último. Para recargar una fuente, construir un repositorio nuevo. `load([])` es no-op; un repositorio vacío devuelve None. El orden de carga puede cambiar el orden de registros diagnósticos, pero nunca la decisión de bloqueo ni el conjunto de candidatos. `get_all` agrupa por orden de primera aparición de identidad y después por orden de inserción; no garantiza el orden intercalado global del archivo.

Error de selección:

```json
{
  "type": "AmbiguousSectionError",
  "code": "AMBIGUOUS_SECTION",
  "message": "Section identity is ambiguous; no catalog record was selected.",
  "details": {
    "requested_name": "hea 100",
    "identity": "HEA 100",
    "record_count": 2,
    "records": ["Cada candidato se serializa completo, con propiedades y source"]
  }
}
```

El fragmento muestra la estructura; `records` contiene objetos Section completos en ejecución, no strings. CLI ya captura `SteelDesignError`: expone el mismo código/detalle con stage=`run_engine`, exit 1 y sin resultado resistente. No hay cambio en el JSON de casos ni otro cálculo en el adaptador. Un perfil único inválido físicamente continúa bloqueado por las guardas HFS-011 del motor; unicidad no equivale a validez.

Consumidores auditados: `engine.run` y `run._build_case_section` llaman get y propagan el error existente; no requieren nueva selección. Las suites usan load/get. La sonda F-13 se adapta al rechazo en get y exige la clase/código exactos. `scripts/audit_baseline.engine_snapshot` usa get_all para un contador histórico llamado repository_count: ahora ese contador representa registros retenidos, no identidades. Su archivo histórico no se edita. La evidencia HFS-016 distingue 1228 registros, 1223 identidades y 1221 identidades únicas recuperables. Clientes externos que enumeraban get_all deben consultar get(name) antes de calcular; clientes que esperaban reemplazo o mutación por referencia deben migrar.

`Section.model_dump()` ahora incluye source (None para objetos sin origen); consumidores estrictos de esa serialización deben admitir el campo. No cambian `SteelCase`, capacidades ni estados de resultados. No se habilitan rutas de selección por hoja/fila ni una nueva API web.

## Anomalías y límites

El catálogo real mantiene dos grupos bloqueados: HEA 100 (dos geometrías diferentes) y PTEXXMM (cinco registros con área cero). Las 1221 identidades restantes son recuperables sin que esos grupos aborten la carga. Esto no certifica su geometría: HFS-011 valida la sección elegida y HFS-040 conserva la auditoría completa.

Se mantiene el comportamiento estricto previo ante errores de esquema, parseo, no finitos o dominios negativos que impiden construir Section: pueden abortar la importación. Esta tarea aísla **duplicados y placeholders ya representables**, no introduce un importador tolerante que descarte filas inválidas. El repositorio no repara ni oculta ninguna fila. No se corrigen unidades ambiguas, encabezados duplicados, D/t, aliases físicos o limitaciones de cobertura. HFS-010 sigue pendiente.
