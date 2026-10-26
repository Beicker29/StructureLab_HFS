# HFS-001 — Informe de decisiones para revisión técnica

Fecha: 2026-10-26 (America/Bogota). Base de trabajo: `main`, `dae8d76507810362c4e31484a00b8d664525f2e6`, que incorpora HFS-000. El usuario aceptó esa línea base de comportamiento; no aceptó con ello validación normativa AISC. Se leyeron completos ROADMAP, baseline, findings e inventory y se contrastaron responsabilidades/duplicaciones con código.

**Resultado:** HFS-001 implementada en documentación. Decisiones arquitectónicas propuestas y listas para revisión; no se declaran aprobadas por el revisor. No se ejecutaron HFS-002, HFS-010 ni tareas posteriores. No hubo cambios de fórmulas, motor, router, contratos, resultados, tests existentes o dependencias; tampoco web, migración de carpetas ni limpieza de evidencia.

## Decisiones y discrepancias con el roadmap

| Tema | Decisión propuesta / fundamento | Consecuencia y pendiente |
|---|---|---|
| Árbol de arquitectura | Conservar funciones AISC en `codes`, reglas/routing en `domain`, catálogo/geometría en `sections`; extraer solo duplicaciones/responsabilidades demostradas. | Discrepo de tratar el árbol objetivo como destino obligatorio: renombrar carpetas y trasladar reglas no resuelve los defectos. ROADMAP ahora distingue propuesta original y revisión. |
| Servicios e interfaces | `SteelDesignEngine.run` como entrada canónica actual; futura ejecución común de caso/lote y adaptadores delgados. | No exigir `services` en cada capa ni `steel_design_web/services.py`. Cada extracción deberá tener consumidor/beneficio, sin segundo motor ni lógica AISC en web. |
| DRY | Una fuente por concepto, con simplicidad, responsabilidad única y separación. Inventario de 16 grupos: conservar justificadamente, consolidar o eliminar/sustituir con condiciones. | No se refactoriza. Consolidar capacidades necesita resolver fallbacks/dominios; no basta compartir fórmulas básicas. Oráculos independientes permanecen independientes. |
| Contratos | Evolucionar modelos Pydantic compartidos y errores estructurados; no crear DTO/modelos ingenieriles distintos por interfaz. | Estados/unidades/precisión futuros requieren transición explícita. No modificar el JSON actual en una tarea documental. |
| Completitud | INCOMPLETE como único estado público objetivo para incompletitud; BLOCKED como causa, no segundo sinónimo. | Discrepo de la ambigüedad `INCOMPLETE / BLOCKED`. Agregación conceptual decidida, sin construir la matriz de cobertura ni cambiar estados. |
| F-13 | Proponer P0 por geometrías reales diferentes bajo HEA 100 y sobrescritura dependiente del orden. | Discrepo de posponer toda mitigación hasta HFS-040/fase 4; planificar corrección acotada antes de G1. No se renombra catálogo ni se introduce rechazo ahora. |
| F-32 | Separar éxito de ejecución y cumplimiento estructural; conservar el exit actual hasta revisión de consumidores. | FAIL con exit 0 es contrato observado, no prueba de defecto numérico. No cambiarlo automáticamente al «endurecer» el CLI. |
| Trazabilidad | Ampliar registro existente y traza emitida por evaluación; referencias y pruebas independientes por dominio. | Sin DSL, base de datos o segundo registro de reglas para la web. No certificar cobertura por número de tests o líneas. |
| Evidencia | Conservar HFS-000 íntegro; documentar copias exactas y candidatos a archivo/deduplicación. | Sin `.gitignore` nuevo ni borrados. Un hash sin destino recuperable no justifica retirar evidencia. |

Los tres ADR contienen problema, alternativas, decisión, justificación, consecuencias y riesgos. Las decisiones de unidades, ejes y dominios normativos aún pendientes no se resolvieron mediante supuestos nuevos. Se mantienen `float` y dependencias existentes; no se instala FastAPI ni otro framework.

## Seguridad y seguimiento

[tracking.md](../tracking.md) incorpora F-01–F-32 con prioridad, certeza, destino y criterio de cierre; todos siguen abiertos. F-31 permanece P0 (omisión por eje reproducida en sonda; caso físico real pendiente). F-32 permanece P1 (semántica de transporte/consumo). F-13 se eleva a P0 **propuesto para revisión**, sustentado en [catalog-duplicates.json](../catalog-duplicates.json); aún no se sabe qué fila es correcta.

Los 11 `known defect` permanecen en el mismo archivo y con el mismo contenido. No se cerró ningún hallazgo por aprobar documentación ni se llamó defecto normativo confirmado a una hipótesis. No se elaboró la matriz familia × demanda × estado límite reservada a HFS-002.

## Verificación ejecutada

- Suite original reejecutada en `.venv/hfs001-review/work`, copia verificada por hash de fuentes/tests/ejemplos/catálogo. Python 3.12.10 y paquetes del entorno HFS-000; comandos completos, cwd, entorno y hashes en [original-tests.json](original-tests.json).
- Resultado: **68 métodos y 12 subpruebas aprobados; 0 fallidos, 0 omitidos, 0 errores**, exit 0, 30,79 s según consola. JUnit agrega 80 casos. Una advertencia conocida: `Section.Config` de Pydantic obsoleta. La suite smoke original ejecuta los 12 ejemplos.
- Comando: `python -m pytest -q -ra --tb=short -p no:cacheprovider --ignore=tests/test_hfs000_characterization.py --junitxml=<temporal nuevo>/original.xml`, con Python del entorno fijado, `PYTHONNOUSERSITE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONUTF8=1` y sin PYTHONPATH heredado. Desactivar caché no omite pruebas; evita una escritura prescindible.
- **No se reejecutó la caracterización en HFS-001**: no cambió runtime ni el archivo de tests; su evidencia aceptada sigue siendo 11 xfail en HFS-000 y se verificó integridad. No se presenta ese conteo como una ejecución nueva.
- Se comprobaron los hashes de los 90 archivos incluidos en los dos manifiestos HFS-000: cero discrepancias. Se compararon los 184 archivos versionados al inicio: solo ROADMAP cambió. Git confirma diff vacío para `src`, `tests`, `scripts`, `data`, `examples` y `requirements.txt`.
- `git diff --check` sin errores y enlaces locales de la documentación HFS-001 comprobados. Sin nuevos tests, lint, tipos o dependencias para este cambio documental. No se realizaron cálculos normativos independientes porque no se modifican cálculos ni se declara su validación.

[verification.json](verification.json) conserva la prueba Git y de integridad. Persisten avisos de acceso a los directorios históricos no versionados ya clasificados; no impidieron verificar archivos versionados ni ejecutar la suite aislada. No se cambió ninguna ACL. La igualdad de archivos prueba ausencia de modificaciones del motor; no se afirma una nueva comparación numérica exhaustiva de todas sus rutas.

## Inventario completo de cambios entregables

| Archivo | Cambio / finalidad |
|---|---|
| `AGENTS.md` | Nuevo: reglas permanentes de alcance, DRY, exactitud, pruebas y evidencia |
| `CONTRIBUTING.md` | Nuevo: procedimiento de contribución y reproducción |
| `docs/ROADMAP.md` | Modificado: revisión arquitectónica, principio DRY, F-13/F-31/F-32 y enlaces al seguimiento |
| `docs/adr/001-engine-architecture.md` | Nuevo: arquitectura y separación de interfaces |
| `docs/adr/002-contracts-errors.md` | Nuevo: contratos, completitud, precisión y errores |
| `docs/adr/003-traceability-testing.md` | Nuevo: referencias normativas, cobertura y pruebas independientes |
| `docs/architecture/dry-inventory.md` | Nuevo: 16 diagnósticos y fuentes canónicas por responsabilidad |
| `docs/audit/tracking.md` | Nuevo: seguimiento vivo de 32 hallazgos, sin alterar el diagnóstico histórico |
| `docs/audit/evidence-policy.md` | Nuevo: retención, duplicaciones y candidatos documentados, sin limpieza |
| `docs/audit/hfs001/duplicate-evidence.json` | Nuevo: 10 grupos idénticos por hash con rutas/tamaños |
| `docs/audit/hfs001/original-tests.json` | Nuevo: ejecución real de la suite original y entorno |
| `docs/audit/hfs001/verification.json` | Nuevo: Git, integridad y comprobaciones finales |
| `docs/audit/hfs001/report.md` | Nuevo: este cierre y pendientes |

Total: **1 archivo preexistente modificado y 12 nuevos**. Los auxiliares y temporales `.venv/hfs001_verify.py`, `.venv/hfs001-review/` quedan ignorados por Git; contienen la copia de ejecución, JUnit temporal y snapshot de hashes para verificación. No se hicieron commits ni cambios al índice. Los 103 entregables históricos de HFS-000 no se regeneraron ni reescribieron.

## Pendientes para revisión, sin ejecución

1. Revisar los tres ADR y ratificar/corregir las fuentes canónicas del inventario DRY.
2. Decidir ubicación y dependencias de la mitigación acotada F-13 antes de G1; no está autorizada su implementación por este informe.
3. Resolver en sus tareas la semántica de ejes/fallbacks, reglas compartibles y contratos futuros; las propuestas DRY condicionadas no acreditan equivalencia normativa.
4. Revisar candidatos de retención y preparar destino durable/índice/restauración antes de una posible limpieza. Ningún archivo propuesto para exclusión/eliminación se ha cambiado.
5. Tras revisión, decidir el siguiente trabajo del roadmap. HFS-002, HFS-010, refactorizaciones y web siguen pendientes.

Reversibilidad: las decisiones son adiciones documentales y una actualización acotada de ROADMAP; retirar/revisar esos cambios no modifica el motor ni las capturas. No se realizó ningún rollback o borrado.
