# Inventario HFS-021

Base `main`, `f3a5198309d24f772f6cac69ccc483846b81d21a`.
Sin ramas, PR, commits, push, cambios de permisos ni eliminación de evidencia.
Listado exhaustivo por ruta y hash en [file-inventory.json](file-inventory.json).

## Runtime

| Archivo | Cambio / responsabilidad |
|---|---|
| `src/steel_design/engine.py` | `run_with_context` conserva el pipeline; `run` mantiene contrato. Constructor antiguo reexportado desde geometría |
| `src/steel_design/run.py` | Adaptador CLI; conserva aliases y fachada de helpers. Delega preparación, ejecución y presentación |
| `src/steel_design/execution.py` (nuevo) | Preparación/ejecución individual y secuencial de lotes en memoria; contexto de modelos existentes; agregación compartida |
| `src/steel_design/reporting.py` (nuevo) | Helpers extraídos, datos compactos/detallados puros y exportación explícita JSON/diagramas |
| `src/steel_design/sections/geometry.py` (nuevo) | Constructor macizo canónico, expresiones exactas previas |

## Verificación y documentación

| Archivo | Cambio |
|---|---|
| `tests/test_hfs021_execution.py` (nuevo) | 51 pruebas de geometría, ejecución, contratos, consumidores y ausencia de efectos |
| `scripts/verify_hfs020.py` | Una entrada nueva en SUITES; HFS-021 separada, sin cambiar comparaciones ni tests anteriores |
| `scripts/compare_hfs021.py` (nuevo) | Contraste exacto antes/después, identidad AST, fuentes protegidos y bytes SVG; reutiliza comparación HFS-020 |
| `CONTRIBUTING.md` | Reproducción de la suite adicional y contrato Python |
| `docs/ROADMAP.md` | HFS-020 aprobado con run remoto confirmado; HFS-021 para revisión, sin avance |
| `docs/audit/tracking.md` | Únicamente F-15/F-16: cierre funcional acotado para revisión |
| `docs/architecture/dry-inventory.md` | Propietarios actuales de ejecución, geometría, presentación y verificación |
| `docs/contracts/hfs021-execution.md` (nuevo) | API Python, efectos, errores, compatibilidad y límites |
| `docs/audit/hfs021/preparation.md` (nuevo) | Estado inicial, consumidores, diagnóstico y decisión previa |
| `docs/audit/hfs021/report.md` (nuevo) | Decisiones, pruebas reales, resultados, incidentes y riesgos |
| Este inventario y `file-inventory.json` (nuevos) | Relación completa de rutas cambiadas |
| `docs/audit/hfs021/evidence/**` (nuevo) | Capturas reproducibles antes/después, logs, ZIP recuperables, hashes, fuente GitHub, JUnit inicial y controles finales; cada ruta en el inventario JSON |

## Pendientes explícitos

- Revisión técnica independiente de HFS-021 y publicación por el usuario.
- Nueva corrida remota Windows/Ubuntu del cambio cuando sea publicado; la
  confirmación remota incluida pertenece a HFS-020, no al código sin commit.
- Rama PNG preservada por AST, pero no ejecutada con matplotlib real; los
  entornos limpios prueban el fallback SVG sin dependencia gráfica obligatoria.
- HFS-022/024, ASD HFS-039 y todos los defectos normativos fuera de alcance.
  F-31 no se considera resuelto. No hay archivos de esas tareas modificados.
- Directorios temporales inaccesibles heredados permanecen intactos; no se
  conoce ni se elimina su contenido.

`models.py`, `results_model.py`, reglas, cálculos AISC, routing, validación,
guardas LRFD/ASD, loader/repositorio, catálogo, ejemplos y expectativas
históricas no cambian. La evidencia de hitos anteriores permanece intacta.
Los archivos de trabajo bajo `.venv/21*` son regenerables y están ignorados;
la evidencia necesaria se preserva en los ZIP, sin incluir entornos completos.
