# HFS-021B — Cierre documental y limpieza incremental controlada

Fecha: 2026-10-28. Base verificada: `main`,
`35dd7b8e09f05b8ac77af1ba0b7b735d59456b6a`. Árbol inicial limpio; permanecen
las advertencias históricas de acceso, sin limpiezas ni cambios de permisos.
HFS-021B se entrega para revisión, sin commit, push, rama, PR ni HFS-022.

## Cierre documental de HFS-021A

Se verificó mediante GitHub el
[workflow 40736064324](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40736064324),
asociado exactamente al SHA base en main: completed/success.

| Job | ID | Resultado |
|---|---:|---|
| Python 3.12 / Windows 2022 | 122984828020 | SUCCESS |
| Python 3.12 / Ubuntu 24.04 | 122984827536 | SUCCESS |

Los dos jobs completaron la construcción/verificación y subida de artefactos.
La [consulta conservada](evidence/hfs021a-closure-ci.json) identifica run, SHA,
fechas y steps. Con la aprobación del usuario y esta confirmación, el roadmap
registra **HFS-021A aprobado y cerrado**, paquete `steel_design`, distribución
**0.2.0**, corrección SVG multiplataforma aceptada y referencia local aprobada
de **1819 pruebas +12 subpruebas**.

Los informes HFS-020/021/021A y las capturas, incluido el run fallido
40694129771, permanecen íntegros. Sus notas «pendiente» describen su momento de
entrega; este suplemento actualiza el estado vivo sin reescribirlas. La CI
citada acredita la base HFS-021A, no los cambios locales HFS-021B.

El cierre de paquete/API no es certificación AISC. **F-31 continúa P0 abierto**,
mitigado por bloqueos sin resistencia mayor completa y validada del canal.
El [seguimiento normativo](../tracking.md) permanece intacto; no se cierran
otros defectos ni se habilitan dominios de diseño.

## Diagnóstico, decisiones y cambio aplicado

El [inventario por símbolo](cleanup-inventory.md) separa consumidores reales,
compromisos de compatibilidad y deuda pendiente. Se revisaron 157 archivos
de texto versionados, 68 candidatos de reflexión/acceso dinámico, entry points,
imports, scripts de captura, tests y contratos. El conteo incluye referencias
históricas clasificadas; no se presenta una búsqueda textual como prueba
suficiente de ausencia de consumidores.

**Se eliminaron dos bindings intermedios de función en `run.py`:**
`extract_output_options` y `merge_case_payload`. Solo alimentaban las
asignaciones de las fachadas privadas. No son rutas de la API oficial,
fachadas prometidas ni nombres usados por otros consumidores inspeccionados.
Las funciones permanecen en execution y las fachadas `_extract_output_options`
y `_merge_case_payload` siguen siendo exactamente esos mismos objetos.
Ahora las asignaciones consultan al propietario mediante un import privado
`_execution`; es el módulo ya existente, sin nueva dependencia o capa.

La diferencia observable de namespace está delimitada: desaparecen esos dos
atributos accidentales de run y aparece la referencia privada `_execution`.
Un consumidor externo que hubiera usado los nombres accidentales necesitaría
las rutas canónicas de execution. No se atribuye conocimiento de consumidores
externos; la decisión se apoya también en el contrato público explícito.
**No se eliminó ningún cuerpo de función.** No se fuerza una reducción de
líneas: se retiran nombres redundantes y se expresa la propiedad de las fachadas.

Se conservan `_build_case_section`, `_run_single_case`, todos los reexports
privados de reporting y `engine._build_custom_section`. Unos tienen llamadas
productivas, otros consumidores de pruebas/scripts, y otros compromiso explícito
HFS-021/021A. `SteelDesignEngine.run` y `run_with_context` son API pública
preservada. El inventario identifica por separado qué retiros quedan pospuestos
y qué autorización de compatibilidad requerirían; los aliases no son fórmulas
duplicadas. Modelos, geometría, reglas, cobertura y errores no se modifican.

`AGENTS.md` incorpora limpieza incremental obligatoria en cinco reglas concretas:
revisión de consumidores; retiro de código muerto demostrado dentro del hito
salvo impedimento documentado; compatibilidad justificada; regresión sin debilitar
pruebas; preservación de evidencia y separación de cambios normativos.
El roadmap y el inventario DRY reflejan el cierre y la responsabilidad canónica.

## Regresión realmente ejecutada

Windows, CPython 3.12.10. Herramientas/dependencias fijadas por las constraints
existentes: pytest 9.1.1, build 1.6.1, Ruff 0.17.3, twine 7.0.0,
pydantic 2.14.1/pydantic-core 2.50.1 y openpyxl 3.1.5. Freeze completo por
instalación y comandos/cwd/exit/stdout/stderr/JUnit dentro de las capturas.
No se añade ninguna dependencia ni se cambia versión 0.2.0.

| Suite | Antes | Después |
|---|---:|---:|
| Original | 68 +12 subpruebas | 68 +12 subpruebas |
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
| HFS-020 comparación | 50 | 50 |
| HFS-021 ejecución | 51 | 51 |
| HFS-021A API | 28 | 28 |
| HFS-021A SVG | 29 | 29 |
| **Métodos, sin sumar subpruebas** | **1819** | **1819** |

Ambos verificadores finales: **exit 0, accepted=true**, cero fallidas, errores,
omitidas, xfail o XPASS. Quince suites separadas; original y caracterización
conservan sus expectativas. La repetición de 28 pruebas de API en editable es
adicional en cada captura y no se suma al total principal. No se añadieron ni
modificaron pruebas para facilitar la eliminación.

Se ejecutaron antes/después los **12 ejemplos del motor**, **24 escenarios
CLI/memoria** y **seis SVG históricos** con la política CRLF/LF vigente. Pasaron
build de sdist y wheel reconstruido desde sdist, inspección de 44 fuentes,
instalación normal/wheel/editable, tres `pip check`, `twine check --strict`,
Ruff, identidad importable única, API pública, ambas entradas CLI e imports
en procesos frescos dentro/fuera del checkout. Los exit 1 deliberados del
namespace retirado y catálogo ausente son esperados, no fallos de suite.

**Diferencias ingenieriles: ninguna.** JSON, DCR (Demand-to-Capacity Ratio),
capacidades, demandas, estados, cobertura, trazas y códigos de salida coinciden
exactamente bajo la política aprobada. Los SVG de ambas capturas Windows son,
además, idénticos por bytes. Se reutiliza `compare_hfs021.compare_results` sin
modificar el comparador JSON/SVG. No se vuelve a ejecutar el comprobador completo
de migración HFS-021A contra un alcance distinto: su guardia de fuente íntegra
pertenece a aquel hito. HFS-021B añade un comprobador de auditoría acotado.

Ese comprobador demuestra:

- **43 de los 44 fuentes productivos idénticos** entre ambos wheels; solo run.py
  cambia. El checkout coincide exactamente con el wheel posterior.
- AST completo de run equivalente salvo el import de módulo, retirada de los
  dos imports intermedios y referencia calificada en las dos asignaciones.
  Texto de todas sus funciones, firmas y anotaciones idéntico.
- Namespace instalado: delta exacto de dos bindings retirados y `_execution`
  añadido. Propietarios/firmas del resto iguales; identidad de las 14 fachadas
  de reporting, dos de preparación, OutputOptions y constructor conservada.
- Git sin cambios en modelos, reglas, cálculo, geometría, cobertura, catálogo,
  ejemplos, tests, scripts, configuración/versión, contratos o evidencia anterior.
  `git diff --check` pasa; índice sin cambios staged.

## Reproducción y evidencia

Desde la raíz, con Git en PATH y el entorno de herramientas existente:

```powershell
# Base antes de la eliminación; después usar carpetas nuevas.
.\.venv\21dev\Scripts\python.exe -X utf8 scripts/verify_hfs020.py --out .venv/21b-before
# Corrida posterior final:
.\.venv\21dev\Scripts\python.exe -X utf8 scripts/verify_hfs020.py --out .venv/21b-after2
# Utilidades de auditoría conservadas en audit-tools.zip:
.\.venv\21dev\Scripts\python.exe -X utf8 .venv/21b-work/verify_cleanup.py
git diff --check
```

La captura previa se ejecutó antes de modificar run.py; reproducirla exige la
base indicada, no usar el código posterior como supuesto «antes». Las utilidades
registran rutas Windows reales y Git de GitHub Desktop: ajustar su ubicación al
reproducir en otro equipo, y extraer `audit-tools.zip` en `.venv/21b-work`.
No cargar simultáneamente dos paquetes para comparar; las sondas se ejecutan
en procesos aislados usando cada wheel y su carpeta externa.

- [Antes](evidence/before.zip) y [después](evidence/after.zip): comandos, entorno,
  freezes, JUnit, distribuciones, entradas verificadas, JSON, SVG originales y hashes.
- [Conteos y estado](evidence/validation.json),
  [comparación de resultados](evidence/results-comparison.json),
  [invariancia acotada de fuentes](evidence/scope-verification.json) y
  [namespace instalado](evidence/namespace-comparison.json).
- [Consumidores por ruta/línea](evidence/consumer-scan.json),
  [utilidades reproducibles](evidence/audit-tools.zip),
  [inventario completo de archivos/miembros](evidence/file-inventory.json) y
  [manifiesto SHA-256](evidence/SHA256SUMS.json).

Incidente conservado: la primera forma de import directo renombrado produjo
dos F401 en Ruff tras build y twine correctos. El verificador terminó exit 1
antes de instalar/ejecutar pruebas. Se mantuvo esa captura en
[failed-import-attempt.zip](evidence/failed-import-attempt.zip) y se corrigió
la forma de referencia al propietario; no se añadieron suppressions, `__all__`,
wrappers ni excepciones de lint. Se usó una salida nueva para la corrida final.
Se conservan las advertencias heredadas de acceso y LF/CRLF de AGENTS; no se
cambian ACL ni se considera inspeccionado contenido inaccesible.

## Archivos cambiados, riesgos y pendientes

Modificados: `AGENTS.md`, `docs/ROADMAP.md`, `docs/architecture/dry-inventory.md`
y `src/steel_design/run.py`. Nuevos: este informe, `cleanup-inventory.md` y la
evidencia enumerada en el inventario. No se alteran documentos históricos
HFS-020/021/021A, oráculos ni fuentes normativas.

La deuda verificada incluye helpers legacy de inferencia/capacidad y fachadas
sin consumidor directo pero con compromiso explícito. Algunos monkeypatch de
T014/T015 actúan sobre aliases de run y no interceptan globals de reporting;
sus aserciones de resultados se conservan, pero no se sobrestima su protección
negativa. Una retirada posterior requiere revisar ese compromiso y fortalecer
la prueba en el propietario, sin eliminarla para lograr un resultado verde.

HFS-021B requiere revisión técnica independiente y eventual publicación por el
usuario. La CI verificada cierra HFS-021A sobre la base publicada; no existe
todavía una corrida remota del cambio local HFS-021B. No se estudian ni modifican
`composite_rules.py`, solver del eje neutro, importador Excel o reglas de cobertura.
F-31 y los demás riesgos normativos abiertos siguen en su seguimiento. No se
inicia HFS-022 ni se declara superada una puerta de validación ingenieril.
