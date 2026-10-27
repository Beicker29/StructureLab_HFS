# HFS-010 — Cobertura normativa y estados de resultado

Fecha: 2026-10-27. Base inicial limpia: `main`,
`a6f7ede7172dc9ef2beb9829157f0af6d14b3d82` (incluye la fusión HFS-016).
Rama de trabajo: `hfs-010-coverage-gate`. Alcance exclusivo HFS-010.
El usuario declaró HFS-000/001/002/011/016 concluidas en sus respectivos alcances.
Durante la entrega sustituyó la instrucción de no fusionar por autorización
expresa de **subir y fusionar en main, con revisión técnica posterior**.
La publicación no equivale a aprobación de ingeniería ni autoriza otra tarea.

## Diagnóstico y decisión

El motor anterior comenzaba en PASS y solo buscaba FAIL entre las reglas que el
router seleccionaba. No existía comparación independiente contra obligaciones.
Cero checks, interacción omitida o cuantía presentada sin resistencia de momento
podían terminar en PASS. Se revisaron AGENTS, CONTRIBUTING, roadmap, ADR-001/002/003,
inventario DRY, matriz/contraste/propuesta HFS-002 y evidencias HFS-000/011/016.

Se conserva motor y router. `domain/coverage.py` construye un plan desde las
entradas antes del routing, sin importar reglas, predicados ni salidas. La matriz
[HFS-002](../../normative/hfs002-applicability.md) sigue siendo la única fuente
documental de requisitos; el código es su proyección acotada, no otra matriz
normativa editable. SHA-256 de la matriz leída:
`0d88a56ad831b7eae32ea185b589d439d8427ed91b83f251e32ca06d647061a9`.

`domain/coverage_evidence.py` contrasta ejecuciones concretas con ese plan. Se
separan referencias a checks ejecutados de checks acreditados: igual etiqueta,
prefijo o cantidad no demuestra equivalencia. N04 tiene dos obligaciones;
N17 separa ala/alma y ejes; las condiciones desconocidas permanecen pendientes.
Las alternativas H1/H2, G2, I4 e I5 se registran como rutas condicionadas, sin
exigir simultáneamente todas ni escoger una por lo que decidió el router.

`results_model.py` agrega cobertura y resistencia. Introduce `AnalysisStatus`
con INCOMPLETE, preserva `CheckStatus` PASS/FAIL y publica `known_failures`.
No se crean checks ficticios. El adaptador CLI serializa el mismo registro y
propaga INCOMPLETE de casos a lotes no vacíos mediante el agregador común.
El defecto del lote vacío permanece F-29/HFS-014 por restricción de alcance.

Se descartó habilitar PASS para todas las familias por su etiqueta o por ejecutar
las reglas registradas: HFS-002 no acredita ese dominio y faltan condiciones.
El subconjunto completo inicial es tracción axial concéntrica de macizos custom
ordinarios con evidencia externa explícita y ambas resistencias D2 evaluadas.
No se habilitan nuevas familias/métodos, capacidades ni fórmulas. Compresión,
flexión, cortante, torsión, interacción y restantes familias conservan sus
cálculos disponibles, sin acreditación global cuando faltan condiciones/validación.

Contrato, defaults, campos, condiciones y migración:
[hfs010-coverage.md](../../contracts/hfs010-coverage.md).

## Fuente y evidencia independiente del dominio completo

S22 local `a360-22w.pdf`, SHA-256
`25c4bf59b4c6fd00589e32a6ddac92cc9fd6be30dd5da07fc7c5f7fd475b2361`,
PDF 100–101, impresas 16.1-32/33: D2 requiere fluencia bruta y rotura efectiva;
D3 define Ae=An·U. Lectura directa con pypdf del entorno existente; no se modifica
el PDF. El primer intento de imprimir texto encontró UnicodeEncodeError en
cp1252; se repitió con PYTHONUTF8=1. Ninguna prueba se omitió por ello.

Oráculo independiente estipulado: Ag=1000 mm², An=800 mm², U=0,8, Fy=345 MPa,
Fu=450 MPa; LRFD: 310,5/216 kN; ASD: 345/1,67 y 144 kN. Cargas de 50, 220 y
350 kN cruzan ambos límites. Otra prueba usa Ag=π·20² para macizo circular.
Tolerancias: absoluta 1e-9 kN y relativa 1e-12 para aritmética float simple;
no cambian decisiones de diseño y las cargas no se sitúan sobre fronteras.
No se llama al cálculo productivo para generar esperados. Esto verifica este
dominio D2 y la puerta de cobertura, no todo D3, conexiones o AISC.

El [índice oficial de erratas](https://www.aisc.org/aisc/publications/revisions-and-errata/)
consultado el 2026-10-27 sigue enumerando enero de 2025 y septiembre de 2026.
No se reconciliaron esas entregas con el PDF local; F-28/HFS-030 permanece abierto
y aparece en la cobertura. No se usaron transcripciones de terceros como autoridad.

## Reproducciones críticas y cambios de estado

[Sondas previas](evidence/probes-before.json),
[posteriores](evidence/probes-after.json), [programa](probes.py).
Las 14 ejecuciones incluyen ambos tamaños de momento de los tres roles compuestos.
Los checks completos conservan sus valores/trazas antes y después; solo se añade
la cobertura y cambia el global.

| Hallazgo | Antes | Después y motivo |
|---|---|---|
| F-01 W, Pu+Mux | PASS sin H | INCOMPLETE: N29 pendiente |
| F-02 cargas cero | PASS sin checks | INCOMPLETE: alcance resistente vacío |
| F-03 sin esbelteces | PASS vía F2 | INCOMPLETE: N02/F1 sin determinar; no se corrige selector |
| F-31 canal Mux+Muy | PASS con F6 menor | INCOMPLETE: Mux pendiente, sin crédito por Muy |
| F-33 biaxial Pu=0 | PASS sin interacción | INCOMPLETE: N29; N42 para compuestos |
| F-34 tres roles, Mx=1 y 1 000 000 | PASS con cuantía/transferencia | INCOMPLETE: N39/N40/N43 sin resistencia M |
| F-35 E7 en W esbelta sintética | PASS con E7 no acreditado | INCOMPLETE: N10, sin cambiar Q/Fn/Ae |
| F-36 ángulo E5 | PASS sin condiciones/ramas completas | INCOMPLETE: N08 pendiente |
| F-06 HSS, T y cortante | FAIL global | INCOMPLETE por N30; FAIL de checks conservados |

F-02 se corrige. Los restantes hallazgos quedan **mitigados por bloqueo**, con
su reparación normativa pendiente. No se declara corregida E7, E5, H3, F2 ni la
implementación de interacción ausente. Los perfiles sintéticos son sondas de
software, no secciones físicas acreditadas.

## Regresión de los 12 ejemplos

Comparación exacta de checks completos, incluidas capacidades, demandas, DCR,
estados, clasificaciones y memorias: **sin diferencias**. El error de 2L también
se conserva exactamente. No se exige igualdad del JSON nuevo completo.

| Archivo en examples/ | Antes | Después | FAIL conocidos conservados |
|---|---|---|---|
| channel_case.json | PASS | INCOMPLETE | 0 |
| circular_hss_case.json | PASS | INCOMPLETE | 0 |
| composite_beam_case.json | PASS | INCOMPLETE | 0 |
| composite_encased_case.json | PASS | INCOMPLETE | 0 |
| composite_filled_circular_hss_case.json | FAIL | INCOMPLETE | 1 |
| composite_filled_rectangular_hss_case.json | FAIL | INCOMPLETE | 2 |
| double_angle_case.json | ERROR | Mismo ERROR | — |
| rectangular_hss_case.json | FAIL | INCOMPLETE | 3 |
| single_angle_case.json | PASS | INCOMPLETE | 0 |
| solid_circular_case.json | PASS | INCOMPLETE | 0 |
| solid_rectangular_case.json | PASS | INCOMPLETE | 0 |
| w_shape_case.json | PASS | INCOMPLETE | 0 |

Razones por obligación/caso en [coverage-transition.json](evidence/after/coverage-transition.json).
Ninguno de los JSON históricos incluye las nuevas declaraciones externas; además,
los ejemplos macizos incluyen demandas fuera del subconjunto de tensión pura.
No se editaron ejemplos para conseguir PASS. Ocho PASS y tres FAIL pasan a
INCOMPLETE; un error permanece error. Se preservan seis FAIL de check, no se
presentan como seis casos. La prueba D2 explícitamente cubierta conserva PASS;
sus variantes incumplidas producen FAIL, demostrando que no se bloquea todo
indiscriminadamente ni se infiere cobertura de ausencia de fallos.

## Pruebas ejecutadas

Windows, Python 3.12.10, pytest 9.1.1, Pydantic 2.14.1, openpyxl 3.1.5;
entorno `.venv/hfs011` reutilizado sin dependencias nuevas. Freeze, comandos,
cwd, SHA, exit y stdout en [entorno](evidence/after/environment.json) y logs.
Copias aisladas con hashes, PYTHONNOUSERSITE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1,
PYTHONUTF8=1, sin PYTHONPATH heredado ni caché de pytest.

| Suite | Antes | Entrega final | Exit |
|---|---|---|---|
| Original | 68 métodos + 12 subpruebas | 68 métodos + 12 subpruebas aprobadas | 0 |
| Caracterización | 5 aprobadas, 7 xfail | 9 aprobadas, 3 xfail estrictos | 0 |
| HFS-011 | 665 aprobadas | 665 aprobadas | 0 |
| HFS-016 | 44 aprobadas | 44 aprobadas | 0 |
| HFS-010 | No existía | 57 aprobadas | 0 |

Sin fallos/errores/XPASS ni omisiones ordinarias finales. Los tres skipped JUnit
son xfail de F-05, F-09 y F-29, no pruebas aprobadas. Nuevas pruebas incluyen
supresión de una/todas las reglas, duplicación de una sola, checks falsos con
etiqueta D2, outputs incongruentes, falta de implementador, FAIL parcial,
incertidumbre, alternativas, condiciones geométricas N/A, métodos existentes,
contratos estrictos y paridad CLI/archivo detallado.

Incidencias preservadas: la primera corrida posterior tuvo dos fallos de la
suite original por las antiguas expectativas de PASS de macizos y dos XPASS
estrictos F-02/F-03. Tras demostrar el cambio se actualizaron únicamente esos
estados; los checks/esperados numéricos permanecen. F-01/F-31 aún xfail exigían
la presencia de H/mayor en lugar del bloqueo que sus nombres también admitían;
se sustituyen por aserciones de INCOMPLETE y obligación específica pendiente,
con nuevas reproducciones independientes. [Logs iniciales](evidence/initial-characterization.json).
Una prueba adicional esperaba INCOMPLETE para An>Ag, pero HFS-011 lo rechaza
antes con error físico: se conservó esa guarda canónica, se retiró la comprobación
redundante y se corrigió la expectativa, sin xfail nuevo; [log](evidence/intermediate-net-area.json).

Comandos finales (usar rutas nuevas al repetir):

```powershell
.\.venv\hfs011\Scripts\python.exe scripts/audit_hfs011.py --baseline docs/audit/hfs016/evidence/after/engine-results.json --out .venv/hfs010-before --work .venv/hfs010-before-work --extra-suite tests/test_hfs016_catalog_integrity.py
.\.venv\hfs011\Scripts\python.exe scripts/audit_hfs011.py --baseline .venv/hfs010-before/engine-results.json --out .venv/hfs010-release --work .venv/hfs010-release-work --extra-suite tests/test_hfs016_catalog_integrity.py --extra-suite tests/test_hfs010_coverage.py --coverage-transition
.\.venv\hfs011\Scripts\python.exe docs/audit/hfs010/probes.py --root .venv/hfs010-before-work --out .venv/hfs010-probes-before.json
.\.venv\hfs011\Scripts\python.exe docs/audit/hfs010/probes.py --root . --out .venv/hfs010-probes-after.json
git diff --check
```

`compare_hfs010.py` comprueba integridad por caso, igualdad de todos los checks
y del error previo, transición esperada a INCOMPLETE para estos JSON legacy y
preservación de FAIL. No actualiza snapshots ni ignora diferencias numéricas.
[Verificación final de ejecución](evidence/after/verification.json).

## Archivos y responsabilidades modificadas

| Archivo/grupo | Motivo |
|---|---|
| `src/steel_design/domain/coverage.py` (nuevo) | Obligaciones independientes y condiciones del alcance |
| `src/steel_design/domain/coverage_evidence.py` (nuevo) | Evidencia parcial y acreditación acotada desde implementaciones concretas |
| `src/steel_design/results_model.py` | Estado global, cobertura, FAIL conocidos y propagación de INCOMPLETE |
| `src/steel_design/models.py` | TensionScope opcional, sin nuevos defaults estructurales |
| `src/steel_design/engine.py` | Plan previo al router, ejecución/evidencia, agregación común |
| `src/steel_design/run.py` | Serialización común y propagación del nuevo estado |
| `tests/test_hfs010_coverage.py` (nuevo) | 57 casos independientes de selección y pruebas de seguridad |
| `tests/test_custom_solid_sections.py` | Dos estados globales intencionales, sin cambiar checks |
| `tests/test_hfs000_characterization.py` | Cuatro bloqueos demostrados; tres defectos restantes visibles |
| `scripts/audit_hfs011.py`, `scripts/compare_hfs010.py` (nuevo) | Comparación separada de estados y checks, reutilizando captura |
| `docs/contracts/hfs010-coverage.md` (nuevo) | Contrato/migración y delimitación de PASS |
| `README.md`, `CONTRIBUTING.md`, `docs/ROADMAP.md` | Uso, reproducción y estado de entrega |
| `docs/architecture/dry-inventory.md`, `docs/audit/tracking.md` | Fuentes canónicas y mitigaciones/pendientes |
| Este informe, `probes.py`, `final-checks.json`, `evidence/` (nuevos) | Evidencia antes/después, incidentes y hashes |

[Manifiesto](evidence/manifest.json): 38 capturas promovidas por copia con origen
y SHA-256. Se conservan originales en `.venv`, informes/evidencia congelada,
catálogo, PDFs y ejemplos. [Comprobaciones finales](final-checks.json) registran
enlaces, hashes, ausencia de cambios en ecuaciones/reglas/router/catálogo y
comparación numérica exacta. Git puede avisar LF→CRLF; no se cambian ACL ni se
limpian directorios históricos para esconder errores.

## Riesgos y revisión posterior

1. El subconjunto completo es deliberadamente estrecho. Las demás capacidades
   siguen expuestas como cálculos parciales, algunas afectadas por hallazgos;
   no utilizarlas ignorando INCOMPLETE. Se requiere revisión ingenieril del
   alcance y de sus referencias antes de uso profesional.
2. TensionScope declara información externa sin autenticarla. El motor no revisa
   documentos de material/análisis/conexión ni deriva U/An desde su detalle.
   Declaraciones incorrectas pueden invalidar el alcance; no son un override
   de cargas ni de guardas físicas.
3. Las ramas F/E/G/H/I generales, fabricación, etapas, ejes y alternativas no
   están validadas exhaustivamente. N-ID agrupados en una rama desconocida
   describen pendientes, nunca cobertura acreditada. La matriz HFS-002 sigue
   siendo documental; el modelo no certifica que todas las disposiciones AISC
   hayan sido estudiadas. Erratas F-28 siguen pendientes.
4. F-29, F-05, F-09, F-07 y HFS-012/013/014 permanecen fuera de esta corrección.
   Lote vacío todavía puede mostrar PASS legacy; G1 no queda completada.
5. Clientes con enums cerrados o que miran solo exit/checks deben migrar. Salidas
   nuevas son más grandes e incluyen referencias externas; futuros adaptadores
   deben definir privacidad sin duplicar la política de cobertura.
6. La publicación/fusión está autorizada por el usuario con revisión posterior;
   no se declara aprobada la ingeniería por pasar tests ni se inicia otro hito.
