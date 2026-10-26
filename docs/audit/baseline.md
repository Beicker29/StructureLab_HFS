# HFS-000 — Línea base reproducible

Fecha: 26 de octubre de 2026 (America/Bogota). Plan maestro leído completo: `docs/ROADMAP.md`, secciones 6 y 7. Alcance: únicamente HFS-000. Estado: captura terminada para revisión técnica; no equivale a validación AISC ni a cierre de la puerta G1.

## Identidad y contrato de cambio

- Rama: `main`; HEAD: `80a9d3609d452ab3413ad632629b1fadcab8415c`, coincidente con el roadmap.
- Al inicio no había modificaciones de archivos versionados. `docs/ROADMAP.md` y `docs/StructureLab_HFS_Roadmap_Codex.md` eran archivos del usuario sin seguimiento; se conservaron. En la primera lectura faltaba `ROADMAP.md`; tras la interrupción apareció y se leyó completo.
- Se conservaron los 80 archivos originalmente versionados (46.096.543 bytes), incluyendo 24 módulos Python del motor, PDFs, catálogo, ejemplos y pruebas originales. Hashes en [tracked_inventory.json](evidence-clean/tracked_inventory.json).
- No se cambiaron entradas/salidas públicas, estados, fórmulas, selección de reglas, factores, propiedades de catálogo ni comportamiento del motor. No hubo refactorización, limpieza histórica, cambios de ACL, commit ni avance a otra tarea.
- Cambios acotados: documentación, captura reproducible y pruebas de caracterización. Sus resultados esperados expresan requisitos de seguridad de software; no nuevas interpretaciones normativas.

Alternativa descartada: corregir los defectos durante la captura habría mezclado diagnóstico y cambio de comportamiento, destruyendo el punto de comparación. Decisión: congelar evidencia y dejar las correcciones para revisión y tareas posteriores. Riesgo de esta decisión: los defectos siguen presentes, identificados explícitamente.

## Entorno y comandos

Windows 11, compilación 26200, AMD64; Python **3.12.10**, MSC v.1943. Entorno nuevo: `.venv/hfs000`, `include-system-site-packages=false`. El `.venv` original no se reinstaló: tenía Pydantic 2.12.5; la resolución limpia de los requisitos abiertos instaló **Pydantic 2.14.1**, pydantic-core 2.50.1, openpyxl 3.1.5 y pytest 9.1.1. Todas las dependencias, incluido pip 25.0.1, están fijadas en [environment-freeze.txt](evidence-clean/environment-freeze.txt); plataforma y configuración en [environment.json](evidence-clean/environment.json).

`git` no estaba en PATH. Se utilizó el ejecutable de GitHub Desktop, sin modificar PATH global:

```powershell
$auditGit = 'D:\Users\byomayusa\AppData\Local\GitHubDesktop\app-3.6.7\resources\app\git\cmd\git.exe'
python -m venv .venv/hfs000
.\.venv\hfs000\Scripts\python.exe -m pip install -r requirements.txt pytest
.\.venv\hfs000\Scripts\python.exe scripts/audit_baseline.py --git $auditGit --out docs/audit/evidence-clean --work .venv/hfs000-work-clean
```

Se copió, con igualdad SHA-256 comprobada, `src/**/*.py`, los archivos `tests/test_*.py`, los 12 ejemplos, catálogo y requisitos a una carpeta nueva. La suite se ejecutó sobre esa copia; así sus escrituras en `results/` y `tests/.tmp_tests/` no afectaron históricos. [copied_inputs.json](evidence-clean/copied_inputs.json) fija los bytes probados. No se omitió ningún módulo de la suite original. No se prueba instalación desde wheel: el proyecto aún se ejecuta como `python -m src.steel_design.run`.

En el directorio de la copia, con `PYTHONNOUSERSITE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONUTF8=1` y sin PYTHONPATH heredado, se ejecutaron por separado:

```powershell
# Rutas de ejecutable y junitxml absolutas en los registros JSON.
python -m pytest -q -rA --tb=short --ignore=tests/test_hfs000_characterization.py --junitxml=<evidencia>/pytest-existing.xml -o junit_logging=all
python -m pytest -q -rA --tb=short tests/test_hfs000_characterization.py --junitxml=<evidencia>/pytest-characterization.xml -o junit_logging=all
```

Los comandos reales completos, cwd, stdout, stderr y códigos están en los respectivos `pytest-*.json`, no solo en estos ejemplos abreviados.

## Resultado de pruebas, separado por origen

| Ejecución | Pruebas aprobadas | Subpruebas aprobadas | Fallidas | Omitidas normales | xfail | Errores | Exit |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original, sandbox (`evidence/`) | 68 | 12 | 0 | 0 | 0 | 0 | 0 |
| Caracterización, sandbox (`evidence/`) | 0 | 0 | 0 | 0 | 10 | 1 | 1 |
| Original, repetición autorizada (`evidence-clean/`) | 68 | 12 | 0 | 0 | 0 | 0 | 0 |
| Caracterización, repetición autorizada (`evidence-clean/`) | 0 | 0 | 0 | 0 | 11 | 0 | 0 |

**Conteo real:** son 68 métodos originales en 11 módulos, más 12 subpruebas de ejemplos; pytest 9.1.1 muestra `68 passed, 12 subtests passed`. JUnit suma 80 casos. No son 80 métodos de prueba. Las 11 caracterizaciones no cuentan como aprobaciones: el XML las representa como `skipped type="pytest.xfail"`; todas son defectos conocidos reproducidos. No hubo XPASS. El detalle de cada una está en [findings.md](findings.md).

Duración JUnit de la repetición: 31,582 s para suite original y 3,204 s para caracterización. Una advertencia en cada ejecución limpia: configuración Pydantic basada en `class Config` obsoleta en `sections/models.py:4`. No se cambió en HFS-000.

Incidencias conservadas:

1. Creación inicial de venv interrumpida; luego `ensurepip` falló en sandbox. La repetición autorizada completó el entorno.
2. `pip install -r requirements.txt pytest` no pudo resolver pytest en sandbox y avisó de temporales que no pudo limpiar; la repetición autorizada terminó correctamente. No se borraron esos temporales.
3. La primera caracterización de lote vacío no llegó al cuerpo: `PermissionError/WinError 5` al crear el `tmp_path` en `%TEMP%/pytest-of-byomayusa`. Diez defectos sí se reprodujeron. También hubo advertencias de caché de pytest. La misma prueba, sin cambiar su código, se ejecutó fuera del sandbox y reprodujo el defecto.
4. El primer capturador devolvió 0 aunque el subproceso de caracterización había devuelto 1. El registro conserva ese error; el capturador final agrega los códigos de las suites y no lo oculta. No afectó al motor.

No se ejecutaron lint ni comprobación estática de tipos del motor: no existe configuración de esos controles en el checkout y su implantación pertenece a otra tarea. Se verificó sintaxis de los dos archivos Python nuevos. Las pruebas no constituyen una auditoría normativa independiente.

## Ejemplos existentes

Los 12 JSON se ejecutaron sin editar, dos veces por captura, en subprocesos CLI separados. Comando por ejemplo:

```powershell
python -m src.steel_design.run examples/<nombre>.json --results-dir audit-results/repeat-1
```

| Ejemplo | Exit | Estado observado | Checks | Mayor DCR publicado |
|---|---:|---|---:|---:|
| channel_case | 0 | PASS | 2 | 0,745 |
| circular_hss_case | 0 | PASS | 7 | 0,831 |
| composite_beam_case | 0 | PASS | 5 | 1,000 |
| composite_encased_case | 0 | PASS | 8 | 1,000 |
| composite_filled_circular_hss_case | 0 | FAIL | 5 | 2,490 |
| composite_filled_rectangular_hss_case | 0 | FAIL | 5 | 14,280 |
| double_angle_case | 1 | INCOMPLETE_SECTION_DATA | — | — |
| rectangular_hss_case | 0 | FAIL | 15 | 7,013 |
| single_angle_case | 0 | PASS | 5 | 0,087 |
| solid_circular_case | 0 | PASS | 3 | 0,035 |
| solid_rectangular_case | 0 | PASS | 3 | 0,053 |
| w_shape_case | 0 | PASS | 9 | 0,892 |

`double_angle_case` bloquea por `j`/`cw` faltantes en E4 para `2L12X12X1-3/8`, en `run_engine`. Coincide con el error esperado. El README denomina a los otros 11 ejemplos ejecutables, no necesariamente conformes: **exit 0 significa ejecución sin excepción, no PASS estructural**. Ocho dan PASS y tres FAIL. Los DCR de I1 pueden ser 1 por un check de alcance; no interpretar automáticamente el máximo como agotamiento resistente.

Evidencia:

- [examples.json](evidence-clean/examples.json): resultados normalizados y SHA-256 canónico por ejemplo.
- `evidence-clean/cli/`: 24 registros crudos con comando, salida/error y código, incluyendo rutas y fechas originales.
- [engine-results.json](evidence-clean/engine-results.json): resultados completos, incluidos `details`, obtenidos también directamente del motor para los mismos ejemplos. No se cambió `output.write_results_json=false` de las entradas para producirlos.
- `evidence-clean/artifacts/`: seis SVG emitidos por el CLI (tres casos I5 METHOD_2, dos repeticiones). No estaba instalado matplotlib; se observó el fallback SVG. No se validó visualmente ni normativamente el gráfico.
- [verification.json](evidence-clean/verification.json): dos CLI iguales tras normalización, dos ejecuciones directas del motor exactamente iguales y cero originales cambiados.
- [SHA256SUMS.json](evidence-clean/SHA256SUMS.json): hashes de todos los archivos de esa captura, excluido el propio manifiesto.

Normalización: únicamente campos de timestamp y rutas (`generated_at_utc`, `input_file`, `sections_file`, `results_run_dir`, `detailed_results_json`, `interaction_diagram_i5_method2_image`). Ningún número de ingeniería se redondea ni se elimina. Las salidas crudas permanecen disponibles. Hash canónico de los resultados completos del motor: `040b93b81b47b090f46ebe2e9018e9fd8697b60aac93fd4bcd1c3a2fb2ba5403`; coincide entre sandbox y repetición autorizada.

Estas capturas son fixtures de **comportamiento observado**, no oráculos independientes ni aprobación del resultado. No hay diferencias numéricas entre repeticiones; no se comparó con cálculos manuales u otra implementación. Los históricos son principalmente gráficos, no un conjunto previo completo de resultados comparables.

## Catálogo, documentos y acceso

El inventario de responsabilidades de los 24 módulos y de los 18 artefactos históricos versionados está en [inventory.md](inventory.md). [catalog.json](evidence-clean/catalog.json) registra hojas/familias. Se cargan 1.228 filas y quedan 1.223 nombres: `HEA 100` aparece dos veces con áreas **2.124 y 2.534 mm²** y alturas **96 y 114 mm**; se retiene la última. `PTEXXMM` aparece cinco veces con área cero. Propiedades completas en [catalog-duplicates.json](catalog-duplicates.json). No se corrigieron nombres, geometría ni importador.

| Archivo | SHA-256 |
|---|---|
| data/sections.xlsx | `5aaaf953a32e77e6d9985e9f91db82702d70b3ee0930a2eb6e695e297a5f1359` |
| a360-22w.pdf | `25c4bf59b4c6fd00589e32a6ddac92cc9fd6be30dd5da07fc7c5f7fd475b2361` |
| a341-22w.pdf | `34cdd4a45360b5e3cb39f9fbb55640af79ece0deb9070a112aaccb938c027e0c` |

Se clasificaron 30 directorios históricos inaccesibles en sandbox: 10 en `.tmp_test/` y 20 en `tests/.tmp_tests/`. Sus nombres exactos están en [access-issues.json](access-issues.json) y los errores originales en `evidence/git_before.json`. No hay archivos versionados bajo esas 30 rutas; su contenido no se conoce. Los dos archivos versionados de `tests/.tmp_tests/manual_check/` sí se pudieron leer. Los 80 archivos originales fueron legibles y tienen hash. No se atribuye el error a corrupción o a ACL permanente sin evidencia; sí limita la enumeración completa de archivos no versionados. No se alteraron ni eliminaron esas rutas.

## Reproducción futura y límites

Desde la raíz, usar otro entorno/carpeta nuevos; el capturador rechaza sobrescribir evidencia:

```powershell
python -m venv .venv/hfs000-recheck
.\.venv\hfs000-recheck\Scripts\python.exe -m pip install -r docs/audit/evidence-clean/environment-freeze.txt
.\.venv\hfs000-recheck\Scripts\python.exe scripts/audit_baseline.py --git $auditGit --out .venv/hfs000-recheck-evidence --work .venv/hfs000-recheck-work
```

Comparar hashes de `examples.json` por caso y el hash canónico de `engine-results.json`; las rutas/fechas de los registros crudos variarán. El freeze fija versiones, no hashes de wheels ni disponibilidad futura del índice. Esta línea base caracteriza Windows/Python 3.12.10, sin garantizar otras plataformas ni futuras versiones. Los `xfail(strict=True, raises=AssertionError)` fallarán como XPASS cuando deje de reproducirse el defecto, requiriendo revisión; errores inesperados no quedan ocultos por esa marca.

## Cierre para revisión

Prioridades: falsos PASS por omisión (F-01/02/04/10/29/31), fallback F2 sin razones geométricas (F-03), resumen dimensional (F-05), cargas contradictorias (F-08), precisión publicada (F-09) y duplicados reales de catálogo (F-13). La validez física de H3 y las rutas F4/I sigue pendiente; véase [findings.md](findings.md).

La confirmación final mediante Git y hashes está en `final-verification.json`; la relación exhaustiva de archivos añadidos en [changed-files.md](changed-files.md). No hay diferencias de código del motor frente a HEAD. Reversibilidad: retirar únicamente las adiciones de auditoría y sus carpetas de ejecución, previa revisión; aquí no se realizó borrado. No se ejecutó HFS-001 ni tarea posterior. La siguiente tarea indicada por el roadmap es HFS-001, sujeta a la revisión solicitada por el usuario.
