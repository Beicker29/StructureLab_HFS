# HFS-021A — Paquete convencional y API pública

Fecha: 2026-10-28. Base aprobada `main`,
`39a7614a413a06eef78f597e142f7ba0e889c123`. Alcance de arquitectura/imports/
distribución/compatibilidad. Sin HFS-022/023/024, web, commit ni push.

## Diagnóstico y plan

La distribución 0.1.0 contenía el namespace PEP 420 `src.steel_design`.
Los consumidores dependían de ese prefijo, del comando modular y de que
el checkout raíz añadiera `src` implícitamente. La inspección de wheel también
fijaba versión y ruta de metadata. [Preparación previa](preparation.md) y
[inventario completo de referencias](consumer-inventory.json): 208 referencias
en 36 archivos operativos, incluyendo rutas físicas que se conservan.

HEAD y rama coincidieron con la solicitud; no había cambios locales. Los
temporales históricos inaccesibles no se limpiaron ni se cambiaron permisos.
Se confirmó por herramienta GitHub el
[run 40687160912](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40687160912):
Windows job 122812372184 y Ubuntu job 122812371832 completed/success.
[Registro consultado](evidence/hfs021-remote-status.json).
Es aprobación de HFS-021, no de este cambio aún sin publicar ni certificación AISC.

## Implementación y ruptura deliberada

1. Se conserva `src/steel_design` físicamente. Ocho `__init__.py` convierten
   los directorios existentes en paquetes reales; setuptools usa where=src,
   inclusión explícita steel_design/subpaquetes y namespaces=false.
2. La distribución sube a **0.2.0**: cambian imports y ejecución modular de
   forma incompatible. `structurelab-hfs` conserva nombre y argumentos,
   apuntando a `steel_design.run:main`. El módulo soportado es
   `python -m steel_design.run`.
3. El inicializador raíz rechaza `__name__ != "steel_design"` antes de cargar
   modelos. Así `src.steel_design.models` no puede coexistir como segunda
   clase desde el checkout, incluso si se intenta primero el import legado.
   Sin aliases sys.modules, duplicación de fuentes ni fallback por cwd.
4. API pública explícita por módulos: motor, caso, sección, repositorio,
   ejecución y preparación de reportes. Sin reexports masivos ni nuevo servicio.
   Fachadas HFS-021 se mantienen bajo el paquete convencional; nombres `_`
   siguen internos. [Contrato completo](../../contracts/hfs021a-public-api.md).
5. Tests y capturadores activos migran imports/ejecución. Los scripts que
   toman una copia explícita de fuentes apuntan a su `src`; la prueba instalada
   no copia fuentes productivos y resuelve el paquete desde site-packages.
   Los documentos de auditoría/contratos anteriores y capturas no se reescriben.

No cambian nombres de modelos, funciones, campos o estados. El nombre de clase
Python `__module__` cambia deliberadamente; pickles/consumidores del namespace
0.1.0 requieren migración. JSON se conserva. Para desarrollo desde checkout
se documenta `pip install -e .`; no se ofrece import automático sin instalar.

## Verificadores y protección del cálculo

`verify_hfs020.py` sigue siendo el único verificador del workflow Windows 2022/
Ubuntu 24.04. Se amplía para inspeccionar archivos del wheel sin `src`, sdist
reconstruible con src-layout, versión leída desde pyproject, metadata mediante
parser estándar, entry point, tres instalaciones y orígenes reales de imports.
No es necesario modificar MANIFEST: ya incluía los fuentes bajo la ruta física
correcta. Tampoco cambia el workflow: invoca este mismo verificador ampliado.

Se prueba instalación normal, wheel y editable en entornos limpios; ambos CLI
convencionales dan el mismo JSON normalizado. La sonda de importación recorre
órdenes canónico/legado y directorios checkout/externo en los tres entornos.
Impide escrituras, creación de carpetas, lectura de casos/Excel y salida/sys.exit
al importar. Se permiten y registran lecturas de metadata que Pydantic necesita
para cargar sus modelos; no se confunden con I/O de aplicación. Sin matplotlib.

`hfs020_comparison.py` permanece íntegro: números exactos, hashes y procedencia
de catálogo/entradas no se relajan. `compare_hfs021.py` conserva su verificación
histórica de extracción y ofrece `compare_results` reutilizable para comparar
capturas completas y SVG. `compare_hfs021a.py` lo usa y añade:

- identidad de 35 fuentes productivos preexistentes, incluido motor,
  geometría, cálculos, plan de cobertura, guardas, solver y exportadores;
- un cambio acotado en el productor de metadata de evidencia: conserva el
  identificador textual histórico del JSON. AST completo demuestra que solo
  se adapta ese texto y que las decisiones de cobertura no cambian;
- AST completo de todos los tests previos con una única transformación
  permitida, `src.steel_design` → `steel_design`; expectativas intactas;
- catálogo/ejemplos/comparador protegidos y documentos históricos sin cambios;
- comparación exacta antes/después y con referencia histórica HFS-017, sin
  regenerar resultados esperados ni tolerancias nuevas.

La suite nueva verifica que cambios aislados en factor, condición, estado,
traza o expectativa son rechazados por la invariancia AST. La inspección de
paquete y la regresión complementan ese control; AST no valida la norma.
La comparación de los 6 SVG históricos también queda dentro del verificador
CI, no solo en una herramienta local.

## Reproducción y evidencia

Entorno Windows, Python 3.12.10; pytest 9.1.1, pydantic 2.14.1/core 2.50.1,
openpyxl 3.1.5; build 1.6.1, Ruff 0.17.3 y twine 7.0.0, con constraints
existentes. No se añaden dependencias. Logs completos conservan freeze,
comando, cwd, exit, stdout/stderr y JUnit por suite.

```powershell
# Antes de migrar: verificador y fuentes aprobados de HFS-021.
.\.venv\21dev\Scripts\python.exe -X utf8 scripts/verify_hfs020.py --out .venv/21abefore
# Después: paquete convencional, tres instalaciones, todas las suites.
.\.venv\21dev\Scripts\python.exe -X utf8 scripts/verify_hfs020.py --out .venv/21aafter5
.\.venv\21dev\Scripts\python.exe -X utf8 scripts/compare_hfs021a.py .venv/21abefore .venv/21aafter5 .venv/21a-comparison.json
```

Usar directorios nuevos al reproducir. Git debe estar en PATH. Para una base
histórica usar su commit y herramientas; no importar sus clases bajo un alias
paralelo en el mismo proceso. La captura previa se ejecutó sobre wheel de la
base antes de editar; la migración posterior no modifica ese entorno.

## Resultados reales

| Suite separada | Antes | Después | Subpruebas por corrida |
|---|---:|---:|---:|
| Original | 68 | 68 | 12 |
| Caracterización HFS-000 | 12 | 12 | 0 |
| HFS-011 | 665 | 665 | 0 |
| HFS-016 | 44 | 44 | 0 |
| HFS-010 | 57 | 57 | 0 |
| HFS-012 | 61 | 61 | 0 |
| HFS-013 direccional | 57 | 57 | 0 |
| HFS-013 método | 73 | 73 | 0 |
| HFS-014 | 72 | 72 | 0 |
| HFS-015 | 84 | 84 | 0 |
| HFS-017 | 468 | 468 | 0 |
| HFS-020 comparación | 50 | 50 | 0 |
| HFS-021 | 51 | 51 | 0 |
| HFS-021A | No existía | 28 | 0 |
| **Total** | **1762** | **1790** | **12** |

Ambas corridas finales: exit 0, accepted=true, cero fallidas, errores,
omitidas, xfail o XPASS. La suite original son 68 métodos +12 subpruebas,
no 80 métodos. Las 28 nuevas también pasaron en la instalación editable
(repetición adicional, no sumada al total principal).
[Resultado previo](evidence/before/verification.json),
[resultado posterior](evidence/after/verification.json).

**Ninguna diferencia final de capacidad, demanda, DCR, estado, cobertura,
traza, JSON o código de salida** en los 12 ejemplos y 24 escenarios.
Los 6 SVG son idénticos byte a byte. No se agregaron normalizaciones ni
tolerancias. [Comparación exacta y fuentes protegidos](evidence/comparison.json)
y [comando/exit](evidence/comparison-command.json). Se conservaron los 23
archivos de tests previos bajo la transformación permitida; 35 fuentes
productivos idénticos y uno con solo adaptación del ID histórico.

Build desde sdist, inspección de **44 fuentes Python**, wheel sin paquete src,
twine estricto, Ruff y pip check pasan. Tres instalaciones limpias y seis
recorridos CLI convencionales probados. Doce sondas frescas cubren orden de
imports/directorio/instalación; todas rechazan identidades paralelas. Los tres
comandos legados desde checkout devuelven exit 1 explícito. Las tres ausencias
de catálogo default fuera del checkout conservan exit 1/load_sections esperado;
no son fallos de pruebas. También se ejecutó el módulo convencional desde
checkout usando editable: [registro](evidence/checkout-editable.json).

Archivo completo recuperable: [antes, 62 archivos](evidence/before.zip),
[después, 91 archivos](evidence/after.zip),
[cuatro intentos fallidos, 127 archivos](evidence/failed-attempts.zip) y
[SVG antes/después](evidence/diagrams.zip). Incluyen comandos, stdout/stderr,
JUnit, freeze, distribución y metadata. Se verificó cada miembro de las
capturas finales contra su manifiesto original; [índice de ZIP y hashes](evidence/archives-index.json).
No se incluyen entornos completos regenerables ni se borra evidencia histórica.

[Controles finales](evidence/final-checks.json): Ruff dirigido sobre los 90
archivos Python, sin advertencias; `git diff --check`, enlaces locales válidos,
44 fuentes productivos idénticos al wheel probado y ausencia de build/lib/src
activo. Git permanece en main/39a7614, índice sin cambios staged. Se mantienen
las advertencias heredadas de acceso al listar Git y la conversión LF/CRLF de
AGENTS; no afectan los controles ni se cambian permisos para ocultarlas.
[Manifiesto de evidencia](evidence/SHA256SUMS.json).

## Incidentes de verificación

- Primer intento posterior: build pasó, la inspección falló por buscar
  literalmente `Version: ...\n` frente a metadata con CRLF. Se usa ahora
  `email.parser.Parser`, sin relajar el valor de versión.
- Segundo intento: build/twine/Ruff/instalación normal/imports pasaron; la sonda
  prohibía toda lectura Path.open y bloqueó a Pydantic al leer entry_points.txt
  de metadata instalada. Se restringe la prohibición a escrituras/datos de
  aplicación, conservando lectura legítima registrada. No cambió runtime.
- Tercer intento: la inspección de archivos instalados detectó namespace `src`
  dentro de la instalación normal. El wheel reconstruido desde sdist estaba
  limpio, pero `pip install .` reutilizó **build/lib/src** generado por 0.1.0
  y añadió esa copia retirada. La [reproducción aislada](evidence/contamination-reproduction.json)
  confirmó 72 archivos legados instalados y dos identidades SteelCase distintas
  en ese intento fallido. Era un defecto real de distribución desde un
  checkout con build anterior, no un error de cálculo. Se preservaron 80
  archivos generados en [ZIP verificable](evidence/legacy-generated-build.zip)
  y [manifiesto/motivo/destino](evidence/legacy-build-preservation.json), y se
  movió exclusivamente `build/` a `.venv/21a-legacy-build` tras comprobar sus
  rutas absolutas dentro del workspace. No se borró ningún archivo.
  El verificador ahora detecta ese residuo antes del build y exige preservarlo
  y apartarlo; no limpia automáticamente ni permite continuar con ambos paquetes.
- Cuarto intento: las 1762 pruebas previas +26 pruebas nuevas pasaron, también
  editable, imports y ambas CLI. La comparación exacta detectó diferencias
  exclusivamente en `coverage.executions[].implementation`:
  [65 diferencias registradas](evidence/identifier-differences-attempt4.json). El campo usaba
  `__module__` y publicaba ahora `steel_design...` en lugar del ID previo.
  Se conservó el texto histórico en su único productor
  `domain/coverage_evidence.record_evaluation`, con una adaptación de metadata.
  **No es un import, alias o segunda clase**, ni una nueva normalización del
  comparador. La clase sigue siendo steel_design; `_CLAIMS`, obligaciones,
  índices aceptados y condiciones permanecen idénticos.
  Dos regresiones adicionales prueban ID histórico/identidad canónica y rechazo
  de cambios de acreditación por el comprobador AST. Es necesario para respetar
  el requisito de JSON/trazas exactamente preservados sin modificar snapshots.
- Se conservan los cuatro intentos fallidos y sus logs, no solo la corrida final.
  Las correcciones no alteraron ecuaciones ni expectativas de regresión.

## Riesgos y pendientes

Revisión independiente y publicación corresponden al usuario. El código nuevo
no tiene todavía CI remoto propio: observar ambos jobs SUCCESS después de un
nuevo commit, sin extrapolar el run de HFS-021. La rama PNG conserva código
idéntico, pero se ejecuta realmente SVG sin matplotlib; decidir una dependencia
gráfica opcional queda pendiente de otra tarea, no se añade aquí.

Se retira expresamente el namespace/comando antiguo; scripts externos y pickles
con esas rutas deben migrar. No se soporta instalar dos versiones o cargar
archivos manualmente bajo nombres arbitrarios. Esto no habilita ASD, no corrige
defectos normativos pendientes ni cambia PASS/FAIL/INCOMPLETE/F-32.

[Inventario de cambios y pendientes](changed-files.md). No avanzar a HFS-022.
