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

## Corrección de compatibilidad 2026-10-28

Base `main` / `70adc5edf7c5556d0dd5c1be7de915ad0d63b8bf`, árbol inicial limpio.
Esta lista complementa el inventario histórico anterior. Sin rama/PR/commit/push.

| Archivo | Cambio de esta corrección |
|---|---|
| [scripts/hfs020_comparison.py](../../../scripts/hfs020_comparison.py) (nuevo) | Comparación JSON exacta, hashes originales y cadena de procedencia de entradas. |
| [scripts/verify_hfs020.py](../../../scripts/verify_hfs020.py) | Integra procedencia antes/después, comparador y suite nueva; mantiene build, instalaciones y regresiones. |
| [tests/test_hfs020_comparison.py](../../../tests/test_hfs020_comparison.py) (nuevo) | 50 pruebas de formato, integridad, mutaciones y precisión. |
| [compatibility/input-reference.json](compatibility/input-reference.json) (nuevo) | Bytes Git de los 12 ejemplos vinculados a hashes históricos; no nuevos esperados resistentes. |
| [report.md](report.md) | Suplemento y enlace al diagnóstico; informe original conservado. |
| [compatibility/report.md](compatibility/report.md) (nuevo) | Diagnóstico real, contrato, pruebas, reproducción, incidentes y pendientes remotos. |
| [changed-files.md](changed-files.md) | Este inventario complementario. |
| [CONTRIBUTING.md](../../../CONTRIBUTING.md) | Conteo de suites actualizado y enlace a la política de comparación. |
| [docs/ROADMAP.md](../../ROADMAP.md) | Estado real del run fallido y validación remota de la corrección pendiente. |
| [docs/architecture/dry-inventory.md](../../architecture/dry-inventory.md) | Propietario único de comparación/procedencia y consumidores. |
| [compatibility/evidence/](compatibility/evidence/) (nuevo) | Artifacts remotos originales y sus metadata/logs, diagnóstico previo, replay, regresión local completa, intentos unitarios y controles finales. Cada archivo consta en el manifiesto. |

El [manifiesto de evidencia nueva](compatibility/evidence/SHA256SUMS.json) enumera
archivos y hashes. Los ZIP preservan bytes recuperables. Ningún archivo bajo
`src/`, ejemplo, catálogo, contrato HFS-010/015/017, prueba histórica, capturador
HFS-014, metadato del paquete, `.gitattributes` o workflow cambia. No se modifica
ninguna captura previa ni se corrigen defectos estructurales en este alcance.
