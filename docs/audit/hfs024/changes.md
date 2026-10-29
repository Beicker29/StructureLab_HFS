# HFS-024 - Inventario de cambios

Base `main 93e4f8cd523148c8cb3ccff1d94caafb4cfa8af1`; sin staging, commit, push, rama nueva o PR.
Inventario obtenido con Git al cierre local. Los ZIP contienen evidencia nueva; ningun archivo historico se elimina.

| Archivo | Cambio / responsabilidad |
|---|---|
| [AGENTS.md](../../../AGENTS.md) | Contrato, decisiones, seguimiento o evidencia documental HFS-024 |
| [CONTRIBUTING.md](../../../CONTRIBUTING.md) | Contrato, decisiones, seguimiento o evidencia documental HFS-024 |
| [docs/ROADMAP.md](../../../docs/ROADMAP.md) | Contrato, decisiones, seguimiento o evidencia documental HFS-024 |
| [docs/adr/003-traceability-testing.md](../../../docs/adr/003-traceability-testing.md) | Contrato, decisiones, seguimiento o evidencia documental HFS-024 |
| [docs/architecture/dry-inventory.md](../../../docs/architecture/dry-inventory.md) | Contrato, decisiones, seguimiento o evidencia documental HFS-024 |
| [docs/audit/hfs024/changes.md](../../../docs/audit/hfs024/changes.md) | Contrato, decisiones, seguimiento o evidencia documental HFS-024 |
| [docs/audit/hfs024/evidence/SHA256SUMS.json](../../../docs/audit/hfs024/evidence/SHA256SUMS.json) | Nueva evidencia recuperable / manifiesto de verificacion |
| [docs/audit/hfs024/evidence/after.zip](../../../docs/audit/hfs024/evidence/after.zip) | Nueva evidencia recuperable / manifiesto de verificacion |
| [docs/audit/hfs024/evidence/archives.json](../../../docs/audit/hfs024/evidence/archives.json) | Nueva evidencia recuperable / manifiesto de verificacion |
| [docs/audit/hfs024/evidence/base-ci.json](../../../docs/audit/hfs024/evidence/base-ci.json) | Nueva evidencia recuperable / manifiesto de verificacion |
| [docs/audit/hfs024/evidence/before.zip](../../../docs/audit/hfs024/evidence/before.zip) | Nueva evidencia recuperable / manifiesto de verificacion |
| [docs/audit/hfs024/evidence/comparison.json](../../../docs/audit/hfs024/evidence/comparison.json) | Nueva evidencia recuperable / manifiesto de verificacion |
| [docs/audit/hfs024/evidence/final-checks.json](../../../docs/audit/hfs024/evidence/final-checks.json) | Nueva evidencia recuperable / manifiesto de verificacion |
| [docs/audit/hfs024/evidence/results.json](../../../docs/audit/hfs024/evidence/results.json) | Nueva evidencia recuperable / manifiesto de verificacion |
| [docs/audit/hfs024/evidence/source-proof.json](../../../docs/audit/hfs024/evidence/source-proof.json) | Nueva evidencia recuperable / manifiesto de verificacion |
| [docs/audit/hfs024/evidence/start.json](../../../docs/audit/hfs024/evidence/start.json) | Nueva evidencia recuperable / manifiesto de verificacion |
| [docs/audit/hfs024/evidence/unit-first.xml](../../../docs/audit/hfs024/evidence/unit-first.xml) | Nueva evidencia recuperable / manifiesto de verificacion |
| [docs/audit/hfs024/evidence/unit-second.xml](../../../docs/audit/hfs024/evidence/unit-second.xml) | Nueva evidencia recuperable / manifiesto de verificacion |
| [docs/audit/hfs024/report.md](../../../docs/audit/hfs024/report.md) | Contrato, decisiones, seguimiento o evidencia documental HFS-024 |
| [docs/audit/hfs024/rule-matrix.md](../../../docs/audit/hfs024/rule-matrix.md) | Contrato, decisiones, seguimiento o evidencia documental HFS-024 |
| [docs/audit/tracking.md](../../../docs/audit/tracking.md) | Contrato, decisiones, seguimiento o evidencia documental HFS-024 |
| [docs/contracts/hfs024-calculation-traces.md](../../../docs/contracts/hfs024-calculation-traces.md) | Contrato, decisiones, seguimiento o evidencia documental HFS-024 |
| [scripts/audit_hfs024.py](../../../scripts/audit_hfs024.py) | Sondas reproducibles y prueba estructural de preservacion |
| [scripts/verify_hfs020.py](../../../scripts/verify_hfs020.py) | Suite HFS-024 y sondas de tres instalaciones; seleccion original preservada |
| [src/steel_design/codes/aisc_360_22/combined_hss_calc.py](../../../src/steel_design/codes/aisc_360_22/combined_hss_calc.py) | Emision de valores realmente calculados; aritmetica preservada por AST/regresion |
| [src/steel_design/codes/aisc_360_22/flexure_calc.py](../../../src/steel_design/codes/aisc_360_22/flexure_calc.py) | Emision de valores realmente calculados; aritmetica preservada por AST/regresion |
| [src/steel_design/codes/aisc_360_22/tension_calc.py](../../../src/steel_design/codes/aisc_360_22/tension_calc.py) | Emision de valores realmente calculados; aritmetica preservada por AST/regresion |
| [src/steel_design/domain/evaluators/hss_shear.py](../../../src/steel_design/domain/evaluators/hss_shear.py) | Emision de valores realmente calculados; aritmetica preservada por AST/regresion |
| [src/steel_design/domain/evaluators/tension_evaluator.py](../../../src/steel_design/domain/evaluators/tension_evaluator.py) | Emision de valores realmente calculados; aritmetica preservada por AST/regresion |
| [src/steel_design/domain/rules/axial_rules.py](../../../src/steel_design/domain/rules/axial_rules.py) | Observacion transparente de check; pasos locales donde estan implementados |
| [src/steel_design/domain/rules/combined_hss_rules.py](../../../src/steel_design/domain/rules/combined_hss_rules.py) | Observacion transparente de check; pasos locales donde estan implementados |
| [src/steel_design/domain/rules/composite_rules.py](../../../src/steel_design/domain/rules/composite_rules.py) | Observacion transparente de check; pasos locales donde estan implementados |
| [src/steel_design/domain/rules/flexure_rule.py](../../../src/steel_design/domain/rules/flexure_rule.py) | Observacion transparente de check; pasos locales donde estan implementados |
| [src/steel_design/domain/rules/shear_rules.py](../../../src/steel_design/domain/rules/shear_rules.py) | Observacion transparente de check; pasos locales donde estan implementados |
| [src/steel_design/domain/rules/tension_rule.py](../../../src/steel_design/domain/rules/tension_rule.py) | Observacion transparente de check; pasos locales donde estan implementados |
| [src/steel_design/engine.py](../../../src/steel_design/engine.py) | Enlace por identidad y copia de estado/cobertura ya producidos |
| [src/steel_design/reporting.py](../../../src/steel_design/reporting.py) | Exportacion optativa de snapshot sin calculos; funciones legacy intactas |
| [src/steel_design/tracing.py](../../../src/steel_design/tracing.py) | Nuevo propietario optativo de observaciones y contrato de traza |
| [tests/test_hfs024_tracing.py](../../../tests/test_hfs024_tracing.py) | 114 pruebas nuevas; ninguna expectativa historica modificada |

Total: 39 archivos nuevos/modificados; 20 rutas previamente versionadas modificadas.

## Pendientes explicitos

- Revision tecnica humana del contrato optativo y del alcance progresivo; CI remota del commit que publique el usuario.
- Expansion de subramas/intermedios en E/F/G/H/I y migracion explicita de memorias legacy cuando exista informacion suficiente.
- Acreditacion normativa independiente y erratas por sus tareas autorizadas; F-31 P0 y restantes hallazgos abiertos.
- No se implementan HFS-030 ni web. No se eliminan duplicaciones de calculo preexistentes bajo el nombre de instrumentacion.
- No se modifica JSON 1.0, modelos/contratos, routing, cobertura, catalogo ni oraculos historicos.
