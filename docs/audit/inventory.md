# HFS-000 — Inventario de módulos y responsabilidades

Inspección del checkout, sin aceptar automáticamente la arquitectura. Rutas relativas a `src/steel_design/`.

| Módulo | Líneas | Responsabilidad observada |
|---|---:|---|
| `codes/aisc_360_22/axial_calc.py` | 226 | Funciones de compresión, clasificación/esbeltez y pandeo. |
| `codes/aisc_360_22/combined_hss_calc.py` | 172 | Funciones de torsión e interacción HSS. |
| `codes/aisc_360_22/composite_calc.py` | 504 | Funciones auxiliares de miembros compuestos y anclajes. |
| `codes/aisc_360_22/flexure_calc.py` | 578 | Funciones de flexión por familia/estado límite, incluida ruta F4 mediante F5. |
| `codes/aisc_360_22/shear_calc.py` | 132 | Funciones de resistencia a cortante. |
| `codes/aisc_360_22/tension_calc.py` | 37 | Funciones de tracción y factores LRFD/ASD. |
| `domain/errors.py` | 50 | Errores estructurados de datos, validación, sección y reglas no implementadas. |
| `domain/evaluators/flexure_evaluator.py` | 20 | Evaluación F2 y presentación de variables intermedias. |
| `domain/evaluators/tension_evaluator.py` | 50 | Orquestación de capacidades de fluencia/rotura y selección gobernante de tracción. |
| `domain/routing/profile_router.py` | 799 | Registro de reglas, aplicabilidad, requisitos de propiedades y selección por familia. |
| `domain/rules/axial_rules.py` | 417 | Checks E3/E4/E5/E7 y clasificación de elementos. |
| `domain/rules/combined_hss_rules.py` | 575 | Obtención de capacidades e interacción H1/H3 para HSS. |
| `domain/rules/composite_rules.py` | 1870 | Checks I1–I5, geometría, integración de franjas, neutral axis, capacidades e interacción. |
| `domain/rules/flexure_rule.py` | 775 | Checks por estado límite/eje F2–F11 implementados y alias de compatibilidad. |
| `domain/rules/shear_rules.py` | 489 | Checks G2–G6, selección de demanda y etiquetas de ejes. |
| `domain/rules/tension_rule.py` | 99 | Checks D2, demandas, capacidades, DCR y memoria. |
| `domain/validation.py` | 100 | Validación de longitudes, materiales, factores, conexiones, método y compuesto. |
| `engine.py` | 156 | Valida, obtiene/construye sección, enruta reglas, ejecuta y agrega estado. |
| `models.py` | 319 | Contratos Pydantic de caso, material, cargas, longitudes, compuesto y CheckResult; normalización de cortante. |
| `results_model.py` | 7 | Agregado EngineResult con checks y estado. |
| `run.py` | 746 | Adaptador CLI, lotes, JSON, admisibilidad, memorias, diagramas y geometría custom duplicada. |
| `sections/loader.py` | 377 | Importación Excel, clasificación de familias, encabezados, conversiones y razones derivadas. |
| `sections/models.py` | 63 | Section: propiedades geométricas con alias de catálogo. |
| `sections/repository.py` | 23 | Índice en memoria por nombre en mayúsculas; sobrescritura de duplicados. |

## Otros componentes

| Ruta | Responsabilidad / observación |
|---|---|
| `tests/test_*.py` originales | 11 módulos unittest, 68 pruebas y 12 subpruebas pytest; incluye pruebas de reglas, routing, loader, CLI y smoke de 12 ejemplos. |
| `examples/*.json` | 12 entradas CLI: 8 familias de acero incluidas las macizas custom; 4 configuraciones de compuesto. |
| `data/sections.xlsx` | 7 hojas; 1.228 entradas cargadas, 1.223 nombres retenidos. |
| `scripts/debug_loader.py` | Cuenta familias e imprime primeras secciones; solo lectura. |
| `scripts/dump_headers.py` | Escribe headers.json; inspeccionado, no ejecutado sobre el checkout. |
| `scripts/make_dummy_excel.py` | Genera catálogo aproximado de ejemplo; no usado como referencia normativa ni ejecutado. |
| `requirements.txt` | Solo pydantic>=2.0 y openpyxl>=3.1; sin lock ni herramientas de pruebas. |
| `docs/unidades.md`, `docs/aisc_360_22_traceability.md` | Convenciones y matriz manual de implementaciones; no certifican validez. |
| `a360-22w.pdf`, `a341-22w.pdf` | Referencias preservadas e identificadas por SHA-256; contenido/erratas no auditados en HFS-000. |
| `results/`, `.tmp_debug_cli/`, `tests/.tmp_tests/` | Artefactos históricos; inventario abajo. |
| `.venv/`, `.vscode/`, `.git/` | Entorno local, configuración de editor y control de versiones. .venv original conservado. |
| `scripts/audit_baseline.py`, `tests/test_hfs000_characterization.py` | Nuevos: captura reproducible aislada y pruebas conocidas de defectos. |

## Qué conservar y qué revisar

Conservar la separación existente entre funciones, reglas y orquestación como punto de partida; los errores estructurados y bloqueos por datos faltantes tienen evidencia en pruebas. Conservar las trazas y el catálogo sin cambios. Esto no valida todas las fórmulas ni todos los bloqueos.

Revisar primero cobertura y contratos: una regla declarada no garantiza que se seleccione. El CLI concentra responsabilidades y repite geometría; los compuestos concentran cálculo numérico en reglas. Son razones concretas para evaluar futuras extracciones, no para reorganizar ahora. La arquitectura objetivo del roadmap sigue siendo una propuesta, no una aprobación de HFS-000.

## Artefactos versionados y plan de limpieza (sin ejecutar)

| Archivo | Bytes |
|---|---:|
| `.tmp_debug_cli/case.json` | 309 |
| `.tmp_debug_cli/i5_method2_plot_case.json` | 783 |
| `.tmp_debug_cli/sections.xlsx` | 4990 |
| `.tmp_debug_cli/table_6_2_pdfplumber.txt` | 13039 |
| `.tmp_debug_cli/table_6_extract.txt` | 7083 |
| `results/COMPOSITE_ENCASED_CASE/20260413T170017263405Z/interaction_diagrams/W/W14X90__20260413T170017264405Z__I5_METHOD2.svg` | 4696 |
| `results/COMPOSITE_ENCASED_CASE/20260413T170156712189Z/interaction_diagrams/W/W14X90__20260413T170156713145Z__I5_METHOD2.svg` | 4696 |
| `results/COMPOSITE_ENCASED_CASE/20260413T170755477072Z/W/W14X90__20260413T170755478083Z__I5_METHOD2.svg` | 4696 |
| `results/COMPOSITE_FILLED_CIRCULAR_HSS_CASE/20260413T170022490053Z/interaction_diagrams/CIRCULAR_HSS/PTER4_X6.00MM__20260413T170024312208Z__I5_METHOD2.svg` | 4754 |
| `results/COMPOSITE_FILLED_CIRCULAR_HSS_CASE/20260413T170202061243Z/interaction_diagrams/CIRCULAR_HSS/PTER4_X6.00MM__20260413T170203769226Z__I5_METHOD2.svg` | 4754 |
| `results/COMPOSITE_FILLED_CIRCULAR_HSS_CASE/20260413T170800912186Z/CIRCULAR_HSS/PTER4_X6.00MM__20260413T170802697850Z__I5_METHOD2.svg` | 4754 |
| `results/COMPOSITE_FILLED_RECTANGULAR_HSS_CASE/20260413T170018988612Z/interaction_diagrams/RECTANGULAR_HSS/PTE50X30X2.5MM__20260413T170020753022Z__I5_METHOD2.svg` | 4750 |
| `results/COMPOSITE_FILLED_RECTANGULAR_HSS_CASE/20260413T170034666906Z/interaction_diagrams/RECTANGULAR_HSS/PTE50X30X2.5MM__20260413T170036450402Z__I5_METHOD2.svg` | 4750 |
| `results/COMPOSITE_FILLED_RECTANGULAR_HSS_CASE/20260413T170158509310Z/interaction_diagrams/RECTANGULAR_HSS/PTE50X30X2.5MM__20260413T170200267101Z__I5_METHOD2.svg` | 4750 |
| `results/COMPOSITE_FILLED_RECTANGULAR_HSS_CASE/20260413T170730460739Z/RECTANGULAR_HSS/PTE50X30X2.5MM__20260413T170732380245Z__I5_METHOD2.svg` | 4750 |
| `results/COMPOSITE_FILLED_RECTANGULAR_HSS_CASE/20260413T170757278273Z/RECTANGULAR_HSS/PTE50X30X2.5MM__20260413T170759093730Z__I5_METHOD2.svg` | 4750 |
| `tests/.tmp_tests/manual_check/a.txt` | 4 |
| `tests/.tmp_tests/manual_check/sections.xlsx` | 4835 |

18 archivos históricos versionados. El inventario completo y hashes de los 80 archivos originales está en `evidence-clean/tracked_inventory.json`.

Plan posterior: identificar qué muestras tienen procedencia y utilidad; conservar fixtures necesarias con contexto; acordar exclusiones de salidas/temporales; retirar del seguimiento solo después de revisar dependencias y respaldo. No se ejecutó limpieza, borrado, movimiento ni cambio de ACL. Los directorios inaccesibles se listan en `access-issues.json`; su contenido sigue desconocido.
