# HFS-017 — Blindaje transversal LRFD/ASD

Fecha: 2026-10-27. Estado: implementación y evidencia listas para **revisión
técnica independiente**, sin declarar acreditación normativa integral.
Se trabajó directamente en `main`, HEAD
`7234df8ba3de88db0f57de7f09e7d1b33c089d93`, árbol inicialmente limpio.
No se creó rama/PR, ni se hizo commit/push. No se inició HFS-020/HFS-039.

## Resultado y diagnóstico

Se cerraron escapes de método en reglas/evaluadores F e I y fallbacks implícitos
en conversores D/E/G/H. Se conserva el bloqueo público ASD en flexión y
compuestos, la corrección F-43 interna H1/H3 y todos los resultados correctos
observados. Las once suites pasan: **1661 pruebas + 12 subpruebas originales**,
sin fallos, errores, omisiones ni xfail. Doce ejemplos y 24 ejecuciones
CLI/memoria son literalmente iguales tras normalizar rutas/fechas con el
capturador histórico. No se alteran nominales, interacciones ni acreditaciones
HFS-010.

Fuentes leídas: AGENTS, CONTRIBUTING, ADR-001/002/003, inventario DRY, roadmap,
matrices HFS-002, seguimiento y evidencia de HFS-011/013/014/015. La autorización
actual parte de dependencias completadas; eso no convierte sus pruebas de
regresión en validación de toda AISC. [Matriz de soporte](support-matrix.md),
[contrato/migración](../../contracts/hfs017-design-method.md) e
[inventario](changed-files.md) forman parte de esta entrega.

| Hallazgo reproducido | Antes, código base | Después |
|---|---|---|
| F-44: F directo con caso ASD | F11 de la sonda publica 288 kN·m LRFD y PASS bajo caso ASD | Error F estructurado antes de evaluar nominal; no se sustituye por capacidad ASD |
| F-44: demanda cero F/I | F11 devolvía PASS; otras rutas podían salir antes de comprobar método | Rechazo ASD también antes de retornos inactivos |
| F-44: helper I de cortante acero | Usaba `design_method="LRFD"` sin examinar el caso ASD | Guarda I antes del cálculo; se conserva constante dentro del dominio LRFD |
| F-45: conversores D/E/G/H | `LFRD` podía seleccionar Ω de ASD; E con nominal cero devolvía cero | `ValueError` explícito, incluso nominal cero |
| Trazabilidad D2 | Capacidad calculada por método, pero sin factor/método en su memoria | Factor activo y método añadidos a la traza, cálculo sin cambios |
| F-43 H1/H3 | Ya corregido en HFS-013 | Preservado: nominal F7/F8 idéntico y F1 por método; 73 tests previos pasan |

Las [sondas](evidence/probes/before.json) y su
[contraste](evidence/probes/after.json) muestran los valores/error completos.
No todas las reglas I eran alcanzables con un caso ASD válido a través del
motor; el defecto era la invocación directa que eludía esa barrera.

## Decisiones y recorrido del método

`SteelCase` valida el enum → `validate_case` conserva HFS-011 y llama a la
política compartida → `ProfileRouter.get_rules` aplica esa misma política aun
si se llama sin motor → cada regla/evaluador valida su método antes de calcular
o devolver un placeholder. El motor continúa generando obligaciones desde
`coverage.py` y registrando evidencia con `coverage_evidence.py`, sin cambios.
CLI llama al mismo motor y publica su método en `coverage.method`.

- `design_methods.py` contiene solo el enum y reconocimiento de métodos.
  La reexportación desde `models` conserva imports existentes. No hay registro
  genérico, servicio ni dependencia nueva.
- `domain/design_methods.py` es dueño de las restricciones públicas F/I y de
  las guardas defensivas de casos. No duplica ecuaciones ni reglas de cobertura.
- D2 posee los factores diferenciados de fluencia/rotura usados tanto en cálculo
  como en traza; E1 posee su conversión y traza. `_design_factor` axial conserva
  un alias de compatibilidad. F1 sigue en `flexure_calc`; sus reglas LRFD usan
  explícitamente el método validado y la constante canónica existente.
- G conserva los factores definidos por su rama, incluida la excepción G2.1(a).
  H1/H3 reciben D/E/F/G/H3 coherentes. Sus nominales no dependen del método.
- I conserva φc=.75, φt=.90, φM=.90, φV=.90/.75 donde estaban. Sus reglas y
  helpers de capacidades disponibles/interacción ahora exigen LRFD. Los
  helpers nominales sin factor, incluida la construcción nominal de puntos
  rellenos, siguen siendo nominales y no habilitan una verificación ASD.

No se unifican factores de disposiciones distintas aunque coincidan. Tampoco
se confunden 0,85/0,95 del bloque de concreto, Cv, Cp/Cm, coeficientes de
interacción o límites geométricos con factores φ/Ω. El capítulo I y sus puntos
de interacción mantienen reservas de nominal/disponible y dominio (F-20/37);
no se acreditan ni corrigen sus ecuaciones en este hito.

La compatibilidad de las demandas es una responsabilidad externa declarada en
el contrato. El programa no verifica combinaciones LRFD/ASD, no convierte cargas
al cambiar el selector y no aplica automáticamente 1,6 por referencias del
capítulo C. El default LRFD de HFS-011 permanece explícitamente documentado.

## Evidencia y pruebas

Entorno realmente usado: Windows, Python 3.12.10, Pydantic 2.14.1,
pytest 9.1.1, openpyxl 3.1.5, entorno existente `.venv/hfs011`.
No se instalaron paquetes. Los [entornos antes](evidence/before/environment.json)
y [después](evidence/after/environment.json) contienen freeze, SHA, estado,
ejecutable y variables. Captura aislada con `PYTHONNOUSERSITE=1`,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONUTF8=1`, sin PYTHONPATH heredado.

| Suite separada | Antes | Después | Exit |
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
| HFS-017, misma suite final contra ambas fuentes | 35 pasan / 433 fallan | 468 pasan | 1 / 0 |

Las diez suites históricas se ejecutaron **antes de editar runtime**. La suite
HFS-017 final se ejecutó además contra una copia aislada del código base; sus
433 fallos esperados no son xfail ni una regresión ocultada. Registro íntegro:
[red](evidence/incidents/17-final-red.json),
[JUnit red](evidence/incidents/17-final-red.xml),
[verde](evidence/after/pytest-test_hfs017_design_method.json).
La reproducción final no reemplaza el [primer intento](evidence/incidents/17-red.txt)
de 440 casos (412 fallos, 28 aprobados).

Oráculos de la nueva suite, con entradas explícitas e independientes del cálculo
productivo: factores D2/E1/F1/G1/G2/H3; fluencia/rotura D2; E3 de un miembro
corto no esbelto; G2 W/canal con Cv1=1; G4 por cada dimensión resistente; H3-6
sin flexión con Tr/Tc>0,20. Fuentes/páginas en la matriz y encabezado del test.
Tolerancia de conversores 1e-12 relativa y 1e-12 absoluta en kN/kN·m para error
de representación de float; E3/H3 1e-12 relativa. Algunos controles de traza y
nominal simple son exactos; los `pytest.approx` sin parámetros usan sus valores
por defecto (1e-6 relativa, 1e-12 absoluta), suficientes para detectar el cambio
de método pero no acreditan tolerancia de diseño. Ninguna tolerancia entra en
la decisión productiva PASS/FAIL.

La parametrización inspecciona las clases de reglas para comprobar que ninguna
llamada directa elude el contrato; **no genera esperados normativos desde el
router**. Hay pruebas de demanda cero/activa, método corrupto, helpers I/H,
router y evaluadores, pares LRFD/ASD, entrada pública ASD rechazada, INCOMPLETE
en HSS no acreditado y CLI/memoria de tracción con demanda externa intacta.
Las 73 pruebas F-43 conservadas cubren también H1/H3 con momentos y ambos HSS.

Incidencias de desarrollo conservadas: primer verde de 440; ampliación a 468
con cuatro errores de fixture (nombre de clave G, longitudes obligatorias,
elección inicial bajo umbral H3), luego dos errores de lectura del envelope de
memoria CLI. Se corrigieron fixtures/lectura del contrato, no producción ni
expectativas históricas. Los logs `17-green1..5.txt` están en `incidents/`.
La primera comprobación de bytes contra blobs Git falló por CRLF del checkout;
se registran ahora hashes de ambos y normalización **solo** de finales de línea,
sin tocar archivos. Un intento de leer PDF por consola cp1252 falló por Unicode
y se repitió con `-X utf8`; un comando de lectura con sintaxis brace de bash
se corrigió para PowerShell. No se omitieron pruebas por infraestructura.

## Diferencias, cobertura e invariantes

La captura antes/después de los 12 ejemplos conserva el hash semántico
`d6d270c46877c9698d0c4ad0239f378403006fffeddc9f4a984354afae48c02c`:
**cero diferencias** en resistencias nominales/disponibles, demandas, DCR,
estados, obligaciones, fallos conocidos o trazas. Las 24 ejecuciones CLI
conservan sus códigos de salida y JSON normalizados, incluidas memorias.
El [comparador estricto](../../../scripts/compare_hfs017.py) solo permite añadir
la traza D2 esperada por método; en estos ejemplos no necesita esa excepción:
[cero cambios observados](evidence/comparison.json).

Las sondas dirigidas sí cambian deliberadamente: respuesta resistente bajo
método indebido → error; desconocido convertido con Ω → error. Tracción válida
mantiene capacidades y añade traza. La captura general sale **0**, porque
estos doce ejemplos no ejercen los escapes ni contienen la traza D2 añadida.

[Verificación de alcance](evidence/scope-verification.json): 424 archivos
protegidos contrastados contra HEAD (contenido idéntico, salvo representación
CRLF del checkout donde se indica); PDF, catálogo, ejemplos y pruebas previas
preservados. `flexure_calc`, `composite_calc`, engine, CLI, resultados,
acciones y las dos fuentes HFS-010 no cambiaron. En H/I, todos los cuerpos
de funciones/clases son AST idénticos tras retirar únicamente las llamadas
de guarda nuevas. En D/E/G/H calc, todos los métodos preexistentes ajenos a
conversión disponible son AST idénticos. No hubo cambios de ecuaciones AISC,
interacciones, selección de estados o ejes.

## Reproducción

Usar rutas nuevas para cada ejecución; las rutas aquí fueron las realmente
ejecutadas. No sobrescribir evidencia aceptada. La ejecución base utilizó el
mismo comando siguiente con `--out .venv/17b --work .venv/17bw`, referencia
`docs/audit/hfs015/evidence/after/engine-results.json` y sin la última suite.

```powershell
.\.venv\hfs011\Scripts\python.exe scripts/audit_hfs011.py --baseline .venv/17b/engine-results.json --out .venv/17a --work .venv/17aw --extra-suite tests/test_hfs016_catalog_integrity.py --extra-suite tests/test_hfs010_coverage.py --extra-suite tests/test_hfs012_flexure_selection.py --extra-suite tests/test_hfs013_directional_h3.py --extra-suite tests/test_hfs013_design_method.py --extra-suite tests/test_hfs014_summary_bundle.py --extra-suite tests/test_hfs015_precision_advice.py --extra-suite tests/test_hfs017_design_method.py
.\.venv\hfs011\Scripts\python.exe scripts/audit_hfs014_cli.py .venv/17bw .venv/17bc
.\.venv\hfs011\Scripts\python.exe scripts/audit_hfs014_cli.py .venv/17aw .venv/17ac
.\.venv\hfs011\Scripts\python.exe scripts/audit_hfs017_probes.py .venv/17bw .venv/17-probes2-before.json
.\.venv\hfs011\Scripts\python.exe scripts/audit_hfs017_probes.py . .venv/17-probes2-after.json
.\.venv\hfs011\Scripts\python.exe scripts/compare_hfs017.py .venv/17b/engine-results.json .venv/17a/engine-results.json .venv/17bc/cli-examples.json .venv/17ac/cli-examples.json .venv/17-comparison.json
git diff --check
```

Para reproducir la base posteriormente, extraer el SHA indicado en una carpeta
nueva mediante `git archive` y ejecutar allí el capturador anterior con el mismo
Python. Para el red final, preparar otra copia de esa base (src/examples/data),
añadir únicamente `tests/test_hfs017_design_method.py` de esta entrega y ejecutar
el comando/cwd registrado en `17-final-red.json`. Es un rechazo esperado de las
nuevas exigencias sobre código antiguo, exit 1, no una suite aceptable para uso.
La captura `copied_inputs.json` permite comprobar cada fuente y entrada.

## Riesgos y pendientes de revisión

- HFS-039 no implementada: flexión pública ASD y todo compuesto ASD bloqueados.
  Un helper nominal o F1 ASD aislado no habilita esos dominios.
- H1 tracción/etiquetas F-37, nominal E7 F-35, ángulos F-36, interacción/capacidades
  I F-18/20, cobertura F-01/31/33/34/38 y catálogo F-27 siguen pendientes.
- Los factores G2 se eligen con información actual de familia/geometría; W no
  prueba por sí sola fabricación laminada. No se acredita ese dominio completo.
- Modelos válidos no prueban origen de combinaciones, K/Cb, unidades externas ni
  compatibilidad real del análisis. Tampoco las guardas directas sustituyen la
  validación física completa de HFS-011.
- Erratas AISC y procedencia documental integral siguen F-28/HFS-030. La matriz
  distingue el PDF local de la consulta del índice oficial actualizado.
- Los factores parametrizados de helpers puros G/H son parámetros de bajo nivel;
  el llamador es responsable de su disposición/dominio. Los recorridos del
  motor usan sus factores existentes; no se crea una API pública de factores libres.
- Deserializadores cerrados necesitan la migración de metadatos D2 y errores.
  F-32 y rediseño de contratos públicos HFS-022/024 no se adelantan.

F-44/F-45 quedan corregidos funcionalmente para revisión con reproducción;
ningún defecto histórico pendiente se cierra por esta suite. Falta revisión
técnica independiente de la entrega y de las limitaciones de la matriz.
