# HFS-016 — Integridad mínima del catálogo

Fecha: 2026-10-27. Entrega para revisión técnica, sin fusión ni avance a otra tarea.
Base: `main`, SHA `40d67b91e4b2b2285e4b3881f3a87e92894dd6e9`, árbol limpio al
iniciar. Rama: `hfs-016-catalog-integrity`. HFS-011 aprobada por el usuario;
HFS-002 aceptada como matriz documental y diagnóstico, no validación normativa.

Se elimina la sobrescritura silenciosa: el repositorio conserva cada registro y
solo selecciona identidades únicas. Los duplicados no impiden consultar los demás
perfiles. Ninguna fila se renombra, corrige o escoge por orden de carga.

## Diagnóstico y decisiones

Se revisaron [AGENTS](../../../AGENTS.md), [roadmap](../../ROADMAP.md),
[ADR-001](../../adr/001-engine-architecture.md),
[ADR-002](../../adr/002-contracts-errors.md),
[ADR-003](../../adr/003-traceability-testing.md),
[inventario DRY](../../architecture/dry-inventory.md),
[hallazgos HFS-000](../findings.md), [duplicados históricos](../catalog-duplicates.json),
[informe HFS-011](../hfs011/report.md) y [política de evidencia](../evidence-policy.md).
El contrato completo y la migración están en [hfs016-catalog.md](../../contracts/hfs016-catalog.md).

La identidad es el nombre dentro de un repositorio, normalizado por una función
compartida: espacios ASCII repetidos/extremos y letras ASCII en mayúsculas.
Separadores, unidades, sufijos y caracteres no ASCII permanecen significativos.
No se introducen equivalencias físicas ni normalización Unicode. Fuente, hoja,
fila, tipo y propiedades describen candidatos; no resuelven colisiones.

Se eligió rechazo al consultar, porque rechazar toda la carga inutilizaría perfiles
independientes y elegir primero/último dependería del orden. Deduplicar geometrías
iguales ocultaría repetición de procedencia; también se bloquean. No se ofrece
selección por fila: no hay evidencia para determinar una geometría correcta.

`loader.py` registra ruta absoluta, SHA-256 de los mismos bytes que parsea, hoja,
fila base 1 y texto original. `models.py` añade `SectionSource` opcional; objetos
programáticos conservan origen desconocido explícito (`None`). `repository.py`
agrupa todos los registros; carga lotes validados y snapshots profundos, devuelve
copias y lanza `AmbiguousSectionError` con código `AMBIGUOUS_SECTION`, identidad,
consulta y todos los candidatos con propiedades/procedencia. La copia evita que
mutaciones externas cambien la identidad o evidencia almacenada.

No hay cambios en motor, CLI, ecuaciones, capacidades, routing, ejes, interacción,
métodos LRFD/ASD ni validación física HFS-011. Se mantiene el Excel original.

## Antes frente a después y cierre de F-13

Catálogo SHA-256: `5aaaf953a32e77e6d9985e9f91db82702d70b3ee0930a2eb6e695e297a5f1359`.

| Observación | Antes | Después |
|---|---|---|
| Registros importados | 1228 | 1228 |
| Identidades | 1223 | 1223 |
| Registros retenidos por get_all | 1223 (cinco perdidos) | 1228 |
| HEA 100, orden original | A=2534 mm², d=114 mm | Error con ambos registros |
| HEA 100, orden inverso | A=2124 mm², d=96 mm | Error con ambos registros |
| PTEXXMM | Último de cinco placeholders | Error con los cinco registros |
| Identidades únicas recuperables | Sin aislamiento explícito | 1221, verificadas individualmente |
| Selección única físicamente inválida | Rechazo HFS-011 | Mismo rechazo |
| 12 ejemplos, resultado completo | Captura base | Igualdad exacta |

HEA 100 procede de `W_IPE_HEA_HEB`, filas 309 y 310; PTEXXMM de `PTE_RECT`,
filas 77–81 (área cero). Las [sondas previas](evidence/probes-before.json) y
[posteriores](evidence/probes-after.json) conservan resultados en ambos órdenes.
[probes.py](probes.py) permite repetirlas contra un checkout concreto.

F-13 tiene cierre funcional demostrado de la sobrescritura/selección silenciosa,
pendiente aprobación técnica del PR. El test histórico ahora exige rechazo en
`get` y conservación de ambas áreas; solo se retira su xfail. No se afirma que
las filas sean correctas ni se cierra HFS-040/F-27. Los otros siete xfail estrictos
permanecen; las evidencias congeladas HFS-000/011 no se editan.

## Compatibilidad y consumidores

Se inspeccionaron `engine.run`, `run._build_case_section`, las suites y
`scripts/audit_baseline.engine_snapshot`. Motor/CLI ya consultan `get` y propagan
`SteelDesignError`; no duplican política. CLI devuelve exit 1, stage `run_engine`
y error estructurado al seleccionar ambiguos. La recuperación posterior de W12X26
está probada tanto en repositorio/motor como mediante CLI.

Cambios intencionales incompatibles:

- `get` puede lanzar `AMBIGUOUS_SECTION`; antes devolvía el último duplicado.
- `get_all` enumera registros diagnósticos, incluidos ambiguos; su longitud ya no
  representa identidades. Consumidores que calculan deben pasar por `get`.
- `load` acumula también repeticiones: recargar el mismo catálogo en la misma
  instancia bloquea identidades. Para reemplazarlo, crear otro repositorio.
- Mutar un objeto recibido/cargado ya no modifica los registros almacenados.
- `Section.model_dump()` incluye `source`; consumidores estrictos de esa salida
  deben admitir el campo. El JSON de casos y los resultados del motor no cambian.
- Nombres con variaciones de espacios ASCII ahora colisionan/consultan según la
  política común; no se compactan nombres como HEA100 y HEA 100.

El contador histórico `repository_count` del capturador HFS-000 ahora cuenta
registros de get_all. No se cambia ese script ni se reinterpreta su evidencia
anterior: este informe distingue registros, identidades e identidades únicas.

## Pruebas y resultados reales

Windows, Python 3.12.10, Pydantic 2.14.1, pytest 9.1.1, openpyxl 3.1.5.
Se reutilizó `.venv/hfs011` sin instalar dependencias. Entorno y freeze:
[antes](evidence/before/environment.json), [después](evidence/after/environment.json).
El capturador aísla escrituras en copias nuevas, verifica hashes, desactiva plugins
externos/caché de pytest y fija PYTHONNOUSERSITE/PYTHONUTF8.

| Suite | Antes | Final | Exit final |
|---|---|---|---|
| Original | 68 métodos + 12 subpruebas aprobadas | 68 métodos + 12 subpruebas aprobadas | 0 |
| Caracterización | 4 aprobadas, 8 xfail | 5 aprobadas, 7 xfail | 0 |
| Contratos HFS-011 | 664 aprobadas | 665 aprobadas | 0 |
| Integridad HFS-016 | No existía | 44 aprobadas | 0 |

Final sin fallos, errores, XPASS ni omisiones ordinarias. Los siete skipped de
JUnit son xfail, no aprobados. El caso adicional HFS-011 resulta de su parametrización
automática al incorporar `Section.source`; no se cambia ese archivo de pruebas.
Los 44 casos HFS-016 incluyen nombres exactos/case/espacios, geometrías iguales y
distintas, ambos órdenes, procedencia sintética/real, colisiones entre fuentes y
tipos, recarga, atomicidad, copias, errores CLI y mantenimiento de guardas físicas.

Comandos ejecutados desde la raíz (todos los capturadores finalizaron; la ejecución
intermedia se documenta por separado):

```powershell
.\.venv\hfs011\Scripts\python.exe scripts/audit_hfs011.py --baseline docs/audit/hfs011/evidence/after/engine-results.json --out .venv/hfs016-before --work .venv/hfs016-before-work
.\.venv\hfs011\Scripts\python.exe scripts/audit_hfs011.py --baseline .venv/hfs016-before/engine-results.json --out .venv/hfs016-final --work .venv/hfs016-final-work --extra-suite tests/test_hfs016_catalog_integrity.py
.\.venv\hfs011\Scripts\python.exe docs/audit/hfs016/probes.py --root .venv/hfs016-before-work --out .venv/hfs016-probes-before.json
.\.venv\hfs011\Scripts\python.exe docs/audit/hfs016/probes.py --root . --out .venv/hfs016-probes-after.json
git diff --check
```

[Verificación final de suites](evidence/after/verification.json),
[comparación por ejemplo](evidence/after/comparison.json) y
[resultados completos](evidence/after/engine-results.json).
Los 12 casos y sus trazas coinciden exactamente (tolerancia cero para esta
regresión), hash canónico `040b93b81b47b090f46ebe2e9018e9fd8697b60aac93fd4bcd1c3a2fb2ba5403`.
No se cambian expectativas numéricas para hacer pasar la comparación. Esto prueba
preservación del comportamiento, no exactitud normativa independiente.

Incidencias conservadas: la primera ejecución posterior falló en la caracterización
F-13 porque el antiguo test solo capturaba el error durante load; el nuevo rechazo
ocurre en get. No fue XPASS ni fallo de infraestructura. Tras comprobar el contrato
y su reproducción real se actualizó únicamente ese test; [log](evidence/initial-characterization.json).
Crear la rama inicialmente encontró denegación al escribir `.git`; se utilizó
el mecanismo de escalación autorizado, sin modificar permisos. Git sigue avisando
de una carpeta temporal histórica inaccesible y de conversión LF/CRLF en el script
de captura; no se limpia evidencia ni se ocultan estos avisos.

Para repetir, usar rutas de salida/trabajo nuevas y el mismo entorno; baseline
`docs/audit/hfs016/evidence/before/engine-results.json`, con `--extra-suite` como arriba.

## Inventario y conservación

| Archivos | Cambio |
|---|---|
| `src/steel_design/sections/identity.py` (nuevo) | Política única de identificación |
| `sections/loader.py`, `sections/models.py` bajo `src/steel_design` | Procedencia exacta y contrato SectionSource |
| `src/steel_design/sections/repository.py` | Retención, rechazo por identidad, diagnóstico y copias |
| `src/steel_design/domain/errors.py` | Error estructurado de ambigüedad |
| `tests/test_hfs016_catalog_integrity.py` (nuevo) | 44 pruebas de integridad |
| `tests/test_hfs000_characterization.py` | Cierre funcional demostrado de F-13 |
| `scripts/audit_hfs011.py` | Opción de suite adicional separada, reutilizando captura existente |
| `README.md`, `CONTRIBUTING.md` | Contrato visible y reproducción de suites |
| `docs/ROADMAP.md`, `docs/audit/tracking.md`, `docs/architecture/dry-inventory.md` | Estado vivo y responsabilidad canónica |
| `docs/contracts/hfs016-catalog.md` (nuevo) | Decisiones y migración |
| `docs/audit/hfs016/report.md`, `probes.py`, `final-checks.json`, `evidence/` (nuevos) | Informe y evidencia reproducible |

[Manifiesto](evidence/manifest.json): 31 archivos promovidos por copia con origen
y SHA-256; capturas originales permanecen en `.venv`. No se elimina ni sobrescribe
HFS-000, HFS-011, Excel, PDFs o resultados históricos. [Comprobaciones finales](final-checks.json)
registran hashes, enlaces locales, diff y alcance preservado.

## Riesgos residuales y revisión

1. La procedencia ubica datos; no acredita fuente editorial, licencia, unidades,
   conversiones, D/t ni coherencia geométrica. HFS-040 sigue pendiente. No hay base
   verificable para corregir HEA 100 o PTEXXMM.
2. Se aíslan duplicados y placeholders representables. Errores previos de esquema,
   parseo, no finitos o dominios negativos pueden seguir abortando la importación;
   no se introduce descarte silencioso ni un importador tolerante completo.
3. Las 1221 identidades únicas son recuperables, no certificadas. Se conserva el
   rechazo físico HFS-011 cuando se selecciona una sección. Catálogos custom
   requieren información de origen fiable; source suministrado no está autenticado.
4. HFS-010 y defectos normativos/estados/interacción siguen abiertos; un PASS actual
   no es certificación global AISC. No se habilitan métodos ni nuevas capacidades.
5. Detalles de error incluyen ruta de origen y propiedades completas. Futuros
   adaptadores remotos deberán definir presentación/privacidad sin otra política
   de selección. Copias profundas añaden memoria/tiempo; no se acredita escalabilidad
   fuera del catálogo ensayado.

Revisar identidad ASCII, bloqueo incluso de duplicados idénticos y migración de
get_all/recargas antes de aprobar. El PR se prepara hacia main y no se fusiona.
