# HFS-023 — Registro normativo declarativo mínimo

Fecha de entrega: 2026-10-29. Base `main`, SHA
`1b170929374bd590292ce3f5a17fca1e65bb79ce`, árbol inicial limpio.
HFS-022Q aprobado arquitectónicamente por declaración del usuario. No se
autoasigna calificación ni se realiza aprobación ingenieril.

## Diagnóstico arquitectónico

Existían 56 `RuleDefinition` con ID/clase/campos/predicado, mientras 17 clases
compuestas se seleccionaban mediante `_get_composite_rules` fuera de esa
colección. Las referencias documentales y tests estaban en una tabla manual,
comentarios, memorias e informes de hitos; una clase implementada o una etiqueta
de cláusula no demostraba correspondencia normativa. El inventario distingue
94 clases con método `check`: 71 seleccionables/concretas registradas y 23
bases por eje o fachadas con herencia/consumidores vigentes.

Se consultaron AGENTS, roadmap HFS-023/024, ADR-001/002/003, inventario DRY,
tracking, fuentes y matrices HFS-002 y contratos de cobertura, método, API y
transporte vigentes. F-26 motiva retirar la segunda autoridad manual; F-37
exige separar ID y ecuación. F-31 continúa **P0 abierto**. No se corrigieron
ecuaciones, capacidades o interpretaciones normativas pendientes.

La [CI de la base](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40792213050)
se consultó en GitHub: Windows 2022 y Ubuntu 24.04 SUCCESS en el SHA exacto.
[Registro inicial](evidence/start.json). Esto acredita la base publicada, no
una ejecución remota de los cambios locales HFS-023.

## Decisión, alternativas y responsabilidades

Se amplía `RuleDefinition.metadata` y se mantiene **una sola colección** en
`profile_router.RULE_DEFINITIONS`. Se descarta un JSON normativo editable
paralelo, un segundo router, un DSL y un registro de plugins. Los metadatos
tipados/inmutables se construyen en un módulo pequeño de anotaciones, sin I/O,
sin recibir casos ni ejecutar condiciones. Los modelos de ingeniería y el
transporte Pydantic HFS-022 no se versionan ni se duplican.

Se mantienen separadas tres preguntas: existe una implementación; existen
referencias de verificación de software; existe acreditación normativa para
el dominio completo. Las 93 entradas conservan `NOT_ACCREDITED` en la tercera.
Las pruebas de integridad no convierten ese estado en validado. La cobertura
condicional D2 ya existente queda en sus guardas HFS-010, intactas.

Los grupos comparten contexto documental, no ecuaciones. El registro reutiliza
clases/predicados originales; el auditor deriva propietario del `check` y perfiles
ruteados de esos mismos objetos. Las condiciones normativas remiten a la matriz
independiente; no se generan desde los perfiles ruteados. Chapter I conserva
su selección procedimental, sin nueva bifurcación ni predicado duplicado.

El [contrato del registro](../../contracts/hfs023-normative-registry.md) detalla
campos, estados, identidad, fuentes, compatibilidad y mantenimiento. El
[índice derivado](../../aisc_360_22_traceability.md) sustituye la autoridad manual
de implementación. Los originales se conservan en
[legacy-traceability.md](evidence/legacy-traceability.md); HFS-002 no se genera
ni se sobrescribe. La evidencia JSON contiene los textos completos del dominio,
condiciones, limitaciones y referencias por entrada.

## Cobertura del inventario y pendientes

| Clasificación descriptiva | Entradas | Significado |
|---|---:|---|
| PARTIAL | 69 | Clase existente, sin acreditación integral de disposición |
| BLOCKED | 2 | Clases G3 presentes que rechazan el dominio no acreditado |
| NOT_IMPLEMENTED | 16 | Check ausente, incluido el descriptor del placeholder histórico I2 |
| EXTERNAL | 5 | Procedencia/condiciones externas no acreditadas por el motor |
| ADVISORY | 1 | D1/E2 informativo, sin crédito resistente |
| Total | 93 | 56 IDs conservados, 17 clases I indexadas y 20 descriptores nuevos |

78 entradas tienen referencias de software; 15 indican explícitamente ausencia
de prueba directa identificada. Doce entradas vinculan oráculos existentes de
alcance limitado: D2, una trayectoria E3, fluencia F2, factores G2, G4/G5 o
expresiones H3. No se infiere una validación completa de esas familias ni de
las ramas hermanas. Los N01–N45 están enlazados al menos una vez; ese conteo es
completitud del **índice documental**, no cobertura AISC ni del caso de usuario.

Se distinguen expresamente:

- F3 IDs internos frente a ecuaciones S22; F4/F5 y User Note pendiente de
  acreditar; F7 numeración del PDF local y erratas pendientes (F-19/28/37).
- F6 menor frente a canal mayor fuera de F2; F-31 no se cierra por metadatos.
- E5 condiciones/ramas pendientes y E7 Q frente a área efectiva (F-35/36).
- H1/H2 fuera de HSS, biaxial sin axial y la etiqueta legacy H1-2 (F-01/33/37).
- H3 umbral, longitudes, C, direcciones y límites; correcciones acotadas
  HFS-013 no acreditan todas las capacidades que consume la interacción.
- I3 cuantías y transferencia frente a resistencia a momento, capacidades
  auxiliares de I5 frente a checks independientes ausentes, alternativas I4
  y condiciones/etapas/conexiones pendientes (F-18/20/34/38).
- D4, E6, F13, G7, H3.3, H4, I6 completo, alcances especiales y responsabilidades
  externas; ausencia de implementación no se convierte en NOT_APPLICABLE.

No se inicia una reconciliación normativa/erratas ni una auditoría de capacidades.
La evidencia acotada y las limitaciones quedan disponibles para esas tareas.

## Limpieza incremental y compatibilidad

`_has_interaction` solo devolvía False y su único consumidor era el placeholder
`I2`, ausente de `PROFILE_RULE_MAP`; la selección compuesta ya tenía su propio
dueño real. Se retira esa función muerta. El ID I2 se conserva como descriptor
histórico con `applicability=None`; no significa que todo I2 esté sin código.
No hay consumidor operativo ni compromiso público del helper retirado.

Las 23 clases base/fachadas permanecen por herencia y/o el consumidor dinámico
`test_hfs017_design_method.rule_classes`, que verifica guardas en llamadas
directas. Tres fachadas tienen además usos explícitos en tests originales.
No se eliminan pruebas para facilitar limpieza ni se reestructura cálculo.
El inventario de consumidores registra símbolos, propietarios, referencias
textuales y consumidor dinámico; distingue una mención de una llamada resuelta.

Los 55 bindings restantes, predicados, métodos completos de `ProfileRouter` y
mapa de perfiles se contrastan con la base. No cambia ninguna función
ingenieril. `RuleDefinition` gana un campo opcional; el conjunto iterable ahora
incluye descriptores sin predicado, por lo que no representa una lista de reglas
para ejecutar indiscriminadamente. Los consumidores existentes usan el mapa
explícito, no recorren todos los registros para calcular.

No cambia JSON 1.0, schemas, estados, traza legacy, cláusulas de resultados,
CLI, memorias, SVG, versión 0.2.0 o cobertura HFS-010. Las guardas ASD de F/I
permanecen. No se modifica `_CLAIMS` ni se añade crédito por presencia en el índice.

## Verificación reproducible

Entorno aislado editable `.venv/23dev`, Python 3.12.10, dependencias dev/runtime
instaladas con `requirements/ci-constraints.txt`. Comandos principales:

```powershell
.\.venv\23dev\Scripts\python.exe -m pip install -c requirements/ci-constraints.txt -e ".[dev]"
.\.venv\23dev\Scripts\python.exe -X utf8 scripts/verify_hfs020.py --out .venv/23-before-clean
.\.venv\23dev\Scripts\python.exe -X utf8 scripts/audit_hfs023.py --check --out .venv/23-registry-cleanup
.\.venv\23dev\Scripts\python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider tests/test_hfs023_registry.py --junitxml=.venv/23-unit-cleanup.xml --basetemp=.venv/23-unit-cleanup-tmp
.\.venv\23dev\Scripts\python.exe -X utf8 scripts/verify_hfs020.py --out .venv/23-after-final
```

Usar directorios nuevos al reproducir. El verificador común conserva suites
separadas, instalaciones normal/wheel/editable y consumidores externos. Solo
añade la nueva suite y copias de documentos/fixtures/utilidad de auditoría
necesarios para comprobar referencias desde la instalación real; no copia
código productivo al temporal externo.

La primera tentativa `.venv/23-before` terminó con exit 1 al detectar
`build/lib/src` generado con el namespace retirado. Se archivaron y verificaron
33 archivos con hashes antes de mover `build` a `.venv/23-legacy-build`, dentro
de rutas absolutas comprobadas del workspace. No hubo borrado, cambio de ACL,
xfail ni modificación de fuentes. [Archivo recuperable](evidence/legacy-build.zip)
y [procedencia](evidence/legacy-build.json). La repetición limpia terminó con
2352 aprobadas +12 subpruebas y aceptó ejemplos/consumidores/SVG.

Las primeras pruebas nuevas dieron 205 aprobadas. Tras retirar el predicado
muerto y añadir controles de IDs blancos/con espacios, dieron 209 aprobadas;
no se relajaron esperados históricos. Las mutaciones detectan duplicados,
registros incompletos, referencias rotas, propietarios de otro capítulo,
intentos de acreditar por tests y descriptores enlazados indebidamente al router.
Se verifica además que importar contratos en un proceso nuevo no carga el registro.

Se preserva una primera regresión completa `.venv/23-after`, también aprobada.
La revisión final separó citas de capítulos diferentes y precisó el propietario
de los avisos D1/E2; la corrida `.venv/23-after-final` verifica esos metadatos.
El comprobador de fuentes se vinculó además a blobs Git, manteniendo hashes
originales y aceptando exclusivamente sus representaciones LF/CRLF de texto.
[Sonda de portabilidad](evidence/source-portability.json): la representación LF
simulada pasa y una mutación distinta de EOL se rechaza, sin escribir fuentes.
No se usa esa simulación para afirmar una ejecución Ubuntu nueva.

Ruff general terminó con exit 0, pero registró una advertencia local de acceso
denegado al recorrer el árbol. Ruff explícito sin caché sobre los 105 archivos
Python del alcance pasó sin advertencias. No se cambiaron permisos ni se
eliminaron carpetas. Los dos resultados quedan conservados como tales.

Los resultados definitivos de la regresión, diferencias y manifiestos se
registran en [results.json](evidence/results.json). No se usa el hecho de
tener tests verdes como prueba de exactitud AISC.

| Verificación final | Resultado |
|---|---|
| Línea base HFS-022Q, 18 suites separadas | 2352 aprobadas +12 subpruebas |
| HFS-023, 19 suites separadas | 2561 aprobadas +12 subpruebas; 209 nuevas |
| Fallidas / errores / omitidas / xfail / XPASS | 0 / 0 / 0 / 0 / 0 |
| Ejemplos del motor | 12 idénticos, comparación exacta |
| CLI y memorias | 24 escenarios idénticos, incluidos estados/cobertura/trazas/exit |
| SVG generados | 6 idénticos en bytes entre antes/después |
| Instalaciones | Normal, wheel y editable aprobadas; imports y consumidores externos verificados |
| Distribuciones | Build desde sdist, twine y contenido aprobados; 46→47 archivos Python por el módulo de metadatos |
| JSON 1.0 | Diez schemas más manifiesto sin deriva; verificación en las tres instalaciones |
| Ruff | 105 archivos explícitos sin caché, exit 0; advertencia del barrido general preservada |
| Índice derivado / alcance de fuentes | Integridad y AST aprobados; ecuaciones, resultados y contratos protegidos |

No se observan diferencias numéricas ni cambios de PASS/FAIL/INCOMPLETE.
Los rechazos esperados del namespace antiguo y del catálogo default ausente
mantienen exit 1; los verificadores y suites de aceptación terminan con exit 0.
JUnit suma 2573 porque incluye las 12 subpruebas; no se presentan como 2573
métodos. Las comprobaciones adicionales de API/contratos en editable son
repeticiones deliberadas y no se suman como pruebas nuevas.

La prueba de fuentes protege 98 archivos previos: solo cambia el router, con
sus métodos/predicados activos y mapa iguales por AST; la única retirada es
el predicado I2 muerto documentado. La actualización posterior de
`audit_hfs023.source_proof` solo hace portable el contraste de archivos Git
(LF/CRLF) y se probó mediante sonda de mutación; no cambia el paquete instalado.

### Recuperación y reproducción de evidencia

[archives.json](evidence/archives.json) enumera ruta/tamaño/SHA de cada miembro
de los ZIP [before](evidence/before.zip), [after](evidence/after.zip),
[intermediate](evidence/intermediate.zip), [initial-blocked](evidence/initial-blocked.zip)
y [registry](evidence/registry.zip). Cada miembro se releyó y verificó contra
su hash. Los originales crudos y los manifiestos viajan dentro de ZIP para
preservar bytes aunque Git convierta EOL en copias de texto de consulta.
Los hashes del conjunto nuevo están en [SHA256SUMS.json](evidence/SHA256SUMS.json).
Ninguna captura HFS-000 a HFS-022Q fue sobrescrita.

La corrida final contiene por suite el comando completo, cwd, entorno, exit,
stdout/stderr y JUnit; también freezes, wheel/sdist, hashes de entradas, resultados
y originales SVG. Para comparar dos corridas recién ejecutadas desde la raíz:

```powershell
.\.venv\23dev\Scripts\python.exe -c "import sys; from pathlib import Path; sys.path.insert(0,'scripts'); from compare_hfs021 import compare_results; print(compare_results(Path('.venv/23-before-clean').resolve(), Path('.venv/23-after-final').resolve()))"
```

Ese comparador reutilizado no cambia tolerancias o expectativas: exige igualdad
exacta de los resultados y bytes SVG. Si se trabaja solo con ZIP restaurados,
las rutas temporales originales podrían no existir; los seis SVG generados
permanecen recuperables en `svg-originals.zip` de cada corrida y pueden
compararse por nombre de miembro y bytes. Los consumidores/clases y metadatos
completos también se entregan como [JSON de consulta](evidence/registry.json)
y [mapa de consumidores](evidence/class-consumers.json).

## Inventario de cambios

| Archivo | Cambio / motivo |
|---|---|
| `src/steel_design/domain/routing/profile_router.py` | Amplía RuleDefinition y su colección; descriptores I/vacíos; retira únicamente `_has_interaction` muerto |
| `src/steel_design/domain/routing/registry_metadata.py` (nuevo) | Modelos y anotaciones inmutables, construcción e integridad pura, sin otro router |
| `scripts/audit_hfs023.py` (nuevo) | Referencias, índice derivado, consumidores y alcance AST/bytes |
| `scripts/verify_hfs020.py` | Incorpora la suite separada y recursos documentales/fixture para instalación externa |
| `tests/test_hfs023_registry.py` (nuevo) | 209 pruebas de integridad, mutación, propietarios, referencias y compatibilidad |
| `tests/fixtures/hfs023/runtime-registry.json` (nuevo) | Bindings y mapas previos congelados como caracterización de software, no oráculo AISC |
| `docs/aisc_360_22_traceability.md` | Vista derivada; tabla anterior archivada antes de sustituir autoridad manual |
| `docs/contracts/hfs023-normative-registry.md` (nuevo) | Contrato de metadatos, consumidores, límites y compatibilidad |
| `docs/audit/hfs023/report.md`, `evidence/*` (nuevos) | Diagnóstico, decisiones, resultados, inventario, riesgos y archivos recuperables |
| `docs/adr/003-traceability-testing.md` | Suplemento de aplicación HFS-023, conservando decisión histórica |
| `docs/architecture/dry-inventory.md` | Propietario canónico y responsabilidades que permanecen separadas |
| `docs/ROADMAP.md`, `docs/audit/tracking.md` | Estado para revisión; F-26 arquitectónico y F-31 P0 abierto |
| `CONTRIBUTING.md` | Suite nueva y comando de mantenimiento del índice |

No se modifican tests anteriores, matrices HFS-002, catálogo, ejemplos,
ecuaciones, factores, geometría, motor, cobertura, preparación, transporte,
reporting, SVG, schemas, dependencias, workflow ni metadatos de distribución.

## Riesgos residuales y evaluación crítica

El registro detecta roturas de referencias y omisiones de campos, no errores
ingenieriles en el texto ni suficiencia de cada oráculo. Algunos tests se
referencian por módulo y no acreditan cada rama del grupo; los oráculos
individuales y su alcance están separados. Persisten correspondencias pendientes
entre etiquetas legacy y ecuaciones, dominios sin oráculos completos y erratas
sin cotejar. Ninguna de esas limitaciones se oculta con un estado VALIDATED.

El registro Python continúa siendo un diccionario mutable por compatibilidad;
los descriptores son inmutables, pero un consumidor interno podría sustituir
una entrada. Es responsabilidad del proceso de revisión y de las pruebas
preservar integridad; no es un sistema de certificación o autenticación.
La anotación descriptiva no sustituye la condición ejecutable: se vinculan y
contrastan, sin intentar convertir lenguaje normativo en un segundo motor.

La CI remota observada corresponde al SHA inicial. La nueva entrega se deja
local para publicación/revisión por el usuario; no se crea commit ni push.
Una corrida local Windows y las pruebas de integridad independientes del SO
no se presentan como nueva ejecución Ubuntu de HFS-023.

## Recomendación para HFS-024 (no iniciado)

Usar el ID estable del registro para vincular trazas producidas por el evaluador
real, conservando variable/unidad/eje/método/expresión y la rama efectivamente
elegida. Evitar reconstruir esa información desde nombres o prefijos de cláusula.
Priorizar los conflictos F3/F4/H1/I3/I4 y definir compatibilidad/versionado antes
de cambiar etiquetas de resultados. Mantener las guardas de cobertura y la
acreditación normativa separadas de la nueva traza. Una etiqueta ambigua debe
seguir explícitamente pendiente, sin inventar la ecuación faltante. La revisión
independiente debe decidir si este registro basta como base y qué cambios de
traza autoriza; HFS-024 no se implementa en esta entrega.
