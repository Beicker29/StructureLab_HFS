# HFS-011 — Endurecimiento de contratos de entrada

Fecha: 2026-10-27, America/Bogota. Estado: implementación y pruebas completadas, presentada para revisión técnica. No constituye validación ingenieril exhaustiva ni aprobación de nuevos métodos.

## Alcance autorizado y diagnóstico

Se ejecutó exclusivamente HFS-011, adelantada a HFS-010 por instrucción expresa del usuario. HFS-002 se acepta como matriz documental de aplicabilidad y diagnóstico. Se leyeron AGENTS, CONTRIBUTING, roadmap, ADR-001/002/003, inventario DRY, ambas matrices HFS-002 y hallazgos F-04/08/10/22. Inicio: rama `main`, SHA `5fe2c67a0d14f2541be032278d272cd85c080ecf`, árbol limpio. Se mantuvo la rama; cambios locales sin commit, sin PR ni publicación.

La auditoría confirmó extras ignorados, NaN aceptado, sobrescritura de Vu, dominios locales incompletos y fallbacks de datos. Se revisaron los 17 modelos ingenieriles de entrada (16 en models.py y Section), incluidos sus objetos/listas anidados. Se añadió un modelo pequeño para opciones CLI. Modelos de salida identificados y excluidos de la modificación. Inventario de campos, defaults, condiciones y rupturas: [contrato de entrada](../../contracts/hfs011-inputs.md).

## Decisiones e implementación

- Una política compartida de extras prohibidos, números estrictos finitos y dominios locales. Se rechazan booleanos/cadenas como magnitudes, conteos no enteros, valores positivos/nulos fuera de dominio y enums inválidos.
- Se distingue `loads:{}` de un cero explícito. Se conserva el contrato parcial histórico: componente omitida declara cero, no desconocido. Longitudes siguen siendo obligatorias y positivas; no se infiere arriostramiento continuo a partir de cero.
- Se elimina la transformación de Vux/Vuy a resultante Vu. Cortante legacy no nulo y componentes direccionales no nulas son representaciones incompatibles: se rechazan incluso si su norma coincide. Los ceros son campos inactivos. No se transforma ni renombra ningún eje.
- Se exigen Fu/Rg/Rp explícitos en STUD y deck_present explícito en viga compuesta; no se hereda Fu del perfil por ausencia. Se revisan envolventes, An≤Ag y propiedades compuestas ausentes que antes podían convertirse en cero. Se conservan defaults históricos K/Cb/E, método y otros, documentando su significado y límites.
- El motor revalida objetos manipulados y secciones seleccionadas. El catálogo conserva sus cinco filas con área cero para diagnóstico; seleccionarlas para cálculo produce error. Finitud se verifica antes de derivar razones y tras escalar en el parser, reutilizando el mismo tipo numérico.
- CLI conserva exit 0/1 y ahora expone `code`, `details.fields[].loc/type/msg` en errores Pydantic; no serializa NaN en el error. Rechaza claves JSON duplicadas y opciones de salida desconocidas/ambiguas.

No se modificaron archivos de ecuaciones AISC ni reglas de capacidades/interacciones. El único cambio del router es la guarda de finitud en `_is_missing_numeric`; mapas, predicados de selección y condiciones normativas se conservan. No se implementaron HFS-010, HFS-016, API/web, empaquetado o nuevas dependencias productivas. No se calculó un nuevo límite AISC ni se afirma que una entrada aceptada satisfaga N01–N45.

Mapa de propiedad, consumidores y guardas conservadas: [inventario DRY actualizado](../../architecture/dry-inventory.md). Es consolidación de contratos y rechazo intencional de entradas; no se presenta como refactor neutro ni como deduplicación de fórmulas.

## Pruebas reales y entorno

Python 3.12.10 en Windows, entorno nuevo `.venv/hfs011`, paquetes exactos del freeze HFS-000: Pydantic 2.14.1, pydantic_core 2.50.1, pytest 9.1.1, openpyxl 3.1.5. [Entorno previo](evidence/before/environment.json), [freeze](evidence/before/environment-freeze.txt), [entorno final y Git](evidence/after/environment.json). Se fijaron PYTHONNOUSERSITE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONUTF8=1 y se retiró PYTHONPATH heredado.

Las ejecuciones se hicieron en copias nuevas con hashes verificados, preservando la evidencia HFS-000 y temporales del usuario. Comandos raíz realmente ejecutados:

```powershell
python -m venv .venv/hfs011
.\.venv\hfs011\Scripts\python.exe -m pip install -r docs/audit/evidence-clean/environment-freeze.txt
.\.venv\hfs011\Scripts\python.exe scripts/audit_baseline.py --out .venv/hfs011-before-clean --work .venv/hfs011-before-clean-work
.\.venv\hfs011\Scripts\python.exe scripts/audit_hfs011.py --baseline .venv/hfs011-before-clean/engine-results.json --out .venv/hfs011-final --work .venv/hfs011-final-work
```

Los logs enlazados incluyen comando completo, cwd, exit, stdout/stderr. El capturador final añade `-p no:cacheprovider`, basetemp nuevo y JUnit. Las suites originales excluyen caracterización y pruebas HFS-011; no se mezclan los conteos.

| Ejecución | Exit | Aprobadas | Fallidas / errores | Omitidas / xfail / XPASS | Evidencia |
|---|---:|---|---|---|---|
| Previa original limpia | 0 | 68 métodos + 12 subpruebas | 0 / 0 | 0 / 0 / 0 | [log](evidence/before/pytest-existing.json), [JUnit](evidence/before/pytest-existing.xml) |
| Previa caracterización | 0 | 0 | 0 / 0 | 0 / 11 / 0 | [log](evidence/before/pytest-characterization.json) |
| Primer contraste original | 1 | 66 métodos + 12 subpruebas | 2 / 0 | 0 / 0 / 0 | [rechazo adelantado](evidence/attempts/early-original.json) |
| Primer contraste caracterización | 1 | 0 | 4 XPASS estrictos / 0 | 0 / 7 / 4 | [reproducción de corrección](evidence/attempts/early-xpass.json) |
| Final original | 0 | 68 métodos + 12 subpruebas | 0 / 0 | 0 / 0 / 0 | [log](evidence/after/pytest-original.json), [JUnit](evidence/after/pytest-original.xml) |
| Final caracterización | 0 | 4 pruebas | 0 / 0 | 0 / 8 / 0 | [log](evidence/after/pytest-characterization.json), [JUnit](evidence/after/pytest-characterization.xml) |
| Final contratos HFS-011 | 0 | 664 casos parametrizados/pruebas | 0 / 0 | 0 / 0 / 0 | [log](evidence/after/pytest-contracts.json), [JUnit](evidence/after/pytest-contracts.xml) |

Los 80 registros JUnit de la suite original no son 80 métodos. Los 8 xfail se codifican como skipped en JUnit pero no son omisiones ordinarias ni pruebas aprobadas. Las ejecuciones finales no emitieron advertencias. Las previas incluían la de `Section.Config` deprecado; se reemplazó por ConfigDict al adoptar el contrato común.

Nuevas pruebas: extras en los 18 modelos, todos sus campos numéricos frente a NaN/±inf/bool/cadenas, dominios positivos/factores/conteos, coordenadas firmadas, ubicación de errores anidados, cargas ausentes/cero, contradicción y roundtrip de cortantes, longitudes, anclajes, mutaciones/model_copy, sección seleccionada, datos compuestos, parser/escalado de catálogo, opciones CLI y errores CLI reales. No son oráculos AISC ni tests de redacción.

Incidencias conservadas:

- El primer pip en sandbox falló por socket WinError 10013 (exit 1); se completó con el mecanismo de escalación, sin cambiar ACL. No hubo rechazo del revisor automático.
- Se inició una primera captura antes de que terminara la instalación: un error de colección `ModuleNotFoundError: pydantic`, exit 2. Se conservó el [log](evidence/attempts/installation-race.json) y se repitió en carpeta nueva tras completar la instalación. No se marcó xfail ni se contó como regresión de código.
- La primera prueba dirigida detectó un error de implementación en el dominio de Ix negativo (1 fallo, 617 aprobadas): se corrigieron tipos de inercias/módulos/radios y se amplió la prueba negativa a todas las propiedades geométricas sin signo. [JUnit inicial](evidence/attempts/initial-contracts.xml). La corrida intermedia ya pasó 657 casos antes de añadir las pruebas de transporte finales; [verificación](evidence/attempts/intermediate-verification.json).
- Los dos fallos originales fueron por rechazo Pydantic anterior a entrar al `assertRaises` del motor (U>1 y xa<0). Se preservó su expectativa de rechazo en el motor usando objetos manipulados; las pruebas nuevas verifican el rechazo temprano. No se ajustó ninguna expectativa resistente congelada.

## Diferencias numéricas y caracterización

[Comparación por ejemplo](evidence/after/comparison.json), [captura previa](evidence/before/engine-results.json), [captura final](evidence/after/engine-results.json), [verificación final](evidence/after/verification.json).

Los **12 archivos de ejemplo conservan exactamente el resultado completo del motor**, incluidos checks, capacidades, demandas, DCR, estados y trazas; el caso de doble ángulo conserva su error por datos faltantes. No se redondeó ni eliminó un campo ingenieril para comparar. Tolerancia de comparación: igualdad exacta; se compararon 1679 valores numéricos y la diferencia absoluta máxima fue **0**. Hash canónico conjunto antes/después:

`040b93b81b47b090f46ebe2e9018e9fd8697b60aac93fd4bcd1c3a2fb2ba5403`

Esto acredita regresión para esos casos, no corrección de sus capacidades. Se mantienen 1228 registros y 1223 identidades en catálogo; no se resolvieron duplicados. No se añadió una tolerancia de PASS/FAIL. Los ensayos contractuales usan fronteras exactas de positividad, unidad y cardinalidad; no cambian umbrales resistentes.

Cuatro sondas HFS-000 pasan ahora por rechazo demostrado: typo F-04, NaN F-10, mezcla Vu F-08 y loads vacío F-02. Tras observar XPASS se retiraron sus marcas estrictas, manteniendo las pruebas de seguridad. Se añadió el caso residual `loads={"Pu":0}` como xfail estricto F-02: aún produce PASS sin checks. Los otros siete xfail históricos permanecen. [Seguimiento vivo](../tracking.md) distingue F-04 contractual y avances parciales F-08/10/22; no se cierra F-02 ni se altera evidencia histórica.

Cambio intencional de representación: `{Vux:3,Vuy:4}` ya no produce Vu=5; conserva Vu=0 como componente legacy inactiva. Las demandas y cálculos que consumen componentes no cambian en los ejemplos. Fu/Rg/Rp ausentes, typos, no finitos y geometrías inválidas pasan de aceptación/fallback a error; no hay una nueva capacidad calculada para esas entradas.

## Archivos modificados y evidencia

| Archivos | Propósito |
|---|---|
| `src/steel_design/input_contracts.py` (nuevo) | Política local compartida, tipos y revalidación |
| `src/steel_design/models.py`, `sections/models.py` | Contratos de todos los modelos de entrada; salida preservada |
| `src/steel_design/domain/validation.py`, `engine.py` | Relaciones, sección seleccionada, revalidación y error de rango custom |
| `src/steel_design/domain/routing/profile_router.py` | Solo guarda defensiva de finitud |
| `src/steel_design/sections/loader.py` | Finitud de parseo/escalado y errores contextualizados |
| `src/steel_design/run.py` | Opciones CLI estrictas, claves duplicadas y detalle de error |
| `tests/test_hfs011_input_contracts.py` (nuevo) | Pruebas de contrato y CLI |
| `tests/test_chapter_e_rules.py`, `test_custom_solid_sections.py` | Adaptar dos pruebas de defensa del motor al rechazo temprano |
| `tests/test_hfs000_characterization.py` | Cuatro correcciones demostradas y reproducción residual F-02 |
| `scripts/audit_hfs011.py` (nuevo) | Captura reproducible de suites separadas y comparación; reutiliza auditor HFS-000 intacto |
| `README.md`, `CONTRIBUTING.md`, `docs/ROADMAP.md`, `docs/architecture/dry-inventory.md`, `docs/audit/tracking.md` | Migración, suites separadas, alcance, responsables y seguimiento |
| `docs/contracts/hfs011-inputs.md` (nuevo) | Inventario completo, defaults, decisiones y rupturas JSON |
| Este informe y `evidence/` (nuevos) | Resultados, fallos intermedios, entornos, hashes y procedencia |

[Manifiesto de evidencia](evidence/manifest.json): 27 archivos promovidos por copia, con origen y hash; los originales exploratorios siguen en `.venv/`. No se borró, movió ni sobrescribió HFS-000, PDFs, catálogos, resultados históricos o carpetas con errores de acceso. Los hashes de entradas de la captura final coinciden con el código entregado; no se editaron fuentes durante esa captura.

[Comprobaciones finales](final-checks.json): `git diff --check` exit 0, enlaces locales de documentos modificados sin roturas, hashes de evidencia/entradas sin discrepancias y ausencia de cambios en ecuaciones, reglas, catálogo, ejemplos y evidencia congelada. La revisión documental no añade tests que reproduzcan redacción.

Reproducción posterior, usando carpetas nuevas:

```powershell
.\.venv\hfs011\Scripts\python.exe scripts/audit_hfs011.py --baseline docs/audit/hfs011/evidence/before/engine-results.json --out .venv/hfs011-recheck --work .venv/hfs011-recheck-work
git diff --check
```

## Riesgos residuales y revisión requerida

1. HFS-010 pendiente: cero explícito, checks omitidos y cobertura incompleta aún pueden producir PASS. F-01/02/03/31/33/34/35/36/38 no se resuelven aquí. La documentación de entradas no redefine el alcance como lo que ejecutó el router.
2. F-08/11/06: se elimina pérdida de demanda, pero no se valida física de ejes ni máximo de cocientes H3. Se conserva la ruta legacy; revisar HFS-013 antes de anunciar correspondencia física.
3. F-22: defaults K/Cb/E/método y cargas parciales quedan explícitos, pero no acreditan combinaciones, estabilidad global, arriostramiento ni procedencia. Revisar técnicamente esta política de compatibilidad y migración.
4. F-10/13/14/27: se bloquea finitud/dominio local y sección seleccionada inválida; identidad, unidades, coherencia integral y procedencia del catálogo siguen pendientes. No se infiere OD desde ID ni se cambia b+3t, D/t o espesor de diseño.
5. No se acredita detallado completo de compuestos, interferencias de barras, elegibilidad I1 ni correspondencia normativa del recubrimiento. El motor recibe números finitos sin un máximo ingenieril arbitrario; operaciones extremas finitas aún pueden exceder el rango de otros cálculos. Endurecer todos los kernels escalares o los resultados no forma parte de esta tarea.
6. Cambios JSON incompatibles: los consumidores deben seguir la [guía de migración](../../contracts/hfs011-inputs.md). No completar faltantes copiando antiguos defaults sin evidencia. Los modelos de resultados, reporte de unidades/DCR y semántica FAIL/exit mantienen sus defectos y contratos actuales.

Pendiente aprobación técnica de HFS-011 y de las decisiones contractuales; no se inicia otra tarea automáticamente.
