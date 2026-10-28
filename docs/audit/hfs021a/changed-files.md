# Inventario HFS-021A

Base `main`, `39a7614a413a06eef78f597e142f7ba0e889c123`.
El [inventario JSON](file-inventory.json) enumera cada archivo nuevo/modificado
y su hash. No hay commits, push, ramas ni PR. No se sobrescribe evidencia previa.

| Conjunto | Cambio y límite |
|---|---|
| `pyproject.toml` | Versión 0.2.0, entry point steel_design.run, src-layout con paquetes explícitos y namespaces=false. Dependencias intactas |
| `src/steel_design/__init__.py` | Rechazo temprano del namespace legado; sin reexports, alias ni efectos de aplicación |
| Otros siete `__init__.py` en codes, codes/aisc_360_22, domain, domain/evaluators, domain/routing, domain/rules, sections | Declaración de subpaquetes reales; solo docstrings |
| `src/steel_design/domain/coverage_evidence.py` | Adaptación exclusiva del identificador textual histórico en JSON; clases canónicas, decisiones de cobertura idénticas. No se normaliza el comparador para ocultar cambios |
| 22 archivos `tests/test_*.py` preexistentes | Solo cambio del prefijo de imports/comandos/dinámicos. Los 23 archivos de pruebas de la base conservan AST bajo esa transformación; test_hfs020_comparison no necesitó cambio |
| `tests/test_hfs021a_public_api.py` | Nueva suite de API, identidad, importaciones, fachadas, comando legado y mutaciones del comparador AST |
| `scripts/audit_baseline.py`, `audit_hfs011.py`, `audit_hfs014_cli.py`, `audit_hfs017_probes.py`, `probe_hfs015.py`, `debug_loader.py` | Imports/ejecución convencionales y src explícito en capturas de fuentes; mismas ecuaciones, inputs y normalización |
| `scripts/verify_hfs020.py` | Inspección de distribución convencional, versión dinámica, tres instalaciones, API/identidades, rechazo legado y residuos de build, nueva suite y 6 SVG históricos |
| `scripts/compare_hfs021.py` | Extrae compare_results reutilizable sin cambiar comparación exacta; conserva chequeo histórico de extracción |
| `scripts/compare_hfs021a.py` | Comparación de capturas, SVG e invariantes de fuentes/tests contra la base aprobada |
| `scripts/hfs021a_invariants.py` | AST completo bajo una única sustitución explícita de prefijo |
| `scripts/probe_hfs021a_imports.py` | Sonda en proceso fresco de identidad, API e importaciones sin efectos de aplicación |
| `README.md`, `CONTRIBUTING.md` | Instalación/uso vigente, editable, ruptura de imports y migración de residuos de build |
| `AGENTS.md` | Regla permanente de un solo paquete/identidad, sin aliases de modelos |
| `docs/ROADMAP.md` | HFS-021 aprobado; HFS-021A entre 021 y 022, entrega para revisión |
| `docs/architecture/dry-inventory.md` | Dueños de identidad pública, ejecución existente y verificadores reutilizados |
| `docs/contracts/hfs021a-public-api.md` | API oficial por módulos, helpers internos, compatibilidad y retirada de comandos |
| `docs/audit/hfs021a/**` | Preparación, mapa, informe, este inventario y evidencia nueva con procedencia/hashes |

## Archivos preservados y traslado justificado

**35 de los 36 fuentes productivos anteriores** permanecen idénticos: motor,
ejecución, reportes, geometría, modelos, dominio, cálculos, catálogo/importador,
precisión y guardas LRFD/ASD. El archivo restante conserva toda la lógica y
adapta únicamente el ID histórico de metadata, verificado con AST restringido.
Los nuevos inicializadores no cambian esas implementaciones.
`scripts/hfs020_comparison.py`, catálogo, ejemplos y
documentos/capturas históricas permanecen intactos.

`MANIFEST.in` se inspeccionó y no necesitó cambio: la ubicación física sigue
siendo src/steel_design. `.github/workflows/ci.yml` sigue llamando el verificador
ampliado con Windows 2022/Ubuntu 24.04; no se modifican jobs, fallos ni permisos.

Se trasladó exclusivamente el build **generado e ignorado** de 0.1.0 que
contaminaba pip install: `build/` → `.venv/21a-legacy-build`. Se verificaron
ambas rutas absolutas y se conservaron antes sus 80 archivos en ZIP con hashes.
[Justificación y recuperación](evidence/legacy-build-preservation.json).
No hubo borrado ni cambios de permisos. Los nuevos builds actuales se prueban
sin ese residuo. Los entornos y temporales de intentos fallidos se conservan
localmente; sus logs/distribuciones se archivan como evidencia de esta tarea.

## Pendientes

- Revisión técnica independiente y publicación por el usuario.
- Nueva ejecución remota Windows/Ubuntu para el futuro commit HFS-021A.
- Adaptación de consumidores externos que aún importen src.steel_design;
  no existe paquete puente ni compatibilidad de pickles antiguos.
- Decisión específica sobre matplotlib opcional, sin añadirla ahora; SVG
  ejercido y algoritmo PNG preservado.
- HFS-022/023/024, web y defectos normativos siguen fuera del alcance.
- Temporales históricos inaccesibles intactos. No se interpreta su contenido
  ni se propone borrarlo como parte de esta migración.
