# HFS-021 — Ejecución común y presentación

Fecha: 2026-10-28. Base `f3a5198`. Contrato Python de aplicación, sin nuevo
esquema JSON versionado. No implementa HFS-022, HFS-024 ni API/web.

## Dependencias y uso sin archivos

```text
CLI / adaptador futuro -> execution -> SteelDesignEngine -> dominio/cálculos
                                           |
                                  sections.geometry
                         CaseExecution (caso, Section, EngineResult)
                                           |
                         reporting: datos / exportación explícita
```

```python
from src.steel_design.engine import SteelDesignEngine
from src.steel_design.execution import execute_payload, execution_status
from src.steel_design.sections.repository import SectionRepository
from src.steel_design.reporting import build_compact_summary

engine = SteelDesignEngine(SectionRepository())
# Para un catálogo, repo.load(lista_de_Section) antes de crear el motor.
# El repositorio vacío basta para casos con custom_section válidos.
executions = execute_payload(payload, engine)  # dict individual o bundle existente
status = execution_status(executions)
summaries = [build_compact_summary(item) for item in executions]
```

La biblioteca no lee JSON/Excel, no imprime, no llama sys.exit, no genera rutas
ni marcas temporales y no escribe artefactos. `output.write_results_json=True`
es una preferencia de exportación conservada, no una orden de I/O al servicio.
El adaptador decide si llama `reporting.export_execution`.

## Entradas, resultados y errores

| Entrada Python | Salida / responsabilidad |
|---|---|
| `execute_case(engine=..., case=SteelCase, input_payload=None, output_options=None, case_tag=None)` | Un `CaseExecution`; ejecuta validación ingenieril exclusivamente en el motor. Los argumentos opcionales aportan contexto de presentación; el resultado nunca depende de ellos |
| `iter_executions(payload, engine)` | Iterador secuencial, un contexto por caso; prepara cada entrada con los modelos existentes. Un error se propaga al avanzar, sin ejecutar los casos restantes |
| `execute_payload(payload, engine)` | Materializa el mismo iterador en una lista, también para un caso individual. No devuelve un lote parcial si se lanza una excepción |
| `execution_status(executions)` | Delega en `results_model.aggregate_case_statuses`, nunca calcula un estado propio |
| `SteelDesignEngine.run(case)` | Mismo `EngineResult` público, sin cambio de firma |
| `SteelDesignEngine.run_with_context(case)` | `(caso_validado, sección_validada, EngineResult)`, una única ejecución del pipeline |

`CaseExecution` es una tupla nombrada interna que transporta los modelos
Pydantic existentes; no es un segundo modelo de ingeniería ni un contrato de
serialización versionado. Incluye `input_payload`, `output_options`, `case_tag`.
El caso y la sección son los objetos validados usados por el motor; no se
reconstruyen para presentar. Los consumidores no deben mutarlos para producir
otro caso: ejecutar de nuevo con una entrada distinta. No hay cache compartida.

`execute_payload` valida `OutputOptions` y `SteelCase`; `execute_case` acepta
un SteelCase y contexto explícito de un llamador Python. Ambos pasan por las
guardas canónicas del motor. El contexto de exportación no sustituye ninguna
entrada del cálculo. Demanda, ejes, método y responsabilidad por combinaciones
externas conservan [HFS-017](hfs017-design-method.md).

Lotes: mismo merge profundo, herencia de `output`, alias de escritura y nombres
por defecto `case_1`, etc. La forma del bundle se valida antes del primer caso.
`cases=[]` lanza `EMPTY_CASE_BUNDLE`; listas mal formadas,
`INVALID_CASE_BUNDLE`. Pydantic conserva sus detalles y errores de campo; los
errores de dominio conservan tipo/código/details. No se convierten excepciones
técnicas en FAIL resistente. Orden de estados: INCOMPLETE precede a FAIL y PASS.

El CLI conserva `load_sections`, `parse_input`, `run_engine`, stdout/stderr,
argumentos/defaults y exit 0 para ejecuciones terminadas, incluso FAIL o
INCOMPLETE (F-32). `--sections` sigue siendo un archivo externo. Un error de
caso posterior conserva los artefactos anteriores; la biblioteca no los genera
ni los elimina. No se cambia la política histórica de errores del repositorio.

## Geometría y presentación

`sections.geometry.build_custom_section(case)` es el único constructor
aritmético para macizos. Conserva expresiones, orden de operaciones, unidades
mm/mm²/mm³/mm⁴, ejes x/y, campos y errores. El modelo mantiene validación local;
el motor sigue traduciendo overflow/división por cero y validando Section.
No se amplían geometrías ni se unifican aproximaciones normativas HSS.

`build_compact_summary(execution, ...)` y `build_detailed_results_payload(...)`
son funciones sin escritura. El segundo recibe timestamp y metadatos del
llamador; nunca consulta el reloj. Consumen checks/cobertura/DCR existentes y
las recomendaciones compartidas; no recalculan capacidades ni acreditaciones.
Los datos compactos en memoria tienen rutas None salvo que se proporcionen.

`export_execution` posee reloj UTC, nombres, rutas, JSON y gráficos. Mantiene
los nombres y claves anteriores; JSON estricto, memoria optativa, SVG de
respaldo cuando matplotlib no importa. `write_results_json=False` **no**
desactiva diagramas I5, como antes. Matplotlib sigue sin ser obligatorio.

## Compatibilidad y límites

- `run.OutputOptions`, `_extract_output_options`, `_merge_case_payload`,
  helpers de resumen/trazas/exportación y `_build_execution_results_dir`
  siguen importables: alias a sus propietarios nuevos.
- `engine._build_custom_section` es alias al constructor canónico.
  `run._build_case_section(case, repo)` conserva su lookup directo y None
  si no encuentra sección; el CLI normal ya no lo utiliza para reconstruir.
- `run._run_single_case` conserva firma y delega en ejecución/exportación.
  `repo` se conserva por compatibilidad; el repositorio del motor es el dueño
  de la sección calculada. Pasar repositorios distintos ya no puede cambiar
  solo la geometría del reporte.
- Cambian módulos propietarios e introspección `__module__` de los símbolos
  movidos; no se promete compatibilidad de pickles ni de monkeypatch de globals
  internos del módulo anterior. Los consumidores registrados y las firmas
  auxiliares utilizadas por ellos se prueban sin modificar sus expectativas.
- Se conserva la deuda de helpers legacy de inferencia, actualmente sin uso
  para reconstruir el DCR. La traza canónica futura corresponde a HFS-024.
- PASS solo expresa cumplimiento del alcance verificable declarado. Ninguna
  extracción concede cobertura, resuelve F-31 o habilita ASD F/I.

Pruebas, evidencias y mapa de consumidores: [informe](../audit/hfs021/report.md)
y [preparación](../audit/hfs021/preparation.md).
