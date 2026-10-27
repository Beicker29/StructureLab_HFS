# HFS-013 — Inventario de cambios y pendientes

Base main `3af52aa9848ccb6ff040fd1f8203a4609599f341`. Cambios locales, sin commit,
push, ramas ni PR. `M` significa modificación de archivo versionado; `A` nuevo
archivo propuesto, aún sin añadir al índice. No hay eliminaciones.

El [informe](report.md) explica decisiones y efectos. Se preservan por Git 20
archivos y 11 símbolos protegidos de cálculo/selección; detalle y hashes en
[final-verification.json](evidence/final-verification.json). El runtime coincide
con la captura final y `git diff --check` pasó. Los dos módulos nuevos son
funciones compartidas de demandas y capacidades G/H3, sin clases adicionales.

Los JSON/XML de `before`, `after` y `final` son capturas distintas: base, punto
intermedio verde y código final. `incidents` conserva fallos investigados.
El resultado previo de ejemplos se reutiliza por ruta/hash desde HFS-010; no se
duplica ni se elimina evidencia antigua. El manifiesto del conjunto excluye
su propio hash por definición. Los detalles de ejecución incluyen rutas locales,
comandos y entorno reproducible; no son un lock nuevo de dependencias.

Pendientes: revisión técnica de ejes y fórmulas H3, validación integral D/E/F/G/H1,
datos Lv/L/C con procedencia, alternativas bloqueadas G3/G6/H3 y F-31 abierto.
HFS-014/015 no iniciadas. Publicación reservada al usuario.

No se proponen eliminaciones/exclusiones nuevas. Copias de trabajo, lecturas PDF
y cachés bajo `.venv` permanecen ignoradas; no se cambian ACL. El temporal nuevo
inaccesible `pytest-cache-files-93oft8sd/` se documenta, no se limpia.

## Relación completa

| Estado | Archivo |
|---|---|
| M | `CONTRIBUTING.md` |
| M | `README.md` |
| M | `docs/ROADMAP.md` |
| M | `docs/aisc_360_22_traceability.md` |
| M | `docs/architecture/dry-inventory.md` |
| M | `docs/audit/tracking.md` |
| M | `docs/unidades.md` |
| M | `src/steel_design/codes/aisc_360_22/combined_hss_calc.py` |
| M | `src/steel_design/codes/aisc_360_22/shear_calc.py` |
| M | `src/steel_design/domain/coverage.py` |
| M | `src/steel_design/domain/routing/profile_router.py` |
| M | `src/steel_design/domain/rules/combined_hss_rules.py` |
| M | `src/steel_design/domain/rules/shear_rules.py` |
| M | `src/steel_design/engine.py` |
| M | `src/steel_design/models.py` |
| M | `tests/test_chapter_g_rules.py` |
| M | `tests/test_chapter_h_rules.py` |
| M | `tests/test_hfs010_coverage.py` |
| A | `docs/audit/hfs013/changed-files.md` |
| A | `docs/audit/hfs013/evidence/SHA256SUMS.json` |
| A | `docs/audit/hfs013/evidence/after/SHA256SUMS.json` |
| A | `docs/audit/hfs013/evidence/after/catalog.json` |
| A | `docs/audit/hfs013/evidence/after/comparison.json` |
| A | `docs/audit/hfs013/evidence/after/copied_inputs.json` |
| A | `docs/audit/hfs013/evidence/after/engine-results.json` |
| A | `docs/audit/hfs013/evidence/after/environment.json` |
| A | `docs/audit/hfs013/evidence/after/hfs013-comparison.json` |
| A | `docs/audit/hfs013/evidence/after/hfs013-verification.json` |
| A | `docs/audit/hfs013/evidence/after/pytest-characterization.json` |
| A | `docs/audit/hfs013/evidence/after/pytest-characterization.xml` |
| A | `docs/audit/hfs013/evidence/after/pytest-contracts.json` |
| A | `docs/audit/hfs013/evidence/after/pytest-contracts.xml` |
| A | `docs/audit/hfs013/evidence/after/pytest-original.json` |
| A | `docs/audit/hfs013/evidence/after/pytest-original.xml` |
| A | `docs/audit/hfs013/evidence/after/pytest-test_hfs010_coverage.json` |
| A | `docs/audit/hfs013/evidence/after/pytest-test_hfs010_coverage.xml` |
| A | `docs/audit/hfs013/evidence/after/pytest-test_hfs012_flexure_selection.json` |
| A | `docs/audit/hfs013/evidence/after/pytest-test_hfs012_flexure_selection.xml` |
| A | `docs/audit/hfs013/evidence/after/pytest-test_hfs013_directional_h3.json` |
| A | `docs/audit/hfs013/evidence/after/pytest-test_hfs013_directional_h3.xml` |
| A | `docs/audit/hfs013/evidence/after/pytest-test_hfs016_catalog_integrity.json` |
| A | `docs/audit/hfs013/evidence/after/pytest-test_hfs016_catalog_integrity.xml` |
| A | `docs/audit/hfs013/evidence/after/verification.json` |
| A | `docs/audit/hfs013/evidence/before/SHA256SUMS.json` |
| A | `docs/audit/hfs013/evidence/before/catalog.json` |
| A | `docs/audit/hfs013/evidence/before/comparison.json` |
| A | `docs/audit/hfs013/evidence/before/copied_inputs.json` |
| A | `docs/audit/hfs013/evidence/before/environment.json` |
| A | `docs/audit/hfs013/evidence/before/pytest-characterization.json` |
| A | `docs/audit/hfs013/evidence/before/pytest-characterization.xml` |
| A | `docs/audit/hfs013/evidence/before/pytest-contracts.json` |
| A | `docs/audit/hfs013/evidence/before/pytest-contracts.xml` |
| A | `docs/audit/hfs013/evidence/before/pytest-original.json` |
| A | `docs/audit/hfs013/evidence/before/pytest-original.xml` |
| A | `docs/audit/hfs013/evidence/before/pytest-test_hfs010_coverage.json` |
| A | `docs/audit/hfs013/evidence/before/pytest-test_hfs010_coverage.xml` |
| A | `docs/audit/hfs013/evidence/before/pytest-test_hfs012_flexure_selection.json` |
| A | `docs/audit/hfs013/evidence/before/pytest-test_hfs012_flexure_selection.xml` |
| A | `docs/audit/hfs013/evidence/before/pytest-test_hfs016_catalog_integrity.json` |
| A | `docs/audit/hfs013/evidence/before/pytest-test_hfs016_catalog_integrity.xml` |
| A | `docs/audit/hfs013/evidence/before/verification.json` |
| A | `docs/audit/hfs013/evidence/final-verification.json` |
| A | `docs/audit/hfs013/evidence/final/SHA256SUMS.json` |
| A | `docs/audit/hfs013/evidence/final/catalog.json` |
| A | `docs/audit/hfs013/evidence/final/comparison.json` |
| A | `docs/audit/hfs013/evidence/final/copied_inputs.json` |
| A | `docs/audit/hfs013/evidence/final/engine-results.json` |
| A | `docs/audit/hfs013/evidence/final/environment.json` |
| A | `docs/audit/hfs013/evidence/final/hfs013-comparison.json` |
| A | `docs/audit/hfs013/evidence/final/hfs013-verification.json` |
| A | `docs/audit/hfs013/evidence/final/pytest-characterization.json` |
| A | `docs/audit/hfs013/evidence/final/pytest-characterization.xml` |
| A | `docs/audit/hfs013/evidence/final/pytest-contracts.json` |
| A | `docs/audit/hfs013/evidence/final/pytest-contracts.xml` |
| A | `docs/audit/hfs013/evidence/final/pytest-original.json` |
| A | `docs/audit/hfs013/evidence/final/pytest-original.xml` |
| A | `docs/audit/hfs013/evidence/final/pytest-test_hfs010_coverage.json` |
| A | `docs/audit/hfs013/evidence/final/pytest-test_hfs010_coverage.xml` |
| A | `docs/audit/hfs013/evidence/final/pytest-test_hfs012_flexure_selection.json` |
| A | `docs/audit/hfs013/evidence/final/pytest-test_hfs012_flexure_selection.xml` |
| A | `docs/audit/hfs013/evidence/final/pytest-test_hfs013_directional_h3.json` |
| A | `docs/audit/hfs013/evidence/final/pytest-test_hfs013_directional_h3.xml` |
| A | `docs/audit/hfs013/evidence/final/pytest-test_hfs016_catalog_integrity.json` |
| A | `docs/audit/hfs013/evidence/final/pytest-test_hfs016_catalog_integrity.xml` |
| A | `docs/audit/hfs013/evidence/final/verification.json` |
| A | `docs/audit/hfs013/evidence/incidents/initial-hfs010.json` |
| A | `docs/audit/hfs013/evidence/incidents/initial-targeted.json` |
| A | `docs/audit/hfs013/evidence/incidents/initial-verification.json` |
| A | `docs/audit/hfs013/evidence/probes-after.json` |
| A | `docs/audit/hfs013/evidence/probes-before.json` |
| A | `docs/audit/hfs013/evidence/reused-evidence.json` |
| A | `docs/audit/hfs013/probes.py` |
| A | `docs/audit/hfs013/report.md` |
| A | `docs/contracts/hfs013-axes.md` |
| A | `scripts/audit_hfs013.py` |
| A | `scripts/compare_hfs013.py` |
| A | `src/steel_design/domain/actions.py` |
| A | `src/steel_design/domain/evaluators/hss_shear.py` |
| A | `tests/test_hfs013_directional_h3.py` |

Total: 18 modificados + 81 nuevos = 99 archivos revisables.
