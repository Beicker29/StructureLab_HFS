# HFS-022R — Consolidación y verificación independiente de contratos

Fecha: 2026-10-28. Estado: entrega para revisión técnica independiente; cierre
condicionado a la CI Windows/Ubuntu del commit que publique el usuario. Trabajo
directo en `main`, base `bae64633751ae96bd9780ce626045f2da0c66cc9`, inicialmente
sin cambios locales. No se crea rama, PR, commit ni push. Distribución 0.2.0,
contratos 1.0 y cobertura HFS-010-v1 se conservan.

La base fue aprobada por el usuario. Se consultó el run
[40777094705](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40777094705):
SUCCESS para ese SHA, tanto Ubuntu como Windows; respuesta identificable en
[base-ci.json](evidence/base-ci.json). No se confunde esa aprobación con CI de
estos cambios locales. El [informe HFS-022](../report.md), inventario y evidencia
anteriores permanecen intactos.

## Diagnóstico y decisión arquitectónica

La importación original era `contracts → execution → engine`. El motor se
importaba en execution para sus anotaciones, no para preparar una entrada.
Un proceso nuevo cargaba **40 módulos** de steel_design, incluyendo router,
reglas, evaluadores y repositorio. No se observó una ejecución de capacidades
al importar; el defecto demostrado era dependencia innecesaria, no un cálculo
oculto. La sonda nueva que prohíbe importar ejecución fallaba antes del cambio.

| Alternativa | Beneficio | Costos y riesgo | Decisión |
|---|---|---|---|
| A: TYPE_CHECKING y anotaciones diferidas en execution | Retira el import del motor con menos movimiento | Mantiene contratos dependiendo de ejecución; la evaluación runtime de anotaciones cambia o requiere resolver sus nombres de otra manera | Viable, no elegida |
| B: un módulo preparation con cinco símbolos relacionados | Separa preparación y ejecución para dos consumidores reales, mantiene anotaciones de ejecución y una única validación/merge | Un archivo adicional; cambia el propietario de objetos trasladados | Elegida |
| Dividir contracts por longitud, añadir servicios o interfaces genéricas | Ningún beneficio demostrado para esta revisión | Más capas, API y puntos de divergencia | Descartada |

Se trasladan juntos `OutputOptions`, `merge_case_payload`,
`extract_output_options`, `validate_bundle_shape` y `prepare_cases`.
`execution` reexporta esos mismos objetos; no conserva cuerpos duplicados ni
wrappers nuevos. La comparación AST contra Git acredita cuerpos, firmas y
defaults intactos, así como todas las clases/funciones restantes de execution.
Las firmas se cotejan además entre las instalaciones wheel anterior y posterior.

Los imports públicos de execution y las fachadas comprometidas de run se
conservan por identidad; la API HFS-021/021A justifica su permanencia. Cambia
`__module__` a `steel_design.preparation`; no se promete compatibilidad de
persistencia pickle entre versiones. No hay compromiso documentado ni consumidor
identificado de esa representación. No se modifica `run.py`, sus aliases,
entry points o las anotaciones de sus servicios. El módulo nuevo es propietario
interno; no obliga a migrar a los consumidores públicos existentes.

### Dependencias y responsabilidades finales

| Componente | Dependencias propias relevantes | Responsabilidad / consumidores |
|---|---|---|
| preparation | InputModel, SteelCase, results_model y errores de dominio | Preparación local, merge profundo, opciones y guardas de forma; contracts y execution |
| contracts | preparation, modelos, input_contracts y domain.validation | Transporte, revalidación, integridad, migración explícita y esquemas |
| domain.validation | Modelos/método y constante `axial_calc.NORMATIVE_E_MPA` | Guardas canónicas de caso; no se mueven ni duplican |
| execution | preparation y engine | Iteración secuencial y llamadas al motor; CLI y API |
| run / reporting | Servicios existentes | Adaptación de CLI y presentación, sin cambios |

Importar contracts carga ahora **16 módulos** del proyecto. No carga execution,
engine, run, reporting, repositorio, geometría, cobertura ejecutable, router,
reglas ni evaluadores. Se conserva el import de axial_calc requerido por la
guarda E; no se duplica su constante ni se desplaza la guarda para mejorar una
estadística de imports. La prueba instrumentada bloquea llamadas a funciones
de cálculo, lectura de JSON/XLSX/PDF/SVG, escritura, creación de directorios,
red y subprocess dentro del proceso comprobado. Además de importar, migra y
revalida entradas individual y bundle. Las importaciones Python normales de
código no se consideran archivos de aplicación.

La preparación conserva el orden de errores y su pereza: la forma completa de
`cases` se comprueba antes de ejecutar; la validación local de cada caso ocurre
al consumirlo. Si el segundo caso tiene un campo inválido, el primero ya se
ejecutó y no se ejecutan los siguientes. La validación optativa de contratos
examina todos los casos sin ejecutar ninguno, como en HFS-022.

## Verificación independiente de JSON Schema

Se añade **jsonschema 4.26.0 solo al extra dev**. No es dependencia runtime,
no se llama desde el motor ni sustituye a Pydantic. Se fijan attrs 26.1.0,
jsonschema-specifications 2025.9.1, referencing 0.37.0 y rpds-py 2026.9.1 en
constraints; typing_extensions ya estaba fijado. Versiones resueltas e
instaladas están en los freezes y reportes pip archivados. El verificador toma
los requisitos directos de pyproject; no mantiene otro listado de versiones.

La elección de `Draft202012Validator.check_schema` y `validate` sigue la
[documentación oficial del validador](https://python-jsonschema.readthedocs.io/en/stable/validate/).
Las pruebas leen **los diez archivos congelados**, no los generados en memoria.
Cubren los cinco tipos por ambos modos: dialecto, documentos completos generados
por la API, envolturas/versiones/kind, campos obligatorios, extras, estructuras,
enums, null, tipos numéricos y referencias locales. Recorren también definiciones
no alcanzadas por los fragmentos de bundle; validan las migraciones de los doce
ejemplos en ambos modos. Los fixtures existentes aportan entradas, nunca los
esperados del validador independiente.

No se encontró una restricción estructural faltante que justificara cambiar
los esquemas publicados. Se conservan los diez JSON y su manifiesto byte por
byte. `generate_hfs022_schemas.py --check` se ejecuta sobre las tres instalaciones.

| Restricción | JSON Schema congelado | Validación Python canónica |
|---|---|---|
| Envoltura, versión/kind, tipos, enums, campos obligatorios y extras tipados | Sí | Sí |
| Referencias `$ref`, límites locales de modelos y null declarados | Sí | Sí |
| Merge profundo y restricciones del caso efectivo | Fragmentos deliberadamente abiertos en sus valores; no aplica prematuramente el esquema efectivo | prepare_cases y SteelCase |
| Fy/Fu, bloqueos de método y otras relaciones de dominio | No representa todas las relaciones | Modelos y validate_case |
| DCR/display/estado/known_failures/complete coherentes | Describe sus tipos/presencia | Constructores y agregadores originales más cotejo del contrato |
| IDs, índices, enlaces y aceptación de cobertura | Describe estructura | Integridad referencial, sin acreditar resistencia |
| Índice escrito como `0.0` | Es entero matemático según JSON Schema | La lectura estricta exige entero; se rechaza sin coerción |
| Claves JSON duplicadas, no finitos, pérdida al convertir entero a float | No sustituye decodificación/controles de representación | Parser y controles canónicos |
| JSON dinámico en details/evidence | Estructura abierta | JSON finito y sin pérdida; no acredita semántica normativa |

Dieciséis pruebas (ocho casos por dos modos) demuestran documentos aceptados
por el esquema pero rechazados por Python. No se crea un segundo sistema de
reglas para forzar equivalencia. Un esquema aceptado no es validación AISC ni
prueba de completitud de cobertura.

## Diagnósticos e integridad (P2)

Se conservan códigos, tipos de excepción y encadenamiento de causas. La mejora
observable está en `ContractError.path`, precisada mediante JSON Pointer:

| Reproducción | Antes | Después |
|---|---|---|
| accepted_checks fuera de executed_checks | `""` (documento completo) | `/payload/coverage/obligations/0/accepted_checks` |
| Índice de ejecución repetido | `""` (documento completo) | `/payload/coverage/executions/1/check_index` |
| DCR contradictorio de check anidado | `""` (documento completo) | `/payload/checks/0/dcr` |
| known_failures omitido en snapshot completo | `/payload` | `/payload/known_failures` |
| Opción de salida de tipo inválido | `/payload` | `/output/write_results_json` |
| Pu inválido en segundo caso efectivo | `/payload` | `/payload/cases/1/loads/Pu` |
| Infinito en details al serializar modelo | `/details/a~1b~0c/0` | `/payload/details/a~1b~0c/0` |

`_coverage_integrity` distingue duplicados, índices no contiguos, referencias,
claims, aplicabilidad y evidencia aceptada sin cambiar sus condiciones.
`_output_integrity` compara por campo con el constructor original, sin copiar
la fórmula de DCR. `_same` señala la primera clave ausente/extra y mantiene
exactitud y cero con signo. `_validate` conserva sus etapas y añade el índice
del caso efectivo incluso si falla el siguiente elemento del iterador.
`_validation_path` proyecta ubicaciones de Pydantic/dominio; todos los detalles
originales permanecen en `__cause__`. No adivina campos desde un mensaje.

Las ubicaciones de bundle describen el caso efectivo: un campo heredado puede
estar en la base común y no literalmente en el override señalado. Las guardas
de forma conservan la ubicación original de cases. Cuando el productor no
identifica un campo, se conserva la ubicación del objeto. Ante varios defectos
simultáneos, puede variar el primer diagnóstico de integridad; no se promete
reportar todos ni se modifica la secuencia del CLI legacy.

`_strip_derived` se conserva: su recursión por metadatos Pydantic tiene una
responsabilidad coherente. La prueba nueva demuestra que claves como display,
complete y known_failures dentro de JSON dinámico no desaparecen. No se separa
contracts por tamaño ni se cambian constructores/agregadores.

## Auditoría de riesgos y pruebas nuevas

| Riesgo revisado | Evidencia / decisión |
|---|---|
| Claves duplicadas, versiones futuras, documentos parciales y defaults | Regresión HFS-022 existente; nuevos casos de envoltura/obligatoriedad con validador independiente |
| Derivados manipulados, índices/IDs repetidos y enlaces contradictorios | Reproducciones existentes conservadas; nuevos pointers exactos y referencias schema |
| No finitos, mutación Pydantic, claves dinámicas no textuales, legacy con pérdida | Pruebas originales conservadas; nueva ubicación al serializar y causa de dominio |
| Entero no representable como float | Rechazo original de entrada/bundle preservado; nuevo entero `2**64+1` en mapa dinámico permanece int exacto |
| Ceros positivo/negativo, null y booleanos como números | Casos originales y nuevas pruebas independientes de tipos/null y roundtrip |
| Placeholder PASS 0/0 | Pruebas HFS-022 preservadas: no se convierte en resistencia acreditada |
| Overrides parciales y opciones | Casos de override que reparan una base inválida; rechazo de opciones de tipo incorrecto; alias y orden históricos |
| Acoplamiento y efectos de importación | Proceso nuevo con imports/efectos/cálculos prohibidos, comprobado con wheel y editable |

La primera ejecución de la nueva suite, **antes de modificar producción**,
dio 234 aprobadas y 16 fallidas (exit 1): una prueba de importación, catorce de
diagnóstico y una de identidad que esperaba el módulo todavía inexistente.
Esta última es una prueba del diseño nuevo, no un defecto histórico. Las otras
quince reproducen las observaciones antes de corregirlas. No se introducen
xfail ni se relajan expectativas previas. Las 250 iniciales pasaron después,
junto con las 233 HFS-022 (483 aprobadas); se añadieron ocho verificaciones de
frontera, opciones, overrides y ubicaciones. Suite final nueva: **258 aprobadas**.
Los logs/JUnit antes y después se conservan en development.zip. Como control
adicional se ejecutó la versión final de las 258 pruebas contra el wheel
original instalado: **238 aprobadas, 20 fallidas**, exit 1. Incluye los cuatro
diagnósticos adicionales de salida independiente, causa de dominio y forma del
bundle. Para esta reproducción posterior se añadió jsonschema únicamente a
ese entorno temporal, después de congelar la captura anterior; no se modificó
su wheel ni se sobrescribieron sus freezes históricos. El comando, cwd, exit
y salidas están en `baseline-final-review.json` dentro de development.zip.

## Regresión y reproducción

Entorno: Windows, Python **3.12.10** AMD64, pytest 9.1.1, Pydantic 2.14.1/core
2.50.1, openpyxl 3.1.5, Ruff 0.17.3, build 1.6.1, twine 7.0.0. Los freezes
completos y comandos con cwd/exit/stdout/stderr están archivados; las versiones
anteriores y posteriores se distinguen. Desarrollo usa `.venv/21dev`.

Comandos principales realmente ejecutados (Git de GitHub Desktop incorporado
a PATH; el verificador fija UTF-8 y desactiva plugins pytest externos):

```powershell
.venv/21dev/Scripts/python.exe -X utf8 scripts/verify_hfs020.py --out .venv/22r-before
.venv/21dev/Scripts/python.exe -X utf8 scripts/verify_hfs020.py --out .venv/22r-after
.venv/21dev/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_hfs022r_review.py
.venv/21dev/Scripts/python.exe -X utf8 scripts/audit_hfs022r.py --before .venv/22r-before --after .venv/22r-after --development .venv/22r-work
```

Los comandos completos de las suites finales, incluyendo JUnit/basetemp,
se registran en ambas capturas; desarrollo conserva además sus logs y JUnit.
La referencia anterior se construyó antes de los
cambios productivos y sus pruebas/ejemplos usan ese wheel; el nuevo wheel se
compara además con las fuentes finales. No se copian fuentes productivas al
directorio externo de pruebas. Las instalaciones normal/wheel importan su
paquete instalado; editable resuelve src desde fuera del checkout por diseño.

Los dos verificadores completos terminaron con **exit 0**. Recuentos de
métodos/casos parametrizados (las 12 subpruebas se cuentan aparte):

| Suite | Antes | Después |
|---|---:|---:|
| Original | 68 +12 subpruebas | 68 +12 subpruebas |
| Caracterización HFS-000 | 12 | 12 |
| HFS-011 | 665 | 665 |
| HFS-016 | 44 | 44 |
| HFS-010 | 57 | 57 |
| HFS-012 | 61 | 61 |
| HFS-013 ejes/H3 | 57 | 57 |
| HFS-013 método | 73 | 73 |
| HFS-014 | 72 | 72 |
| HFS-015 | 84 | 84 |
| HFS-017 | 468 | 468 |
| HFS-020 comparadores | 50 | 50 |
| HFS-021 ejecución | 51 | 51 |
| HFS-021A API | 28 | 28 |
| HFS-021A SVG | 29 | 29 |
| HFS-022 contratos | 233 | 233 |
| HFS-022R | 238 pasan /20 fallan sobre wheel base, reproducción separada | 258 |
| **Total regresión de la base / final** | **2052 +12 subpruebas** | **2310 +12 subpruebas** |

Las 16 suites preexistentes y las 17 finales tienen **0 fallidas, 0 errores,
0 omitidas, 0 xfail y 0 xpass**. Los fallos deliberados de reproducción sobre
la base se reportan aparte; no se suman al total histórico. El JUnit original
reporta 80 entradas porque incluye sus 12 subpruebas; no son 80 métodos.
En editable, fuera del checkout, pasaron además las 28 de API y las 258 nuevas
(verificaciones adicionales, no se suman otra vez al total).

| Comprobación | Resultado observado |
|---|---|
| Wheel/sdist y sus contenidos | Construidos/verificados antes y después; paquete de 45 a 46 archivos Python |
| Instalaciones normal, wheel y editable | Exit 0; imports y CLI fuera del checkout; sin fuente productiva copiada al directorio de pruebas |
| Ruff, pip check, twine check --strict | Exit 0 antes y después; pip check adicional en entornos finales con herramientas de prueba |
| Esquemas con --check | Exit 0 en las tres instalaciones, antes y después; archivos/manifest históricos intactos |
| Doce ejemplos del motor | Iguales contra HFS-017 y entre capturas, incluyendo errores comprometidos |
| Veinticuatro escenarios CLI/memorias | Iguales bajo comparador histórico exacto y procedencia de entradas; mismos exits |
| Seis SVG | Bytes idénticos antes/después en Windows; también pasan la comparación histórica que permite únicamente CRLF/LF |
| Contratos/migraciones versionados | 28 documentos serializados idénticos (5 tipos, 12 entradas, 11 resultados) y mismo código de rechazo del error histórico restante |
| Dependencia runtime jsonschema | Ausente de los seis freezes iniciales de instalación (tres por captura); presente solo al añadir herramientas de pruebas |
| Fuentes finales frente al wheel probado | Iguales; únicos cambios runtime: contracts, execution y nuevo preparation |

No hay diferencias numéricas de demanda, capacidad o DCR, ni de estado,
cobertura, trazas, JSON legacy, opciones o artefactos. Las únicas diferencias
intencionales son propiedad/importación Python y precisión del diagnóstico
contractual. Los rechazos CLI del namespace retirado y catálogo implícito
ausente siguen con **exit 1 esperado**, sin confundirse con fallos de suite.

### Conservación de evidencia y límites del entorno

`before.zip` y `after.zip` contienen capturas, comandos, JUnit, entornos,
wheel/sdist, entradas identificadas por hash y SVG originales. `development.zip`
conserva reproducciones y sondas. `archives.json` identifica cada miembro por
tamaño/hash; `SHA256SUMS.json` identifica los archivos del suplemento. Se
reutilizan el archivador y comparadores históricos; no se duplican sus políticas.
`scope.json` coteja contra Git fuentes protegidas, catálogo, pruebas previas,
esquemas y evidencia HFS-022 anterior, además del traslado AST de preparación.
`contract-comparison.json` contiene firmas/propietarios/grafo y cotejo de
snapshots; `runtime-wheel.json` vincula fuentes finales con wheel probado.

Las 31 advertencias iniciales de acceso afectan directorios temporales
históricos: diez bajo `.tmp_test`, una caché pytest y veinte bajo
`tests/.tmp_tests`. Se conservan; no se eliminan ni se cambian permisos.
La ejecución aislada requiere el mecanismo de permisos del entorno para crear
y usar temporales externos; no se transforma una restricción de infraestructura
en xfail ni en fallo normativo. Las rutas externas aparecen en las capturas;
los ZIP permiten recuperar la evidencia aun si esos temporales desaparecen.

## Inventario y control de alcance

| Archivos | Cambio / motivo |
|---|---|
| `src/steel_design/preparation.py` (nuevo) | Propietario único de los cinco símbolos de preparación |
| `src/steel_design/execution.py` | Retira los cuerpos trasladados; reexports e importaciones necesarias |
| `src/steel_design/contracts.py` | Import independiente de ejecución y diagnósticos precisos |
| `tests/test_hfs022r_review.py` (nuevo) | 258 pruebas arquitectónicas, independientes de schema y de diagnóstico |
| `pyproject.toml`, `requirements/ci-constraints.txt` | Herramienta independiente solo dev y resolución fijada |
| `scripts/verify_hfs020.py` | Nueva suite, herramientas de test desde pyproject, freeze/check de entornos de pruebas y suite editable |
| `scripts/audit_hfs022r.py` (nuevo) | Sondas instaladas, prueba de alcance y evidencia; reutiliza comparadores/archivador |
| `AGENTS.md`, `CONTRIBUTING.md` | Frontera canónica y reproducción/verificación independiente |
| `docs/contracts/hfs022-versioned-json.md`, `docs/adr/002-contracts-errors.md` | Decisión, contratos preservados, precisión y límites |
| `docs/architecture/dry-inventory.md`, `docs/ROADMAP.md` | Propietarios vigentes y estado real de revisión |
| `docs/audit/hfs022/architecture-review/` (nuevo) | Este suplemento y evidencia identificada por hash |

La lista exhaustiva, incluidos los artefactos de evidencia, está en
[file-inventory.json](evidence/file-inventory.json), con exclusiones de hash
autorreferente explícitas. No se borra evidencia ni código que siga teniendo
consumidores. Se retiran únicamente definiciones e imports sustituidos en
execution. No se modifican fórmulas, factores, nominales, geometría, solver,
catálogo, router, guardas normativas ni resultados_model. En particular,
CheckResult.from_values, EngineResult.aggregate y CoverageReport.complete
permanecen íntegros. F-31 sigue **P0 abierto**, F-32 conserva su contrato.

## Riesgos residuales y recomendación

La validación estructural no autentica documentos ni descubre una falsificación
coherente; tampoco acredita capacidades, matriz normativa o trazabilidad
semántica de mapas dinámicos. Las limitaciones previas siguen visibles. El
import de axial_calc por su constante se mantiene justificadamente. Las
ubicaciones de casos efectivos y el cambio de propietario Python quedan
documentados, sin promesas adicionales de persistencia o introspección.

Recomendación: someter el suplemento a revisión técnica independiente con
esta evidencia, sin autoasignar una calificación ni aprobación plena. La
condición pendiente es publicar por decisión del usuario y obtener SUCCESS
Windows/Ubuntu sobre **ese commit final**. La CI aprobada de la base no cubre
este diff. No se inicia HFS-023, HFS-024, web ni otra tarea.
