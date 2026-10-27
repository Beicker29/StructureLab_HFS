# HFS-015 — Precisión, resultados y recomendaciones normativas

Entrega para revisión técnica, 2026-10-27. Base comprobada: **main**,
`dbd87cbd6874073750925125fb2db262f2af6f04`; sin cambios locales detectados al
comenzar. Alcance exclusivo **F-09/F-07**. No hay commit, push, rama ni PR.
No se implementan HFS-017/039 ni auditorías posteriores.

## Diagnóstico, reproducción y decisiones

**F-09 confirmado:** los seis grupos D/E/F/G/H/I decidían con una razón sin
redondear, pero publicaban `round(dcr,3)`; E/F/G/H/I redondeaban también demanda
y capacidad. `_build_dcr_trace` reconstruía un supuesto bruto desde demanda
publicada y una capacidad alternativa de memoria. Podía diferir de la razón
usada realmente, y sus unidades se inferían por cláusula.

Reproducción independiente D2-1: Fy=345 MPa, A=1000 mm², LRFD, capacidad
0,90×345×1000/1000 = **310,5 kN**. Demanda **310,53105 kN** implica
**DCR=1,0001**. La base publicaba `FAIL` y `dcr=1.0`; ahora publica `FAIL` y
`dcr=1.0001`, con display abreviado y etiqueta que conserva estado/valor original.
[Sonda inicial previa a editar runtime](evidence/incidents/initial-reproduction.json),
[sondas reproducibles base](evidence/probes/before.json) y
[después](evidence/probes/after.json).

**F-07 confirmado:** D1/E2 se expresaban como booleanos de admisibilidad y SI/NO
en CLI/memoria. Se comparaba la misma razón efectiva KL/r con 300/200. Esto
confundía recomendaciones con requisitos y confundía dos longitudes diferentes.
La base se reprodujo con tracción KL/r=299,999/300/300,001 y compresión
199,999/200/200,001. Ahora esos datos se conservan, pero D1 no inventa longitud
fabricada, radio mínimo principal ni excepción de rod desde KL/r.

## Fuente normativa y condiciones

Fuente directa: [ANSI/AISC 360-22 local](../../../a360-22w.pdf), Specification
del 1 de agosto de 2022, SHA-256
`25c4bf59b4c6fd00589e32a6ddac92cc9fd6be30dd5da07fc7c5f7fd475b2361`.
Se extrajeron y revisaron visualmente las páginas pertinentes; numeración PDF
1-based. Renderizados/extractos regenerables: `.venv/15norm`. No se duplica el
PDF ni se modifica evidencia histórica. [Identidad y límites de S22](../../normative/hfs002-sources.md).

| Referencia | Página impresa / PDF | Decisión y límite |
|---|---|---|
| A1, Specification | 16.1-1 / 69 | Commentary y User Notes no forman parte de la Specification; no convertir orientación en obligación resistente |
| D1, Specification y User Note | 16.1-32 / 100 | La disposición no fija máximo general de esbeltez en tracción. El aviso recomienda longitud fabricada/radio mínimo ≤300 y exceptúa rods; **no es KL/r** |
| E2, Specification y User Notes | 16.1-40 / 108 | Lc=KL se determina según C/Apéndice 7. El aviso recomienda Lc/r≤200 y, adicionalmente, esbeltez fabricada≤300; no son fallos resistentes automáticos |
| E5 introducción y condiciones (1)–(5), en particular (4) | 16.1-43/44 / 111–112 | La alternativa que permite despreciar excentricidad requiere, entre otras condiciones, Lc/r determinado para esa alternativa ≤200. No se reemplaza por el aviso general E2; si no se cumplen las condiciones, corresponde evaluar axial/flexión según H |
| D2-1 y factores D2(a) | 16.1-32 / 100 | Capacidad independiente 310,5 kN para el caso fronterizo; no se modifica la ecuación |

No se utilizaron transcripciones web de terceros como autoridad. La búsqueda
externa no sustituyó la lectura del PDF local. La reconciliación de erratas
sigue pendiente en F-28/HFS-030, como ya declara HFS-002. No se afirma haber
auditado íntegramente E5, C ni los dominios resistentes de los demás capítulos.

## Implementación mínima y DRY

1. **Propietario numérico:** `CheckResult.from_values` recibe demanda y capacidad
   originales, calcula la razón una vez y decide con `<=1.0`. Sin epsilon nuevo,
   sin Decimal ni redondeo intermedio. Los seis grupos de reglas usan esta misma
   función; sus ecuaciones/factores/evaluadores permanecen en sus propietarios.
2. **Representación:** `demand/capacity/dcr` son la única terna original.
   `display` deriva cadenas a tres decimales y `dcr_label` incluye estado/bruto.
   No se crean campos numéricos `*_raw` duplicados y editables.
3. **Unidades:** se declaran donde se construye cada resultado: kN, kN-m o ratio.
   Los fillers/llamadas legacy sin metadata tienen unidad desconocida explícita.
4. **Traza:** consume directamente el resultado, sin dividir valores publicados,
   buscar otra capacidad en memoria ni inferir unidad por cláusula. Las expresiones
   normativas existentes siguen en `calculations`.
5. **No finitos:** proyección única `finite_json_payload`: null con diagnóstico de
   ubicación/tipo; no muta valores de cálculo. Se aplica a CheckResult y memoria
   completa, con JSON estricto en el CLI. Razón indefinida tiene diagnóstico y
   no acredita PASS; no se fabrica capacidad cero.
6. **Recomendaciones:** una función de dominio `slenderness_recommendations`,
   consumida por ambas presentaciones. Los tres datos opcionales de
   `SlendernessAdviceBasis` son necesarios porque longitud no arriostrada y radios
   locales no acreditan longitud fabricada/radio mínimo principal ni condición rod.
   No intervienen en capacidades, router ni cobertura.

[Inventario DRY actualizado](../../architecture/dry-inventory.md). Se conservan
wrappers por capítulo para preparar memoria y unidad. No hay servicios genéricos,
segundo motor ni reorganización general del CLI. Los antiguos helpers privados
de inferencia/extracción quedan sin consumidores productivos; su presencia no
significa que la nueva traza o resumen los utilice.

### Auditoría de recorridos numéricos

| Productores/consumidores | Antes | Después / comprobación |
|---|---|---|
| D2 yielding/rupture | Demanda/capacidad originales; DCR publicado redondeado | Terna original y unidad kN; oráculo D2 y frontera |
| E3/E4/E5/E7 | `_result` redondeaba terna | Mismo cálculo previo; terna original kN |
| F2–F11 implementados | `_build_flexure_result` redondeaba terna | Mismos Mn/factores; terna original kN-m. No se habilita ASD público |
| G implementado | `_build_result` redondeaba terna | Mismas capacidades direccionales; terna original kN |
| H1/H3 | Interacciones con capacidades originales; salida redondeada | Se preservan capacidades F-43, pares direccionales e interacción original; unidad ratio o kN-m en torsión |
| I1/I2/I3/I4/I5 | Constructores redondeaban terna | Metadatos dimensionales por productor; originales conservados |
| I5 desde checks I2 | Recibía `res.capacity` ya redondeada | Recibe capacidad original; no cambia la ecuación de interacción |
| I4 agregado encased | Elegía entre capacidades de subchecks ya redondeadas | Compara y consume originales; no cambia la política de selección existente |
| Resumen HFS-014 | Ordenaba DCR publicado a tres decimales | Ordena el original publicado; empates reales exactos |
| Memoria/CLI | Traza reconstruida y posibles Infinity legacy | Traza directa, JSON estricto y diagnósticos de sentinelas no finitos |

La búsqueda de `round` en `codes` y evaluadores no encontró redondeos intermedios.
En reglas, los encontrados pertenecían a los constructores sustituidos. Los
cálculos H1/H3 y la función compartida F-43 no se modifican; se revisaron tanto
el recorrido estático como los oráculos LRFD/ASD ya existentes y los nuevos.

## Contrato y compatibilidad

[Contrato completo y migración JSON](../../contracts/hfs015-precision-advice.md).

- `CheckResult` publica ahora precisión original y agrega `unit`, `numeric_issue`
  y `display`. Los valores no finitos se proyectan a null con diagnóstico.
- Resumen **HFS-015-v2**: mantiene nombres `max_dcr_published/dcr_published`,
  cuyos números publicados ahora son originales. Empate visual no implica empate
  numérico; mantiene todos los empates exactos, todos los fallos y ámbito observado.
- Traza **HFS-015-raw-v1**: retira las reconstrucciones y sus campos obsoletos.
- Se conserva la clave externa `admissibility`, pero su contenido es
  **HFS-015-advice-v1**, sin booleano `admissible`, ni SI/NO ni decisión resistente.
  D1/E2 distinguen dentro/fuera de recomendación, desconocido y no aplicable.
- Para D1/E2 fabricado se añade el objeto opcional de declaraciones externas;
  ausencia permanece UNKNOWN. Una sección maciza/circular no se clasifica
  automáticamente como rod. Si falta un radio local, E2 conserva el máximo
  parcial observado y sus ejes, pero no declara el aviso plenamente evaluado.
- E5 se identifica como condición de alternativa, NOT_EVALUATED, sin desactivar
  su requisito ni calificar la implementación actual. No se resuelve F-18.
- F-29, F-32, HFS-012/013 y las obligaciones/estados HFS-010 se preservan. Los
  avisos no aparecen entre checks resistentes ni obtienen crédito de cobertura.

## Pruebas efectivamente ejecutadas

Windows; Python **3.12.10** en `.venv/hfs000/Scripts/python.exe`. Dependencias
principales: pytest 9.1.1, pydantic 2.14.1/pydantic_core 2.50.1, openpyxl 3.1.5.
Freeze, comandos, cwd, SHA, códigos de salida y advertencias:
[antes](evidence/before/environment.json), [después](evidence/after/environment.json).
Sin instalar ni actualizar dependencias. La lectura PDF utilizó el entorno
existente `.venv/Scripts/python.exe`, que ya tenía pypdf/pypdfium2.

| Suite independiente | Base | Final | Fallos / errores / omisiones ordinarias finales |
|---|---:|---:|---|
| Original | 68 métodos + 12 subpruebas | 68 métodos + 12 subpruebas | 0 / 0 / 0 |
| Caracterización HFS-000 | 11 aprobadas + 1 xfail F-09 | 12 aprobadas | 0 / 0 / 0 |
| HFS-011 | 665 | 665 | 0 / 0 / 0 |
| HFS-016 | 44 | 44 | 0 / 0 / 0 |
| HFS-010 | 57 | 57 | 0 / 0 / 0 |
| HFS-012 | 61 | 61 | 0 / 0 / 0 |
| HFS-013 direccional | 57 | 57 | 0 / 0 / 0 |
| HFS-013 F-43 | 73 | 73 | 0 / 0 / 0 |
| HFS-014 | 72 | 72 | 0 / 0 / 0 |
| HFS-015 | — | 84 | 0 / 0 / 0 |

Total final: **1193 aprobadas + 12 subpruebas, cero xfail/XPASS**. Cada suite
terminó con exit 0. JUnit cuenta 80 registros originales, no 80 métodos.
[Verificación de suites](evidence/after/verification.json).

La nueva suite incluye:

- 0,9999 / 1 / 1,0001 en fuerza, momento y razón; misma cifra abreviada con
  decisiones diferentes; originales distintos de redondeados y traza no reconstruida.
- Los seis productores D/E/F/G/H/I; oráculo numérico D2; FAIL conocido con INCOMPLETE;
  empates brutos frente a empates visuales; unidades explícitas opacas a la cláusula.
- Capacidad cero/negativa/no finita, NaN, overflow de razón y no finitos anidados;
  JSON estricto en todas las proyecciones y preservación de datos originales.
- H3 LRFD/ASD por eje/biaxial con cortante y torsión; H1 en tracción/compresión
  baja/alta, usando geometría de referencia independiente F-43. Las pruebas
  anteriores F-43 cubren además combinaciones con axial/torsión y nominales.
- D1 300 y E2 200, ambos lados e igualdad; esbeltez fabricada E2 300; excepción
  rod; dato desconocido; condición E5 diferenciada; avisos sin cambiar cobertura.
- Propagación I4/I5 con capacidades estipuladas independientemente; CLI con/sin
  memoria, valores originales, recomendaciones y contrato HFS-014.

Tolerancias de oráculos: identidades de almacenamiento/serialización y comparaciones
de estado son exactas; divisiones de referencia de resultados E/F/G/H/I usan
relativa/absoluta 1e-15; D2 absoluta 2e-16 en DCR; H1/H3 relativa/absoluta 1e-12
para aritmética binaria compuesta. No se aplican esas tolerancias al PASS/FAIL.

### Cambios justificados en tests previos

F-09 dio **XPASS(strict)** después de la corrección y antes de retirar la marca;
exit 1 esperado, una prueba y 11 deseleccionadas. Se investigó `FAIL`, DCR=1,0001
con capacidad 310,5 kN. [Log](evidence/incidents/xpass.json). Solo se retiró esa
marca; el assert de seguridad se conserva.

Dos métodos originales CLI exigían la presentación defectuosa D1/E2 como
admisibilidad. Se migran **solo esas expectativas** a los avisos documentados,
con fuente S22 anterior. No se reescriben capturas ni se debilitan asserts para
aprobar un defecto. Las expectativas previas están en el commit base y sus
pruebas se ejecutaron antes del cambio. Las 72 pruebas HFS-014 no se editaron.

Hubo una corrida inicial completa con 76 pruebas nuevas y otra final con 84 tras
agregar fronteras de longitud fabricada y regresiones I4/I5; ambas pasaron.
La ejecución dirigida final de 84 está en [targeted.json](evidence/incidents/targeted.json).
La evidencia promovida conserva la corrida completa final, sin duplicar todas
las corridas exploratorias exitosas.

## Comparación antes/después: motor y consumidores

Se ejecutaron los **12 ejemplos** antes y después y **24 procesos CLI por versión**:
12 entradas originales y 12 variantes que únicamente activan la memoria JSON.
La comparación distingue controles de regresión de validación normativa.
[Comparación detallada aceptada](evidence/comparison.json),
[CLI base](evidence/cli/before.json), [CLI posterior](evidence/cli/after.json).

Se conservan **65 checks**, sus nombres, cláusulas, orden, estados, cobertura,
known_failures y factores/nominales. 58 checks publican algún número con mayor
precisión. Once ejemplos conservan INCOMPLETE; doble ángulo conserva su error
previo. No se convierte cobertura pendiente en PASS.

| Ejemplo | DCR máximo publicado antes → después | Índices observados finales |
|---|---|---|
| channel | 0,745 → 0,7453914662487955 | 1 |
| circular_hss | 0,950 → 0,9495377581812909 | 6 |
| composite_beam | 1,000 → 1,0 | 2 |
| composite_encased | 0,593 → 0,593096438764825 | 5 |
| composite_filled_circular_hss | 2,490 → 2,4902049823291503 | 2 |
| composite_filled_rectangular_hss | 14,280 → 14,280338222293134 | 2 |
| double_angle | Mismo error previo | — |
| rectangular_hss | 2,367 → 2,3673952968865497 | 12 |
| single_angle | 0,087 → 0,08682675349342016 | 3 |
| solid_circular | 0,035 → 0,03492827908743906 | 0 |
| solid_rectangular | 0,053 → 0,053225401176784586 | 0 |
| w_shape | 0,892 → 0,892141599283337 | 0 y 2, empate real conservado |

El comparador exige identidad del resto de resultados y verifica cada cifra
publicada previa contra la original o su redondeo histórico. Comprueba el DCR
desde los números **originales** exclusivamente como identidad de contrato de
prueba; no lo reconstruye en producción. Contrasta CLI con motor, traza con
check original, unidades, estados, ranking y avisos. Registra cada diferencia
por ruta; no ignora globalmente todo `details`, `calculations` o coverage.

### Diferencias de propagación I4/I5

En ejemplos I5, las capacidades axiales consumidas ahora son originales:

| Caso | P disponible consumida antes → después, kN |
|---|---|
| Encased | 11471,003 → 11471,003420452487 |
| Filled circular | 312,443 → 312,44261545965537 |
| Filled rectangular | 18,692 → 18,692332252762498 |

Cambian los cocientes trazados Pu/P. En estos ejemplos la rama del método 2 y
su razón original no cambian; la diferencia visible de DCR es quitar el redondeo
final. El comparador exige la capacidad original del check I2 correspondiente.

En I4 encased, la capacidad consumida pasa de 742,815 a **742,8153599999999 kN**;
la razón original para 180 kN pasa de 0,24232143938934997 a
**0,24232132195004694**, conservando PASS. No cambia la fórmula del subcheck;
desaparece el redondeo entre productor y agregado. El comparador verifica cada
subcapacidad original y su máximo, y preserva la selección existente.

Las regresiones sintéticas adicionales demuestran por qué no exigir igualdad
numérica ciega en esos recorridos. **Son identidades de propagación, no validación
de las capacidades AISC estipuladas**:

| Prueba | Con capacidad intermedia redondeada | Con capacidad original |
|---|---|---|
| I4, demanda 1,00045; capacidades 1,00049 / 1,00041 / 0,99999 | DCR 1,00045, FAIL | 0,9999600195904007, PASS |
| I5 método 1, P=0,100049; Pc=1,00049; suma Mr/Mc=0,94999 | 1,0000145, FAIL | 0,99999, PASS |

Se preservan ecuaciones, condiciones y factores; lo corregido es el dato perdido
entre resultados. No se reivindica validación integral de I5/H1, ni cierre F-37.

## Reproducción, entorno e incidencias

Desde raíz, usar rutas **nuevas**, Git en PATH y el entorno fijado. El capturador
fija PYTHONNOUSERSITE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONUTF8=1 y retira
PYTHONPATH. Los comandos completos de pytest/cwd/stdout/stderr/exit y JUnit están
en `evidence/before` y `after`. No se eliminan directorios inaccesibles ni se
cambian permisos; permanecen los 31 avisos heredados de Git. Los fixtures y
procesos CLI se ejecutaron con escalación aprobada, sin omitir tests.

```powershell
$env:PATH = 'D:\Users\byomayusa\AppData\Local\GitHubDesktop\app-3.6.7\resources\app\git\cmd;' + $env:PATH
# Base: nueve suites, antes de modificar runtime; exit 0.
.\.venv\hfs000\Scripts\python.exe scripts/audit_hfs014.py --baseline docs/audit/hfs013/evidence/final/engine-results.json --out .venv/15b --work .venv/15bw
# Final: diez suites; cada pytest exit 0; capturador exit 1 por igualdad literal intencionalmente rota.
.\.venv\hfs000\Scripts\python.exe scripts/audit_hfs011.py --baseline .venv/15b/engine-results.json --out .venv/15af --work .venv/15awf --extra-suite tests/test_hfs016_catalog_integrity.py --extra-suite tests/test_hfs010_coverage.py --extra-suite tests/test_hfs012_flexure_selection.py --extra-suite tests/test_hfs013_directional_h3.py --extra-suite tests/test_hfs013_design_method.py --extra-suite tests/test_hfs014_summary_bundle.py --extra-suite tests/test_hfs015_precision_advice.py
# Capturas CLI reales: exit 0 del capturador; los errores de ejemplo conservan exit 1.
.\.venv\hfs000\Scripts\python.exe scripts/audit_hfs014_cli.py .venv/15bw .venv/15bc
.\.venv\hfs000\Scripts\python.exe scripts/audit_hfs014_cli.py .venv/15aw1 .venv/15ac1
# Comparación específica de la migración; exit 0.
.\.venv\hfs000\Scripts\python.exe scripts/compare_hfs015.py --engine-before .venv/15b/engine-results.json --engine-after .venv/15af/engine-results.json --cli-before .venv/15bc/cli-examples.json --cli-after .venv/15ac1/cli-examples.json --out .venv/15compare-final.json
# Sondas reproducibles en las copias, ambas exit 0.
.\.venv\hfs000\Scripts\python.exe scripts/probe_hfs015.py .venv/15bw .venv/15probe-b.json
.\.venv\hfs000\Scripts\python.exe scripts/probe_hfs015.py .venv/15aw1 .venv/15probe-a.json
```

`.venv/15aw1` procede de la primera corrida completa (`--out .venv/15a1 --work
.venv/15aw1`, mismo comando de diez suites). Su runtime es **idéntico por hash**
al de la corrida final, y los JSON completos de motor se repitieron idénticos.
Solo se añadieron ocho tests antes de la captura final. No se afirma haber
repetido el CLI contra otra copia: [procedencia y hashes](evidence/reused.json).

El capturador heredado devuelve **exit 1 / examples_identical=false** porque
exige igualdad literal anterior. Se preserva esa evidencia; no se lo modifica
para esconder la transición. La aceptación de diferencias está en el comparador
HFS-015, que devuelve **exit 0**, con 12 ejemplos y 24 escenarios aceptados.

Incidencias de preparación: el entorno hfs000 no tenía pypdf; se usó el entorno
local existente con esas librerías. Una extracción a consola falló por cp1252;
se repitió con PYTHONUTF8=1. La primera sonda intentó importar un nombre privado
inexistente y se corrigió al símbolo real antes de guardar evidencia. No fueron
errores de cálculo ni xfail. Una edición documental por pipeline perdió acentos;
se corrigió con escritura UTF-8 antes de entregar. No se instalaron dependencias
ni se tocaron ACL para ocultar incidencias. Las salidas no guardadas como archivo
se describen aquí; no se presentan logs crudos inventados.

## Alcance verificado y riesgos residuales

[Inventario completo](changed-files.md), [verificación Git/AST](evidence/scope-verification.json)
y [manifiesto de entrega](evidence/SHA256SUMS.json). La comprobación protege
499 archivos versionados, incluyendo fórmulas puras, catálogo, PDFs, ejemplos,
router, cobertura y capturas previas. En los seis módulos de reglas, tras
normalizar solo construcción/decisión de resultados y keywords de unidad,
el AST permanece idéntico: nominales, evaluadores, factores y trazas resistentes
no cambian. Los hashes de entradas coinciden con la ejecución final.

No se cambia `engine.py`, `results_model.py`, `domain/coverage*.py`, el enrutador,
las ecuaciones `codes/*`, los evaluadores ni el catálogo. Las declaraciones
opcionales de recomendaciones no cambian los resultados del motor, como verifica
una comparación exacta. F-31, F-32, F-37 y las carencias normativas previas siguen
abiertas. HFS-010 no obtiene acreditación artificial por precisión o avisos.

Riesgos y límites para revisión:

1. El contrato JSON cambia: consumidores deben usar datos originales y acompañar
   el display de su estado. Un cliente que ignore la migración puede seguir
   presentando mal un límite, aunque el motor ya exponga la información correcta.
2. `float` mantiene límites de precisión binaria. No se añade tolerancia de
   cumplimiento; no se prueba exhaustivamente todo rango extremo de entrada.
3. Los no finitos en variables auxiliares requieren interpretación por dominio.
   Se conservan diagnósticos, sin validar automáticamente su uso en cada ecuación.
   El round-trip de resultados indefinidos pertenece a HFS-022.
4. Longitud fabricada, radio mínimo y condición rod son declaraciones externas;
   positividad/finitud no acreditan que describan correctamente la pieza real.
   Sin esos datos la recomendación pertinente queda UNKNOWN.
5. E5 y estabilidad principal/torsional permanecen fuera de validación integral.
   La advertencia no sustituye las condiciones obligatorias ni la cobertura.
6. Los casos I4/I5 sintéticos demuestran propagación, no exactitud normativa de
   sus resistencias; F-37 y auditoría I siguen pendientes. F-43 y bloqueos ASD
   permanecen vigentes; no se adelantan HFS-017/039.

Cierre funcional F-09/F-07 demostrado **para revisión técnica del usuario**.
No se declara certificación AISC integral, puerta G1 ni autorización para otro
hito. Cambios locales listos para que el usuario revise y publique.
