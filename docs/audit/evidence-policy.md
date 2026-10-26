# HFS-001 — Política mínima de evidencia

Estado: política propuesta para revisión; **no se elimina, mueve, excluye ni reescribe ningún archivo en HFS-001**. `.gitignore` no cambia. La evidencia aceptada de HFS-000 continúa accesible por las mismas rutas y hashes.

## Autoridad y retención

1. Conservar en Git informes aceptados, instrucciones de reproducción, freeze, hashes de entradas, manifiestos y las fixtures canónicas de resultados. Su aceptación es de comportamiento; no las usar como oráculo AISC.
2. Conservar los errores de intentos fallidos y su contexto: son evidencia diferente de una ejecución exitosa. No retener solo la corrida «verde».
3. Nuevas ejecuciones exploratorias deben escribir fuera de rutas congeladas, preferentemente en una carpeta ignorada bajo `.venv/`. Promover a evidencia de revisión solo lo necesario para explicar un cambio, con comando, entorno, SHA y resultado. No llenar Git con cada repetición de outputs.
4. Evidencia aceptada es inmutable. Corregir documentación histórica con un suplemento, no cambiando sus resultados. El estado actual de defectos vive en [tracking](tracking.md).
5. Una futura reducción debe preservar tanto contenido como recuperación verificable. Un hash solo no permite recuperar un archivo. Hasta que exista destino durable revisado y probado, mantener los archivos actuales, aunque estén duplicados.

## Duplicaciones medidas

[duplicate-evidence.json](hfs001/duplicate-evidence.json) identifica **10 grupos de archivos idénticos por SHA-256**, con todas las rutas exactas y tamaños, sobre el commit `dae8d76507810362c4e31484a00b8d664525f2e6`. Es igualdad de bytes; no se llama duplicado exacto a un log que difiere por rutas, fechas o errores.

- Siete pares `evidence/` vs `evidence-clean/`: `catalog.json`, `copied_inputs.json`, `engine-results.json`, `environment-freeze.txt`, `environment.json`, `examples.json`, `tracked_inventory.json`.
- Tres grupos SVG: 7 copias encased, 7 circular y 9 rectangular entre ambas capturas y `results/`. Las 23 rutas están en el manifiesto. Las imágenes son iguales por bytes, aunque los nombres incluyan distintos timestamps.
- Los 48 registros `cli/*.json` de las dos capturas documentan ejecuciones; los resultados normalizados coinciden, pero sus registros crudos no son iguales por bytes. El error de acceso de caracterización en sandbox es evidencia única y debe permanecer.
- HFS-000 menciona dos roadmaps. En el checkout actual solo existe `docs/ROADMAP.md`; no recrear `StructureLab_HFS_Roadmap_Codex.md`. Esa ausencia es previa a HFS-001, no una eliminación realizada aquí.

## Propuestas por archivo o conjunto (sin ejecutar)

| Rutas / inventario exacto | Política objetivo | Motivo y preservación requerida antes de retirar |
|---|---|---|
| `baseline.md`, `findings.md`, `inventory.md`, `changed-files.md`, `access-issues.json`, `catalog-duplicates.json`, `module-inventory.json`, `final-verification.json`, `git-final-status.json` de HFS-000 | **Conservar** histórico en Git | Explican qué se ejecutó y qué no se pudo inspeccionar. No reemplazarlos por este seguimiento. |
| `evidence-clean/engine-results.json`, `examples.json`, `catalog.json`, `copied_inputs.json`, `tracked_inventory.json`, `environment-freeze.txt`, `environment.json`, `verification.json`, `SHA256SUMS.json` | **Conservar** conjunto canónico aceptado | Referencia compacta y reproducible; mantienen identidad de entradas/resultados. |
| Los siete archivos homónimos en `evidence/` indicados arriba | **Candidatos a deduplicar** en tarea posterior | Misma información binaria. Crear mapa `ruta original -> SHA-256 -> ruta canónica`, preservar manifiestos originales y copia recuperable de captura antes de retirar las copias. |
| `evidence*/pytest-*.json`, `pytest-*.xml`, `git_before.json`, `git_after.json`, `verification.json`, `SHA256SUMS.json` | **Conservar por ahora** | XML aporta resultados por test; JSON guarda comando/stdout/errores. Se solapan, pero no son equivalentes completos. Una reducción exigiría comprobar campos y recuperar el registro íntegro, incluido el fallo de infraestructura. |
| `evidence*/cli/*.repeat-2.json` (24 archivos); otros logs CLI si luego se acuerda | **Candidatos a archivo externo recuperable**, no descarte directo | Las repeticiones prueban estabilidad, pero no conviene multiplicarlas indefinidamente en Git. Conservar al menos una corrida cruda completa por captura y prueba de repetición; archivar todo lo retirado con índice/hashes. Sin destino durable actual, no retirar nada. |
| Los 23 SVG de `hfs001/duplicate-evidence.json` | **Candidatos a consolidar** en tres blobs canónicos | Mantener una muestra por grupo y mapas de todas las rutas/corridas; preservar archivo de capturas y manifiestos. No borrar una referencia sin resolver sus enlaces. |
| `results/**` (11 SVG versionados); `.tmp_debug_cli/**` (5 archivos); `tests/.tmp_tests/manual_check/**` (2 archivos) | **Proponer excluir futuras salidas/temporales** tras clasificar fixtures | Inventario completo en [inventory.md](inventory.md). JSON/XLSX y extractos pueden ser muestras útiles; revisarlos individualmente y promover los necesarios con procedencia antes de retirar del seguimiento. No inferir que son basura por el nombre. |
| `.tmp_test/**`, otros `tests/.tmp_tests/**` inaccesibles | **Conservar sin tocar; inspección pendiente** | No conocemos el contenido. No cambiar ACL ni borrar. Los 30 directorios concretos están en [access-issues.json](access-issues.json). |
| `.venv/**`, bytecode, caché de pytest | **Mantener fuera de Git**, como ya dispone `.gitignore` | Regenerables; el freeze y los comandos documentan reproducción, no son sustituto del archivo de evidencia aceptado. |
| `a360-22w.pdf`, `a341-22w.pdf`, `data/sections.xlsx` | **Conservar** | Son entradas/fuentes identificadas por hash; permisos, fuente y erratas siguen pendientes de su tarea. No deduplicar ni retirar por tamaño. |

Los patrones son propuestas de política, no reglas aplicadas. No agregar una exclusión amplia como `docs/audit/**` que oculte nueva evidencia. `.gitignore` tampoco elimina archivos ya versionados; cualquier futura retirada del índice debe ser una decisión explícita, sin reescribir el historial Git.

## Procedimiento mínimo de reducción futura

Antes de cualquier retirada: enumerar archivos exactos, motivo y propietario; comprobar SHA-256; identificar vínculos y herramientas que usan sus rutas; preparar archivo recuperable sin pérdida y registrar ubicación, hash y prueba de restauración. Conservar en Git un índice de procedencia con ruta/commit original, blob/hash, destino y cambio de retención. No alterar los manifiestos de las capturas: una vista deduplicada necesitará un resolvedor/índice nuevo o recuperación de la carpeta original para verificarlos.

Si no se puede demostrar recuperación, detener esa limpieza y mantener evidencia. Revisar el inventario antes de aplicarlo; hacerlo en una tarea propia y limitada. Los nuevos logs de HFS-001 no reemplazan HFS-000 y solo registran la verificación documental y de reproducibilidad pertinente.
