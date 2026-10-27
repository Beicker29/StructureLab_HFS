# HFS-015 — Archivos modificados y pendientes

Base `main`, `dbd87cbd6874073750925125fb2db262f2af6f04`. Sin cambios locales
detectados al comenzar. Sin staging, commit, push, ramas ni PR. No se eliminan
archivos, capturas ni directorios inaccesibles. No se cambia `.gitignore` ni ACL.

## Responsabilidades

| Archivos | Motivo |
|---|---|
| `src/steel_design/models.py` | Constructor canónico de resultado original, unidad, display y serialización segura; entrada opcional de datos para recomendaciones |
| `src/steel_design/domain/rules/{axial_rules,combined_hss_rules,composite_rules,flexure_rule,shear_rules,tension_rule}.py` | Consumir constructor común y declarar unidades; retirar redondeos de resultado. Sin cambio de fórmulas/nominales/factores |
| `src/steel_design/domain/recommendations.py` | Avisos D1/E2 por fuente, datos desconocidos y condición distinta E5; no crea checks ni acredita cobertura |
| `src/steel_design/run.py` | Traza desde originales, resumen versionado, recomendaciones compartidas y JSON estricto |
| `tests/test_hfs015_precision_advice.py` | 84 pruebas independientes/de contrato y propagación |
| `tests/test_hfs000_characterization.py` | Retirar únicamente marca F-09 tras XPASS investigado; conservar assert |
| `tests/test_engine_cli_integration.py` | Migrar dos expectativas de admisibilidad defectuosas con evidencia D1/E2, conservando su histórico en base |
| `scripts/probe_hfs015.py` | Reproducción contra una copia explícita antes/después |
| `scripts/compare_hfs015.py` | Comparar motor y 24 consumidores admitiendo solo precisión, avisos y contrato documentados |
| `scripts/verify_hfs015_scope.py` | Verificar Git, archivos protegidos, AST de reglas y hashes de captura |
| `docs/contracts/hfs015-precision-advice.md` | Contrato, límites numéricos, nuevos datos opcionales y migración |
| `docs/audit/hfs015/report.md`, este inventario y `evidence/**` | Hallazgos, referencias, pruebas, diferencias y evidencia reproducible |
| `docs/architecture/dry-inventory.md` | Propietarios canónicos de resultados, proyección y recomendaciones |
| `docs/audit/tracking.md`, `docs/ROADMAP.md` | Estado F-09/F-07 y precisión del resumen F-05; hitos futuros siguen pendientes |
| `README.md`, `CONTRIBUTING.md` | Contrato actual y reproducción de diez suites |

## Evidencia y preservación

Las capturas anteriores HFS-000 a HFS-014 permanecen intactas. La captura nueva
base reutiliza el JSON de motor idéntico de HFS-013 mediante
[ruta/hash recuperable](evidence/reused.json); no se elimina ni sobrescribe ese
archivo. Los manifiestos de las capturas se preservan; resolver esa única ruta
reutilizada antes de verificar el manifiesto base. El JSON de motor posterior
sí se conserva como fixture nueva bajo `evidence/after/engine-results.json`.

Se conservan comandos/logs/JUnit, sondas, XPASS investigado, diferencias por ruta,
entorno, hashes y verificación de alcance. Copias temporales, renders PDF/SVG y
corridas exploratorias quedan bajo `.venv`, ignorado previamente; no se efectúan
exclusiones nuevas ni limpiezas. La evidencia CLI posterior procede de una copia
con idéntico runtime a la captura final; la procedencia incluye hashes.

Pendiente: revisión técnica y publicación por el usuario; migración de clientes
del contrato JSON; confirmar datos externos de recomendaciones cuando proceda.
Continúan pendientes E5 completo, F-28/F-31/F-32/F-37, HFS-017/039, HFS-022/024 y
auditorías posteriores. No se declara aprobada ingeniería ni puerta G1.

## Lista completa según Git

`M`: modificado contra HEAD. `A`: nuevo y todavía no añadido al índice. La lista
incluye este inventario y el manifiesto; este último contiene los hashes de todos
los archivos de entrega salvo él mismo, más la referencia canónica reutilizada.

<!-- git-file-list -->

```text
M CONTRIBUTING.md
M README.md
M docs/ROADMAP.md
M docs/architecture/dry-inventory.md
A docs/audit/hfs015/changed-files.md
A docs/audit/hfs015/evidence/SHA256SUMS.json
A docs/audit/hfs015/evidence/after/SHA256SUMS.json
A docs/audit/hfs015/evidence/after/catalog.json
A docs/audit/hfs015/evidence/after/comparison.json
A docs/audit/hfs015/evidence/after/copied_inputs.json
A docs/audit/hfs015/evidence/after/engine-results.json
A docs/audit/hfs015/evidence/after/environment.json
A docs/audit/hfs015/evidence/after/pytest-characterization.json
A docs/audit/hfs015/evidence/after/pytest-characterization.xml
A docs/audit/hfs015/evidence/after/pytest-contracts.json
A docs/audit/hfs015/evidence/after/pytest-contracts.xml
A docs/audit/hfs015/evidence/after/pytest-original.json
A docs/audit/hfs015/evidence/after/pytest-original.xml
A docs/audit/hfs015/evidence/after/pytest-test_hfs010_coverage.json
A docs/audit/hfs015/evidence/after/pytest-test_hfs010_coverage.xml
A docs/audit/hfs015/evidence/after/pytest-test_hfs012_flexure_selection.json
A docs/audit/hfs015/evidence/after/pytest-test_hfs012_flexure_selection.xml
A docs/audit/hfs015/evidence/after/pytest-test_hfs013_design_method.json
A docs/audit/hfs015/evidence/after/pytest-test_hfs013_design_method.xml
A docs/audit/hfs015/evidence/after/pytest-test_hfs013_directional_h3.json
A docs/audit/hfs015/evidence/after/pytest-test_hfs013_directional_h3.xml
A docs/audit/hfs015/evidence/after/pytest-test_hfs014_summary_bundle.json
A docs/audit/hfs015/evidence/after/pytest-test_hfs014_summary_bundle.xml
A docs/audit/hfs015/evidence/after/pytest-test_hfs015_precision_advice.json
A docs/audit/hfs015/evidence/after/pytest-test_hfs015_precision_advice.xml
A docs/audit/hfs015/evidence/after/pytest-test_hfs016_catalog_integrity.json
A docs/audit/hfs015/evidence/after/pytest-test_hfs016_catalog_integrity.xml
A docs/audit/hfs015/evidence/after/verification.json
A docs/audit/hfs015/evidence/before/SHA256SUMS.json
A docs/audit/hfs015/evidence/before/catalog.json
A docs/audit/hfs015/evidence/before/comparison.json
A docs/audit/hfs015/evidence/before/copied_inputs.json
A docs/audit/hfs015/evidence/before/environment.json
A docs/audit/hfs015/evidence/before/pytest-characterization.json
A docs/audit/hfs015/evidence/before/pytest-characterization.xml
A docs/audit/hfs015/evidence/before/pytest-contracts.json
A docs/audit/hfs015/evidence/before/pytest-contracts.xml
A docs/audit/hfs015/evidence/before/pytest-original.json
A docs/audit/hfs015/evidence/before/pytest-original.xml
A docs/audit/hfs015/evidence/before/pytest-test_hfs010_coverage.json
A docs/audit/hfs015/evidence/before/pytest-test_hfs010_coverage.xml
A docs/audit/hfs015/evidence/before/pytest-test_hfs012_flexure_selection.json
A docs/audit/hfs015/evidence/before/pytest-test_hfs012_flexure_selection.xml
A docs/audit/hfs015/evidence/before/pytest-test_hfs013_design_method.json
A docs/audit/hfs015/evidence/before/pytest-test_hfs013_design_method.xml
A docs/audit/hfs015/evidence/before/pytest-test_hfs013_directional_h3.json
A docs/audit/hfs015/evidence/before/pytest-test_hfs013_directional_h3.xml
A docs/audit/hfs015/evidence/before/pytest-test_hfs014_summary_bundle.json
A docs/audit/hfs015/evidence/before/pytest-test_hfs014_summary_bundle.xml
A docs/audit/hfs015/evidence/before/pytest-test_hfs016_catalog_integrity.json
A docs/audit/hfs015/evidence/before/pytest-test_hfs016_catalog_integrity.xml
A docs/audit/hfs015/evidence/before/verification.json
A docs/audit/hfs015/evidence/cli/after.json
A docs/audit/hfs015/evidence/cli/before.json
A docs/audit/hfs015/evidence/comparison.json
A docs/audit/hfs015/evidence/incidents/initial-reproduction.json
A docs/audit/hfs015/evidence/incidents/targeted.json
A docs/audit/hfs015/evidence/incidents/xpass.json
A docs/audit/hfs015/evidence/probes/after.json
A docs/audit/hfs015/evidence/probes/before.json
A docs/audit/hfs015/evidence/reused.json
A docs/audit/hfs015/evidence/scope-verification.json
A docs/audit/hfs015/report.md
M docs/audit/tracking.md
A docs/contracts/hfs015-precision-advice.md
A scripts/compare_hfs015.py
A scripts/probe_hfs015.py
A scripts/verify_hfs015_scope.py
A src/steel_design/domain/recommendations.py
M src/steel_design/domain/rules/axial_rules.py
M src/steel_design/domain/rules/combined_hss_rules.py
M src/steel_design/domain/rules/composite_rules.py
M src/steel_design/domain/rules/flexure_rule.py
M src/steel_design/domain/rules/shear_rules.py
M src/steel_design/domain/rules/tension_rule.py
M src/steel_design/models.py
M src/steel_design/run.py
M tests/test_engine_cli_integration.py
M tests/test_hfs000_characterization.py
A tests/test_hfs015_precision_advice.py
```
