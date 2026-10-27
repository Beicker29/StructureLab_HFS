# HFS-017 ? Inventario de cambios

Base `main`/`7234df8`; cambios locales sin staging/commit/push. ?rbol inicial limpio.

| Archivo | Prop?sito |
|---|---|
| [CONTRIBUTING.md](../../../CONTRIBUTING.md) | Und?cima suite y reproducci?n. |
| [docs/ROADMAP.md](../../ROADMAP.md) | HFS-017 para revisi?n; dependencias y l?mites. |
| [docs/architecture/dry-inventory.md](../../architecture/dry-inventory.md) | Fuentes can?nicas y consumidores de m?todo/factores. |
| [docs/audit/hfs017/changed-files.md](changed-files.md) | Este inventario. |
| [docs/audit/hfs017/report.md](report.md) | Diagn?stico, decisiones, pruebas, diferencias y riesgos. |
| [docs/audit/hfs017/support-matrix.md](support-matrix.md) | Cap?tulo ? familia ? estado ? m?todo; sin acreditaci?n nueva. |
| [docs/audit/tracking.md](../tracking.md) | F-44/F-45 y estado vivo; pendientes preservados. |
| [docs/contracts/hfs017-design-method.md](../../contracts/hfs017-design-method.md) | Contrato, demandas externas y migraci?n. |
| [scripts/audit_hfs017_probes.py](../../../scripts/audit_hfs017_probes.py) | Sondas reproducibles contra ra?z expl?cita. |
| [scripts/compare_hfs017.py](../../../scripts/compare_hfs017.py) | Comparaci?n estricta de ejemplos y CLI. |
| [src/steel_design/codes/aisc_360_22/axial_calc.py](../../../src/steel_design/codes/aisc_360_22/axial_calc.py) | E1: factor/traza ?nicos y m?todo estricto. |
| [src/steel_design/codes/aisc_360_22/combined_hss_calc.py](../../../src/steel_design/codes/aisc_360_22/combined_hss_calc.py) | Rechazar m?todo inv?lido antes de nominal cero. |
| [src/steel_design/codes/aisc_360_22/shear_calc.py](../../../src/steel_design/codes/aisc_360_22/shear_calc.py) | Rechazar m?todo inv?lido antes de nominal cero. |
| [src/steel_design/codes/aisc_360_22/tension_calc.py](../../../src/steel_design/codes/aisc_360_22/tension_calc.py) | D2: factores propios por estado, traza y m?todo estricto. |
| [src/steel_design/design_methods.py](../../../src/steel_design/design_methods.py) | Enum ?nico y rechazo de tokens desconocidos. |
| [src/steel_design/domain/design_methods.py](../../../src/steel_design/domain/design_methods.py) | Guarda y pol?tica p?blica F/I compartidas. |
| [src/steel_design/domain/evaluators/flexure_evaluator.py](../../../src/steel_design/domain/evaluators/flexure_evaluator.py) | Bloqueo directo ASD; m?todo validado hacia F1. |
| [src/steel_design/domain/evaluators/hss_shear.py](../../../src/steel_design/domain/evaluators/hss_shear.py) | Guarda del evaluador compartido G/H. |
| [src/steel_design/domain/evaluators/tension_evaluator.py](../../../src/steel_design/domain/evaluators/tension_evaluator.py) | Guarda, m?todo en resultado y correcci?n de unidad del docstring. |
| [src/steel_design/domain/routing/profile_router.py](../../../src/steel_design/domain/routing/profile_router.py) | Misma pol?tica en router directo y ruta I. |
| [src/steel_design/domain/rules/axial_rules.py](../../../src/steel_design/domain/rules/axial_rules.py) | Guardas directas y alias a traza can?nica E1. |
| [src/steel_design/domain/rules/combined_hss_rules.py](../../../src/steel_design/domain/rules/combined_hss_rules.py) | Guardas de m?todo, F-43/interacciones intactas. |
| [src/steel_design/domain/rules/composite_rules.py](../../../src/steel_design/domain/rules/composite_rules.py) | Guardas I en reglas/helpers, sin tocar ecuaciones. |
| [src/steel_design/domain/rules/flexure_rule.py](../../../src/steel_design/domain/rules/flexure_rule.py) | Guardas LRFD antes de evaluaci?n/retorno; F1 can?nico. |
| [src/steel_design/domain/rules/shear_rules.py](../../../src/steel_design/domain/rules/shear_rules.py) | Guardas incluso en reglas inactivas/bloqueadas. |
| [src/steel_design/domain/rules/tension_rule.py](../../../src/steel_design/domain/rules/tension_rule.py) | Guardas directas y metadatos D2 activos. |
| [src/steel_design/domain/validation.py](../../../src/steel_design/domain/validation.py) | Consumir pol?tica can?nica manteniendo HFS-011. |
| [src/steel_design/models.py](../../../src/steel_design/models.py) | Reexportar DesignMethod sin cambiar JSON/default. |
| [tests/test_hfs017_design_method.py](../../../tests/test_hfs017_design_method.py) | 468 casos de contrato, or?culos y consumidores. |

Los archivos de evidencia est?n enumerados individualmente con SHA-256 en
[el manifiesto](evidence/SHA256SUMS.json): capturas antes/despu?s de suites y
12 ejemplos, 24 consumidores CLI por captura, sondas, comparaci?n, incidentes
incluido red final y prueba de preservaci?n de alcance. No reemplazan evidencia
hist?rica. Las copias de trabajo completas/artifacts exploratorios permanecen
en `.venv/17*`; las capturas necesarias para revisi?n est?n en esta entrega.

Sin cambios de dependencias, cat?logo/PDF, ejemplos, pruebas anteriores, engine,
CLI, cobertura HFS-010, ecuaciones nominales F/I o interacci?n H/I. El informe
distingue archivos ?ntegros preservados de cuerpos AST iguales salvo guardas.
