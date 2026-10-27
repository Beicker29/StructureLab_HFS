# HFS-014 — Inventario de entrega y pendientes

Base: `main`, `d3190d4fab2938bf240024c5128f78943dd1e8d2`. Sin cambios locales
al comenzar; sin staging, commit, push, ramas ni PR. La lista al final enumera
todos los archivos modificados y nuevos detectables por Git, incluidos este
inventario y su manifiesto. Los avisos de acceso heredados se conservan en la
[verificación de alcance](evidence/scope-verification.json), sin cambios de permisos.

## Responsabilidades modificadas

| Archivos | Cambio y motivo |
|---|---|
| `src/steel_design/run.py` | Resumen único por DCR publicado para CLI/memoria; rechazo temprano de lotes vacíos o con forma inválida |
| `src/steel_design/results_model.py` | Guarda de lote vacío en el agregador canónico; misma precedencia para lotes no vacíos |
| `tests/test_hfs000_characterization.py` | Convertir F-05/F-29 confirmados en regresiones ordinarias; conservar F-09 estricto |
| `tests/test_hfs014_summary_bundle.py` | 72 regresiones de ranking, consumidores JSON, estados y errores de lote |
| `scripts/audit_hfs014.py` | Configuración de nueve suites mediante el capturador existente |
| `scripts/audit_hfs014_cli.py` | Captura reproducible de ejemplos, memorias y reproducciones de defectos |
| `scripts/compare_hfs014_cli.py` | Comparación que admite solo las diferencias documentadas del resumen |
| `docs/contracts/hfs014-summary-bundles.md` | Contrato y migración JSON; precisión publicada, empates y errores |
| `docs/audit/hfs014/report.md` y este inventario | Diagnóstico, decisiones, pruebas reales, diferencias, incidencias y riesgos |
| `docs/audit/hfs014/evidence/**` | Evidencia nueva antes/después, fallos investigados, entorno, comandos, Git y hashes |
| `docs/audit/tracking.md` | Cierre funcional de F-05/F-29 sujeto a revisión; otros defectos siguen visibles |
| `docs/ROADMAP.md` | Estado HFS-014; HFS-017 y HFS-039 solo como tareas futuras |
| `docs/architecture/dry-inventory.md` | Fuentes canónicas del resumen y del agregado, sin duplicar cálculo ni cobertura |
| `CONTRIBUTING.md`, `README.md` | Reproducción de pruebas y acceso al contrato vigente |

## Preservación y pendientes

No se eliminan archivos ni se modifican capturas históricas. El JSON de motor
idéntico se reutiliza desde HFS-013: [ruta/hash](evidence/reused.json). Los dos
manifiestos de captura originales conservan esa referencia, aunque no se copia
otra vez `engine-results.json`. El [manifiesto de entrega](evidence/SHA256SUMS.json)
verifica todos los archivos de esta entrega salvo él mismo, más el JSON reutilizado.

La comparación Git/hash verifica 383 archivos históricos de auditoría y protege
el código resistente, router, catálogo, pruebas anteriores y símbolos fuera del
alcance. Las copias temporales, memorias y SVG permanecen bajo `.venv`; no se
proponen nuevas exclusiones ni limpiezas. No se cambia `.gitignore`.

Pendientes: revisión técnica y publicación por el usuario; migración de consumidores
de los campos retirados. F-09/HFS-015, F-32, HFS-017, HFS-039 y los demás riesgos
del informe siguen fuera de esta implementación. HFS-010 no recibe nuevas
acreditaciones; no hay correcciones numéricas resistentes en esta tarea.

## Relación completa según Git

La siguiente lista se genera desde los cambios contra HEAD y los archivos nuevos
no ignorados. `M` indica modificado; `A` indica nuevo, todavía sin añadir al índice.

<!-- git-file-list -->

```text
M CONTRIBUTING.md
M README.md
M docs/ROADMAP.md
M docs/architecture/dry-inventory.md
A docs/audit/hfs014/changed-files.md
A docs/audit/hfs014/evidence/SHA256SUMS.json
A docs/audit/hfs014/evidence/after/SHA256SUMS.json
A docs/audit/hfs014/evidence/after/catalog.json
A docs/audit/hfs014/evidence/after/comparison.json
A docs/audit/hfs014/evidence/after/copied_inputs.json
A docs/audit/hfs014/evidence/after/environment.json
A docs/audit/hfs014/evidence/after/pytest-characterization.json
A docs/audit/hfs014/evidence/after/pytest-characterization.xml
A docs/audit/hfs014/evidence/after/pytest-contracts.json
A docs/audit/hfs014/evidence/after/pytest-contracts.xml
A docs/audit/hfs014/evidence/after/pytest-original.json
A docs/audit/hfs014/evidence/after/pytest-original.xml
A docs/audit/hfs014/evidence/after/pytest-test_hfs010_coverage.json
A docs/audit/hfs014/evidence/after/pytest-test_hfs010_coverage.xml
A docs/audit/hfs014/evidence/after/pytest-test_hfs012_flexure_selection.json
A docs/audit/hfs014/evidence/after/pytest-test_hfs012_flexure_selection.xml
A docs/audit/hfs014/evidence/after/pytest-test_hfs013_design_method.json
A docs/audit/hfs014/evidence/after/pytest-test_hfs013_design_method.xml
A docs/audit/hfs014/evidence/after/pytest-test_hfs013_directional_h3.json
A docs/audit/hfs014/evidence/after/pytest-test_hfs013_directional_h3.xml
A docs/audit/hfs014/evidence/after/pytest-test_hfs014_summary_bundle.json
A docs/audit/hfs014/evidence/after/pytest-test_hfs014_summary_bundle.xml
A docs/audit/hfs014/evidence/after/pytest-test_hfs016_catalog_integrity.json
A docs/audit/hfs014/evidence/after/pytest-test_hfs016_catalog_integrity.xml
A docs/audit/hfs014/evidence/after/verification.json
A docs/audit/hfs014/evidence/before/SHA256SUMS.json
A docs/audit/hfs014/evidence/before/catalog.json
A docs/audit/hfs014/evidence/before/comparison.json
A docs/audit/hfs014/evidence/before/copied_inputs.json
A docs/audit/hfs014/evidence/before/environment.json
A docs/audit/hfs014/evidence/before/pytest-characterization.json
A docs/audit/hfs014/evidence/before/pytest-characterization.xml
A docs/audit/hfs014/evidence/before/pytest-contracts.json
A docs/audit/hfs014/evidence/before/pytest-contracts.xml
A docs/audit/hfs014/evidence/before/pytest-original.json
A docs/audit/hfs014/evidence/before/pytest-original.xml
A docs/audit/hfs014/evidence/before/pytest-test_hfs010_coverage.json
A docs/audit/hfs014/evidence/before/pytest-test_hfs010_coverage.xml
A docs/audit/hfs014/evidence/before/pytest-test_hfs012_flexure_selection.json
A docs/audit/hfs014/evidence/before/pytest-test_hfs012_flexure_selection.xml
A docs/audit/hfs014/evidence/before/pytest-test_hfs013_design_method.json
A docs/audit/hfs014/evidence/before/pytest-test_hfs013_design_method.xml
A docs/audit/hfs014/evidence/before/pytest-test_hfs013_directional_h3.json
A docs/audit/hfs014/evidence/before/pytest-test_hfs013_directional_h3.xml
A docs/audit/hfs014/evidence/before/pytest-test_hfs016_catalog_integrity.json
A docs/audit/hfs014/evidence/before/pytest-test_hfs016_catalog_integrity.xml
A docs/audit/hfs014/evidence/before/verification.json
A docs/audit/hfs014/evidence/cli/after-cli-examples.json
A docs/audit/hfs014/evidence/cli/after-defect-probes.json
A docs/audit/hfs014/evidence/cli/before-cli-examples.json
A docs/audit/hfs014/evidence/cli/before-defect-probes.json
A docs/audit/hfs014/evidence/cli/comparison.json
A docs/audit/hfs014/evidence/incidents/long-path-comparison.json
A docs/audit/hfs014/evidence/incidents/long-path-errors.json
A docs/audit/hfs014/evidence/incidents/red.json
A docs/audit/hfs014/evidence/incidents/targeted.json
A docs/audit/hfs014/evidence/incidents/xpass.json
A docs/audit/hfs014/evidence/reused.json
A docs/audit/hfs014/evidence/scope-verification.json
A docs/audit/hfs014/report.md
M docs/audit/tracking.md
A docs/contracts/hfs014-summary-bundles.md
A scripts/audit_hfs014.py
A scripts/audit_hfs014_cli.py
A scripts/compare_hfs014_cli.py
M src/steel_design/results_model.py
M src/steel_design/run.py
M tests/test_hfs000_characterization.py
A tests/test_hfs014_summary_bundle.py
```
