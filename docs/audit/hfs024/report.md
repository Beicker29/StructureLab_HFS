# HFS-024 — Trazas de cálculo canónicas

Fecha: 2026-10-29. Entrega local para revisión técnica independiente, sin
autocalificación ni acreditación normativa nueva. **F-31 permanece P0 abierto.**

Se implementa captura optativa de la ejecución real y pasos numéricos progresivos.
Se conservan capacidades, DCR, estados, selección, cobertura y formatos existentes.
No se afirma que las 93 entradas tengan una traza aritmética completa.

## Base, alcance y diagnóstico

- Rama `main`, SHA inicial/final `93e4f8cd523148c8cb3ccff1d94caafb4cfa8af1`;
  árbol inicial sin cambios listados por Git. Se conservan 31 advertencias de
  acceso históricas: 10 directorios `.tmp_test`, uno `pytest-cache-files-*` y
  20 `tests/.tmp_tests`. Sin cambios de permisos, limpiezas ni eliminaciones.
- HFS-023 aprobado arquitectónicamente por el usuario. La consulta del SHA exacto
  confirma [CI 40858414332](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40858414332)
  SUCCESS: jobs 123395165702 Ubuntu 24.04 y 123395166053 Windows 2022.
  [Respuesta preservada](evidence/base-ci.json). Esta CI acredita la base publicada,
  no estos cambios locales. CI del futuro commit pendiente del usuario.
- Leídos AGENTS, roadmap, ADR, contratos vigentes y seguimiento. HFS-024 no revisa
  erratas, no inicia HFS-030, no modifica catálogo ni crea interfaz web.

El sistema ya tenía tres fuentes útiles: operaciones en `codes/aisc_360_22`,
evaluadores/reglas con diccionarios `memory`, y CheckResult con valores brutos
y unidad. HFS-023 agregó identidad/citas/evidencia declarativa, pero no registra
qué rama se ejecutó. Engine conserva ejecuciones y cobertura HFS-010; reporting
formatea las memorias y mantiene algunos consumidores legacy de etiquetas.

Inventario de responsabilidades encontrado:

| Área | Producción actual / problema | Decisión HFS-024 |
|---|---|---|
| D/E | Nominales y factores en funciones; reglas construyen memory | Observar D2/D3 y valores E3 reales; conservar pendientes de otras subramas |
| F | Evaluadores devuelven limit_states/intermediate; constructor elige nominal | Observar nominal entregado y conversión F1; no convertir ID F3/F4 en ecuación |
| G/H | G4/G5 compartido, H1/H3 combinan capacidades; convenciones HFS-013 | Conservar pares/ejes y emitir pasos desde sus consumidores reales |
| I | Cálculo, integración y presentación local en composite_rules | Observar 17 clases y selección real I5; no inventar fórmulas de iteración/Commentary |
| Engine/cobertura | Selecciona, captura algunos errores, agrega estado | Copiar estado/cobertura ya producidos y asociar checks por identidad, sin nuevo plan |
| Reporting | CheckResult bruto, memory legacy y SVG | Nuevo exportador optativo de snapshot; no recalcula, infiere ni sustituye formatos legacy |

Las 57 implementaciones de `check` cubren por herencia 71 clases HFS-023; 22
entradas son descriptores sin check. La [matriz de 93 entradas](rule-matrix.md)
separa frontera instrumentada, observación en ejemplos y pasos efectivamente
emitidos. Los ejemplos ejercitan 45 IDs; 26 emiten pasos. Los otros IDs no se
declaran completos por tener un decorador.

## Arquitectura y alternativas

**Elegida:** un módulo pequeño de observación, `steel_design.tracing`, modelos
Pydantic de traza y contexto optativo. Un decorador común observa las llamadas a
reglas, sus resultados y excepciones; pasos explícitos reciben valores locales
desde el productor. El registro HFS-023 es consultado por clase real, sin mapa
de reglas paralelo. Engine enlaza los checks y copia la cobertura canónica.

Alternativas rechazadas: reconstruir expresiones desde `clause`/nombres/memory
(ambiguo F3/F4/H1/I); añadir campos al JSON congelado sin transición; repetir
un registro para reporting; introducir un motor de fórmulas; propagar nuevos
argumentos por todas las funciones para esta primera instrumentación. El contexto
preserva firmas y evita esa propagación, pero introduce dependencia contextual
y consumo de memoria que se declaran y prueban.

El [contrato formal](../../contracts/hfs024-calculation-traces.md) documenta
campos, unidades, fuentes, desconocidos, API y semántica. Se reutiliza RuleMetadata
y CheckResult; no se duplican modelos ingenieriles, factores, clasificadores o
decisiones de cobertura. La edición/citas/evidencia están en metadata HFS-023;
las expresiones/subreferencias de paso describen la operación ejecutada, nunca
un catálogo alternativo de aplicabilidad. La prueba de existencia de tests
permanece separada de `NOT_ACCREDITED`.

No hay reconstrucción retroactiva al leer JSON 1.0. La traza optativa se exporta
como documento auxiliar HFS-024-v1 con valores brutos; los consumidores pueden
formatear una presentación separada. Legacy sigue conservando más detalle en
algunas ramas: reemplazar sus memorias ahora perdería información. Esa transición
es un pendiente explícito, no una migración silenciosa ni una segunda implementación
de cálculos. No se retira código porque no se sustituyó ningún consumidor existente.

## Decisiones normativas de identidad, sin auditoría nueva

Las referencias se apoyan en las decisiones/evidencias previas HFS-002/013/017/023,
no en una nueva validación de AISC ni reconciliación de erratas:

- D2-1/D2-2 y D3-1 se emiten en sus operaciones; factores por método se leen de
  la conversión existente, sin otra tabla de factores.
- F1(a) registra la conversión que ya se ejecuta. F3-3 no se usa como número de
  ecuación. F4 registra delegación F5 y User Note informativa; F-19 sigue pendiente.
- H1 registra las ramas compresivas H1-1a/b. Tracción conserva la expresión
  implementada y la etiqueta legacy H1-2, con `equation=null` y F-37 explícito.
- H3-6 registra sumas/cocientes reales y operación final. Umbral Tr/Tc ≤0,20
  conserva el bloqueo, sin resultado resistente inventado. F1 interno ASD no
  habilita rutas públicas ASD de F/I.
- I5 registra método, rama, capacidades y resultado existentes. La referencia
  auxiliar/Commentary del método 2 no se presenta como ecuación Specification.
  La correspondencia completa y convergencia siguen pendientes F-18/20/37.

Los checks inactivos legacy pueden devolver PASS; la traza conserva el hecho y
declara ausencia de pasos/unidad cuando corresponde. No le asigna cobertura.
INCOMPLETE se copia del motor. BLOCKED es resultado de un intento impedido, no
un estado estructural adicional. Errores anteriores a selección no crean reglas
ficticias. Pruebas específicas preservan el canal biaxial pendiente F-31.

## Verificación efectivamente ejecutada

Python **3.12.10**, herramientas y dependencias instaladas fijadas por
`requirements/ci-constraints.txt`: Pydantic 2.14.1/core 2.50.1, pytest 9.1.1,
jsonschema 4.26.0, Ruff 0.17.3; distribución structurelab-hfs 0.2.0.
Los freezes completos, comandos, cwd, exit, stdout/stderr, JUnit, artefactos
instalados y hashes están en los ZIP de evidencia.

| Verificación | Antes | Después |
|---|---:|---:|
| Suite original | 68 métodos +12 subpruebas | 68 métodos +12 subpruebas |
| Caracterización HFS-000 | 12 | 12 |
| Suites HFS-010–023 restantes | 2481 | 2481 |
| Nueva HFS-024 | — | 114 |
| Total, sin contar dos veces subpruebas | **2561 +12** | **2675 +12** |
| Fallidas / errores / omitidas / xfail / XPASS finales | 0 / 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 / 0 |

Son 19 suites antes y 20 después. JUnit cuenta 80 en la suite original porque
incluye las 12 subpruebas; no se informa como 80 métodos. Las ejecuciones extra
en editable no se suman nuevamente al total. [Resultados por suite](evidence/results.json).

La nueva suite verifica D2 LRFD/ASD con esperados independientes, H3 con ambos
ejes y métodos, H1 sin falsa identificación, cargas G firmadas/Vu, bloqueos,
INCOMPLETE, PASS/FAIL de tirantes acreditados por la puerta ya existente,
F3/F4/F31, no finitos y desconocidos, herencia, firmas e identidad. En los 12
ejemplos compara también la secuencia de llamadas a todas las funciones de los
seis módulos normativos con/sin captura; el exportador no vuelve a calcular.
Prueba aislamiento de contextos anidados/hilos y separación de snapshots.

El verificador construyó sdist/wheel, inspeccionó contenido, ejecutó Twine y
pip check, probó instalación normal, wheel y editable fuera del checkout. Las
tres instalaciones ejecutaron la sonda de los 12 ejemplos con/sin captura.
Wheel ejecutó las 20 suites; editable, la suite de trazas y las comprobaciones
de API/contratos ya comprometidas. Diez esquemas congelados y manifiesto: sin
deriva. Registro HFS-023: 93 entradas, integridad e índice vigentes.

Ruff y `git diff --check` pasan. El recorrido local Ruff sin elevación advierte
directorios históricos inaccesibles; el chequeo explícito de fuentes editados
también pasa. No se usan esas advertencias como xfail ni se cambian permisos.

**Intento exploratorio conservado:** `unit-second.xml` registra 154 aprobadas
y dos errores de setup por `PermissionError` en el temporal pytest del usuario,
en dos consumidores HFS-022Q. No fueron fallos de cálculo. Se ejecutaron después
sin error en el verificador aislado con permisos de ejecución adecuados; no se
relajó ninguna prueba. `unit-first.xml` conserva las 113 pruebas de la primera
iteración; el contrato de excepción previa se añadió después y la suite final
contiene 114. No se sobrescriben esas capturas para aparentar una única corrida.

La comprobación final de bytes encontró también una restricción de lectura del
wheel en `.venv/24-after/dist` desde el proceso restringido. Se leyó el mismo
wheel del ZIP de evidencia ya verificado, sin cambiar permisos: sus 48 módulos
coinciden byte a byte con los fuentes finales. Los tres documentos de sondas
normal/wheel/editable también son idénticos. Diagnóstico en `final-checks.json`.

Comandos principales, desde instalación editable de desarrollo (prefijo Python
local utilizado: `.venv/21dev/Scripts/python.exe -X utf8`):

```text
python scripts/verify_hfs020.py --out .venv/24-before
python -m pytest -q -p no:cacheprovider tests/test_hfs024_tracing.py
python scripts/verify_hfs020.py --out .venv/24-after
python scripts/audit_hfs024.py --source-proof --out NUEVO-source.json
python scripts/audit_hfs024.py --probe . --out NUEVO-traces.json
python scripts/audit_hfs023.py --check
python scripts/generate_hfs022_schemas.py --check
python -m ruff check .
git diff --check
```

## Diferencias y evidencia recuperable

Comparación antes/después exacta: **12 ejemplos, 24 escenarios CLI/memoria y
6 SVG idénticos byte a byte** en Windows. Once ejemplos retornan INCOMPLETE;
double_angle conserva su excepción previa. No se cambian capacidades, DCR,
checks, estados, errores o códigos de salida. Las trazas se producen únicamente
al solicitarlas y se guardan aparte. Los JSON 1.0 y las memorias legacy no
incluyen campos nuevos. No se modificó ningún oráculo histórico.

[Prueba estructural](evidence/source-proof.json): los 47 módulos Python existentes
conservan AST de operaciones/control de flujo al descontar imports/decoradores,
observaciones y variables descriptivas enumeradas. No prueba por sí sola exactitud
normativa; complementa regresiones y conteo de llamadas. El nuevo módulo de captura
es la única adición de producción. Router, registro, modelos, cobertura, catálogo
y expresiones fuera de esa instrumentación no cambian.

- [before.zip](evidence/before.zip) y [after.zip](evidence/after.zip): ejecución
  completa, distribuciones, logs/JUnit, versiones, resultados, SVG originales;
  el segundo incluye `traces-project/wheel/editable.json` con las observaciones.
- [archives.json](evidence/archives.json): hashes y tamaños por miembro. Se
  reabrieron ambos ZIP y se comprobaron todos los hashes; son recuperables.
- [comparison.json](evidence/comparison.json): igualdad antes/después y hashes SVG.
- [start.json](evidence/start.json), [base-ci.json](evidence/base-ci.json),
  [results.json](evidence/results.json), [final-checks.json](evidence/final-checks.json)
  y [manifiesto](evidence/SHA256SUMS.json) documentan procedencia y cierre local.
- [changes.md](changes.md): inventario completo de archivos modificados/nuevos
  y pendientes. No se elimina, excluye o mueve evidencia histórica.

## Riesgos residuales y evaluación crítica

1. **F-31 P0 abierto** y demás vacíos de aplicabilidad/resistencia siguen visibles;
   ninguna traza concede crédito HFS-010. No cambia la matriz independiente.
2. **Instrumentación parcial:** E4/E5/E7, subramas F/G, integración compuesta y
   varios factores/intermedios siguen sin expansión canónica. La frontera común
   aporta identidad y salida real, no una memoria normativa completa.
3. **Metadata/cadenas descriptivas pueden divergir del código.** Pruebas enlazan
   valores y ramas ejercitadas; no certifican todos los textos. La ampliación
   debe hacerse junto a la operación, con pruebas específicas y revisión.
4. **Contexto implícito y memoria:** captura optativa, sin I/O ni cache global de
   capacidades. Un buffer por request; compartirlo entre tareas concurrentes no
   es contrato soportado. Se conservan copias de contexto por intento para evidencia.
5. **Duplicación existente no corregida:** algunas capacidades se evalúan varias
   veces. Se prueba que la captura no aumenta esas llamadas. Consolidarlas exige
   tarea de cálculo/aplicabilidad y oráculos; hacerlo aquí excedería el alcance.
6. **Memorias legacy aún no migradas.** El nuevo exportador cumple separación de
   cálculo/presentación; no se anuncia sustitución completa de sus productores.
7. CI remota de los cambios locales pendiente del commit que publique el usuario.
   No se hizo commit/push, ni se creó rama/PR.

La decisión reduce una duplicación real de mecanismos de observación y evita
otro motor o registro. No reduce artificialmente líneas ni fusiona ecuaciones.
La revisión humana debe evaluar el contrato optativo y el alcance progresivo;
extenderlo después por productores acreditados, sin reconstrucción retrospectiva.
No se inicia HFS-030 ni otro hito en esta entrega.
