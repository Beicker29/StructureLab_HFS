# HFS-012 — Selección F2 con esbeltez acreditada

Fecha: 2026-10-27, America/Bogota. **Implementación y pruebas entregadas para
revisión técnica**, sin declarar validación AISC exhaustiva. Base: `main`,
`90724b2efa8333ab59cd7c863d1052f0d0d1bbfd`, árbol inicialmente limpio.
Se trabajó directamente en `main`, sin rama nueva, commit, PR, push ni cambios
de historial. Solo HFS-012; no se inicia HFS-013/014 ni web.

## Diagnóstico y decisión

`_w_or_channel_major_flexure_selection` convertía razones ausentes/incorrectas
a cero y devolvía F2 cuando cualquiera era cero. HFS-010 impedía PASS global,
pero seguían publicándose capacidades F2 sin compacidad demostrada. Además,
para canal se reutilizaba `bf/(2tf)`, que no es su razón B4.1 de ala.

Se conserva el clasificador y registro existentes, eliminando ese fallback.
Una ausencia no se convierte en compacto ni en NOT_APPLICABLE. La decisión
separa datos declarados, derivación explícita, desconocimiento e inconsistencia.
No se añade un clasificador paralelo, una capa de servicios ni una nueva
formulación de resistencia. Cambiar solo el estado global sería insuficiente:
el objetivo es impedir también el cálculo F2 no justificado.

## Base normativa y alcance de la interpretación

Fuente primaria local: `a360-22w.pdf`, ANSI/AISC 360-22, **Specification for
Structural Steel Buildings, August 1, 2022**, SHA-256
`25c4bf59b4c6fd00589e32a6ddac92cc9fd6be30dd5da07fc7c5f7fd475b2361`.
Se revisaron los textos y las tablas B4.1b visualmente. Páginas PDF indicadas
desde 1, con numeración impresa entre paréntesis.

| Fuente Specification | Condición utilizada |
|---|---|
| B4.1, PDF 87–88 (16.1-19/20) | Ala unida continuamente al alma; compacto si λ≤λp, no compacto si λp<λ≤λr, esbelto si λ>λr |
| B4.1a(a)/(b), PDF 88 (16.1-20) | I: b=bf/2. Canal: b=ancho completo del ala, no vuelo medido desde la cara del alma ni bf/2 |
| B4.1b(a), PDF 88 (16.1-20); espesor de ala variable PDF 92 (16.1-24) | h de laminado descuenta acuerdos en ambas alas; tf de ala inclinada es el nominal en el punto medio normativo. No inferir h=d−2tf sin radios |
| Tabla B4.1b casos 10 y 15, PDF 90–91 (16.1-22/23) | Ala de I laminada/canal: λp=0,38√(E/Fy), λr=1,00√(E/Fy); alma de I doblemente simétrica/canal: 3,76√(E/Fy) y 5,70√(E/Fy) |
| F2, PDF 121–122 (16.1-53/54) | I doblemente simétrica o canal, flexión mayor, ala y alma compactas; fluencia y pandeo lateral torsional según sus condiciones |
| F3, PDF 123–124 (16.1-55/56) | I doblemente simétrica, alma compacta, ala no compacta/esbelta. No habilita canales |
| F4, PDF 124–128 (16.1-56/60) | I doblemente simétrica con alma no compacta; dominio adicional de I monosimétrica centrada no se incorpora mediante el tipo W |
| F5, PDF 128–129 (16.1-60/61) | I con alma esbelta, respetando simetría/unión a la mitad del ancho de las alas; no habilita canales |
| F6 y tabla caso 13, PDF 129–130 (16.1-61/62), 90 (16.1-22) | Flexión menor I/canal; no cubre Mux ni la interacción biaxial; también distingue medio ancho I/ancho completo canal |

Las User Notes de F2/F3 sobre perfiles usuales no sustituyen datos faltantes.
La User Note de F4 que permite el uso conservador de F5 tampoco valida por sí
sola `evaluate_f4_conservative` (F-19). No se usa Commentary como obligación.
La clasificación aplicada es la de **I laminada doblemente simétrica declarada
como W**, y canal; no se extiende a I armada (caso 11), I monosimétrica (caso 16)
o ala no unida continuamente. El modelo actual no certifica fabricación,
simetría ni procedencia de todos esos datos: esas condiciones conservan sus
pendientes HFS-010. Selección por compacidad no equivale a acreditar F1, toda
la resistencia F2 ni cumplimiento global.

Se verificó la existencia de erratas en la [página oficial AISC](https://www.aisc.org/aisc/publications/revisions-and-errata/),
que lista enero de 2025 y septiembre de 2026. No se afirma reconciliación de
esas erratas con el PDF local; F-28/HFS-030 permanece pendiente. Esta corrección
identifica expresamente su base S22 local, igual que la matriz independiente.

## Comportamiento y compatibilidad

| Datos del elemento | Decisión HFS-012 |
|---|---|
| Razón explícita, finita y >0 | Clasificar con el único clasificador existente; verificar contradicción de clase si también hay dimensiones |
| Razón ausente, dimensiones B4.1 explícitas positivas | Derivar localmente bf/(2tf) en W, bf/tf en canal, h/tw para alma. No modificar Section ni completar el catálogo |
| Razón ausente, dimensión necesaria desconocida | Error de selección `MISSING`; cero checks F2 y cobertura pendiente |
| Razón/dimensión inválida | No reemplazarla por una derivación; HFS-011 rechaza inválidos al entrar al motor; llamada directa al router obtiene `INVALID` |
| Razón declarada y geometría dan clases distintas | Bloquear con `INCONSISTENT`; no elegir la fuente más favorable ni aplicar tolerancia de clasificación |
| bf≤tw o h>d−2tf, cuando están disponibles | Bloquear por inconsistencia física |
| Canal no compacto/esbelto | `UNSUPPORTED`; no seleccionar F3/F4/F5 |

En canal, `b_t_ratio` declara el ancho completo del ala con su espesor B4.1;
si falta, se exige bf/tf. `bf_2tf_ratio` solo no basta. No se reutilizan b/t
de otro elemento ni el espesor t genérico como tf. La validez semántica de
estas declaraciones sigue siendo responsabilidad de quien suministra los datos;
`SectionSource` identifica una fila, no certifica ingeniería. «Derivable» aquí
significa dimensiones explícitas con significado B4.1, finitas, positivas y
sin contradicción de clase/física detectada, no reconstrucción aproximada ni
validación integral de propiedades. Si el significado de h/tf no es conocido,
deben permanecer ausentes. Un importador que etiquete mal esos datos conserva
un riesgo de catálogo pendiente HFS-040.

Si razones y dimensiones tienen diferencias por redondeo pero producen la misma
clase, prevalece la razón explícita. No se añade epsilon a λp/λr. Esta decisión
evita invalidar automáticamente razones tabuladas por redondeo dimensional,
pero **no certifica igualdad geométrica completa** dentro de una misma clase.
También se rechaza E/Fy fuera del rango finito positivo aunque sus operandos
sean individualmente finitos.

`ProfileRouter.get_rules(case, section)` conserva su interfaz estricta y lanza
el error ante ausencia o dominio mayor no soportado, incluso con Muy activo.
Un tercer argumento opcional recoge errores de selección/propiedades de las
reglas F de W/canal. Lo utiliza el motor para seguir con verificaciones que
sí se pueden ejecutar. No se introduce estado mutable compartido en el router.
Otros errores de catálogo, validación y routing conservan su política previa;
esto no convierte todo error del motor en una evaluación parcial.

Las razones derivadas sirven a la **selección**; no se inyectan en los
evaluadores F3–F6 ni se enriquecen modelos. Si una rama seleccionada exige un
campo explícito que falta para su evaluación, queda pendiente con el error de
propiedad correspondiente. Sus capacidades nunca se fabrican por default.

En CLI, un caso con esbeltez desconocida puede pasar de excepción/exit 1 a
resultado INCOMPLETE/exit 0. Es éxito de ejecución con cobertura insuficiente,
no cumplimiento resistente. Se prueba la igualdad de cobertura entre stdout
y el JSON detallado. No se cambian opciones, formato de errores ni códigos
de salida del CLI; se usa el contrato común existente.

## Integración con HFS-010 y F-31

`build_coverage_plan` se ejecuta antes del router y **no se modifica**. El
diagnóstico se añade a `coverage.evaluation_errors` y a la razón de la obligación
ya existente `N11.conditions.Mux` o `Muy`. No crea requisitos desde las reglas,
no elimina obligaciones y no cambia UNKNOWN/PENDING por NOT_APPLICABLE.
Los errores bloquean `coverage.complete`; las resistencias F continúan sin
acreditación completa. Los FAIL conocidos de checks menores se preservan.

Se prueba Mux+Muy con alma desconocida: desaparece F2, F6 sigue ejecutándose
y se mantienen Mux e interacción pendientes. Se prueba también falta de ala
con cortante independiente. En canal fuera de F2, la llamada estricta ya no
silencia la carencia de Mux por existir F6, y el motor conserva esa carencia.
**F-31 no se cierra:** no hay nueva resistencia mayor para ese dominio, no se
valida F6 de canales ni la interacción. El evaluador F6 aún utiliza la razón
legacy `bf_2tf_ratio`; su revisión por ancho normativo queda visible para
HFS-032. Los checks F6 conservados son resultados parciales no acreditados.

## Pruebas ejecutadas y evidencia

Python **3.12.10**, Windows, ejecutable `.venv/hfs000/Scripts/python.exe`.
pytest **9.1.1**, pydantic **2.14.1**, pydantic_core **2.50.1**, openpyxl **3.1.5**.
Freeze completo, comandos, cwd, Git y variables en
[entorno final](evidence/after/environment.json). Sin instalaciones ni
actualizaciones de dependencias. El entorno histórico `.venv/hfs011` citado
en informes previos no existe aquí: el primer intento no arrancó; se utilizó
el entorno HFS-000 disponible con las versiones registradas.

Se fijaron PYTHONNOUSERSITE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONUTF8=1,
se retiró PYTHONPATH heredado y se deshabilitó cacheprovider. Las pruebas se
ejecutaron sobre copias aisladas verificadas por hash, no sobre fixtures
históricas con permisos alterados.

| Suite separada | Base limpia | Final | Fallos/errores finales | Exit final |
|---|---|---|---|---|
| Original | 68 métodos + 12 subpruebas | 68 métodos + 12 subpruebas | 0/0 | 0 |
| Caracterización HFS-000 | 9 aprobadas, 3 xfail | 9 aprobadas, 3 xfail | 0/0 | 0 |
| HFS-011 | 665 aprobadas | 665 aprobadas | 0/0 | 0 |
| HFS-016 | 44 aprobadas | 44 aprobadas | 0/0 | 0 |
| HFS-010 | 57 aprobadas | 57 aprobadas | 0/0 | 0 |
| HFS-012 | No existía | 61 aprobadas | 0/0 | 0 |

Total final: **904 pruebas + 12 subpruebas aprobadas**, **3 xfail**, sin XPASS
ni omisiones ordinarias. Los xfail estrictos siguen siendo F-05, F-09 y F-29;
no se ocultan errores de infraestructura bajo xfail. Ver
[base](evidence/before/verification.json) y [verificación final](evidence/after/verification.json).

Los esperados nuevos se enumeran desde los dominios F2–F5: E/Fy=625,
√625=25, límites independientes **9,5/25** para ala y **94/142,5** para alma.
Se prueban igualdad y vecinos `nextafter`, W compacto/F3/F4/F5, ausencia de
una/ambas razones, derivación, no finitos/cero/negativos, discrepancia de clase,
inconsistencia geométrica, ambos ejes, canal compacto y fuera de F2, falta de
datos de resistencia, F-03 y F-31. El esperado de fluencia F2-1 es
0,90×320×500000/10⁶=**144 kN·m**, tolerancia absoluta 10⁻⁹ kN·m (solo aritmética).
No se generan esperados con el selector ni se presenta el snapshot como
validación independiente de pandeo lateral o de F3–F6.

Incidencias preservadas en [manifiesto](evidence/manifest.json):

- Primera captura en sandbox: original aprobada; 1/5/3/2 errores de acceso en
  caracterización/HFS-011/HFS-016/HFS-010. Repetición fuera del sandbox en rutas
  nuevas: todas aprobadas. Sin limpieza ni cambios ACL.
- Primera corrida dirigida: 14 fallos y 54 aprobadas. Doce correspondían a
  esperar error de dominio donde el repositorio ya rechaza por Pydantic; uno
  mezclaba alias Zx/zx en una fixture nueva; otro era la fixture histórica F3–F5
  con dimensiones incompatibles con sus razones. Se corrigieron esas fixtures/
  expectativas, sin relajar validación ni modificar esperados de ramas.
- Primera captura posterior: 67 métodos + 12 subpruebas originales aprobados,
  un fallo por la expectativa CLI de excepción. Se sustituyó por aserciones
  de INCOMPLETE, cero checks y diagnóstico Mux, tras confirmar la transición.
  Los tests F-03 previos se fortalecieron: retirar también dimensiones evita
  confundir ausencia derivable con desconocimiento; ahora exigen ausencia F2.

## Diferencias de selección y resultados

Se ejecutaron los **12 archivos de ejemplos** con el capturador y las pruebas
smoke/CLI de la suite original. La captura por motor compara **todos los checks,
trazas, errores y cobertura**: igualdad exacta antes/después, SHA canónico
`584c52add0f13a63f0d43ffd1da07b410f28ce8bb93e03737f88af991da68162`.
Evidencia: [comparación](evidence/after/comparison.json); contenido idéntico
recuperable en [captura HFS-010](../hfs010/evidence/after/engine-results.json).
No se duplica ese archivo grande en Git. Los smoke tests ejecutan los CLI;
no se afirma comparación byte a byte de archivos CLI con timestamps.

Las 13 sondas sintéticas de [probes.py](probes.py) se ejecutan con los mismos
inputs contra la copia base y la final:

| Caso | Antes | Después |
|---|---|---|
| W compacto / derivable, canal compacto | F2 | F2; checks/trazas idénticos |
| W ala no compacta / alma no compacta / alma esbelta | F3 / F4 / F5 | Mismas ramas y checks/trazas idénticos |
| Falta ala, alma o ambas, no derivables | F2-1 y F2-2 = 144 kN·m cada uno | Ningún check F2; diagnóstico y pendientes |
| Falta alma con Mux+Muy | F2 y F6 | Solo F6, 43,2 kN·m; sus FAIL y trazas idénticos |
| Canal b/t=12, bf/(2tf)=6 | F2 indebidamente | Bloqueado; no F3/F4/F5 |
| Canal con alma no compacta y ambos momentos | Solo F6, sin error de selección | Solo F6, diagnóstico explícito de mayor no soportada; INCOMPLETE |
| W razón compacta pero dimensiones implican ala esbelta | F2 | Bloqueado por inconsistencia |

En las 13 sondas, todos los checks retenidos son exactamente iguales al
original; no hay una capacidad sustituta cero ni un resultado inventado.
Todos los casos eran y siguen siendo INCOMPLETE por HFS-010. Resultados completos
en [antes](evidence/probes-before.json) y [después](evidence/probes-after.json).
Son sondas de selección y regresión; sus secciones sintéticas no constituyen
un catálogo de perfiles reales verificados.

## Reproducción

Usar rutas nuevas. Añadir el Git real a PATH si no está disponible (en esta
sesión, GitHubDesktop/app-3.6.7/resources/app/git/cmd/git.exe).

```powershell
.\.venv\hfs000\Scripts\python.exe scripts/audit_hfs011.py --baseline docs/audit/hfs010/evidence/after/engine-results.json --out .venv/hfs012-review --work .venv/hfs012-review-work --extra-suite tests/test_hfs016_catalog_integrity.py --extra-suite tests/test_hfs010_coverage.py --extra-suite tests/test_hfs012_flexure_selection.py
.\.venv\hfs000\Scripts\python.exe docs/audit/hfs012/probes.py --root . --out .venv/hfs012-review-probes.json
git diff --check
git diff HEAD -- src/steel_design/codes src/steel_design/domain/rules src/steel_design/models.py src/steel_design/results_model.py src/steel_design/domain/coverage.py src/steel_design/sections data/sections.xlsx
```

Para reproducir el antes, usar una copia del SHA base. En esta sesión se
preservó `.venv/hfs012-before-work` antes de editar y se repitieron allí las
suites usando una copia sin cambios de los capturadores. No se hace checkout
ni se sustituye el árbol de trabajo del usuario. El manifiesto conserva rutas,
hashes y comandos reales de ambas capturas; la tabla anterior no se infiere
de ejecuciones previas a HFS-012.

## Archivos y confirmación de alcance

Inventario completo, incluidas capturas nuevas: [changed-files.json](changed-files.json).

| Archivo/grupo | Cambio |
|---|---|
| `src/steel_design/domain/routing/profile_router.py` | Resolución de razones y selección F2–F5, bloqueo de canales, colección opcional de errores F |
| `src/steel_design/engine.py` | Solicita diagnósticos y los entrega a cobertura |
| `src/steel_design/domain/coverage_evidence.py` | Anota errores sobre obligaciones previas sin recalcular aplicabilidad |
| `tests/test_hfs012_flexure_selection.py` | 61 pruebas nuevas |
| `tests/test_chapter_f_rules.py` | Geometría sintética consistente, mismas expectativas F3/F4/F5 |
| `tests/test_engine_cli_integration.py` | Transición de error a INCOMPLETE y paridad JSON |
| `tests/test_hfs000_characterization.py`, `tests/test_hfs010_coverage.py` | Fortalecimiento F-03, preservación F-31 |
| `docs/ROADMAP.md`, `docs/audit/tracking.md`, `docs/architecture/dry-inventory.md`, `CONTRIBUTING.md` | Entrega, pendientes, DRY y reproducción |
| `docs/audit/hfs012/` | Este informe, sondas, evidencia seleccionada, manifiesto, inventario y comprobación Git |

[final-checks.json](final-checks.json) registra rama/SHA, diff y hashes de los
archivos protegidos. **Las ecuaciones de resistencia, factores LRFD/ASD,
reglas evaluadoras, catálogo, modelos públicos y plan independiente HFS-010
permanecen idénticos a HEAD.** Los tres archivos runtime cambiados son los
indicados arriba; el motor sí cambia en selección y comunicación de pendientes,
como requiere HFS-012. Sin cambios de `run.py`, dependencias, PDFs ni históricos.
Git sigue notificando los directorios inaccesibles ya inventariados en HFS-000;
se preservan sin abrirlos, eliminarlos ni cambiar sus permisos.

## Riesgos residuales y revisión requerida

1. Revisar ingenierilmente el alcance declarado W/canal y el significado de
   h/tf/b/t en fuentes de catálogo. La validación física implementada es
   parcial; la coincidencia de clase no certifica todas las propiedades.
2. Revisar F-31/F6 canal y dominios mayores no soportados; F-19 y resistencias
   F2–F6 completas siguen HFS-032. Llamar directamente a una regla/evaluador
   evita el router: HFS-012 garantiza el flujo común del motor y la selección,
   no convierte las funciones de bajo nivel en un verificador completo.
3. Los errores ajenos a esta selección pueden todavía interrumpir la ejecución
   (por ejemplo E7 sin datos en compresión). No se promete recuperación de
   cualquier error ni se amplía aquí la arquitectura de ejecución parcial.
4. F-01/06/05/09/29, erratas F-28 y las demás obligaciones pendientes conservan
   su seguimiento. No se declara G1 completada ni aprobación normativa por
   el número de pruebas aprobadas.

Quedan para revisión humana las decisiones anteriores y la transición CLI.
Los cambios permanecen locales, listos para que el usuario decida commit/push.
