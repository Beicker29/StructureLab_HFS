# HFS-022 — Contratos JSON versionados y migración controlada

Fecha: 2026-10-28, America/Bogota. Base verificada: `main`,
`c91e55d5a194dfb8e80777d9e41efa1ee4b7fe02`, árbol inicial sin cambios locales.
Se conservaron advertencias históricas de acceso; sin limpieza ni cambios de ACL.
Entrega exclusivamente HFS-022, sin ramas, PR, commits, pushes ni publicación.
**Para revisión independiente; no cerrado.** CI remota Windows/Ubuntu de los
cambios finales pendiente de publicación por el usuario.

Verificación final local: **exit 0, accepted=true; 2052 pruebas +12 subpruebas**,
con 1819 anteriores y 233 HFS-022, todas aprobadas. Cero fallidas, errores,
omitidas, xfail o XPASS. Quedan pendientes la revisión independiente y la CI
remota de esta entrega.

## Preparación y diagnóstico previo

Se leyeron AGENTS, CONTRIBUTING, roadmap, ADR-001/002/003, contratos
HFS-010/011/014/017/021/021A, inventario DRY e informe/inventario de consumidores
HFS-021B. Se inspeccionaron models, results_model, input_contracts, execution,
reporting, run, coverage y vínculos de evidencia. El inventario generado
registra campos, aliases, defaults, computed fields, validadores, serializadores
y consumidores vigentes; no sustituye los informes históricos.

La base publicada pasó el
[run 40743600221](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40743600221):
Ubuntu 24.04 job **123011397358**, Windows 2022 job **123011397895**, ambos
completed/success para el SHA exacto. [Consulta conservada](evidence/base-ci.json).
No se activó, reejecutó ni publicó un workflow. Esa CI no acredita esta entrega.

Hallazgos contractuales principales:

1. El JSON actual es legacy sin versión explícita; distribución 0.2.0,
   cobertura HFS-010-v1 y AISC 360-22 identifican conceptos distintos.
2. El bundle no es `list[SteelCase]`: contiene base/overrides parciales con
   merge profundo, nombres y opciones. Aplanarlo perdería semántica/procedencia.
3. Las salidas Pydantic pueden ignorar extras, recalcular estado y generar
   propiedades computadas. Deserializar directamente no detecta que un
   `status`, `complete`, `known_failures` o display publicado fue manipulado.
4. Los detalles dinámicos no tienen esquema normativo exhaustivo. Las memorias
   reorganizan información y el CLI compacto omite details; no son snapshots
   completos del motor. El fixture histórico tiene 11 resultados y un error
   esperado de doble ángulo, no 12 resultados de resistencia válidos.
5. Proyecciones no finitas y snapshots antiguos redondeados no siempre pueden
   reconstruirse sin pérdida. Se requiere rechazo explícito, no reparación.

El diagnóstico y la decisión arquitectónica se comunicaron antes de implementar.
El [contrato](../../contracts/hfs022-versioned-json.md) desarrolla alternativas,
compatibilidad, funciones, errores y límites; el [inventario](inventory.md)
identifica responsabilidades y consumidores.

## Decisiones e implementación

- Una capa optativa `steel_design.contracts`: cinco kinds, envoltura 1.0,
  validación, serialización/deserialización, migración explícita y schemas.
  `ContractDocument` es solo transporte. Los payloads siguen siendo los modelos
  canónicos; el bundle conserva su dict de fragmentos. Ninguna versión añadida
  a modelos ingenieriles ni framework de registro/plugins.
- `case_input` conserva campos explícitos/defaults/ausencias con exclude_unset.
  Sus opciones están en la envoltura como OutputOptions, sin duplicar el caso.
  Las opciones legacy se migran explícitamente; el flujo CLI sigue intacto.
- `execution.prepare_cases` comparte el cuerpo de preparación anteriormente
  embebido en iter_executions. Se conserva pereza, orden de errores, merge,
  nombres, opciones y llamadas de ejecución. La validación de contratos puede
  recorrer todo el bundle sin efectos y sin ejecutar el motor.
- `input_contracts.unique_json_object` posee la política productiva de claves
  duplicadas, extraída literalmente de run. La fachada antigua conserva
  identidad con el nuevo propietario, ValueError y mensaje.
- Las salidas exigen snapshot completo; migración compatible puede completar
  defaults omitidos. Se comparan los valores declarados contra la reconstrucción
  canónica; se rechazan extras, pérdidas, no finitos, contradicciones de estado
  y referencias. Los índices mantienen base cero.
- La coherencia aritmética del check reutiliza `CheckResult.from_values`;
  no hay otra ecuación DCR/estado ni cálculo de capacidad. Agregación y complete
  permanecen en sus modelos originales. No se consulta el router para acreditar.
- Se conserva el placeholder inactivo 0/0 fuera de resistencia aceptada. La
  revisión final reprodujo un documento sintético contradictorio que enlazaba
  ese placeholder como resistencia acreditada. El contrato ahora lo rechaza
  con COVERAGE_CONFLICT; no modifica EngineResult ni la acreditación del motor.
- Diez schemas y manifiesto se generan desde Pydantic con dependencias fijadas.
  Verificación sin escritura y regla Git UTF-8/LF acotada a esos archivos.
  Los schemas no pretenden expresar merge, todas las relaciones cruzadas ni
  autenticidad normativa. No se añade una dependencia de JSON Schema externa.
- Se conserva distribución 0.2.0 durante la revisión sin release. El contrato
  1.0 no es versión de paquete. Un incremento para publicar la API nueva debe
  decidirse como release, no inferirse de la envoltura JSON.

No se implementa registro normativo, nueva traza HFS-024, web, solver, geometría,
catálogo, soporte ASD adicional ni corrección de F-31. **F-31 sigue P0 abierto**;
F-32 permanece: exit 0 puede acompañar FAIL o INCOMPLETE estructural.

## Verificación y evidencia reproducible

Entorno local: Windows, CPython **3.12.10**, pytest **9.1.1**, Pydantic
**2.14.1/core 2.50.1**, openpyxl **3.1.5**, build **1.6.1**, Ruff **0.17.3**,
twine **7.0.0**. Resolución fijada en requirements/ci-constraints.txt, sin
modificaciones. Freeze completo por instalación, comandos, cwd, exit,
stdout/stderr y JUnit están en los archivos de evidencia.

La base `.venv/22-before` pasó 1819 métodos +12 subpruebas. La corrida
intermedia `.venv/22-after` pasó esas mismas pruebas y 232 nuevas. La guarda
final de placeholder añadió una prueba; la suite dirigida final pasó **233**.
La captura completa final `.venv/22-final` también pasó las **233** nuevas y
las **1819** anteriores. Las 28 pruebas API repetidas en editable son
adicionales y no se suman a los 2052 métodos. Dieciséis suites separadas.

| Suite | Base previa | Final |
|---|---:|---:|
| Original | 68 métodos +12 subpruebas | 68 métodos +12 subpruebas |
| Caracterización HFS-000 | 12 | 12 |
| HFS-011 | 665 | 665 |
| HFS-016 | 44 | 44 |
| HFS-010 | 57 | 57 |
| HFS-012 | 61 | 61 |
| HFS-013 direccional | 57 | 57 |
| HFS-013 método | 73 | 73 |
| HFS-014 | 72 | 72 |
| HFS-015 | 84 | 84 |
| HFS-017 | 468 | 468 |
| HFS-020 | 50 | 50 |
| HFS-021 | 51 | 51 |
| HFS-021A API | 28 | 28 |
| HFS-021A SVG | 29 | 29 |
| HFS-022 | — | 233 |
| **Total sin subpruebas** | **1819** | **2052** |

La nueva suite cubre los cinco contratos y sus identidades canónicas; métodos,
signos, ejes, defaults y ausencias; aliases y merge de lotes; precisión y cero
con signo; versiones desconocidas; campos/JSON inválidos; no finitos; enums,
nulls y lotes vacíos; campos derivados y decisiones contradictorias; índices,
referencias y evidencia; placeholders; imports sin efectos; migración histórica,
los 12 inputs existentes y schemas congelados/deterministas. Los esperados son
invariantes de transporte, ejemplos sintéticos explícitos y evidencia histórica;
no se presentan como oráculos AISC. Las suites numéricas anteriores permanecen
sin editar y siguen separadas de caracterización.

El verificador común construye sdist y wheel desde sdist, inspecciona contenido,
ejecuta twine estricto/Ruff, instala normal/wheel/editable en carpetas externas,
ejecuta pip check por entorno, probes de identidad y entry points, todas las
suites en wheel, API editable, 12 ejemplos, 24 recorridos CLI/memoria y seis
SVG. Los schemas se contrastan con cada una de las tres instalaciones.
No hay fuentes productivos copiados en la carpeta externa de pruebas.
**Diferencias ingenieriles: ninguna** en las capturas comparadas: capacidades,
demandas, DCR, estados, cobertura y trazas coinciden exactamente bajo la
política vigente. Los seis SVG antes/después Windows coinciden además por
bytes; contra la referencia histórica se aplica únicamente la política CRLF/LF.
El fixture de doble ángulo conserva su error esperado, sin convertirlo en PASS.

El [cotejo final del wheel](evidence/runtime-wheel.json) confirma que los
**45 fuentes Python** empaquetados coinciden con el checkout. Los 41 fuentes
previos fuera de las tres extracciones permitidas permanecen intactos; el
nuevo archivo es contracts.py. No hay cambios en ecuaciones o factores.

Comandos principales (desde raíz; Git de GitHub Desktop añadido al PATH):

```powershell
.venv/21dev/Scripts/python.exe -X utf8 scripts/verify_hfs020.py --out .venv/22-before
.venv/21dev/Scripts/python.exe -X utf8 scripts/generate_hfs022_schemas.py
.venv/21dev/Scripts/python.exe -X utf8 scripts/generate_hfs022_schemas.py --check
.venv/21dev/Scripts/python.exe -X utf8 scripts/verify_hfs020.py --out .venv/22-after
.venv/21dev/Scripts/python.exe -X utf8 scripts/verify_hfs020.py --out .venv/22-final
.venv/21dev/Scripts/python.exe -X utf8 scripts/audit_hfs022.py .venv/22-before .venv/22-final --intermediate .venv/22-after --development .venv/22-work
```

El intérprete de herramientas tenía una instalación histórica 0.1.0; se
actualizó a editable 0.2.0 para desarrollo. Los entornos runtime de la captura
base ya se habían instalado limpios con 0.2.0. No atribuir ese cambio del freeze
de herramientas a una diferencia numérica del motor.

### Intentos y errores conservados

- La primera instalación editable en sandbox falló por acceso a temporales
  externos; no se limpió ni modificó ACL. El intento sin aislamiento falló
  por backend setuptools no disponible en ese entorno. Se usó el backend
  aislado/fijado ya declarado y la instalación terminó correctamente.
- La primera prueba dirigida en sandbox terminó con PermissionError al
  finalizar pytest; no se cuenta como suite aprobada. Se repitió con acceso
  normal a temporales nuevos, sin eliminar los anteriores.
- Dos intentos nuevos dieron 206 aprobadas/1 fallida al desarrollar el test
  histórico: primero confundía el error esperado con EngineResult; después
  esperaba 12 resultados en lugar de 11 más un error. Se corrigió solo la
  prueba nueva y se añadió el rechazo explícito del error, sin editar fixtures.
- El primer intento mostró dos advertencias de serializer sobre modelos
  mutados. La API ahora convierte el rechazo del serializer en ContractError;
  no silencia ni acepta esa pérdida de tipo.
- La captura completa intermedia se conserva antes de la guarda final 0/0;
  no se presenta como prueba del binario final. Las regresiones se repiten
  porque hubo ese cambio de integridad posterior, no para ocultar fallos.

[Desarrollo](evidence/development.zip), [intermedia](evidence/intermediate.zip),
[base](evidence/before.zip), [final](evidence/after.zip) y
[manifiestos recuperables](evidence/archives.json). Se conservan bytes y hashes
por miembro de archivo; no se archivan entornos virtuales ni se borra evidencia.

## Alcance, cambios y pendientes

La [comprobación de alcance](evidence/scope.json) compara fuentes contra Git:
motor, domain/codes/sections, modelos, reporting, catálogo, tests anteriores y
documentos históricos protegidos. Comprueba además el AST de preparación y
del parser extraído, y la ausencia de otros cambios del CLI.
La [comparación](evidence/comparison.json) reutiliza los comparadores existentes
para JSON exacto, procedencia y SVG, sin tolerancias nuevas o pérdida de campos.
La política histórica normaliza exclusivamente metadatos de ejecución/rutas
aprobados y, para el contraste multiplataforma de SVG, CRLF/LF. No normaliza
demanda/capacidad/DCR/estado/cobertura/trazas.

Archivos productivos: nuevo `contracts.py`; modificados `execution.py`,
`input_contracts.py` y `run.py` por las dos consolidaciones descritas.
Verificación: nuevo `test_hfs022_contracts.py`, generador/auditor HFS-022;
actualizado `verify_hfs020.py` sin omitir suites ni relajar comparación.
Documentación: README, AGENTS, CONTRIBUTING, ROADMAP, inventario DRY, contrato,
informe/inventario nuevos, schemas y evidencia; `.gitattributes` solo fija LF
para los schemas nuevos. [Relación completa y hashes](evidence/file-inventory.json).

Residuos eliminados: exclusivamente cuerpo duplicado de preparación dentro de
iter_executions y cuerpo local del parser de claves duplicadas; permanecen
implementaciones canónicas y fachada comprometida. No eliminación de archivos,
funciones normativas, pruebas históricas o helpers pospuestos de HFS-021B.

Pendientes: revisión independiente, publicación por el usuario y CI Windows/
Ubuntu de los cambios finales; decisión de release; tipificación normativa
fina de details, trazas y reglas en sus hitos. Integridad JSON no autentica
documentos ni acredita capacidades o referencias externas. No se permite
cerrar F-31, afirmar cumplimiento global AISC o avanzar de hito con estos tests.
