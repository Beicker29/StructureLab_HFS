# HFS-030 — Verificación ejecutada y límites

SHA base: `76a908673259211b2d5b2407b046608ca96384ec`, Windows, Python 3.12.10.
Entorno de pruebas: `.venv/21dev/Scripts/python.exe`, instalación editable.
Dependencias exactas en [freeze](evidence/verified/freeze.log); pytest 9.1.1,
Pydantic 2.14.1 / pydantic-core 2.50.1, Ruff 0.17.3, jsonschema 4.26.0.
La extracción de PDF usa el entorno `.venv/Scripts/python.exe`; su versión de
`pypdf`, Python, páginas, metadata y hashes están en
[local-sources.json](evidence/local-sources.json).

## Suites, sin modificar expectativas

Se ejecutaron las 20 suites del verificador vigente, separando original y
caracterización. Se muestran los resultados finales por suite, sin sumar
intentos repetidos. Todos tienen exit 0, cero fallos, cero errores, cero omitidas
y cero xfail. Las 12 subpruebas se contabilizan aparte de los 68 métodos originales.

| Suite | Aprobadas | Evidencia final |
|---|---:|---|
| Original | 68 +12 subpruebas | `evidence/original.log` |
| Caracterización HFS-000 | 12 | `evidence/verified/test_hfs000_characterization.log` |
| HFS-011 | 665 | `evidence/verified/test_hfs011_input_contracts.log` |
| HFS-016 | 44 | `evidence/verified/test_hfs016_catalog_integrity.log` |
| HFS-010 | 57 | `evidence/verified/test_hfs010_coverage.log` |
| HFS-012 | 61 | `evidence/test_hfs012_flexure_selection.log` |
| HFS-013 direccional | 57 | `evidence/test_hfs013_directional_h3.log` |
| HFS-013 método | 73 | `evidence/test_hfs013_design_method.log` |
| HFS-014 | 72 | `evidence/verified/test_hfs014_summary_bundle.log` |
| HFS-015 | 84 | `evidence/verified/test_hfs015_precision_advice.log` |
| HFS-017 | 468 | `evidence/verified/test_hfs017_design_method.log` |
| HFS-020 | 50 | `evidence/test_hfs020_comparison.log` |
| HFS-021 | 51 | `evidence/verified/test_hfs021_execution.log` |
| HFS-021A API | 28 | `evidence/verified/test_hfs021a_public_api.log` |
| HFS-021A SVG | 29 | `evidence/verified/test_hfs021a_svg_comparison.log` |
| HFS-022 | 233 | `evidence/verified/test_hfs022_contracts.log` |
| HFS-022R | 258 | `evidence/verified/test_hfs022r_review.log` |
| HFS-022Q | 42 | `evidence/verified/test_hfs022q_independent.log` |
| HFS-023 | 209 | `evidence/test_hfs023_registry.log` |
| HFS-024 | 114 | `evidence/test_hfs024_tracing.log` |
| **Total** | **2675 +12 subpruebas** | No acreditación normativa |

Los comandos exactos, horas UTC y exit se conservan en
[primer intento](evidence/checks.json) y [corridas finales](evidence/verified/checks.json).
Patrón de reproducción para una suite, usando directorio nuevo y padre existente:

```powershell
New-Item -ItemType Directory .venv/hfs030-review-new
.venv/21dev/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_hfs000_characterization.py --basetemp=.venv/hfs030-review-new/characterization
.venv/21dev/Scripts/python.exe scripts/audit_hfs023.py --check
.venv/21dev/Scripts/python.exe scripts/generate_hfs022_schemas.py --check
.venv/21dev/Scripts/python.exe -m ruff check src tests scripts docs/audit/hfs030/reproduce.py --exclude tests/.tmp_tests
```

La suite original usa `pytest tests` con `--ignore` explícito para cada suite
posterior de `SUITES` en `scripts/verify_hfs020.py`; el comando completo está en
`checks.json`. No se añadió un test que refleje la redacción documental.

## Errores y recuperación, sin ocultarlos

1. Primer intento: 2617 aprobadas +12 subpruebas y 58 errores de setup por
   `PermissionError` al acceder a `%TEMP%/pytest-of-byomayusa`; cero fallos de
   aserción. Las suites que terminaron correctamente se conservaron sin repetir.
2. `evidence/retry/`: se intentó `--basetemp` dentro del repositorio, pero faltaba
   crear el directorio padre; `FileNotFoundError`, error del procedimiento de
   ejecución, no del motor. Se conserva el intento íntegro.
3. `evidence/retry2/`: padre creado y destinos nuevos; el sandbox impidió acceder
   a temporales creados por pytest (`WinError 5`, también durante limpieza).
   No se modificaron ACL ni se eliminaron directorios para ocultarlo.
4. `evidence/verified/`: únicamente las 13 suites afectadas se repitieron fuera
   del sandbox, con base temporal nueva. Todas aprobadas. No se añadieron xfail,
   exclusiones de pruebas ni cambios de oráculos.

Git/Ruff restringidos también advirtieron acceso denegado a 10 directorios
`.tmp_test`, 20 `tests/.tmp_tests` y un `pytest-cache-files-*`, previos a esta
tarea. Son temporales históricos de contenido no inspeccionado; se conservan.
Ruff general salió 0 con advertencias; el chequeo final de fuentes/tests/scripts
y utilidad documental pasa sin advertencias, excluyendo explícitamente los
temporales históricos. `pip freeze` inicial advirtió Git ausente en PATH; se
repitió con el ejecutable Git de GitHub Desktop en PATH, sin instalar nada.

## Comprobaciones documentales y de integridad

- `audit_hfs023.py --check`: 93 entradas, integridad y correspondencia del índice
  derivado correctas. No se regeneró el índice ni se alteraron sus citas.
- `generate_hfs022_schemas.py --check`: sin diferencias en los 11 archivos
  generados (diez esquemas y manifiesto). No modifica JSON 1.0.
- Ruff y `git diff --check`: resultados finales en
  [document-checks.json](evidence/document-checks.json).
- Enlaces locales de los nuevos documentos, hashes de los cuatro PDF, 93 enlaces
  de registro y correspondencia del snapshot con su regeneración: comprobados
  sin ejecutar cálculos nuevos.
- El mapa de páginas se construyó leyendo las fuentes; los hashes de extracción
  son auxiliares. No se deducen obligaciones desde IDs, regex ni resultados.
- Git confirma ausencia de cambios de runtime, contratos, pruebas/oráculos,
  catálogos, PDF originales y evidencia histórica. Las diferencias propuestas
  son documentos de seguimiento y nuevas evidencias/utilidad de auditoría.

## Lo que no se ejecutó

No se reconstruyeron wheel/sdist ni se repitieron las tres modalidades de
instalación: no cambió empaquetado ni runtime. No se ejecutó de nuevo el capturador
completo de 12 ejemplos/24 escenarios CLI-memoria/seis SVG. Se conservaron sus
evidencias HFS-024; el mapa de observaciones se leyó del `traces-wheel.json`
histórico por hash. Las suites sí ejercitan sus escenarios internos, pero eso
no se presenta como repetición de aquel capturador. La CI HFS-024 previamente
verificada y la regresión local se distinguen de una CI del árbol no publicado.

No se produjeron diferencias numéricas intencionales, nuevos oráculos ni
acreditaciones. El cotejo documental no sustituye una auditoría de ecuaciones.
