# HFS-022 — Inventario contractual y limpieza incremental

Base: main `c91e55d5a194dfb8e80777d9e41efa1ee4b7fe02`. Este inventario describe
fuentes actuales, no asume vigente la semántica de informes antiguos.
El [inventario generado](evidence/contracts-consumers.json) enumera campos,
tipos, defaults/factories, aliases, validators, serializers y computed fields
de los modelos canónicos, junto con rutas/líneas candidatas de consumidores.
Los [esquemas](../../schemas/contracts/1.0/) documentan tipos, unidades,
restricciones locales, enums y nullables desde Pydantic.

## Responsabilidades y consumidores

| Concepto | Fuente actual | Consumidores / decisión HFS-022 |
|---|---|---|
| Caso individual | `models.SteelCase`, modelos anidados e `input_contracts.InputModel` | Motor, execution, tests, ejemplos/capturadores. Conservar; ningún campo/version/default nuevo en ingeniería |
| Material, cargas, longitudes, factores, conexiones, custom, compuestos y evidencias externas | Modelos de `models.py`; guardas `domain.validation` | Mismos enums, signo Pu, unidades y LRFD/ASD. Validar sin construir Section, consultar catálogo o seleccionar estados límite |
| Lote y nombres | `execution.validate_bundle_shape`, `merge_case_payload`, nuevo `prepare_cases` | `iter_executions` y contracts; conservar dict de fragmentos. No otra clase de caso ni flatten que pierda herencia |
| Opciones de exportación | `execution.OutputOptions` y `extract_output_options` | CLI/ejecución/contratos. AliasChoices: write_results_json, write_detailed_json, save_results_json. StrictBool; default true; varios aliases simultáneos siguen inválidos |
| Decodificación de claves duplicadas | `input_contracts.unique_json_object`, extraído literalmente de run | CLI mantiene alias `_unique_json_object`; contratos traducen el ValueError al error de transporte. Una sola política productiva |
| Check | `models.CheckResult` y `from_values` | Reglas, reporting, motor y API de contratos. Conservar datos brutos; reutilizar decisión canónica solo para contrastar coherencia, sin capacidades nuevas |
| Proyección no finita legacy | `finite_json_payload`, serializers wrap/details de CheckResult | CLI/memoria/salida legacy, intactos. Contratos 1.0 no esconden pérdida: rechazan no finitos/proyecciones escalares no reconstruibles |
| Display | `CheckResult.display` computed | Comparación con valor publicado; no redondear datos de ingeniería ni implementar otro display |
| Obligación y ejecución | `results_model.CoverageObligation`, `ExecutedEvaluation` | Coverage plan/evidence y contratos. Índices base cero y texto histórico de implementación conservados; integridad referencial sin acreditación |
| Cobertura completa | `CoverageReport.complete` | Motor/reportes/contratos. Computed canónico, no copia de algoritmo ni derivación desde checks/cláusulas |
| Estado y fallos conocidos | `EngineResult.aggregate`, `known_failures` | Motor/reportes/contratos. Rechazar discrepancias declaradas; no reparar estados silenciosamente |
| Resumen compacto | `reporting.build_compact_summary` | CLI y consumidores Python. Excluye details y añade resumen/avisos/artifacts. **No** EngineResult completo; no migración automática |
| Memoria detallada | `reporting.build_detailed_results_payload` | Exportación explícita; meta/input/output/memory/admissibility y trazas reorganizadas. No convertirla en resultado canónico por inferencia |
| Contrato optativo | `contracts.ContractDocument` y funciones explícitas | Nuevos consumidores Python; futuros adaptadores. Solo envoltura, sin reemplazar CaseExecution o modelos ingenieriles |
| JSON Schema | `contracts.get_schema` desde Pydantic; script único `generate_hfs022_schemas` | Documentación congelada, tests y verificador instalado en tres modos. Ninguna edición manual ni segundo generador |
| Comparación histórica | `hfs020_comparison`, `compare_hfs021.compare_results` | Verificador/auditor HFS-022. Mantener independencia respecto al serializador productivo; Decimal/procedencia exactos no se sustituyen por comparaciones nuevas |

## Campos, coerción y errores actuales relevantes

- Entradas: extra forbid, números estrictos finitos, defaults validados,
  revalidate_instances always. Al menos una carga explícita; loads omitido/null
  o vacío no se acepta. Omitido y cero explícito se distinguen por fields_set.
- `SteelCase.design_method` default LRFD; F/I ASD siguen bloqueados. Opciones
  de salida se extraen antes de construir SteelCase. Ningún selector se invoca
  desde contratos. Las guardas que requieren Section quedan para el motor.
- Salidas legacy: BaseModel permite ignorar extras; floats pueden aceptar
  conversiones; validadores/computed fields modifican/derivan el estado. La
  capa nueva exige JSON estricto, extras tipados prohibidos y cotejo de datos.
  Esta política optativa no endurece ni modifica el constructor legacy.
- Enum de check actual: PASS/FAIL; no inventar NOT_EVALUATED como nuevo check.
  Análisis: PASS/FAIL/INCOMPLETE. Coverage: EVALUATED/NOT_APPLICABLE/PENDING;
  aplicabilidad TRUE/FALSE/UNKNOWN. Edición normativa no equivale a contrato.
- Salidas dinámicas: details (dict[str, Any]), scope_evidence y evaluation_errors
  no describen todas sus estructuras normativas. Se conserva contenido JSON,
  sin anunciar validación fina o importación del ID `src.steel_design...`.
- Error de catálogo/ejecución no es EngineResult. El fixture HFS-017 contiene
  11 resultados y un error esperado de doble ángulo. Todos se preservan;
  la prueba de migración rechaza expresamente el error como resultado.
- F-32 intacto: exit CLI expresa ejecución, no decisión resistente; F-31 P0
  abierto. Un contrato íntegro no valida la resistencia mayor del canal.

## Sustituciones y retiros comprobados

| Símbolo / copia anterior | Propietario canónico | Decisión y motivo | Consumidores / riesgo / prueba |
|---|---|---|---|
| Cuerpo de preparación dentro de `iter_executions` | `execution.prepare_cases` | **Consolidar**, retirar cuerpo embebido sustituido en el mismo hito. Iteración sigue delegando caso a caso antes de execute_case | CLI, execute_payload, pruebas y ahora contratos. AST del cuerpo salvo yield, tests de pereza/error y 24 escenarios antes/después; no se materializa el lote en legacy |
| Cuerpo `_unique_json_object` de run | `input_contracts.unique_json_object` | **Consolidar**, retirar copia local; mantener alias exacto en run | json.load CLI, prueba HFS-011 y contratos. Tipo ValueError y texto idénticos; prueba de identidad y cuerpo AST. No cambiar errores JSON legacy |
| Guardas Pydantic / del caso | Propietarios actuales | **Conservar** y reutilizar; no copiar restricciones en contracts | Nueva validación se adapta al transporte. El esquema por sí solo no reemplaza validadores cruzados |
| Serialización/decisión de checks y cobertura | Modelos actuales | **Conservar**; dump_json delega, luego verifica reconstrucción | No crear otra división/DCR, display, agregación ni evaluación de cobertura. Oráculos de transporte independientes de routing |
| Serialización CLI y memoria | Reporting/modelos | **Conservar justificadamente** | Son formatos legacy distintos y comprometidos, no serializadores rivales del contrato 1.0. Retirarlos violaría el alcance |
| Fachadas HFS-021/021A/021B | Dueños existentes | **Conservar** todas | Sin cambio a compromisos de compatibilidad ni limpieza de helpers de otros módulos |
| Parser/comparador de auditoría | Scripts históricos | **Conservar justificadamente** | Su independencia y Decimal detectan pérdida de precisión; no reemplazarlos por el código bajo prueba |

No se elimina ningún módulo, test congelado, dato, evidencia, solver, ecuación,
helper compuesto o geometría. Solo se retiran los dos cuerpos sustituidos
indicados; los aliases de compatibilidad siguen vigentes. No se añaden
dependencias ni motor de validación normativa paralelo.

## Riesgos/pendientes de revisión

1. Integridad estructural/aritmética no autentica evidencia ni valida AISC; un
   documento coherentemente falsificado puede pasar controles de transporte.
2. Schema no expresa merge ni todos los validadores; usar siempre API Python.
3. JSON proyectado desde no finitos, snapshots antiguos redondeados o formatos
   parciales no son necesariamente migrables. Rechazar, preservar y diagnosticar;
   no rellenar datos ni modificar evidencia aceptada.
4. Tipificación de detalles, evolución de trazas/registro normativo y web quedan
   fuera del hito. No extrapolar el soporte a HFS-023/024/039.
5. Inventario de consumidores se limita a código/documentación activa accesible;
   no presume conocimiento de clientes externos o carpetas históricas denegadas.
