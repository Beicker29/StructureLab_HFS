# HFS-020 — Corrección de compatibilidad Windows/Ubuntu

Entrega para revisión técnica independiente: 2026-10-28. Base `main`, HEAD
`70adc5edf7c5556d0dd5c1be7de915ad0d63b8bf`; árbol limpio al iniciar. Solo se
corrige la verificación de CI. No se crean ramas/PR ni se hace commit/push.
**Implementación verificada localmente; cierre remoto pendiente de publicación
por el usuario y de ambos jobs SUCCESS.** No se inicia HFS-021.

## Causa raíz demostrada antes de implementar

Se inspeccionaron `scripts/verify_hfs020.py`, `scripts/audit_hfs014_cli.py` y
`scripts/audit_baseline.py::sha`, `.gitattributes`, los blobs Git de los 12
ejemplos y las capturas congeladas HFS-017 usadas por el verificador. `sha`
aplica SHA-256 a `read_bytes()`: identifica bytes, no contenido JSON.
`source_sha256` corresponde al archivo original incluso en el escenario
`detailed`, cuya variante solo activa `output.write_results_json`. Esa política
histórica del capturador no se cambia.

Se descargaron los artifacts y el log Ubuntu del
[run 40617061992](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40617061992),
en el mismo SHA. La [evidencia previa](evidence/diagnosis-before.json) registra
las doce identidades y comparaciones; [jobs](evidence/remote/jobs.json),
[metadata de artifacts](evidence/remote/artifacts.json) y
[log Ubuntu](evidence/remote/ubuntu-job.txt) conservan el diagnóstico real.

| Artifact original | ID | SHA-256 del ZIP, contrastado con GitHub |
|---|---|---|
| [Windows](evidence/remote/windows.zip) | 12786265826 | `01d86e423b05dea04d5735cf4c992a42f170777f81cbcc340ca9cec1c8d534a4` |
| [Ubuntu](evidence/remote/ubuntu.zip) | 12786126188 | `b61751b5fd578ff5b42875df86e3754539dba0fa73c87f89738df17f92ec0ef6` |

Windows terminó SUCCESS y Ubuntu FAILURE en la comparación de
`channel_case.json/original`, campo `source_sha256`, línea 179 del verificador
publicado. Ambas plataformas terminaron las once suites con exit 0 y ejecutaron
build, instalación, los ejemplos del motor y los consumidores CLI/memoria.

`.gitattributes` contiene `* text=auto`; Git conserva LF. El checkout local
tiene `core.autocrlf=true` y `git ls-files --eol` informa `i/lf w/crlf` para
los doce ejemplos. En cada uno, el SHA Ubuntu es exactamente el del blob LF;
el SHA Windows y el SHA histórico son exactamente el del mismo blob convertido
a CRLF. Se verificó por hash, sin deducirlo solo del nombre del sistema operativo.
Los artifacts no incluyen los JSON originales sueltos: se reconstruyeron las
dos representaciones desde Git y se exigió coincidencia con sus hashes reales.

Ejemplo `channel_case.json`: 36 saltos de línea; LF produce
`2edd774aecf8b10ec0994b8685ca08d3c2bdd89c53aff6182d726e472fd0fc8b`,
CRLF produce
`d46f938a8f5e66960d9e05898d191e196177e893b6cca8f2f9775c5a9ca29bcd`.
El contenido JSON es idéntico. En los doce casos se observó la misma causa.

Se distinguieron tres niveles: **bytes distintos** en entradas; **contenido
JSON idéntico**; **resultados estructurales idénticos**. Los 24 pares
`normalized_cli`/`normalized_details`, sus códigos de salida y su indicador
de variante coinciden entre Windows, Ubuntu y HFS-017. Los 12 resultados del
motor también coinciden. No se observó un segundo fallo de resultados tras
examinar el resto de las capturas Ubuntu.

## Decisión y contrato de comparación

`scripts/hfs020_comparison.py` centraliza la política de auditoría para
`scripts/verify_hfs020.py` y `tests/test_hfs020_comparison.py`. Solo usa la
biblioteca estándar; no se distribuye como parte del paquete ni modifica
serializadores del motor. No se fuerza un EOL nuevo en `.gitattributes`.

1. Se conserva `source_sha256` sin sustituirlo por un hash semántico. Se exige
   que el hash observado corresponda a los bytes copiados para ejecutar y que
   el hash histórico corresponda a la referencia histórica.
2. La nueva [referencia de entradas](input-reference.json) conserva el texto
   exacto de cada blob Git LF, su SHA y el SHA histórico CRLF. Se verifica el
   vínculo criptográfico con las capturas HFS-017. No es una nueva expectativa
   de cálculo ni una regeneración automática a partir de entradas modificadas.
3. `git ls-tree`/`git show HEAD:...` proporcionan las entradas versionadas. Sus
   contenidos, los del checkout y los copiados para ejecutar deben coincidir
   con la referencia. El conjunto de archivos y escenarios es exacto. La copia
   debe además ser idéntica en bytes al checkout; se comprueba antes y después
   de ejecutar. Un cambio semántico se rechaza incluso si ya está en HEAD.
4. La representación canónica ordena claves de objetos y elimina diferencias
   de formato. Los números se leen como `Decimal` y se escriben mediante
   coeficiente/exponente exactos, sin operaciones que redondeen por contexto,
   conversión a float ni tolerancias. `1`, `1.0` y `1e0` tienen el mismo valor;
   `true` y `1` son distintos. Se conserva el signo del cero, el orden de arrays
   y todo contenido de strings. Claves duplicadas y NaN/infinitos se rechazan.
   Es una convención interna de auditoría, no una afirmación de RFC 8785.
5. Se comparan íntegramente los objetos normalizados del motor, CLI y memorias,
   con todos sus campos y valores numéricos exactos: capacidades nominales y
   disponibles, demandas, DCR, estados, cobertura y trazas. Se mantienen códigos
   de salida y se verifica también el indicador de variante. Se rechazan campos
   superiores o escenarios añadidos/eliminados. La normalización histórica de
   rutas y datos de transporte permanece intacta; no se añaden exclusiones de
   campos resistentes ni se altera el capturador HFS-014.

El [registro de procedencia local](evidence/local-after/input-provenance.json)
conserva seis hashes por entrada: histórico, blob de referencia, blob HEAD,
checkout, copia ejecutada y JSON canónico. El hash canónico complementa los
hashes originales, nunca los reemplaza. El puente LF/CRLF se usa únicamente
para vincular los bytes históricos; no transforma valores JSON.

| Antes | Después |
|---|---|
| CRLF/LF provocaba un falso fallo pese a JSON idéntico | Ambos formatos se aceptan tras comprobar integridad y contenido |
| Una igualdad directa de hashes no explicaba la procedencia | Cadena explícita histórico → referencia → HEAD → checkout → copia |
| Comparación JSON cargada como float | Comparación exacta de números JSON sin pérdida de precisión |
| Once suites históricas | Las mismas once más 50 pruebas de comparación |

No cambia ningún contrato de entrada/salida del motor, fórmula AISC, factor,
catálogo, capacidad, eje, interacción, selección ni acreditación HFS-010.
No cambia el paquete instalable, sus dependencias o el workflow. Se añade un
archivo de evidencia `input-provenance.json` al verificador. Se requiere Git
y un checkout con HEAD, como en el workflow existente; no se requiere historial
profundo. Una modificación futura legítima de ejemplos exige revisión y nueva
evidencia explícita, nunca actualizar automáticamente esta referencia.

## Pruebas reales y diferencias

Entorno Windows, Python 3.12.10; pytest 9.1.1, Ruff 0.17.3 y resolución de
dependencias fijada. [Entorno](evidence/local-after/environment.json),
[freeze de herramientas](evidence/local-after/tools-freeze.json) y logs por
comando conservan rutas, argumentos, stdout/stderr y exit. Las marcas temporales
de las capturas se preservan tal como fueron emitidas; la fecha de esta entrega
no las reescribe.

Comando completo ejecutado con exit 0 y `verification.accepted=true`:

```powershell
.\.venv\20dev\Scripts\python.exe -X utf8 scripts/verify_hfs020.py --out .venv/20compat-final
```

Para reproducir, instalar `.[dev]` con `requirements/ci-constraints.txt` según
CONTRIBUTING y elegir **otra** carpeta de salida. En ambos sistemas:

```text
python scripts/verify_hfs020.py --out .venv/hfs020-review-new
python -m ruff check .
git diff --check
```

| Suite | Aprobadas | Subpruebas | Exit |
|---|---:|---:|---:|
| Original | 68 | 12 | 0 |
| HFS-000 caracterización | 12 | 0 | 0 |
| HFS-011 entradas | 665 | 0 | 0 |
| HFS-016 catálogo | 44 | 0 | 0 |
| HFS-010 cobertura | 57 | 0 | 0 |
| HFS-012 flexión | 61 | 0 | 0 |
| HFS-013 H3 direccional | 57 | 0 | 0 |
| HFS-013 método | 73 | 0 | 0 |
| HFS-014 resumen/bundle | 72 | 0 | 0 |
| HFS-015 precisión | 84 | 0 | 0 |
| HFS-017 método transversal | 468 | 0 | 0 |
| HFS-020 comparación nueva | 50 | 0 | 0 |
| **Total** | **1711** | **12** | **0** |

Cero fallidas, errores, omitidas, xfail o XPASS en la corrida final. JUnit cuenta
1723 incluyendo las 12 subpruebas; no son 1723 métodos. Las suites se ejecutaron
por separado desde un temporal externo, importando el wheel instalado. No se
copió código productivo. [Resultado completo](evidence/local-after/verification.json).

Las 50 pruebas cubren CRLF/LF, formato y notación numérica equivalente;
mutaciones de carga/material/geometría/método en HEAD, checkout y copia;
integridad de referencia y copia; capacidades/demandas/DCR, nominales, trazas,
estados/cobertura, códigos de salida, hashes, escenarios y campos añadidos.
Incluyen diferencias más allá de 28 dígitos, enteros mayores de 2^53, `1e-400`
frente a cero, tipos booleanos, signo del cero, arrays, strings y JSON ambiguo.
Los cambios resistentes de `1e-10` se rechazan; no se introduce tolerancia.

Las once suites previas mantienen sus resultados. Los **12 ejemplos** y los
**24 escenarios CLI/memoria** conservan valores exactos: ninguna diferencia
numérica, de estado, cobertura, traza o salida. Build desde sdist, inspección
de los 33 archivos Python, twine, instalaciones de proyecto/wheel, pip check,
imports externos y ambos entry points pasan. La ausencia deliberada del catálogo
default fuera del checkout conserva exit 1; las demás verificaciones esperadas
terminan con exit 0.

El [replay posterior](evidence/remote-replay-after.json) aplica el comparador
nuevo a los artifacts auténticos de **ambas** plataformas, con los bytes de
entrada reconstruidos y contrastados por sus hashes: 12 resultados y 24
escenarios aceptados en cada plataforma. Es una comparación local de datos
remotos reales; **no es una nueva ejecución Ubuntu ni un nuevo SUCCESS remoto**.

### Reproducción del contraste de artifacts reales

Desde la raíz, guardar este bloque en un archivo temporal o ejecutarlo por stdin
con Python. Solo lee evidencia, no modifica capturas:

```python
from pathlib import Path
from zipfile import ZipFile
from scripts.hfs020_comparison import (
    parse_json, sha256, versioned_examples, verify_input_provenance,
    compare_cli_records, assert_json_equal,
)

base = Path('docs/audit/hfs020/compatibility')
reference = parse_json((base / 'input-reference.json').read_bytes())['files']
old = parse_json(Path('docs/audit/hfs017/evidence/cli/after.json').read_bytes())
engine = parse_json(Path('docs/audit/hfs017/evidence/after/engine-results.json').read_bytes())
blobs = versioned_examples(Path.cwd())
metadata = parse_json((base / 'evidence/remote/artifacts.json').read_bytes())['artifacts']
for system in ('windows', 'ubuntu'):
    path = base / f'evidence/remote/{system}.zip'
    artifact = next(a for a in metadata if system in a['name'])
    assert 'sha256:' + sha256(path.read_bytes()) == artifact['digest']
    with ZipFile(path) as archive:
        cli = parse_json(archive.read('cli-examples.json'))
        actual_engine = parse_json(archive.read('engine-results.json'))
    inputs = {}
    for name, record in reference.items():
        lf = record['git_blob_utf8'].encode()
        candidates = (lf, lf.replace(b'\n', b'\r\n'))
        inputs[name], = [b for b in candidates
                         if sha256(b) == cli[f'{name}/original']['source_sha256']]
    proof = verify_input_provenance(blobs, inputs, inputs, reference, old)
    compare_cli_records(cli, old, proof)
    assert_json_equal(actual_engine, engine, system)
    print(system, '12 ejemplos y 24 escenarios idénticos')
```

## Incidentes, evidencia e inventario

- Primera ejecución de las pruebas nuevas: 49 aprobadas/1 fallida. El parser
  inicial convertía enteros con `int` y perdía el signo de `-0`. Se corrigió
  leyendo también enteros como `Decimal`; 50 aprobadas después y en la corrida
  instalada. No se cambió la expectativa. Se conservan
  [JUnit inicial](evidence/unit-initial.xml) y [corregido](evidence/unit-corrected.xml).
- Ruff general devolvió exit 0, con advertencia `Acceso denegado (os error 5)`
  durante el recorrido de carpetas locales. No se cambió ACL ni se limpió el
  árbol. Una ejecución adicional sin caché sobre los **73 archivos Python**
  de `src`, `scripts` y `tests/test_*.py` pasó sin advertencias ni nuevas
  excepciones. [Comando completo y resultado](evidence/ruff-explicit.json).
- La primera copia de las distribuciones generadas recibió acceso denegado
  desde el sandbox. Se completó con lectura autorizada y verificación de bytes;
  no se cambiaron permisos ni se eliminaron temporales. No es un fallo de tests.
- [Controles finales](evidence/final-checks.json) registran HEAD, diff check,
  enlaces y preservación del alcance. [Inventario de archivos](../changed-files.md#corrección-de-compatibilidad-2026-10-28).

Las capturas históricas HFS-000 a HFS-020 no se sobrescriben. Toda evidencia nueva
reside aquí. [Manifiesto](evidence/SHA256SUMS.json) registra hashes de bytes al
capturar; los ZIP binarios remoto y [local](evidence/local-after.zip) conservan
los originales recuperables aunque un checkout futuro convierta los EOL de las
copias de texto para lectura. El manifiesto de la corrida local también viaja
dentro del ZIP. Las copias sueltas de wheel/sdist bajo `local-after/dist` están
ignoradas por las reglas Git existentes; ambos binarios se entregan dentro de
`local-after.zip`, desde donde pueden extraerse para verificar el manifiesto
original completo. No hace falta cambiar `.gitignore` ni forzar su incorporación
por separado. No se eliminan PDFs, catálogos, artifacts ni históricos.
El log remoto también se conserva como `ubuntu-job.txt`, idéntico en bytes al
`.log` descargado, porque las reglas existentes ignoran archivos `.log`.

## Riesgos y revisión pendiente

La integridad por SHA-256 no sustituye la revisión humana de un cambio autorizado
de fixtures. Estas pruebas acreditan regresión y procedencia, no conformidad
global AISC. Los defectos ingenieriles y límites normativos permanecen intactos.

El usuario debe publicar los archivos del inventario. Después se debe registrar
el nuevo SHA/run y comprobar **Windows SUCCESS y Ubuntu SUCCESS**, incluida la
suite nueva y la comparación final. La ejecución remota conocida sigue teniendo
Ubuntu FAILURE; no se declara HFS-020 cerrado. Si el nuevo run revela otro fallo,
se debe conservar su log e investigarlo dentro de este alcance. No se ha
ejecutado ninguna publicación ni se ha alterado el workflow para omitir jobs.
