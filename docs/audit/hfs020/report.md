# HFS-020 — Empaquetado, CI y calidad

## Corrección de compatibilidad Windows/Ubuntu — 2026-10-28

Base `main`, HEAD `70adc5edf7c5556d0dd5c1be7de915ad0d63b8bf`, árbol inicial
limpio. Los artifacts reales de Actions 40617061992 demuestran que los 12
SHA-256 de entrada difieren únicamente por CRLF/LF. Resultados, cobertura,
trazas y memorias coinciden. Se conserva cada hash de bytes y se verifica por
separado contenido JSON exacto contra una referencia vinculada a la captura
histórica y a los archivos versionados. No cambia el motor ni sus entradas.

Regresión local completa: 1711 aprobadas + 12 subpruebas; cero fallos,
errores, omitidas o xfail. Doce ejemplos y 24 escenarios CLI/memoria idénticos.
[Diagnóstico, solución, pruebas, reproducción y riesgos](compatibility/report.md).
[Inventario actualizado](changed-files.md#corrección-de-compatibilidad-2026-10-28).
**Pendiente de publicación por el usuario y nueva ejecución remota con ambos
jobs SUCCESS; HFS-020 no está completamente cerrado.** Sin commit ni push.

## Informe original de implementación (conservado)

Fecha: 2026-10-27. Base `main`, HEAD
`8af8e435812bfeff23d921c2aa4c860ca98ef4dd`; árbol inicial limpio.
Alcance exclusivo HFS-020. Sin ramas, PR, commit ni push. Implementación local
para revisión técnica independiente; **no se presenta una corrida remota de
GitHub Actions ni soporte Ubuntu como verificados**.

## Diagnóstico y decisiones

El proyecto ejecutaba `python -m src.steel_design.run` desde su checkout con
dos requisitos sueltos, sin metadatos de distribución, entry point o CI. No
hay `__init__.py` convencionales: `src` forma parte del nombre público, no es
simplemente la carpeta que un backend deba quitar al instalar.

Se usa setuptools con descubrimiento explícito desde `.` y allowlist
`src.steel_design` / `src.steel_design.*`, conservando namespaces PEP 420.
No se añaden `__init__.py`, no se crea el alias `steel_design` y no se migran
imports. [Setuptools documenta el descubrimiento de namespaces implícitos](https://setuptools.pypa.io/en/stable/userguide/package_discovery.html);
la distinción con un src-layout convencional es deliberada.

| Concepto | Decisión HFS-020 |
|---|---|
| Distribución | `structurelab-hfs`, versión inicial de empaquetado `0.1.0`; no certifica madurez normativa ni publicación |
| Backend | `setuptools==84.2.1`, build aislado PEP 517 |
| Python | Metadata `>=3.12`; ejecutado localmente 3.12.10/Windows; versiones posteriores no acreditadas por este hito |
| Runtime | `pydantic>=2.14.1,<3`, `openpyxl>=3.1.5,<4`; mínimos conservadores de las versiones efectivamente auditadas |
| Desarrollo | Extra `dev`: pytest 9.1.1, build 1.6.1, Ruff 0.17.3, twine 7.0.0 |
| Resolución reproducible | `requirements/ci-constraints.txt`, versiones directas/transitivas observadas en Windows; no sustituye metadatos ni instala paquetes por sí solo |
| Compatibilidad requirements | `requirements.txt` delega a `.`; usar desde raíz del proyecto, como antes |
| CLI instalado | `structurelab-hfs = src.steel_design.run:main`; mismo parser y motor |
| Catálogo | Recurso externo; `--sections` explícito fuera del checkout; no empaquetado, descargado ni corregido |
| Contenido | 33 archivos Python de producción + metadata; sdist añade README/pyproject/MANIFEST y archivos de build permitidos |

`MANIFEST.in` usa allowlist para impedir que setuptools incorpore las pruebas
automáticamente en sdist. Wheel y sdist se inspeccionan por contenido y hash
de cada archivo Python. Se excluyen Excel, PDF, evidencias, resultados, ejemplos,
tests, temporales y scripts de auditoría. El wheel es `py3-none-any`, pero esa
etiqueta de distribución no demuestra soporte funcional multiplataforma.
No se inventa una licencia: no había archivo LICENSE ni autorización para
asignarla; publicación/distribución a terceros requiere revisar ese punto.

No se ha modificado **ningún archivo bajo `src/`**, ninguna prueba histórica,
ejemplo o catálogo. Los 67 fuentes/tests/entradas de la captura inicial se
conservan por SHA-256: [verificación](evidence/protected-files.json). Las guardas
HFS-017, factores, selección, obligaciones HFS-010, ejes HFS-013 y precisión
HFS-015 quedan intactos. No se implementan HFS-021/022/039/040.

## Instalación y CLI fuera del checkout

`scripts/verify_hfs020.py` construye primero sdist y luego wheel **desde ese
sdist**, valida ambos con `twine check --strict` y comprueba la allowlist.
Crea dos entornos virtuales nuevos sin system-site-packages:

1. Instalación normal del proyecto mediante `pip install -c ... .`, sin editable.
2. Instalación del archivo wheel con constraints y únicamente sus dependencias
   de runtime. Pytest se añade después para las once suites.

Cada entorno se prueba desde una carpeta temporal externa inicialmente vacía.
`python -I` importa engine, CLI, modelos, guardas y repositorio; cada `__file__`
debe quedar bajo el entorno instalado, no bajo el checkout. Se elimina PYTHONPATH
y PYTHONHOME heredado. El freeze confirma que no se introducen build, Ruff,
twine, pytest o herramientas gráficas como dependencias de runtime.

En ambos entornos se ejecutan `structurelab-hfs` y el comando histórico
`python -m src.steel_design.run`, con `--help` y un caso real usando ruta externa
a catálogo y salida. Sin `--sections`, desde esa carpeta sin `data/`, el comando
conserva su **error JSON de etapa `load_sections`, exit 1**. El default relativo
se documenta sin cambiar el parser ni inventar una búsqueda de datos instalada.
El catálogo es input de integración externo, no una dependencia accidental del
checkout: se copia por hash fuera de él para las verificaciones.

La instalación directa deja un `direct_url.json` con la procedencia de instalación,
como hace pip; eso no es una ruta usada por el motor ni un editable. Se prueba
la resolución real desde `site-packages`. El wheel no necesita ningún archivo
de código del repositorio. La biblioteca no requiere matplotlib: se verifica su
ausencia en los entornos limpios y se conserva el fallback SVG previo del CLI.
No se introduce dependencia gráfica ni se extrae la interfaz en este hito.

## Qué se verificó y dónde

Resultado local final: **once suites, 1661 pruebas aprobadas + 12 subpruebas
originales**, sin fallos, errores, omitidas ni xfail. **Cero diferencias** en
resistencias nominales/disponibles, demandas, DCR, estados, cobertura o trazas
de los 12 ejemplos y los 24 escenarios CLI/memoria. Los cuatro recorridos del
caso externo (proyecto/wheel × módulo/console-script) son también idénticos
tras normalizar rutas/fechas. [Comparación](evidence/comparison.json) y
[resumen instalado](evidence/installed/verification.json).

| Suite | Checkout antes | Wheel instalado fuera del checkout | Exit antes/después |
|---|---:|---:|---|
| Original | 68 métodos + 12 subpruebas | 68 + 12 | 0 / 0 |
| Caracterización HFS-000 | 12 | 12 | 0 / 0 |
| HFS-011 | 665 | 665 | 0 / 0 |
| HFS-016 | 44 | 44 | 0 / 0 |
| HFS-010 | 57 | 57 | 0 / 0 |
| HFS-012 | 61 | 61 | 0 / 0 |
| HFS-013 direcciones | 57 | 57 | 0 / 0 |
| HFS-013 F-43 | 73 | 73 | 0 / 0 |
| HFS-014 | 72 | 72 | 0 / 0 |
| HFS-015 | 84 | 84 | 0 / 0 |
| HFS-017 | 468 | 468 | 0 / 0 |

Build, twine, Ruff, installs, pip check, imports, CLI y comparación terminaron
con exit 0. Los dos ensayos negativos de catálogo ausente salieron 1 como se
exige; no son suites fallidas ni resultados resistentes FAIL.

| Verificación | Entorno/origen del código | Evidencia |
|---|---|---|
| Once suites de línea base | Copia aislada de fuentes del checkout antes de editar | `evidence/before/` |
| Doce ejemplos y 24 CLI/memorias base | Código de esa copia, herramientas históricas | `before/engine-results.json`, `cli-before.json` |
| Construcción, metadata, contenido, Ruff | Herramientas de desarrollo; checkout y sdist | Logs de instalación/verificación |
| Imports y dos comandos CLI tras `pip install .` | Solo paquete instalado, cwd temporal externo | `imports-project`, `external-project-*` |
| Imports y dos comandos CLI tras instalar wheel | Solo paquete instalado, cwd temporal externo | `imports-wheel`, `external-wheel-*` |
| Once suites después | Tests y datos externos; **sin carpeta src copiada**, producción desde wheel | `pytest-*.json/xml` |
| Doce ejemplos después | Engine instalado desde wheel | `engine-results.json` |
| 24 escenarios CLI/memoria después | Módulo CLI instalado desde wheel | `cli-examples.json` |
| Workflow | actionlint 1.7.12 local; mismo verificador que usa CI | `actionlint.json` |
| GitHub Actions y Ubuntu | Configurados, no ejecutados remotamente | Pendiente; sin push autorizado |

El verificador copia solo tests/ejemplos/Excel y dos utilidades históricas de
captura, que no contienen implementación del motor. Reutilizar esas utilidades
evita redefinir la normalización de rutas/fechas y las capturas de casos.
Las entradas externas tienen manifiesto de hashes. Las pruebas de empaquetado
son las comprobaciones reproducibles de este script; no se cuentan como otra
suite normativa ni se altera la selección de las once suites existentes.

Se comprobó además el comando exacto de bootstrap de CI/README en un tercer
entorno limpio (`.venv/20dev`): `pip install -c requirements/ci-constraints.txt
".[dev]"`, `pip check`, freeze y Ruff; todos exit 0. Se conservan sus registros
en [`evidence/development/`](evidence/development/). Esta instalación de
desarrollo desde el checkout no se confunde con las pruebas del wheel externo.

## Ruff y deuda explícita

Antes de introducir configuración se ejecutó Ruff 0.17.3 sobre `src tests scripts`
con E4/E7/E9/F. Resultado: **51 incidencias**, exit 1. El
[registro completo](evidence/ruff-initial.json) y [resumen](evidence/ruff-debt.json)
identifican regla, archivo y ubicación. Configuración final: esas mismas reglas,
excepciones limitadas a los nueve archivos siguientes. No se ejecutó autofix,
formatter ni reordenación masiva; no hubo corrección mecánica de runtime.

| Archivo | Deuda conservada |
|---|---|
| `domain/rules/composite_rules.py` | 2 F841; una asignación llama a cálculo/validación, no eliminar su llamada por parecer sin uso |
| `scripts/audit_hfs017_probes.py` | 1 E702 |
| `scripts/compare_hfs015.py` | F401×1, E701×9, E702×6, E731×1 |
| `scripts/compare_hfs017.py` | E731×1, E701×1 |
| `scripts/probe_hfs015.py` | E701×1, E402×5; imports después de seleccionar raíz histórica |
| `scripts/verify_hfs015_scope.py` | E701×4, E702×1 |
| `tests/test_hfs014_summary_bundle.py` | F401×1, E702×1 |
| `tests/test_hfs015_precision_advice.py` | E701×5, E702×2 |
| `tests/test_hfs017_design_method.py` | E702×9 |

No se suprimen archivos completos: las demás reglas siguen activas en ellos.
La configuración se limita a fuentes/tests/scripts actuales; evidencias congeladas
y copias temporales no son objetivos de lint. `ruff check .` pasa con esa deuda
declarada. El código nuevo no tiene excepciones. Las excepciones por archivo
pueden admitir incidencias nuevas del mismo código: requieren revisión, no se
deben ampliar silenciosamente. [Referencia de configuración Ruff](https://docs.astral.sh/ruff/configuration/).

## CI y límites de verificación remota

`.github/workflows/ci.yml` se activa por push a main, PR o despacho manual.
Matriz obligatoria Windows 2022 / Ubuntu 24.04, Python 3.12.10; no hay
`continue-on-error` ni tests omitidos para Ubuntu. Cada job instala `.[dev]`
con constraints y ejecuta el mismo verificador. Conserva logs/JUnit/distribuciones
como artifacts durante 14 días, incluso si falla. Esto no sustituye la evidencia
durable de revisión en el repositorio.

Actions checkout/setup-python/upload-artifact están fijadas por SHA consultado
en sus repositorios oficiales; permisos `contents: read`, sin credenciales
privadas ni `persist-credentials`. El token estándar del runner no se utiliza
para publicar ni fusionar. Versiones de herramientas fijadas; no hay rutas de
LENOVO o del entorno local en el workflow.

Se validó YAML, expresiones, matriz, inputs y shell con
[actionlint](https://github.com/rhysd/actionlint/blob/main/docs/checks.md) 1.7.12.
El binario Windows se descargó del release oficial y se contrastó contra su
checksum publicado: [procedencia](evidence/actionlint-source.json).
Esta es validación estática, **no un resultado de GitHub Actions**. No se
ejecutó remoto porque se pidió no hacer commit/push. WSL no está instalado;
[registro de disponibilidad](evidence/ubuntu-availability.json). No se instala
un sistema operativo ni se simula una ejecución Ubuntu con Windows.

La resolución fijada corresponde a Windows; dependencias de herramientas que
solo aparezcan en Linux deberán registrarse al ejecutar esa plataforma.
Los jobs no ocultan discrepancias de float, rutas, catálogo o dependencias:
comparan números/trazas exactamente contra la referencia. No se afirmará soporte
Ubuntu hasta revisar sus resultados reales.

## Reproducción y conservación

Ejecuciones reales: `.venv/20b` / `.venv/20bw` para línea base;
`.venv/20bc` para 24 consumidores base; `.venv/20v1` para el primer intento
instalado; `.venv/20v2` para la verificación final con exit 0. Se usaron Python
3.12.10 y las versiones de herramientas/runtime fijadas en el informe. Las
once suites base se capturaron con `scripts/audit_hfs011.py` y sus ocho
`--extra-suite` de HFS-017, contra
`docs/audit/hfs017/evidence/after/engine-results.json`. Comandos de cada suite
y sus salidas están en `evidence/before/pytest-*.json`.

Comandos locales finales del nuevo verificador y lint:

```powershell
.\.venv\20tools\Scripts\python.exe -X utf8 scripts/verify_hfs020.py --out .venv/20v2
.\.venv\20actionlint\bin\actionlint.exe .github/workflows/ci.yml
.\.venv\20tools\Scripts\python.exe -m ruff check .
git diff --check
```

Las distribuciones comprobadas se conservan en
[`evidence/installed/distributions/`](evidence/installed/distributions/), con
contenido/metadatos/hashes en [archives.json](evidence/installed/archives.json).
Se trasladan **copias** desde `dist/` a `distributions/` en evidencia para no
ocultarlas con el gitignore preexistente; originales locales intactos y mapa
[artifact-relocation.json](evidence/artifact-relocation.json). No se modificó
`.gitignore`. El intento inicial y sus distribuciones se conservan aparte en
[`incidents/first-installed/`](evidence/incidents/first-installed/).

Desde la raíz con Python 3.12.10:

```powershell
python -m venv .venv/hfs020-review
.\.venv\hfs020-review\Scripts\python.exe -m pip install -c requirements/ci-constraints.txt ".[dev]"
.\.venv\hfs020-review\Scripts\python.exe scripts/verify_hfs020.py --out .venv/hfs020-new
```

Elegir siempre una salida nueva. Las carpetas temporales externas se conservan
y su ruta queda en `environment.json`; no se borra evidencia para aparentar éxito.
Las referencias congeladas HFS-017 se usan solo como regresión conductual.
El script comprueba valores/trazas/estados/cobertura literalmente y normaliza
únicamente las rutas/fechas ya definidas por la utilidad histórica.
No se promete igualdad byte a byte entre builds (timestamps/metadata del archivo
comprimido pueden cambiar); sí inspección completa y hashes de cada artefacto
real verificado. No hay edición de expectativas históricas.

Los comandos/cwd/exits/stdout/stderr se registran por paso; el manifiesto final
permite recuperar y comprobar la evidencia publicada para revisión. El inventario
está en [changed-files.md](changed-files.md). No se modifican PDFs, catálogo,
evidencia HFS-000/011/013/014/015/017 ni sus manifiestos.

## Incidencias y riesgos pendientes

- La primera descarga pip dentro del sandbox falló por WinError 10013; se
  repitió con acceso de red autorizado en un entorno virtual nuevo. No fue una
  incompatibilidad de la librería ni se marcó xfail.
- Primera corrida instalada: original aprobada, caracterización 11 aprobadas
  y un error de infraestructura porque el padre de `--basetemp` no existía.
  Se corrigió el verificador creando ese directorio; no se alteró el test.
  Logs y artifacts iniciales permanecen recuperables.
- El primer build exploratorio produjo distribuciones pero la invocación
  PowerShell con redirección devolvió exit 1; la captura definitiva usa
  `subprocess.run`, registra el exit nativo y verifica archivos/instalación.
  No se usa esa corrida exploratoria como prueba de aceptación.
- Una inspección adicional del tar generado bajo permisos elevados recibió
  acceso denegado desde el sandbox. La inspección autorizada del verificador
  ya había pasado; no se cambiaron ACL ni se ocultó el error mediante limpieza.
- `src` es un namespace público muy genérico; otra distribución podría
  ocuparlo con un paquete regular. Se conserva por compatibilidad; cualquier
  renombrado/migración requiere tarea y contrato propios.
- Catálogo externo y default relativo requieren configuración del consumidor.
  Rutas válidas y paquete instalable no validan la geometría o la norma.
- Soporte Ubuntu, ejecución real Actions, actualización futura de constraints,
  deuda Ruff y política de licencia/publicación quedan visibles para revisión.
  No se habilitan nuevos dominios ASD ni se cierran defectos ingenieriles.
