# Contribuir a StructureLab_HFS

Aplican [AGENTS.md](AGENTS.md), el [roadmap](docs/ROADMAP.md) y los tres ADR de HFS-001. La base aceptada es [HFS-000](docs/audit/baseline.md); los defectos abiertos están en [tracking.md](docs/audit/tracking.md).

## Un cambio revisable

Antes de implementar, especificar problema/F-ID, tarea, alcance, contratos afectados, invariantes y verificación. Usar una rama y un cambio pequeño cuando sea posible; no mezclar modificación de ecuaciones, reorganización de archivos y actualización de fixtures. Un cambio documental no autoriza ejecutar la siguiente tarea.

Una propuesta DRY debe nombrar las copias, explicar qué concepto comparten, identificar su propietario canónico y justificar por qué la consolidación preserva dominios normativos. Una coincidencia de constantes no basta. Las pruebas independientes deben seguir independientes del código productivo que verifican.

## Entorno reproducible

Desde la raíz, para reproducir el entorno aceptado, usar una carpeta nueva:

```powershell
python -m venv .venv/hfs-review
.\.venv\hfs-review\Scripts\python.exe -m pip install -r docs/audit/evidence-clean/environment-freeze.txt
```

El freeze es un entorno de auditoría Windows/Python 3.12.10, no un lock de distribución ni garantía para todas las plataformas. No actualizar paquetes dentro de una reproducción y atribuir luego diferencias solo al código.

Para aislar las escrituras de pruebas y CLI, el capturador existente copia y verifica las entradas por hash. Elegir rutas nuevas, nunca sobre evidencia aceptada:

```powershell
$auditGit = (Get-Command git -ErrorAction Stop).Source
.\.venv\hfs-review\Scripts\python.exe scripts/audit_baseline.py --git $auditGit --out .venv/hfs-review-evidence --work .venv/hfs-review-work
```

Si Git no está en PATH, pasar su ruta real (HFS-000 registra la usada con GitHub Desktop). Si hay restricciones del entorno, registrar el error y usar el mecanismo de permisos disponible; no desactivar pruebas ni cambiar permisos históricos para aparentar éxito.

## Suites separadas

En la copia de trabajo, con el Python del entorno fijado, ejecutar:

```powershell
python -m pytest -q -ra --ignore=tests/test_hfs000_characterization.py
python -m pytest -q -ra tests/test_hfs000_characterization.py
```

Fijar `PYTHONNOUSERSITE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONUTF8=1` y retirar PYTHONPATH heredado para repetir las condiciones de HFS-000. El capturador lo hace automáticamente. Escribir JUnit/logs fuera de la evidencia congelada; `-p no:cacheprovider` evita una caché prescindible sin omitir tests.

Base original: **68 métodos + 12 subpruebas aprobadas**, no 80 métodos. Caracterización: **11 xfail**, no 11 pruebas aprobadas. Los ejemplos incluyen resultados FAIL con exit 0; una prueba de ejecución correcta no acredita cumplimiento estructural. Después de correcciones autorizadas, explicar cualquier cambio de estos conteos.

Registrar comando completo, cwd, SHA, Python/dependencias, códigos de salida y advertencias. Si solo se verificaron hashes o se usó evidencia anterior, indicarlo; no presentarlo como nueva ejecución. Lint/tipos/CI se incorporarán en su tarea; no se exige instalar un sistema adicional para editar documentación.

Para HFS-016, añadir `--ignore=tests/test_hfs011_input_contracts.py` y
`--ignore=tests/test_hfs016_catalog_integrity.py` al comando de suite original.
Ejecutar ambos archivos aparte. El capturador `audit_hfs011.py` admite
`--extra-suite tests/test_hfs016_catalog_integrity.py` para mantener las cuatro
suites separadas. Reproducción y conteos actuales en el
[informe HFS-016](docs/audit/hfs016/report.md).

## Evidencia, revisión y cierre

HFS-013 añade la séptima suite `tests/test_hfs013_directional_h3.py` y usa
`scripts/audit_hfs013.py --baseline <captura previa> --out <ruta nueva> --work <copia nueva>`.
Ejecuta por separado original, caracterización, HFS-011/016/010/012/013. Registra
igualdad literal fallida de ejemplos **intencionalmente**: G/H3 cambian; el
comparador exige invariantes D/E/F/H1/I, estado global y obligaciones, y enumera
todas las diferencias G/H3. La aceptación está en `hfs013-verification.json`,
no en la comparación literal heredada. Los oráculos independientes están en las
pruebas, no en este comparador. [Comandos, conteos y ajustes de expectativas](docs/audit/hfs013/report.md).

HFS-012 añade `tests/test_hfs012_flexure_selection.py` como sexta suite separada:
pasar también `--extra-suite tests/test_hfs012_flexure_selection.py` al capturador.
No usar `--coverage-transition` para esta corrección: los ejemplos existentes
deben conservarse íntegros; las diferencias dirigidas de selección se contrastan
con sondas antes/después. [Reproducción y evidencia](docs/audit/hfs012/report.md).

HFS-010 añade una quinta suite: `tests/test_hfs010_coverage.py`, separada también
de la original. Pasar `--extra-suite` para HFS-016 y HFS-010 al capturador, además
de `--coverage-transition`: esta opción exige igualdad exacta de checks/trazas y
errores previos, pero comprueba los cambios intencionales de estado global por
separado. No usar igualdad literal de resultados completos para ocultar o impedir
esa transición. [Comandos y resultados](docs/audit/hfs010/report.md).

Para HFS-011 y siguientes, separar también `tests/test_hfs011_input_contracts.py` de la suite original. El capturador [audit_hfs011.py](scripts/audit_hfs011.py) ejecuta las tres suites por separado en una copia nueva y compara los ejemplos con la captura previa; comandos y migración en el [informe HFS-011](docs/audit/hfs011/report.md). No presentar los casos parametrizados nuevos como métodos de la suite histórica ni los xfail como aprobados.

- Cambio normativo o de propiedades: fuente precisa, cálculo esperado independiente, tolerancia, fronteras y revisión ingenieril antes de declararlo validado.
- Corrección de defecto: reproducción previa, contraste posterior y actualización del F-ID; no borrar un xfail sin reemplazar su objetivo de seguridad.
- Refactorización sin cambio de comportamiento: comparación por caso/estado límite y preservación de trazas. No conservar un defecto por obediencia a un snapshot; separar su reparación.
- Describir efectos, pruebas y límites en la revisión; incluir `git diff --check` y un inventario de cambios/pendientes. Las capturas generadas se conservan conforme a [evidence-policy.md](docs/audit/evidence-policy.md).
