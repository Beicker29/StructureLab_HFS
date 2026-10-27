# HFS-014 — Integridad del resumen CLI y agregación de lotes

Entrega para revisión técnica, 2026-10-27. Base **main**,
`d3190d4fab2938bf240024c5128f78943dd1e8d2`, sin cambios locales al comenzar.
Alcance exclusivo **F-05/F-29**. No hay commit, push, rama o PR. No se inicia otro
hito; HFS-017 y HFS-039 se registran únicamente como planificación futura.

## Correcciones demostradas

**F-05:** el resumen ya no busca una capacidad mínima entre unidades distintas.
Selecciona el mayor **DCR publicado** entre checks resistentes elegibles
efectivamente ejecutados y conserva todos los empates. Registra índice base cero,
cláusula, nombre, DCR publicado y estado. No calcula otra capacidad, infiere
unidades por cláusula ni reconstruye DCR dividiendo valores redondeados.

**F-29:** `aggregate_case_statuses([])` lanza un error de entrada estructurado;
el CLI lo aplica antes de ejecutar casos o crear directorios/memorias. Un lote
vacío no tiene resultado de cumplimiento. Para lotes no vacíos se conserva la
precedencia INCOMPLETE > FAIL > PASS y la información individual de los fallos.

Las reproducciones previas están en [sondas antes](evidence/cli/before-defect-probes.json)
y [dos pruebas rojas](evidence/incidents/red.json), ejecutadas antes de editar
runtime. Las [sondas después](evidence/cli/after-defect-probes.json) prueban:

| Caso | Antes | Después |
|---|---|---|
| Axial: 100 kN, DCR=0,90; flexión: 50 kN·m, DCR=0,02 | `governing_capacity_kn_or_knm=50`, flexión gobernante por mezclar magnitudes | Máximo publicado 0,90; check axial índice 0. Sin campo de capacidad mezclada |
| `aggregate_case_statuses([])` | PASS | `ValidationError`, código `EMPTY_CASE_BUNDLE` |
| CLI `{"cases":[]}` | stdout con PASS, exit 0, directorio de resultados creado | stderr con error, exit 1, stdout vacío, sin `status` de cumplimiento ni directorio de salida |

Estas son correcciones de contrato/agregación, no modificaciones normativas de
resistencia. No requieren cambiar ni reinterpretar ecuaciones AISC. El oráculo
de ranking son los DCR publicados estipulados por los casos; el oráculo de
agregación es la tabla de estados solicitada, no una copia de la implementación.

## Decisiones de alcance y arquitectura

Se conserva la función pequeña existente `run.py::_build_global_summary` como
fuente única para CLI y memorias. Se añade la misma estructura al CLI por caso
y a `output.global_summary`; `memory.global_summary` conserva además
`admissibility`. No hay otro motor, agregador de estados o reorganización general
del CLI. El [inventario DRY](../../architecture/dry-inventory.md) registra los
consumidores y responsabilidades.

Con coverage disponible, el resumen consume **sin modificar** los vínculos
`executed_checks` de obligaciones con `resistance=True`. No exige acreditación
de `accepted_checks`: identifica ejecución observada, no cobertura completa.
Así, no usa la cadena «H3» o «I1» para decidir tipo, unidad o papel resistente.
Sin coverage, los candidatos numéricos se identifican expresamente como
provisionales, sin habilitar PASS o inventar una interpretación normativa.

Cada candidato requiere demanda publicada finita no nula, capacidad publicada
finita positiva y DCR publicado finito no negativo. Los checks 0/0, inactivos,
no vinculados a una obligación resistente o sin datos numéricos utilizables
quedan en `excluded_checks` con su motivo. No se confunde una capacidad cero
con resistencia gobernante. Todos los FAIL, incluso los excluidos o no
gobernantes, siguen en `failed_checks`, y `known_failures` del motor no cambia.

La etiqueta siempre limita el resumen a **gobernantes observados de checks
ejecutados**, incluso con cobertura completa. Con INCOMPLETE no pretende
identificar el estado límite definitivo de toda la estructura. Sin candidatos:
`max_dcr_published=null` y `observed_governing_checks=[]`.

El agregador de lotes sigue siendo `results_model.aggregate_case_statuses`.
La guarda CLI invoca esa misma política para el vacío. Validación adicional de
transporte: presencia de `cases` exige lista; todos sus elementos deben ser
objetos antes de ejecutar el primero. No se implementa una transacción general
ni una prevalidación completa de la ingeniería de todo el lote: un objeto con
valores inválidos puede fallar después de casos anteriores, como antes.

## Contrato JSON y migración de consumidores

Especificación completa: [HFS-014 resumen/lotes](../../contracts/hfs014-summary-bundles.md).

- Se retiran `governing_capacity_kn_or_knm`, `governing_clauses` y
  `governing_check_names`. Se sustituyen por `max_dcr_published` y
  `observed_governing_checks`, con registros trazables por índice. Es cambio
  incompatible dentro de `memory.global_summary`, no un renombrado de capacidad.
- CLI por caso (individual o dentro de `cases`) y `output` de memoria incorporan
  `global_summary`. Los checks, cobertura, estados y `known_failures` no cambian.
- Consumidores deben conservar empates, leer estado/cobertura por separado y
  representar una lista vacía como ausencia de check resistente elegible.
- Un lote vacío produce `EMPTY_CASE_BUNDLE` con `field=cases`,
  `minimum_items=1`, `received_items=0`. Los tipos/elementos no válidos producen
  `INVALID_CASE_BUNDLE` indicando campo/tipo. Son errores de entrada, no FAIL.
- Los lotes no vacíos correctamente ejecutados mantienen exit 0 con PASS, FAIL
  o INCOMPLETE. No se corrige F-32 ni se cambia esa política.

Las pruebas de consumidores comprueban igualdad del resumen de CLI y memoria,
incluido `output`, salvo el campo histórico `admissibility` de memoria. Verifican
que cada índice permite recuperar el DCR y el estado del check correspondiente,
con y sin escritura de memoria y con lotes que contienen FAIL e INCOMPLETE.

### Precisión y exclusiones explícitas

Solo se usa `check.dcr`. Empates por igualdad **a la precisión publicada**, sin
epsilon ni redondeo adicional. Un PASS y un FAIL que publican ambos DCR=1,0
permanecen empatados con sus estados originales; el resumen no decide cumplimiento.
F-09 permanece como `xfail(strict=True)` y HFS-015 no se implementa.

Si la demanda/capacidad fue redondeada a cero, no se reconstruye el valor bruto
desde la memoria. El candidato se excluye con motivo, pero su fallo no se oculta.
Si un DCR de un FAIL no es finito, este resumen lo representa como `null` y no lo
ordena como número; el check original se conserva. No se cambia el contrato
numérico de CheckResult ni la serialización general de checks.

La traza legacy `_build_dcr_trace` sigue infiriendo unidades/reconstruyendo datos;
**el nuevo resumen no la consume**. Corregirla integralmente pertenece a
HFS-015/022/024. Se preserva byte a byte en esta tarea y se documenta para evitar
que otro consumidor la trate como DCR bruto canónico.

## Pruebas ejecutadas

Windows; Python **3.12.10** (`.venv/hfs000/Scripts/python.exe`). Entorno completo,
Git, freeze y comandos en [before/environment.json](evidence/before/environment.json)
y [after/environment.json](evidence/after/environment.json). Dependencias
principales: pytest 9.1.1, pydantic 2.14.1/pydantic_core 2.50.1, openpyxl 3.1.5.
No se instalaron ni actualizaron dependencias.

| Suite separada | Antes | Después | Fallidas / errores / omitidas ordinarias final |
|---|---:|---:|---|
| Original | 68 métodos + 12 subpruebas | 68 métodos + 12 subpruebas | 0 / 0 / 0 |
| Caracterización HFS-000 | 9 aprobadas + 3 xfail | 11 aprobadas + 1 xfail | 0 / 0 / 0 |
| HFS-011 contratos | 665 | 665 | 0 / 0 / 0 |
| HFS-016 catálogo | 44 | 44 | 0 / 0 / 0 |
| HFS-010 cobertura | 57 | 57 | 0 / 0 / 0 |
| HFS-012 selección | 61 | 61 | 0 / 0 / 0 |
| HFS-013 direccional | 57 | 57 | 0 / 0 / 0 |
| HFS-013 F-43 | 73 | 73 | 0 / 0 / 0 |
| HFS-014 nueva | No existía | 72 | 0 / 0 / 0 |

Final: **1108 aprobadas + 12 subpruebas + 1 xfail estricto (F-09)**. Nueve suites
con exit 0. [Verificación](evidence/after/verification.json). JUnit representa
80 registros en original (no 80 métodos) y un skipped para xfail (no omisión
ordinaria). No quedan XPASS. Los métodos originales no se modificaron.

La nueva suite [test_hfs014_summary_bundle.py](../../../tests/test_hfs014_summary_bundle.py)
cubre:

- Ranking axial/flexión/cortante/interacción, capacidad menor que no gobierna,
  etiquetas opacas, empates, FAIL con INCOMPLETE, cero checks/rellenos, ausencia
  de capacidad, metadata resistente y preservación del resultado sin mutarlo.
- DCR publicados deliberadamente distintos de demanda/capacidad: una división
  desde redondeados fallaría la prueba. Un guardia de test impide usar la función
  de inferencia de unidades o la traza para construir el resumen.
- Tabla completa de **39 combinaciones** de estados de uno, dos o tres casos,
  más error de lista vacía. Ningún INCOMPLETE se transforma en PASS.
- Ocho escenarios CLI de lotes válidos: PASS, FAIL, INCOMPLETE individuales;
  PASS+FAIL, PASS+INCOMPLETE, FAIL+INCOMPLETE y lotes de varios casos. Mantienen
  los FAIL individuales y exit 0; se leen las memorias realmente publicadas.
- Caso CLI individual con/sin memoria; lote vacío en proceso real; ocho formas
  vacías/malformadas de `cases`, incluidos lista con segundo elemento inválido,
  con guardias que prohíben ejecutar o publicar cualquier caso.

### Reproducción roja y conversión de xfail

Primera reproducción dirigida: **2 fallidas / 70 deseleccionadas**, exit 1,
antes de cambiar runtime ([log](evidence/incidents/red.json)). Tras corregir,
la suite nueva completa dio **72 aprobadas**, exit 0 ([log](evidence/incidents/targeted.json)).

Después se ejecutaron las dos pruebas históricas todavía marcadas estrictamente:
ambas dieron **XPASS(strict)**, exit 1 esperado ([log](evidence/incidents/xpass.json)).
Se investigaron las salidas: F-05 devuelve el axial por DCR y F-29 rechaza antes
de crear la salida. Se retiraron solo esas dos marcas y se reforzaron los asserts
de contrato. Sus reproducciones previas se conservan en Git y evidencia. La
prueba/marca de F-09 no se modificó.

## Comparación de los 12 ejemplos

Todos se ejecutaron antes/después por el motor; resultados **idénticos completos**
con hash semántico
`8b34cead811434c03119e0c456e9c70cd49ca555a8c17589013911a51d77f3d2`.
Se reutiliza el JSON canónico anterior por ruta/hash en [reused.json](evidence/reused.json).
La igualdad no es validación AISC, sino control de ausencia de cambios resistentes.

Además se ejecutaron **24 procesos CLI por versión**: los 12 ejemplos sin
modificar y los mismos 12 con el único cambio de transporte `write_results_json=true`.
Las entradas de ingeniería permanecen iguales. La captura normaliza únicamente
rutas/timestamps; conserva cálculos/trazas, estados, cobertura y errores.
Un token no finito legacy de memoria se registra explícitamente como
`{"nonfinite_json_token":"Infinity"}`, sin modificar producción ni reemplazarlo
por un valor numérico. La salida CLI cruda queda en cada registro de ejecución.

[Antes](evidence/cli/before-cli-examples.json), [después](evidence/cli/after-cli-examples.json)
y [comparación de 24 ejecuciones](evidence/cli/comparison.json). El comparador
admite solo `global_summary` en las posiciones documentadas; exige identidad
del resto de CLI/memoria, incluyendo checks, `clause_results`, estados, cobertura,
admisibilidad y códigos de salida. Resultado: **24 comparaciones aceptadas**.
El error previo de doble ángulo continúa igual; los otros 11 ejemplos siguen
INCOMPLETE, con FAIL parciales preservados.

Gobernantes observados ahora (índices base cero; no constituyen nuevos cálculos):

| Ejemplo | DCR publicado máximo | Índice/cláusula observada |
|---|---:|---|
| channel | 0,745 | 1 / E4-1 |
| circular_hss | 0,950 | 6 / H3-2 |
| composite_beam | 1,000 | 2 / I3-1b, transferencia; no acredita resistencia a momento |
| composite_encased | 0,593 | 5 / I4-1b |
| composite_filled_circular_hss | 2,490 | 2 / I5, FAIL |
| composite_filled_rectangular_hss | 14,280 | 2 / I5, FAIL |
| double_angle | — | Error previo, no resumen inventado |
| rectangular_hss | 2,367 | 12 / H1-1a, FAIL |
| single_angle | 0,087 | 3 / F10-2 |
| solid_circular | 0,035 | 0 / E3-1 |
| solid_rectangular | 0,053 | 0 / E3-1 |
| w_shape | 0,892 | 0 / E3-1 y 2 / E7-1, empate publicado |

Las interacciones se incluyen por sus vínculos resistentes y DCR; ya no se
excluyen por el prefijo de cláusula. Un check de transferencia puede gobernar
observadamente, pero no reemplaza las obligaciones de flexión faltantes: el
alcance declarado permanece incompleto.

### Incidencias de captura y reproducibilidad

La primera captura CLI completó las llamadas, pero al guardar el JSON de
evidencia falló con `ValueError: Out of range float values are not JSON compliant: inf`.
Se confirmó el token Infinity existente en memorias detalladas. Solo se adaptó
el capturador para codificar esos tokens con su nombre, sin corregir precisión
ni serialización del motor. El error se conserva aquí desde la salida de la
herramienta; no se presenta un log crudo que no se guardó.

La repetición con rutas largas generó FileNotFoundError al escribir SVG de dos
ejemplos compuestos, en rutas que excedían el límite clásico de Windows. La
comparación detectó diferencias y **rechazó** esa captura, en lugar de ocultar
los errores ([errores completos](evidence/incidents/long-path-errors.json),
[comparación rechazada](evidence/incidents/long-path-comparison.json)). Se acortaron
solo los directorios del capturador y se repitieron las 24 llamadas en cada copia.
Los mismos ejemplos entonces se ejecutaron y compararon correctamente. No se
cambió generación de SVG, código de capítulos, permisos, ACL ni rutas del usuario.

Los 31 directorios inaccesibles heredados siguen registrados por Git sin
limpiarlos. Las suites se ejecutaron con escalación aprobada para sus fixtures,
sin omitir pruebas o etiquetar infraestructura como xfail. No se añadieron
dependencias ni herramientas de CI.

Comandos ejecutados, desde raíz, con Git en PATH; todas las rutas de evidencia
y trabajo deben ser nuevas:

```powershell
$env:PATH = 'D:\Users\byomayusa\AppData\Local\GitHubDesktop\app-3.6.7\resources\app\git\cmd;' + $env:PATH
# Base: ocho suites, antes de editar runtime.
.\.venv\hfs000\Scripts\python.exe scripts/audit_hfs011.py --baseline docs/audit/hfs013/evidence/final/engine-results.json --out .venv/hfs014-before --work .venv/hfs014-before-work --extra-suite tests/test_hfs016_catalog_integrity.py --extra-suite tests/test_hfs010_coverage.py --extra-suite tests/test_hfs012_flexure_selection.py --extra-suite tests/test_hfs013_directional_h3.py --extra-suite tests/test_hfs013_design_method.py
# Final: nueve suites.
.\.venv\hfs000\Scripts\python.exe scripts/audit_hfs011.py --baseline docs/audit/hfs013/evidence/final/engine-results.json --out .venv/hfs014-after --work .venv/hfs014-after-work --extra-suite tests/test_hfs016_catalog_integrity.py --extra-suite tests/test_hfs010_coverage.py --extra-suite tests/test_hfs012_flexure_selection.py --extra-suite tests/test_hfs013_directional_h3.py --extra-suite tests/test_hfs013_design_method.py --extra-suite tests/test_hfs014_summary_bundle.py
# Capturas CLI finales contra las copias respectivas (rutas cortas).
.\.venv\hfs000\Scripts\python.exe scripts/audit_hfs014_cli.py .venv/hfs014-before-work .venv/14cb
.\.venv\hfs000\Scripts\python.exe scripts/audit_hfs014_cli.py .venv/hfs014-after-work .venv/14ca
.\.venv\hfs000\Scripts\python.exe scripts/compare_hfs014_cli.py .venv/14cb/cli-examples.json .venv/14ca/cli-examples.json .venv/hfs014-cli-final-comparison.json
```

Se fija PYTHONNOUSERSITE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONUTF8=1 y se
retira PYTHONPATH para capturas. Comandos completos/cwd/exit/stdout/stderr y XML
por suite están en `evidence/before` y `after`. `--basetemp` usa la copia;
`-p no:cacheprovider` evita caché. La nueva conveniencia `scripts/audit_hfs014.py`
configura las mismas nueve suites usando el capturador existente; se comprobó
su ayuda/sintaxis, pero la captura final se ejecutó con el comando explícito
`audit_hfs011.py` mostrado. No se atribuye otra ejecución al wrapper.

## Archivos, preservación y riesgos residuales

[Inventario completo](changed-files.md), [verificación Git/hash](evidence/scope-verification.json)
y [manifiesto](evidence/SHA256SUMS.json). Solo `run.py` y la guarda del agregador
de lotes en `results_model.py` cambian runtime. Las clases de estado/cobertura
HFS-010 permanecen intactas; también engine, router, nominales, factores LRFD/ASD,
catálogo, HFS-012/013/F-43 y sus pruebas. No se introducen nuevos créditos de
cobertura. No hay diferencias numéricas resistentes autorizadas o detectadas.

La documentación viva, los dos tests de caracterización y los nuevos tests y
capturadores se listan separadamente. Las capturas históricas no se alteran.
Logs/sondas/comparaciones nuevos se conservan en Git; las copias de trabajo,
memorias temporales y renders quedan bajo `.venv`, sin eliminación ni exclusión
nueva. El JSON de motor idéntico se reutiliza desde su ruta canónica con hash
en lugar de duplicarlo; eso no borra ninguna evidencia previa.

Riesgos abiertos para revisión:

1. El DCR publicado puede ocultar diferencias por redondeo; se conservan empates
   y estados, sin reclamar precisión bruta. F-09/HFS-015 siguen abiertos.
2. El papel resistente proviene de metadata de ejecución existente, no de una
   validación normativa nueva. Sin metadata solo hay candidatos provisionales.
   Las exclusiones no justifican recortar retrospectivamente el alcance.
3. Las trazas legacy y tokens no finitos de memoria requieren su revisión futura;
   no se interpretan como fuente canónica para este resumen.
4. Cambia el contrato del resumen detallado: consumidores que lean los tres
   campos retirados deben migrar. F-32 y los códigos de salida de casos/lotes
   no vacíos se conservan, incluidos FAIL e INCOMPLETE con exit 0.
5. El flujo de lote no se vuelve transaccional para errores ingenieriles tardíos.
   Esta tarea garantiza rechazo temprano del vacío y de la forma de `cases`.
6. El roadmap registra **HFS-017**, blindaje LRFD/ASD antes de HFS-020, y
   **HFS-039**, habilitación ASD por dominios validados después de auditorías
   D/E/F/G/H/I. Ninguna se implementa. F-31/F-37 y restantes hallazgos siguen
   abiertos; el resumen no los resuelve.

F-05/F-29 tienen cierre funcional demostrado, pendiente de revisión técnica del
usuario. HFS-015 no se inicia. No se declara G1 ni validación AISC integral por
tener pruebas verdes. Cambios listos para que el usuario decida commit y push.
