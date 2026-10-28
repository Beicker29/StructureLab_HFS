# HFS-021A — API pública Python y migración 0.2.0

El único paquete soportado es `steel_design`. La distribución conserva el nombre
`structurelab-hfs`; cambia de 0.1.0 a **0.2.0** por la ruptura de imports y comando
modular. No hay cambio de contratos JSON, datos, ecuaciones ni significado de
modelos. No se publica en PyPI ni se implementa HFS-022.

## Instalación e identidad

```text
python -m pip install .         # instalación normal
python -m pip install -e .      # desarrollo desde checkout
structurelab-hfs input.json --sections /ruta/sections.xlsx
python -m steel_design.run input.json --sections /ruta/sections.xlsx
```

El wheel distribuye solo `steel_design` y metadata; el sdist conserva archivos
en `src/steel_design`. No se distribuye un paquete `src`. Desde la raíz sin
instalar no se garantiza encontrar `steel_design`; no se añaden imports de
respaldo basados en cwd. El catálogo permanece externo.

`src.steel_design` y `python -m src.steel_design.run` están retirados. El
inicializador raíz comprueba `__name__` y rechaza otro nombre **antes** de
importar submódulos. Esto cubre el namespace implícito `src` que Python puede
encontrar desde el checkout, en ambos órdenes de importación. Fuera del
checkout el paquete antiguo simplemente no está distribuido. No hay aliases
manuales ni segunda copia de clases. Inicializadores de subpaquetes reales
permiten descubrimiento setuptools sin namespaces implícitos.

Usar un entorno limpio o actualizar la distribución instalada; no se soporta
la coexistencia deliberada de dos versiones en sys.path ni carga manual de
archivos con importlib bajo nombres arbitrarios. No se mantienen pickles que
codificaron rutas de clases 0.1.0. Los archivos JSON vigentes sí se conservan.

## Superficie pública mínima

Importar desde los módulos indicados. El inicializador raíz no reexporta la
API ni carga dependencias: no hace I/O, cálculos, selección o registro global.

| Ruta oficial | Responsabilidad / contrato |
|---|---|
| `steel_design.engine.SteelDesignEngine` | `run(case) -> EngineResult`; `run_with_context(case) -> (SteelCase, Section, EngineResult)`. Único pipeline con validación, routing, cálculo y cobertura |
| `steel_design.models.SteelCase` | Entrada Pydantic compartida; tipos anidados Material/Loads/etc. permanecen en este mismo módulo |
| `steel_design.sections.models.Section` | Propiedades normalizadas compartidas; sin transformación de unidades por el adaptador |
| `steel_design.sections.repository.SectionRepository` | Repositorio en memoria; `load/get/get_all/get_duplicates`, snapshots y rechazo de ambigüedad intactos |
| `steel_design.execution.execute_case` | Ejecutar un SteelCase con engine y contexto opcional; devuelve CaseExecution |
| `steel_design.execution.iter_executions` | Iteración secuencial de payload individual/bundle; errores propagados al avanzar |
| `steel_design.execution.execute_payload` | Materializa la misma ejecución en lista, sin archivos ni consola |
| `steel_design.execution.execution_status` | Agregación canónica de los estados existentes; rechaza lista vacía |
| `steel_design.reporting.build_compact_summary` | Datos compactos derivados del resultado, sin escritura ni recálculo |
| `steel_design.reporting.build_detailed_results_payload` | Payload de memoria sin escritura; timestamp/metadatos proporcionados por consumidor |

Tipos de retorno y errores oficiales complementarios:
`steel_design.execution.CaseExecution`, `steel_design.results_model.EngineResult`,
`AnalysisStatus`, y `steel_design.domain.errors.SteelDesignError` y sus subclases.
Se conservan las firmas de HFS-021, también `OutputOptions` y la exportación
explícita `steel_design.reporting.export_execution`. Importar un módulo no
exporta archivos ni importa matplotlib.

```python
from steel_design.engine import SteelDesignEngine
from steel_design.execution import execute_payload, execution_status
from steel_design.sections.repository import SectionRepository
from steel_design.reporting import build_compact_summary

repository = SectionRepository()
repository.load(sections)  # lista de Section suministrada; vacía para custom
executions = execute_payload(payload, SteelDesignEngine(repository))
status = execution_status(executions)
summaries = [build_compact_summary(item) for item in executions]
```

`CaseExecution` conserva caso/sección/resultado de una única ejecución: tratar
esos objetos como resultado producido, sin mutarlos para representar otra carga.
No es un nuevo DTO ni contrato JSON versionado. El adaptador suministra demandas
y su método; el motor no acredita combinaciones externas.

## Helpers internos y compatibilidad

Los nombres con `_` son internos, no nuevas promesas de API estable. Las
fachadas de HFS-021 se conservan en `steel_design.run`/`steel_design.engine`
para tests y scripts existentes: `_build_custom_section`, `_build_case_section`,
`_run_single_case`, helpers de resumen/memoria y aliases de preparación.
Son los mismos objetos/funciones; no crean otra implementación o identidad.
No se garantiza monkeypatch de globals privados ni importaciones por el prefijo
retirado. Para un consumidor nuevo, usar las funciones públicas de la tabla.

Las reglas internas y módulos de cálculo no pasan a ser una API pública
acreditada por este hito. Conservan guardas LRFD/ASD y dominios previos. La
consolidación/refactorización de esas funciones queda fuera del alcance.

Ambos CLI convencionales conservan argumentos/defaults, JSON, etapas de error,
artefactos y exit: FAIL/INCOMPLETE estructural puede terminar con exit 0 (F-32).
No se transforma el rechazo del comando retirado en error JSON del motor:
falla durante importación, antes de argparse/ejecución.

`coverage.executions[].implementation` conserva por compatibilidad su texto
histórico `src.steel_design...`. Es un identificador publicado de evidencia,
**no una ruta importable**. Las clases, excepciones y modelos reales usan
`steel_design`; no cambiar ese texto al intentar resolver imports dinámicos.
La adaptación solo afecta cómo se forma el ID, sin cambiar obligaciones o
acreditaciones. Una futura evolución del contrato corresponderá a HFS-022/024.

## Evidencia y límites

Los contratos funcionales de [HFS-021](hfs021-execution.md) permanecen como
documento de su versión; esta página actualiza únicamente las rutas públicas.
Pruebas en procesos frescos, distintos órdenes y directorios, wheel normal,
editable, API, CLI y regresiones en el [informe](../audit/hfs021a/report.md).
Ninguna comparación AST o instalación acredita conformidad normativa AISC.
