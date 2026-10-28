# HFS-021B — Inventario previo de limpieza y decisiones

Base `35dd7b8e09f05b8ac77af1ba0b7b735d59456b6a`, main. Inventario elaborado
antes de modificar código. Alcance: fronteras introducidas por HFS-020/021/021A;
sin eliminación de ecuaciones, geometría, cobertura, modelos o datos.

## Evidencia y criterio

Se inspeccionaron los imports, cuerpos y llamadas de `run`, `engine`,
`execution` y `reporting`; entry point de pyproject, ejecución modular,
MANIFEST/workflow y API explícita HFS-021A. Búsqueda sobre **157 archivos de
texto versionados**, incluyendo pruebas, scripts y documentación; cero errores
de lectura/parseo en ese conjunto. Los documentos `docs/audit/**` se clasifican
como historia, no como llamadas ejecutables. Se revisaron **68 candidatos AST
de acceso dinámico**: importlib, getattr, monkeypatch, vars y reflexión. El
escáner es deliberadamente amplio (incluye `tarfile.getmembers`); esa cifra no
significa 68 consumidores del CLI. No aparecieron imports `*` operativos.

El listado con rutas/líneas/hashes se conserva en
[consumer-scan.json](evidence/consumer-scan.json). La búsqueda se complementa
con inspección de propietarios, contratos y comprobación de identidad en el
wheel. No se deduce muerte de código por ausencia de un resultado de búsqueda.
No se atribuye conocimiento de consumidores externos o temporales inaccesibles.

La API HFS-021A enumera imports oficiales; los nombres privados no son API
pública automática. No obstante, HFS-021/HFS-021A **sí comprometen conservar
fachadas concretas**. La tarea no autoriza revocar esa compatibilidad ni cambiar
tests para quitarla. Tampoco se asume que todo atributo importado de `run`
pertenece a esa superficie comprometida.

Abreviaturas: `run`, `engine`, `execution`, `reporting` están bajo
`src/steel_design/`; `Tnnn` es `tests/test_hfsnnn_*.py`. Las ubicaciones exactas
por símbolo están en la evidencia. «Posponer» significa conservar el código
actual y registrar la condición necesaria para retirarlo.

## Decisión por candidato

| Símbolo y ubicación | Responsabilidad | Propietario canónico | Consumidores y compromiso | Decisión / justificación | Riesgo |
|---|---|---|---|---|---|
| `run.extract_output_options` | Binding intermedio importado para asignar `_extract_output_options` | `execution.extract_output_options` | Única lectura en run: asignación del alias privado. Sin import, atributo, string dinámico, entrada CLI ni ruta pública documentada para este nombre en run | **Eliminar binding**; la fachada toma directamente `_execution.extract_output_options`. Conserva dueño y fachada comprometida; evita dos nombres para el mismo acceso interno | Un consumidor externo de este atributo accidental tendría que usar execution o la fachada privada conservada; no es API prometida |
| `run.merge_case_payload` | Binding intermedio importado para asignar `_merge_case_payload` | `execution.merge_case_payload` | Igual análisis; funciones homónimas sí se usan en execution y sus pruebas, no a través de este nombre de run | **Eliminar binding**; usar `_execution.merge_case_payload` para la fachada. No eliminar función ni cambiar merge | Mismo límite de consumidores externos no documentados |
| `run._extract_output_options` | Fachada de preparación/validación de output | `execution.extract_output_options` | `scripts/audit_baseline.py`; T011, T021, T021A; compromiso HFS-021 | **Conservar**, mismo objeto del módulo canónico | Su retirada rompería capturas y validación de entradas en pruebas |
| `run._merge_case_payload` | Fachada de merge de entradas | `execution.merge_case_payload` | `scripts/audit_baseline.py`, T021; contrato HFS-021 | **Conservar**, mismo objeto del módulo canónico | Rompería la preparación de bundles de herramientas |
| `run.OutputOptions` | Tipo compartido de preferencias de exportación | `execution.OutputOptions` | T011, T021A; contratos HFS-011/021/021A | **Conservar** reexport explícito, sin segundo modelo | Identidad Pydantic y compatibilidad |
| `run._build_case_section` | Lookup compatible, custom o repo.get; puede devolver None | `sections.geometry.build_custom_section` para custom; `SectionRepository.get` para catálogo | T015 y T021 llaman la fachada; contratos HFS-016/021/021A. `main` no la llama | **Conservar**; no hay fórmula duplicada y su comportamiento de lookup/None está probado | Eliminarla o hacerla pasar por el pipeline cambia el comportamiento comprometido |
| `run._run_single_case` | Adaptación de firma anterior a ejecución/exportación común | `execution.execute_case` + `reporting.export_execution` | Sin llamada productiva en main; T014 hace monkeypatch por nombre. Contratos HFS-021/021A conservan explícitamente firma y `repo` | **Posponer** retiro: requiere decisión explícita de compatibilidad y revisar la prueba. No es otro motor | Rompe contrato de fachada; el patch no prueba por sí solo ejecución real de su cuerpo |
| `engine._build_custom_section` | Nombre local del constructor canónico | `sections.geometry.build_custom_section` | `run_with_context` lo llama; T010, T021, T021A lo importan o verifican; T021 parchea por nombre para contar construcciones | **Conservar**: consumidor productivo, identidad y compromiso documentado | Quitar/renombrar el binding rompe pipeline o sondas de única construcción |
| `engine.SteelDesignEngine.run` | Entrada pública que devuelve el EngineResult del pipeline contextual | `SteelDesignEngine.run_with_context` | Motor, scripts, pruebas, API oficial y contratos | **Conservar**: wrapper público útil, no código muerto por delegar | Ruptura directa de API |
| `run._sanitize_filename` | Reexport de saneamiento de rutas/nombres | `reporting._sanitize_filename` | Implementación usada por payload/exportadores/report dirs; sin llamada CLI a la fachada. Exportadores privados conservados por HFS-021 | **Posponer** retiro del reexport por compromiso explícito de helpers; conservar implementación activa | Compatibilidad de imports de exportación |
| `run._build_global_summary` | Reexport del resumen por DCR bruto | `reporting._build_global_summary` | T000/014/015/021/021A; `scripts/probe_hfs015.py`; reporting compacto/detallado | **Conservar** identidad; un propietario y consumidores vigentes | Resumen, empates, FAIL, precisión; no redefinir ranking |
| `run._build_chapter_admissibility` | Reexport de recomendaciones | `reporting._build_chapter_admissibility` → `domain.recommendations` | `scripts/probe_hfs015.py`; reporting y T021 sobre el dueño | **Conservar** consumidores y nombre legacy; no duplica reglas | Avisos no equivalen a resistencia/cobertura |
| `run._build_compact_admissibility` | Reexport del adaptador identidad para recomendaciones | `reporting._build_compact_admissibility` | `build_compact_summary` usa la implementación; fachada cubierta por compromiso HFS-021, sin llamada CLI directa al reexport | **Posponer** retirar fachada; conservar implementación activa | Cambiar nombres/contrato por aparente trivialidad |
| `run._extract_shared_context` | Reexport de factorización de contexto del reporte | `reporting._extract_shared_context` | `build_detailed_results_payload`; compromiso de helpers de memoria | **Posponer** retiro del reexport; no tocar el dueño activo | Mutación/organización del payload y compatibilidad |
| `run._infer_check_units`; `reporting._infer_check_units` | Inferencia legacy por cláusula, actualmente sin llamada del reporte | Unidades actuales: `CheckResult.unit`; traza: `reporting._build_dcr_trace` | T014/T015 parchean el binding de run; deuda y helpers conservados explícitamente en contrato HFS-021 | **Posponer** ambos retiros hasta resolver compatibilidad/prueba. No volver a usar inferencia como autoridad | Patch de alias no intercepta globals de reporting; protección negativa parcial heredada |
| `run._extract_capacity_from_memory`; `reporting._extract_capacity_from_memory` | Extractor legacy sin llamada del reporte actual | Capacidad actual: `CheckResult.capacity` | T015 parchea run; compromiso de helpers y deuda HFS-021 | **Posponer**, no sustituir capacidad bruta por memoria ni borrar la prueba | Igual limitación de monkeypatch; necesita retiro acordado, no eliminación oportunista |
| `run._build_dcr_trace` | Reexport de traza de valores originales | `reporting._build_dcr_trace` | T014/T015; payload detallado usa dueño | **Conservar**: uso vigente y compatibilidad | Precisión, unidades, diagnóstico y contrato JSON |
| `run._extract_i5_method2_points` | Reexport de lectura de puntos ya calculados | `reporting._extract_i5_method2_points` | Exportador gráfico lo llama; contrato de helpers de exportación, sin consumidor directo del alias hallado | **Posponer** retiro del reexport; dueño activo | Diagrama I5; no tocar cálculo compuesto |
| `run._ordered_pm_points` | Reexport del orden de puntos gráficos | `reporting._ordered_pm_points` | SVG/PNG lo llaman; compromiso de exportación | **Posponer** retiro del alias, conservar dueño | Alterar representación y geometría gráfica |
| `run._write_i5_interaction_diagram_svg` | Reexport del generador SVG | `reporting._write_i5_interaction_diagram_svg` | Fallback de PNG; seis diagramas en regresión; compromiso de exportación | **Posponer** retiro del reexport; implementación activa | PNG ausente hace activo este camino; no es código inalcanzable |
| `run._write_i5_interaction_diagram_png` | Reexport de exportación PNG con fallback SVG | `reporting._write_i5_interaction_diagram_png` | `export_execution`; import opcional de matplotlib, compromiso de exportación | **Posponer** retiro del reexport; conservar dueño y rama opcional | No considerar muerta una rama por no instalar matplotlib en CI |
| `run._write_detailed_results_file` | Reexport de escritura de memoria | `reporting._write_detailed_results_file` | `export_execution` cuando output lo solicita; comparador histórico comprueba extracción, contrato de exportación | **Posponer** retiro del reexport; preservar dueño | Archivos, nombres, JSON y compatibilidad |
| `run._build_execution_results_dir` | Directorio/timestamp de ejecución | `reporting._build_execution_results_dir` | `run.main` lo llama; T014 lo parchea; contrato HFS-021 | **Conservar**: consumidor CLI directo | Orden de validación y efectos de archivos |
| Imports `SteelCase`, `Section`, `build_custom_section`, `execute_case` de run | Anotaciones y dependencias de las fachadas preservadas | Modelos, sections.geometry, execution | `_build_case_section`, `_run_single_case` y sus anotaciones | **Conservar**; no son imports sin uso solo porque main no los lea | Borrar dependencias de una fachada mantenida |
| Imports de engine y funciones de execution | Dependencias del pipeline y preparación canónica | Sus módulos actuales | Uso directo, anotaciones, iteración y API; revisión AST/Ruff sin otros imports sobrantes | **Conservar**; no se encontró otra eliminación inequívoca dentro del alcance | No alterar política de validación ni ejecución |
| Helpers triviales de reporting (`_build_chapter_admissibility`, `_build_compact_admissibility`) | Adaptar nombres/resultados legacy | reporting/recommendations | Llamadas productivas y/o compromiso anterior | **Conservar** implementaciones activas; no expandir este hito a reescribir llamadas | No retirar funciones por número de líneas |
| Dependencias runtime/dev y entry points | Instalación, CLI y verificadores | `pyproject.toml`, constraints existentes | Pydantic, openpyxl; pytest/build/Ruff/twine; `steel_design.run:main` y módulo | **Conservar**: utilidad demostrada; no subir versión 0.2.0 | Importador Excel y empaquetado fuera de una limpieza de dependencias |

## Límites de la limpieza y deuda verificada

Solo se retiran **dos bindings intermedios de función**; las asignaciones de
las fachadas acceden al dueño mediante un único import privado `_execution`.
Ese módulo ya era dependencia; no se crea capa, servicio, dependencia ni clase.
No se elimina ningún cuerpo de función. Las fachadas conservadas no contienen
segundas fórmulas: delegan o reexportan una implementación canónica. Mantenerlas
por un contrato concreto satisface DRY; no las convierte en API pública nueva.

La búsqueda no encontró dispatch por string ni reflexión sobre los dos nombres
retirados en run. La reflexión de API usa una lista explícita de símbolos en
engine/models/sections/execution/reporting; `vars(module)` de T021 inspecciona
execution, no el namespace de run. `getattr` de cargas/secciones y registro de
reglas no consume esos nombres. Ningún entry point ni documento de uso los
ofrece como API de run. El cambio no toca las funciones homónimas en execution.

Las pruebas negativas T014/T015 parchean aliases de run; desde la extracción
HFS-021, `_build_global_summary`/`_build_dcr_trace` ejecutan con globals de
reporting. El patch por sí solo no interceptaría una futura llamada allí. Sus
aserciones de resultados siguen siendo útiles y se preservan. Reorientar esos
patches al dueño y acordar la retirada de helpers legacy es deuda explícita,
no motivo para debilitar pruebas o declarar muerto el contrato en esta tarea.

Retiro futuro de fachadas pospuestas: decisión de compatibilidad por símbolo,
mapa de consumidores actualizado y regresión sin pérdida de protección. No se
autoriza por este inventario. F-31 continúa **P0 abierto**, y la limpieza no
acredita reglas AISC ni altera otros defectos normativos pendientes.
