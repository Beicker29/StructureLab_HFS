# F-43 — Inventario de la corrección final HFS-013

Base `main` / `abafdbbf0305ab489728d0eea5b81cdaf2e7e90c`. Sin commit, push,
ramas, PR ni archivos añadidos al índice. No se eliminan archivos.

Runtime: conversor F1 en `flexure_calc.py` y su llamada con método desde
`combined_hss_rules.py`. Las ecuaciones nominales, validación pública ASD,
catálogo, routing y HFS-010 están preservados. Se añade una suite independiente
y se registra como octava suite del capturador existente. Las otras modificaciones
son documentación viva y evidencia de revisión.

`M` = archivo versionado modificado; `A` = nuevo archivo propuesto, sin stage.
El [informe](report.md) explica cada diferencia. La
[verificación Git](evidence/scope-verification.json) registra hashes, 49 archivos
protegidos, 20 funciones/auxiliares flexurales sin cambios y la modificación
exacta de una llamada en H3/H1. El [manifiesto](evidence/SHA256SUMS.json) usa rutas
relativas a la raíz del repositorio y excluye su propio hash.

Evidencia antes/después y fallos reproducidos son nuevos; no se sobrescriben
capturas previas. Los resultados de ejemplos idénticos se reutilizan por ruta y
hash según `evidence/reused.json`. El hash previo del informe principal puede
restaurarse desde Git con los finales CRLF originales, como queda comprobado.
Copias de trabajo y entornos quedan en `.venv`, sin nuevas exclusiones ni limpieza.

Pendiente: revisión técnica del cierre funcional F-43. Se conserva el bloqueo
público de flexión ASD y los pendientes F-31/F-37; no se ejecutan HFS-014/015.
Los cambios quedan para commit y push del usuario.

## Relación completa de archivos

| Estado | Archivo |
|---|---|
| M | `CONTRIBUTING.md` |
| M | `docs/ROADMAP.md` |
| M | `docs/architecture/dry-inventory.md` |
| M | `docs/audit/hfs013/report.md` |
| M | `docs/audit/tracking.md` |
| M | `docs/contracts/hfs013-axes.md` |
| M | `scripts/audit_hfs013.py` |
| M | `src/steel_design/codes/aisc_360_22/flexure_calc.py` |
| M | `src/steel_design/domain/rules/combined_hss_rules.py` |
| A | `docs/audit/hfs013/f1-correction/changed-files.md` |
| A | `docs/audit/hfs013/f1-correction/compare.py` |
| A | `docs/audit/hfs013/f1-correction/evidence/SHA256SUMS.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/SHA256SUMS.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/catalog.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/comparison.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/copied_inputs.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/environment.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-characterization.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-characterization.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-contracts.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-contracts.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-original.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-original.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-test_hfs010_coverage.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-test_hfs010_coverage.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-test_hfs012_flexure_selection.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-test_hfs012_flexure_selection.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-test_hfs013_design_method.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-test_hfs013_design_method.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-test_hfs013_directional_h3.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-test_hfs013_directional_h3.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-test_hfs016_catalog_integrity.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/pytest-test_hfs016_catalog_integrity.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/after/verification.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/SHA256SUMS.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/catalog.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/comparison.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/copied_inputs.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/environment.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-characterization.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-characterization.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-contracts.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-contracts.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-original.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-original.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-test_hfs010_coverage.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-test_hfs010_coverage.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-test_hfs012_flexure_selection.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-test_hfs012_flexure_selection.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-test_hfs013_directional_h3.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-test_hfs013_directional_h3.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-test_hfs016_catalog_integrity.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/pytest-test_hfs016_catalog_integrity.xml` |
| A | `docs/audit/hfs013/f1-correction/evidence/before/verification.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/comparison.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/initial-red.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/probes-after.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/probes-before.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/reproduced-red.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/reused.json` |
| A | `docs/audit/hfs013/f1-correction/evidence/scope-verification.json` |
| A | `docs/audit/hfs013/f1-correction/report.md` |
| A | `tests/test_hfs013_design_method.py` |

Total: 9 modificados + 54 nuevos = 63 archivos.
