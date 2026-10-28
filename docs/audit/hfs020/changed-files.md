# HFS-020 ? Archivos modificados

Base `main` / `8af8e435812bfeff23d921c2aa4c860ca98ef4dd`, inicialmente limpia.
Sin rama/PR/commit/push. Ning?n archivo productivo o prueba hist?rica cambiado.

| Archivo | Cambio |
|---|---|
| [pyproject.toml](../../../pyproject.toml) | Metadata, backend, namespace, entry point, dependencias y Ruff. |
| [MANIFEST.in](../../../MANIFEST.in) | Allowlist estricta de sdist sin datos/evidencia. |
| [requirements.txt](../../../requirements.txt) | Delegaci?n compatible al pyproject desde ra?z. |
| [requirements/ci-constraints.txt](../../../requirements/ci-constraints.txt) | Resoluci?n auditada de dependencias Windows/Python 3.12. |
| [.github/workflows/ci.yml](../../../.github/workflows/ci.yml) | Build/install/tests externos y artifacts Windows/Ubuntu. |
| [scripts/verify_hfs020.py](../../../scripts/verify_hfs020.py) | Pruebas reproducibles de distribuci?n e instalaci?n, once suites y comparaci?n. |
| [README.md](../../../README.md) | Instalaci?n, cat?logo externo y CLI instalado. |
| [CONTRIBUTING.md](../../../CONTRIBUTING.md) | Reproducci?n, deuda Ruff, CI y separaci?n de suites. |
| [docs/ROADMAP.md](../../ROADMAP.md) | Estado HFS-020 para revisi?n con pendientes remotos. |
| [docs/architecture/dry-inventory.md](../../architecture/dry-inventory.md) | Propietarios de dependencias, CLI y verificador com?n. |
| [docs/audit/hfs020/report.md](report.md) | Diagn?stico, decisiones, pruebas, incidentes, l?mites. |
| [docs/audit/hfs020/changed-files.md](changed-files.md) | Este inventario. |

## Evidencia a?adida

El [manifiesto SHA-256](evidence/SHA256SUMS.json) enumera cada archivo a?adido de
evidencia: baseline once suites/12 ejemplos, 24 escenarios CLI antes y despu?s,
corrida externa instalada completa, distribuciones wheel/sdist verificadas,
bootstrap de desarrollo, Ruff, actionlint, comparaci?n y los incidentes.
Los artefactos iniciales y finales est?n separados, con mapa de origen y hashes.

No se excluye ni elimina evidencia hist?rica. Las carpetas locales `.venv/20*`
y los temporales externos registrados conservan las capturas completas. Las
copias necesarias para revisi?n est?n bajo `evidence/`; no se incluyen en wheel
o sdist. `.gitignore`, PDFs, Excel, tests existentes y los 33 m?dulos de runtime
se conservan intactos. Windows verificado; Actions remoto/Ubuntu pendientes.
