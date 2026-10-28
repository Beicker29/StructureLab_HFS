# HFS-021 — Separación de ejecución, presentación y geometría

Fecha: 2026-10-28. Base `main`,
`f3a5198309d24f772f6cac69ccc483846b81d21a`. Entrega para revisión técnica
independiente, sin rama, PR, commit ni push. Solo HFS-021.

## Diagnóstico y decisiones

F-15: motor y CLI construían separadamente las mismas propiedades custom.
F-16: `run.py` mezclaba transporte, preparación/ejecución, reconstrucción de
sección, agregación, datos de memoria, reloj, rutas y gráficos. El
[mapa previo](preparation.md) registra consumidores, dependencias, errores,
efectos y contratos antes de editar.

La dependencia HFS-020 está aprobada por el usuario. Se consultó el
[workflow 40673575334](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40673575334):
Windows y Ubuntu SUCCESS, incluidos build, instalaciones y pruebas.
[Respuesta conservada](evidence/hfs020-jobs.json). Este cierre posterior
actualiza el seguimiento vivo; no reescribe informes históricos y no constituye
validación normativa AISC.

| Antes | Después y motivo |
|---|---|
| Dos constructores macizos | `sections.geometry.build_custom_section`: una función pura con las expresiones exactas anteriores; fachadas importables sin aritmética duplicada |
| `engine.run` descartaba Section después de calcular | `run_with_context` conserva caso/Section/result; `run` mantiene firma y devuelve el mismo EngineResult. No hay cache ni doble pipeline |
| Preparación/lotes dentro de argparse | `execution`: merge, opciones, preparación, ejecución individual/iterada/materializada, agregación canónica. Invocable sin archivos, consola ni rutas |
| CLI reconstruía Section para memoria | `CaseExecution` lleva la misma Section validada; un lookup/construcción por ejecución |
| Datos y escritura de memoria inseparables | `reporting.build_detailed_results_payload` prepara datos; writer solo determina destino y serializa. Resumen compacto también se consume en memoria |
| Exportación/gráficos junto a ejecución | `reporting.export_execution` concentra efectos optativos; CLI se ocupa del transporte y solicita exportación explícita |

Se conserva lo que ya funcionaba: modelos Pydantic, repositorio con snapshots,
validaciones de dominio, motor, selección, cobertura independiente y agregador.
Se rechaza adoptar por completo el árbol ilustrativo del roadmap: tres módulos
con consumidores concretos bastan; sin servicios web, jerarquías abstractas,
contenedores, plugins, nueva dependencia o segundo motor.

La tupla `CaseExecution` solo transporta los objetos de la ejecución y su
contexto; evita reconstrucción y una cache mutable dentro del motor. No se
crean DTO duplicados ni contratos versionados HFS-022. El iterador conserva
el orden de efectos de lotes del CLI: un fallo tardío no elimina exportaciones
previas. La lista materializada permite al consumidor Python obtener todo en
memoria, sin exportar. [Contrato y ejemplos](../../contracts/hfs021-execution.md).

## Invariantes y compatibilidad

- Cero cambios de ecuaciones, factores, catálogo, reglas, routing, modelos de
  entradas/resultados, precisión HFS-015 u obligaciones HFS-010. Guardas
  LRFD/ASD HFS-017 intactas; ningún dominio ASD adicional.
- `SteelDesignEngine.run`, ambos entry points, argumentos/defaults,
  `--sections`, JSON público, nombres de archivos y etapas de error conservados.
- Se conservan FAIL/INCOMPLETE, fallos conocidos, lote vacío rechazado y F-32:
  éxito de ejecución puede devolver exit 0 con FAIL resistente.
- Los helpers consumidos por pruebas/scripts siguen importables desde `run`
  y `engine`; ningún test histórico se adapta para esconder una diferencia.
- El CLI queda en 149 líneas; la reducción no es el
  criterio DRY. La mejora es un propietario por concepto y la misma sección
  usada en cálculo y presentación.

La comprobación AST compara el pipeline anterior con `run_with_context`
excluyendo únicamente el retorno ampliado. Verifica además el constructor
geométrico completo y los helpers de presentación/gráficos extraídos. Se
complementa con hashes de fuentes protegidos y pruebas de resultados; una
comparación AST por sí sola no acredita equivalencia normativa.

## Pruebas y reproducción

Windows, Python 3.12.10; pydantic 2.14.1, pydantic-core 2.50.1,
openpyxl 3.1.5, pytest 9.1.1, Ruff 0.17.3, build 1.6.1, twine 7.0.0.
Resolución `requirements/ci-constraints.txt`; freezes y comandos completos
con cwd, stdout, stderr y exit en la evidencia. Las fechas/horas de los logs
se conservan tal como fueron emitidas, sin ajustarlas retrospectivamente.

```powershell
.\.venv\hfs000\Scripts\python.exe -m venv .venv/21dev
.\.venv\21dev\Scripts\python.exe -m pip install -c requirements/ci-constraints.txt ".[dev]"
# Antes: fuentes originales, sin pruebas HFS-021 en la distribución/copia.
.\.venv\21dev\Scripts\python.exe -X utf8 scripts/verify_hfs020.py --out .venv/21before
# Prueba dirigida inicial: 51 aprobadas.
.\.venv\21dev\Scripts\python.exe -m pytest -q -ra tests/test_hfs021_execution.py -p no:cacheprovider --basetemp=.venv/21target --junitxml=.venv/21target.xml
# Después: mismo verificador; añade HFS-021 como suite separada.
.\.venv\21dev\Scripts\python.exe -X utf8 scripts/verify_hfs020.py --out .venv/21after
.\.venv\21dev\Scripts\python.exe -X utf8 scripts/compare_hfs021.py .venv/21before .venv/21after .venv/21-comparison.json
```

Usar rutas nuevas para reproducir; el verificador nunca sobreescribe capturas.
Git debe estar en PATH (se utilizó el Git instalado por GitHub Desktop).
El baseline comenzó antes de editar runtime: se construyó/copió/instaló la base
original y se verificó completamente en un temporal externo. La implementación
posterior no altera ese wheel ni sus entradas. Ningún código productivo se
copia a los directorios de pruebas de instalación.

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
| HFS-021 | No existía | 51 | 0 |
| **Total** | **1711** | **1762** | **12** |

Los resultados finales se registran en
[antes](evidence/before/verification.json) y
[después](evidence/after/verification.json); los detalles por comando y JUnit
completos se preservan en los ZIP de cada corrida. Las once suites históricas
y HFS-020 se ejecutaron separadas de HFS-021. Ambas verificaciones terminaron
con exit 0 y `accepted=true`: cero fallos, errores, omitidas, xfail o XPASS.
La original aporta 68 métodos y 12 subpruebas; no son 80 métodos.

Pruebas nuevas: propiedades independientes de círculos/rectángulos a tres
escalas, faltantes/negativos/no finitos/overflow, ausencia de I/O, casos/lotes
con PASS/FAIL/INCOMPLETE, errores tempranos y tardíos, catálogo externo/nombre
ausente, bloqueo ASD, importaciones, fachadas, un lookup/construcción y
identidad de Section. La geometría usa tolerancia relativa `1e-14`, absoluta
cero, exclusivamente para comparar identidades algebraicas de float; no se
aplica a decisiones resistentes ni al contraste exacto de regresión.

## Comparación y evidencia

Los 12 ejemplos y los 24 escenarios CLI/memoria se comparan completos con
HFS-017 y entre ambas ejecuciones HFS-021: capacidades, demandas, DCR, estados,
cobertura, trazas, estructuras y códigos de salida. Se conserva la política
HFS-020 de procedencia de entradas, números JSON exactos y equivalencia LF/CRLF;
no se añaden exclusiones de contenido. Solo normalización histórica autorizada
de rutas/metadatos temporales. Los gráficos SVG se contrastan también por bytes.

Resultado: **ninguna diferencia numérica, de estado, cobertura, traza o JSON**
en los consumidores contrastados. Los **6 SVG** coinciden byte a byte.
Se verificaron **54 archivos protegidos** sin cambios, **13 helpers** de
presentación con AST idéntico, el constructor geométrico y el pipeline del
motor (solo cambia el retorno de contexto). [Evidencia](evidence/comparison.json).

La suite HFS-020 de 50 mutaciones sigue verificando rechazo de cambios
semánticos, tipos, precisión, hashes, escenarios y resultados. El workflow
existente llama al mismo verificador, que ahora incluye HFS-021; no se debilitan
jobs ni comparadores. Esta entrega ejecuta Windows local; no afirma haber
ejecutado una nueva corrida Ubuntu de código aún no publicado.

Se construyen sdist y wheel desde el sdist, se inspeccionan archivos y entry
point, `twine check --strict`, `pip check`, instalaciones limpias de proyecto
y wheel, imports desde site-packages fuera del checkout y ambos comandos CLI.
Matplotlib deliberadamente ausente en esos entornos: se ejerce SVG real; la
rama PNG conserva identidad AST, sin afirmar ejecución PNG real.

Los logs antes/después se archivan sin pérdida con manifiestos; las copias
sueltas son índices para revisión. No se sobrescribe evidencia histórica,
no se eliminan PDFs/catálogos/temporales y no se modifican permisos.
Inventario detallado: [changed-files.md](changed-files.md).

Archivo recuperable: [antes, 60 archivos](evidence/before.zip),
[después, 62 archivos](evidence/after.zip) y
[SVG antes/después](evidence/diagrams.zip). Se verificó la recuperación de cada
entrada contra el manifiesto original dentro del ZIP. Wheel/sdist están dentro
de los archivos completos, sin forzar binarios sueltos ignorados por Git.
[Índice y hashes de los archivos](evidence/archives-index.json).

[Controles finales](evidence/final-checks.json): Ruff sobre los 78 archivos
Python pertinentes, sin advertencias; `git diff --check`, enlaces locales
y los 36 fuentes productivos idénticos al wheel probado. Git sigue en `main`
y en el mismo HEAD, sin archivos staged. [Manifiesto de evidencia](evidence/SHA256SUMS.json).

## Riesgos y revisión

F-15 y F-16 reciben cierre funcional acotado para revisión. La refactorización
no cierra los defectos ingenieriles pendientes, F-31, deuda de trazabilidad
HFS-024 o habilitación ASD HFS-039. No valida combinaciones externas ni certifica
AISC. Los metadatos mutables del contexto no son una cache: un adaptador futuro
debe tratar cada ejecución como un resultado ya producido.

Las funciones movidas cambian de módulo propietario; se preserva su acceso
histórico, pero no se garantiza monkeypatch de globals privados antiguos ni
pickles. `_run_single_case` ahora presenta siempre la sección del repositorio
del motor, incluso si un llamador entrega otro `repo`; así no puede presentar
una geometría distinta de la calculada. No hay consumidores registrados que
dependan de esa discrepancia.

El comparador adicional tuvo un fallo propio inicial: trató los hashes de la
captura nueva como si fueran los históricos HFS-017 referenciados por la prueba
de procedencia. [Fallo conservado](evidence/comparison-initial.json). Se corrigió
el enlace: cada corrida se contrasta con HFS-017 mediante su propia prueba de
procedencia, y luego se comparan directamente antes/después. No se cambiaron
entradas, resultados esperados ni comparadores HFS-020. La primera lectura de
SVG desde los temporales externos recibió PermissionError; se completó con
lectura autorizada sin cambiar permisos ni rutas. El
[comando final](evidence/comparison-final-command.json) terminó con exit 0;
[prueba de identidad y alcance](evidence/comparison.json).

Se preservan las advertencias de acceso históricas de Git. Ruff general pasa
con advertencias de acceso al recorrer temporales; la ejecución explícita de
los archivos Python evita ese recorrido sin añadir excepciones ni ocultar
archivos productivos. La primera prueba nueva
emitió dos avisos de deprecación pytest por iteradores parametrizados; se
cambiaron a listas sin alterar casos/expectativas y se conserva su JUnit inicial.

No iniciar HFS-022 ni otra tarea sin revisión independiente de esta entrega.
