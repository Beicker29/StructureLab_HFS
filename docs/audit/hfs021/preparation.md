# Preparación HFS-021

Fecha: 2026-10-28. Antes de editar: rama `main`, HEAD
`f3a5198309d24f772f6cac69ccc483846b81d21a`, sin cambios locales.
Git mantiene 31 advertencias de acceso a temporales históricos; no se modifican
permisos ni se eliminan archivos. Se leyeron AGENTS, ROADMAP, CONTRIBUTING,
ADR-001/002/003 y el inventario DRY.

HFS-020 fue aprobado por el usuario. Consulta directa de GitHub al
[run 40673575334](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40673575334):
Ubuntu `122766181196` y Windows `122766181653`, ambos completed/success,
incluido el paso de build/instalación/pruebas. Esto acredita el workflow,
no certifica conformidad normativa AISC. Las notas históricas de HFS-020
permanecen intactas; el seguimiento vivo registra este cierre posterior.

## Mapa previo y contratos observables

| Propietario previo | Consumidores | Responsabilidad / efectos / contrato |
|---|---|---|
| `engine.SteelDesignEngine.run(case)` | CLI, tests por capítulos/hitos, `audit_baseline.engine_snapshot` | Validación de caso, selección/validación de Section, cobertura independiente, router, reglas, EngineResult. No imprime ni escribe archivos; repositorio en memoria |
| `engine._build_custom_section` | Motor y tests HFS-010 | Geometría maciza circular/rectangular; mm, mm², mm³, mm⁴; eje x asociado a H. Error si falta custom; overflow traducido por motor |
| `run._build_case_section` | CLI y HFS-015 | Copia aritmética de geometría; segunda lectura de catálogo. Devuelve None si nombre ausente en uso directo |
| `run.main` | `python -m src.steel_design.run`, entry point `structurelab-hfs` | argparse, Excel externo, JSON con rechazo de claves duplicadas, preparación/ejecución secuencial, salida y errores. Etapas load_sections/parse_input/run_engine; exit 1 técnico, exit 0 incluso FAIL/INCOMPLETE |
| `run.OutputOptions`, `_extract_output_options`, `_merge_case_payload` | CLI, HFS-011, `audit_baseline` | Alias estrictos de output, merge profundo de bundle, errores Pydantic con loc output. Los overrides no mutan el base |
| `run._run_single_case` | CLI; instrumentación HFS-014 | Ejecuta, reconstruye sección, prepara resumen, genera gráficos y memoria. write_results_json controla JSON; no desactiva gráficos I5 |
| `run._build_global_summary`, `_build_dcr_trace`, `_build_chapter_admissibility` | HFS-000/014/015, pruebas originales, scripts de captura/sondas | Presentan DCR originales y avisos; no cambian estados ni cobertura |
| Exportadores I5/JSON y `_build_execution_results_dir` de run | CLI | mkdir, reloj UTC, nombres saneados, JSON estricto. Matplotlib opcional; fallback SVG si no importa |
| `models`, `results_model` | Motor, reglas, CLI, tests | Pydantic compartido, precisión HFS-015, agregación HFS-010/014. Se conservan sin cambio |
| `sections.loader/repository/models` | CLI, motor, tests | Excel se lee solo por adaptador; repositorio guarda/devuelve snapshots y rechaza identidad ambigua; catálogo permanece externo |

## Decisión de extracción antes de implementar

- `sections.geometry`: única construcción pura, con las expresiones existentes.
  Mantener fachadas antiguas de importación, sin copias aritméticas.
- El motor devolverá opcionalmente contexto de ejecución mediante un método
  adicional; `run(case) -> EngineResult` conservará firma y comportamiento.
  La sección validada viajará al reporte, sin cache global ni nueva selección.
- `execution`: preparación individual/lotes, ejecución secuencial y agregación
  existente. Funciones sin rutas, reloj, argparse, consola o escritura.
- `reporting`: datos compactos/detallados y exportación; separar construcción
  del payload de memoria de su escritura para consumo en memoria.
- `run`: adaptador de transporte con fachadas de helpers existentes. Conservar
  validación temprana de estructura de bundle y orden secuencial de efectos:
  un error tardío no borra artefactos de casos anteriores.
- No cambiar modelos versionados, ecuaciones, factores, obligaciones, routing,
  guardas de método, catálogo ni tolerancias. No introducir dependencia web.

Línea base completa iniciada antes de incorporar pruebas HFS-021 mediante
`scripts/verify_hfs020.py --out .venv/21before` en entorno fijado `.venv/21dev`.
Sus logs y resultados se incorporarán al informe de cierre.
