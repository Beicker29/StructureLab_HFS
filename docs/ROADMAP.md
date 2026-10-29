# StructureLab_HFS — Roadmap de auditoría crítica, modernización y aplicación web

**HFS-030 (2026-10-29), cotejo documental para revisión:** base `main`
`76a908673259211b2d5b2407b046608ca96384ec`; jobs CI HFS-024 Windows/Ubuntu
SUCCESS verificados. Por instrucción del usuario, comparación únicamente de
PDF locales, incluidas las erratas aportadas de enero de 2025 y septiembre de
2026: 22 grupos cotejados, hashes y diferencias registrados. F-31 P0 y
F-35/F-36/F-37 siguen abiertos; ninguna acreditación o cambio de runtime.
[Informe, fuentes y límites](audit/hfs030/report.md). Autenticación remota de
bytes/permisos pendientes; no se declara una actualización editorial exhaustiva.
2675 pruebas +12 subpruebas aprobadas tras resolver limitaciones de ejecución
sin cambiar permisos ni tests. Sin HFS-031/032, commit ni push.

**HFS-024 (2026-10-29), para revisión:** base main `93e4f8c`, HFS-023 aprobada
arquitectónicamente por el usuario y CI 40858414332 SUCCESS Windows/Ubuntu.
Captura optativa de ejecución y pasos desde productores reales, sin reconstrucción
de ecuaciones desde etiquetas. Instrumentación progresiva con pendientes explícitos;
JSON 1.0, cálculos, cobertura y salidas legacy preservados. F-31 P0 abierto.
[Contrato](contracts/hfs024-calculation-traces.md), [matriz](audit/hfs024/rule-matrix.md)
y [evidencia de revisión](audit/hfs024/report.md). No inicia HFS-030 ni web;
sin commit/push. Las notas anteriores de entrega se conservan a continuación.

**HFS-023 (2026-10-29), para revisión:** base main `1b170929`, árbol inicial
limpio, [CI 40792213050](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40792213050)
SUCCESS Windows/Ubuntu verificada. HFS-022Q aprobado por declaración del usuario.
Registro único ampliado con 93 descriptores, fuentes/condiciones/implementaciones
y evidencia separadas; ninguna acreditación normativa nueva. F-31 P0 abierto.
[Contrato](contracts/hfs023-normative-registry.md) e [informe](audit/hfs023/report.md).
Sin commit/push ni inicio de HFS-024; la CI de la base no acredita cambios locales.

**HFS-022Q (2026-10-28), auditoría final para revisión:** base `449549d9`,
[CI 40788962500](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40788962500)
SUCCESS Windows/Ubuntu verificado. Se amplía evidencia con consumidor externo,
20 documentos manuales independientes y métricas AST; no se modifica producción
ni se asigna una nota. [Informe](audit/hfs022/final-quality-review/report.md).
La revisión independiente decide el cierre; la CI del commit final del suplemento
sigue pendiente de publicación por el usuario. F-31 P0 abierto; sin HFS-023/024.

**HFS-022R (2026-10-28), suplemento para revisión:** base aprobada `bae6463`,
[CI 40777094705](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40777094705)
SUCCESS Windows/Ubuntu verificado. Preparación canónica independiente de ejecución,
verificación Draft 2020-12 de los diez esquemas y diagnósticos JSON Pointer.
Sin cambios ingenieriles, legacy ni versión 1.0/0.2.0. [Informe y evidencia](audit/hfs022/architecture-review/report.md).
La CI de la base no acredita los cambios locales: falta revisión y CI sobre
el commit que publique el usuario. F-31 P0 abierto; sin HFS-023/024.

**HFS-022 (2026-10-28), para revisión:** contratos optativos 1.0 en
`steel_design.contracts`, migración explícita y schemas generados desde modelos
canónicos. Legacy, cálculos y cobertura preservados; F-31 P0 abierto y F-32
vigente. Base main `c91e55d5`, [CI 40743600221](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40743600221)
SUCCESS Windows/Ubuntu verificada. Esa CI acredita la base, no la entrega local.
[Contrato](contracts/hfs022-versioned-json.md), [informe](audit/hfs022/report.md).
Sin commit/push del agente; cierre pendiente de revisión independiente y nueva
CI remota de los cambios. No se inician HFS-023/024 ni web.

**HFS-021A aprobado y cerrado (2026-10-28):** paquete `steel_design`,
distribución 0.2.0. Commit final verificado en main
`35dd7b8e09f05b8ac77af1ba0b7b735d59456b6a`;
[CI 40736064324](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40736064324)
SUCCESS en Windows 2022 y Ubuntu 24.04. Corrección SVG CRLF/LF aceptada;
referencia local aprobada: **1819 pruebas +12 subpruebas**. El cierre acredita
el alcance de paquete/API/regresión, no validación normativa AISC. **F-31 sigue
P0 abierto**, junto con los demás defectos normativos pendientes del seguimiento.
[Confirmación y tarea HFS-021B](audit/hfs021b/report.md).

**HFS-021B (2026-10-28), para revisión:** política de limpieza incremental e
[inventario de consumidores](audit/hfs021b/cleanup-inventory.md); retirada
acotada de dos bindings intermedios de run, preservando las fachadas comprometidas.
Sin incremento de versión, commit/push ni inicio de HFS-022.

**Registro histórico HFS-021A, base main `39a7614`:** migración a `steel_design`
con src-layout, versión 0.2.0 y API pública por módulos; rechazo del namespace
legado para impedir identidades paralelas. [Informe](audit/hfs021a/report.md)
y [contrato](contracts/hfs021a-public-api.md). Para revisión independiente;
El run 40694129771 de `ae5f54b` pasó en Windows y falló en Ubuntu al comparar
SVG CRLF/LF. [Corrección y evidencia local](audit/hfs021a/ci-fix/report.md);
pendiente nueva ejecución SUCCESS en ambas plataformas. Sin HFS-022.
HFS-021 fue aprobado: run 40687160912 SUCCESS Windows/Ubuntu verificado.
Las notas precedentes de entrega se conservan como contexto histórico.

**Entrega HFS-021 (2026-10-28), base main `f3a5198`:** ejecución compartida
en memoria, presentación/exportación separada y geometría maciza canónica.
F-15/F-16 con cierre funcional acotado para revisión; ecuaciones, guardas,
catálogo, cobertura y contratos JSON preservados. [Informe](audit/hfs021/report.md)
y [contrato Python](contracts/hfs021-execution.md). Sin rama/PR/commit/push.
No se inicia HFS-022, HFS-024, HFS-039 ni web.

**Cierre posterior HFS-020:** aprobado por el usuario; workflow
[40673575334](https://github.com/Beicker29/StructureLab_HFS/actions/runs/40673575334),
commit `f3a5198`, Windows y Ubuntu SUCCESS, verificados en GitHub y registrados
en [preparación HFS-021](audit/hfs021/preparation.md). No certificación AISC.
Las notas anteriores de ejecución fallida/pendiente se conservan como historia.

**Corrección HFS-020 (2026-10-28), base main `70adc5e`:** el primer run real
40617061992 terminó Windows SUCCESS/Ubuntu FAILURE por comparar hashes CRLF/LF.
Corrección local con procedencia verificable y comparación JSON exacta: 1711
pruebas + 12 subpruebas, 12 ejemplos y 24 escenarios sin diferencias.
[Evidencia](audit/hfs020/compatibility/report.md). Publicación por el usuario y
nuevo run con ambos jobs SUCCESS pendientes; HFS-020 no cerrado. Sin commit/push.

**HFS-020 (2026-10-27), base main `8af8e43`:** empaquetado del namespace
`src.steel_design`, CLI instalado con catálogo externo, Ruff acotado y workflow
Windows/Ubuntu. [Informe y evidencia](audit/hfs020/report.md). Verificación local
Windows y revisión técnica; ejecución remota GitHub Actions/Ubuntu pendiente,
sin commit/push. No se adelantan HFS-021/022/039/040.

**Entrega HFS-017 (2026-10-27), base main `7234df8`:** guardas transversales de
método, bloqueos F/I directos y rechazo de fallbacks desconocidos; F-43 y
acreditaciones HFS-010 conservados. Once suites: 1661 aprobadas + 12 subpruebas;
12 ejemplos/24 consumidores CLI idénticos. [Informe](audit/hfs017/report.md),
[contrato](contracts/hfs017-design-method.md) y [matriz](audit/hfs017/support-matrix.md).
Para revisión técnica independiente, sin rama/PR/commit/push. HFS-020 y HFS-039
no iniciadas. Las notas de entregas anteriores conservan su contexto histórico.

**Entrega HFS-015 (2026-10-27), base main `dbd87cb`:** F-09 corregido con
valores originales, display separado, JSON estricto y ranking bruto; F-07 con
recomendaciones D1/E2 separadas de resistencia y condición E5 explícitamente
pendiente. [Informe](audit/hfs015/report.md) y [migración](contracts/hfs015-precision-advice.md).
Cierre funcional para revisión; sin commit/push ni avance a otro hito.

**Entrega previa HFS-014 (2026-10-27), base main `d3190d4`:** F-05 corregido mediante
gobernantes observados por DCR publicado, y F-29 mediante rechazo estructurado
de lotes vacíos antes de ejecutar/publicar. [Informe](audit/hfs014/report.md) y
[migración JSON](contracts/hfs014-summary-bundles.md). Revisión técnica pendiente;
sin publicación automática. HFS-017/039 se registran como tareas futuras por
instrucción del usuario, **sin implementarlas**. La nota de entrega HFS-015 precedente actualiza su estado.

**Revisión final HFS-013, F-43:** corrección de conversión F1(a) LRFD/ASD en
capacidad flexural compartida de H3/H1, base main `abafdbb`. Cierre funcional
demostrado, pendiente de revisión técnica; [informe y evidencia](audit/hfs013/f1-correction/report.md).
Prioridad P0 propuesta por exceso de Mc ASD interno del 50,3%; el bloqueo público
de flexión ASD se conserva. No se inicia otro hito ni se publica automáticamente.

**Entrega HFS-013 (2026-10-27):** ejes G/H3 documentados, F-06 corregido en su
agregación direccional, H3-6/H3-5 contrastados y dominios no acreditados bloqueados.
[Informe](audit/hfs013/report.md), [convención](contracts/hfs013-axes.md) y
[seguimiento F-06/08/11/39–42](audit/tracking.md), pendientes de revisión técnica.
Base main `3af52aa9848ccb6ff040fd1f8203a4609599f341` con HFS-012 incorporada.
Sin commit/push, sin HFS-014/015. F-31 permanece abierto. Las entregas siguientes
conservan su contexto histórico, no describen el estado actual completo.

**Entrega HFS-012 (2026-10-27):** corrección acotada de selección F2 presentada
para revisión en [informe](audit/hfs012/report.md). Base `main` con HFS-010/011/016;
cambios locales sin commit ni push por instrucción del usuario. Se conserva la
prioridad de F-31 y no se avanza a otro hito. Las notas siguientes son históricas.

**Actualización HFS-010 (2026-10-27):** HFS-000/001/002/011/016 concluidas dentro de
sus alcances. Control mínimo de cobertura implementado en la rama
`hfs-010-coverage-gate`: [informe](audit/hfs010/report.md) y
[contrato](contracts/hfs010-coverage.md). El usuario autoriza publicación/fusión
con revisión técnica posterior; no acredita validación normativa ni G1.
Los bloques anteriores de estado se conservan como historia de las entregas.

**Estado:** propuesta técnica para ejecución incremental con Codex  
**Referencia de auditoría:** rama `main`, commit `80a9d3609d452ab3413ad632629b1fadcab8415c` de `Beicker29/StructureLab_HFS`.  
**Documento:** 26 de octubre de 2026.  
**Objetivo:** motor AISC 360-22 de diseño/verificación de miembros de acero, trazable, sencillo, testeable, con CLI y app web. AISC 341-22 se reserva como alcance normativo separado y optativo.

**Estado actualizado HFS-002 (2026-10-26):** HFS-000 aceptada como línea base de comportamiento, no validación AISC. HFS-001 aprobada arquitectónicamente con ajustes incorporados en [ADR-001](adr/001-engine-architecture.md), [ADR-002](adr/002-contracts-errors.md) y [ADR-003](adr/003-traceability-testing.md). HFS-002 documental se presenta para revisión en su [informe](audit/hfs002/report.md). El estado vivo F-01–F-38 está en [seguimiento maestro](audit/tracking.md); el diagnóstico HFS-000 permanece inmutable. HFS-010/016 y tareas posteriores no se implementan aquí.

> El diagnóstico inicial del roadmap fue estático. Las pruebas efectivamente ejecutadas se documentan por hito (HFS-000/001/002), sin implicar que todos los ejemplos se hayan recalculado independientemente contra la norma. Distinguir defectos confirmados de riesgos pendientes de validación numérica.

**Actualización HFS-011 (2026-10-27):** el usuario acepta HFS-002 como matriz documental de aplicabilidad y diagnóstico, no como validación normativa exhaustiva. Autoriza exclusivamente HFS-011 antes de HFS-010. Implementación de contratos presentada para revisión en [informe HFS-011](audit/hfs011/report.md) y [migración](contracts/hfs011-inputs.md). HFS-010/016 y web permanecen sin implementar; no se avanza de fase ni se declara G1 cumplida.

## 1. Principios no negociables

1. **No hay PASS por omisión:** un caso sin checks, con checks obligatorios omitidos o con datos insuficientes es `INCOMPLETE` / `BLOCKED`, nunca `PASS`.
2. **Una fuente canónica:** web, CLI y reportes consumen el mismo servicio/núcleo. Ninguna interfaz replica formulaciones AISC.
3. **Rastreabilidad normativo-numérica:** cada regla documenta fuente, edición, capítulo, ecuación, condiciones de aplicabilidad, entradas, variables intermedias, factores, redondeos de presentación, salida y pruebas de referencia.
4. **Sin validación circular:** un golden test no debe obtener su valor esperado ejecutando la misma implementación que evalúa.
5. **No se refactoriza por estética:** cada cambio arquitectónico debe eliminar un problema concreto, mantener resultados caracterizados o documentar divergencias justificadas.
6. **Fronteras simples:** sin microservicios, base de datos requerida, contenedores obligatorios, framework frontend pesado o diseño de plugins genéricos en el MVP.
7. **Sin inventar implementaciones normativas:** reglas no implementadas o validación incierta se declaran explícitamente.
8. **Revisión humana:** los cambios en selección de estados límite, ecuaciones, propiedades de catálogos, estabilidad e interacción requieren evaluación ingenieril antes de declararse validados.
9. **DRY permanente:** una fuente de verdad por concepto técnico, con simplicidad y responsabilidad única. No fusionar ecuaciones de dominios diferentes ni reducir líneas mediante abstracciones sin beneficio. CLI/API/web comparten motor y contratos. Diagnóstico y propietarios en [inventario DRY](architecture/dry-inventory.md); consolidaciones pendientes, sin refactorizar en HFS-001.

## 2. Hallazgos del análisis estático

**Convención:** `C` = defecto/limitación observada directamente en código; `R` = riesgo o hipótesis que debe verificarse con norma, ejemplos o pruebas adicionales. `P0` = seguridad/confiabilidad primero; `P1` = bloque de producto; `P2` = evolución.

| ID | P | Tipo | Evidencia | Hallazgo / decisión propuesta |
| --- | --- | --- | --- | --- |
| F-01 | P0 | C | `domain/routing/profile_router.py`, `PROFILE_RULE_MAP` y `_is_h1_hss_applicable` | H1 solo en HSS; W con Pu y Mx/My puede no verificar interacción. Auditoría de todas las familias y de H1/H2. |
| F-02 | P0 | C | `engine.py::run` | `overall_status=PASS` salvo FAIL explícito; no confirma cobertura ni ausencia de checks. Introducir `INCOMPLETE`, plan de verificaciones requeridas y agregación cerrada. |
| F-03 | P0 | C | `domain/routing/profile_router.py::_w_or_channel_major_flexure_selection` | Faltan razones de esbeltez y el código devuelve F2. Nunca asumir sección compacta por ausencia de datos; bloquear. |
| F-04 | P0 | C | `models.py`, `SteelCase`, `Loads`, Pydantic BaseModel por defecto | Campos desconocidos pueden ignorarse; cargas faltantes son 0. Rechazar campos extra, determinar campos requeridos y semántica de 0. |
| F-05 | P0 | C | `run.py::_build_global_summary` | HFS-014: gobernantes observados por DCR, empates y fallos preservados; sin capacidad mezclada. HFS-015 entrega precisión original y migración del resumen para revisión. |
| F-06 | P0 | C/R | `combined_hss_rules.py::_available_shear_strength` | HFS-013 corrige pares y máximo de cocientes; caso combinado DCR 0,97→1,61. Revisión y auditoría integral de capacidades dependientes pendientes. |
| F-07 | P0 histórico | C | `domain/recommendations.py` | HFS-015: avisos D1/E2 separados de resistencia; longitud fabricada/radio mínimo y excepción rod explícitos. E5 condiciona una alternativa distinta, aún pendiente de validación. |
| F-08 | P0 | C/R | `models.py::Loads`; `domain/actions.py` | HFS-011 eliminó resultante/sobrescritura; HFS-013 explicita Vu alias de Vux en el plano Mux, fuerza local y. Revisar consumidores históricos y futuros adaptadores. |
| F-09 | P0 histórico | C | `models.CheckResult.from_values` | HFS-015: demanda/capacidad/DCR originales, display derivado, umbral sin epsilon, trazas directas y JSON estricto. Fronteras 0.9999/1/1.0001 y propagación I4/I5 verificadas para revisión. |
| F-10 | P0 | C/R | `domain/routing/profile_router.py::_is_missing_numeric`, `sections/loader.py::_coerce_float` | Ausencia de validación explícita de finitud en varios lugares; probar y prohibir NaN, infinito, números negativos y dimensiones imposibles. |
| F-11 | P1 | C/R | `domain/actions.py`; reglas G/H3 | HFS-013 conserva asociación física histórica y añade plano, dirección y entrada a la traza; G3/canal G6 no acreditados se bloquean. Ejes externos y compuesto I pendientes. |
| F-12 | P1 | C/R | `sections/loader.py`, selección `field_values['id']` para D/t | Revisar que D/t corresponda al diámetro exterior físico, no ID, según familia/convención de catálogo. |
| F-13 | P0 | C | `sections/repository.py::load`, `docs/audit/catalog-duplicates.json` | Sobrescritura HEA 100 corregida con rechazo por identidad en HFS-016, cierre funcional demostrado para revisión. [Informe](audit/hfs016/report.md). HFS-040 conserva calidad integral y corrección de datos con fuente. |
| F-14 | P1 | C | `sections/loader.py` | Conversión de unidades por encabezados y fallback `1.0`; definir metadatos por fuente y rechazo si la unidad de entrada es ambigua. |
| F-15 | P1 | C | `run.py::_build_case_section` y `engine.py::_build_custom_section` | Geometría de sección custom duplicada; extracción única a dominio geométrico. |
| F-16 | P1 | C | `run.py`, 747 líneas | CLI mezcla ejecución, generación de memorias, trazas, gráficos y serialización; servicios y exportadores separados. |
| F-17 | P1 | C | `domain/rules/composite_rules.py`, 1871 líneas | Cálculo compuesto monolítico; dividir únicamente por responsabilidades ya observadas (I2/I3/I4/I5 y modelos seccionales). |
| F-18 | P1 | C/R | `composite_rules.py::_filled_strip_model` y `_solve_neutral_axis` | Integración por 800 franjas y soluciones iterativas con parámetros fijos; pruebas de convergencia, balance N/M, material y geometría. |
| F-19 | P1 | R | `flexure_calc.py::evaluate_f4_conservative` | Sustitución de F4 por evaluación de F5; verificar validez y conservadurismo en dominio de aplicabilidad, explicitar alternativa normativa si procede. |
| F-20 | P1 | R | `combined_hss_rules.py`, `composite_rules.py` y Chapter I | Revisar fuentes reales de capacidades, trayectorias conservadoras, métodos I5, interacción biaxial y correspondencia con artículos/Commentary. |
| F-21 | P1 | C/R | `models.py`, `CheckResult` | Check sin propiedad de unidad, estado de completitud, severidad, fuente ni valor crudo; necesidad de resultados tipados y trazas. |
| F-22 | P1 | C/R | `models.py` con `Kx,Ky,Kz,Cb` default 1 y `E=200000` obligatorio | Distinguir valores por defecto de hipótesis de ingeniería, método LRFD/ASD, procedencia de demanda y análisis de estabilidad AISC capítulo C. |
| F-23 | P1 | C | `tests/*` | Hay pruebas, pero no evidencia suficiente de cobertura exhaustiva ni oráculos independientes por cláusula; construir matriz de referencia, límites e interacción. |
| F-24 | P1 | C | Raíz: `requirements.txt` y ejecución `python -m src.steel_design.run` | Empaquetado `pyproject.toml`, entrada CLI convencional y pruebas sobre wheel instalado. |
| F-25 | P1 | C | Raíz `results/`, `.tmp_debug_cli/`, `tests/.tmp_tests/` | Artefactos temporales versionados; inventario, preservación de muestras necesarias y limpieza segura de Git. |
| F-26 | P1 | C | `docs/aisc_360_22_traceability.md` | Tabla útil pero insuficiente: rastreo automatizado hasta pruebas independientes, fórmulas, versiones y estados. |
| F-27 | P1 | R | Catálogo `data/sections.xlsx` | Versionar fuente, licencia, método de importación, conversiones, duplicados, geometrías y coherencia de propiedades. |
| F-28 | P2 | R | Repositorio general | Verificar licencias y permisos de redistribución para normas PDF y tablas/datos; registrar dependencia documental y erratas aplicables. |
| F-29 | P1 | C | `results_model.aggregate_case_statuses`; CLI | HFS-014: lista vacía produce EMPTY_CASE_BUNDLE antes de ejecutar/publicar. Lotes no vacíos conservan precedencia INCOMPLETE y fallos individuales; F-32 intacto. |
| F-30 | P1 | R | `src/steel_design/codes/aisc_360_22` | Auditoría profunda de E4/E5/E7, F2–F11, G2–G6, H, I; revisar todos los factores, dominios, límites y errores numéricos. No asumir fidelidad por etiqueta de ecuación. |
| F-31 | P0 | C/R | `domain/routing/profile_router.py::_validate_flexure_selection`; caracterización HFS-000 | Un check F del eje menor evita bloqueo aunque la demanda mayor no se evalúe. Omisión confirmada en sonda sintética; contraste con canal real pendiente. Seguimiento HFS-002/010/032. |
| F-32 | P1 | C | `run.py::main`, ejemplos HFS-000 | FAIL estructural puede devolver exit 0. Es contrato observable, no regresión. Documentar separación ejecución/cumplimiento y revisar consumidores antes de cambiar exit; HFS-021/022. |

**Nota de rigor:** un defecto de diseño de software no demuestra por sí solo un resultado estructural incorrecto para un caso dado. Y un resultado correcto en una prueba no certifica todas las combinaciones del capítulo correspondiente.

Nuevos IDs HFS-002: **F-33 P0 propuesto** biaxialidad sin axial; **F-34 P0 propuesto** flexión pura compuesta sin check resistente; **F-35 P0 propuesto** método E7 distinto de área efectiva; **F-36 P0 propuesto** condiciones/ramas E5 y E4 ángulo incompletas; **F-37 P1** IDs/citas de interacción; **F-38 P1** complementos y precondiciones sin cobertura. Evidencia, certeza y cierre en [seguimiento maestro](audit/tracking.md) y [contraste normativo](normative/hfs002-implementation.md). No duplicar aquí el diagnóstico completo.

## 3. Arquitectura objetivo mínima

**Actualización HFS-002:** HFS-001 recibió aprobación arquitectónica del usuario. Se precisó PASS como cumplimiento del alcance verificable declarado, nunca certificación global automática AISC 360-22. La [matriz normativa](normative/hfs002-applicability.md) es independiente del router; el [contraste](normative/hfs002-implementation.md) y la [propuesta HFS-010](normative/hfs002-coverage-proposal.md) se entregan para revisión, sin implementar cobertura ni corregir cálculos. F-33–F-38 están en el seguimiento maestro; F-06 tiene discrepancia algebraica confirmada con H3.2. Erratas oficiales pendientes de cotejo, según [fuentes](normative/hfs002-sources.md).

**Revisión crítica HFS-001 aprobada:** el árbol siguiente conserva la propuesta original como contexto, no prescribe crear todas esas capas. ADR-001 conserva `sections`, funciones en `codes` y reglas/routing en `domain`; extraer solo responsabilidades justificadas, sin `services` web obligatorio ni segundo motor. DRY y contratos compartidos son las fronteras requeridas. No hay migración de carpetas en HFS-001/002.

```text
src/
  steel_design/
    domain/          # Pydantic: casos, secciones, materiales, estados y resultados
    codes/aisc_360_22/
                     # Funciones normativas aisladas, reglas y aplicabilidad
    catalog/         # Interfaz del catálogo y modelos normalizados
    services/        # Validar caso, seleccionar reglas, ejecutar, agregar
    reporting/       # Memorias / exportación sin ecuaciones normativas
    adapters/        # JSON y proveedores de catálogos
    cli.py           # Adaptador CLI del mismo servicio
  steel_design_web/
    app.py, routes.py, services.py, static/
                     # FastAPI + HTML/CSS/JS + SVG (sin lógica AISC)

tests/
  reference/         # Oráculos independientes con fuente, fecha, unidades
  unit/
  integration/
  web/

docs/
  adr/
  normative/        # Matriz de reglas y cobertura, erratas
  engineering/      # Hipótesis, ejemplos auditados, convenciones de ejes
schemas/            # Versiones JSON Schema
examples/           # Casos versionados
```

**No mover todos los archivos a la vez.** Esta es una estructura ilustrativa de la propuesta original, revisada por ADR-001; las extracciones se justifican por problemas concretos y compatibilidad controlada, no por completar ese árbol.

### Flujo de cálculo

`CaseInput -> ValidationReport -> Section+Material -> ApplicabilityPlan -> CheckResults -> CoverageGate -> DesignResult -> {CLI, JSON, PDF, Web}`

**Estados:** Check: `PASS | FAIL | NOT_APPLICABLE | NOT_EVALUATED`. Caso: `PASS | FAIL | INCOMPLETE`. Advertencias separadas de cumplimiento. Un cálculo fallido técnicamente también puede devolver un error estructurado, no un falso FAIL de resistencia.

`ApplicabilityPlan` debe demostrar explícitamente: cuáles verificaciones son obligatorias para familia/geometría/solicitaciones, por qué se activan/no activan, y si todas las obligatorias están implementadas y se ejecutaron. Los requisitos proceden de una matriz normativa independiente del router. PASS solo acredita el alcance verificable declarado; no certificación automática global de AISC 360-22. Datos/interpretaciones desconocidos no son NOT_APPLICABLE.

**Precisión:** `float` puede mantenerse para cálculo ingenieril si se prueba la estabilidad numérica y se rechazan valores no finitos. No imponer Decimal universalmente: la física del problema no exige la misma aritmética exacta del detallado geométrico de RCWallDetailer.

## 4. Roadmap de tareas ejecutables con Codex

Las tareas siguientes se implementan con una rama y PR independientes cuando sea posible. Ninguna tarea P0 debe incluir una reescritura integral del proyecto.

| ID | Fase | Tarea Codex | Depende de | Aceptación esencial |
| --- | --- | --- | --- | --- |
| HFS-000 | 0 | Inventario, baseline y congelación de resultados actuales | — | SHA, `pytest`, entornos, CLI ejemplos, hashes/fixtures y limitaciones reproducibles. Sin cambios normativos. |
| HFS-001 | 0 | `AGENTS.md`, guías de contribución, 3 ADR, matriz de hallazgos | 000 | Arquitectura aprobada, políticas simples, decisiones registradas, fuentes clasificadas como evidencia vs hipótesis. |
| HFS-002 | 0 | Matriz *familia × demandas × condiciones × estados límite* | 000 | Identifica todos los huecos y casos no implementados; revisión ingenieril requerida. |
| HFS-010 | 1 | Cierre de cobertura y estados de resultado `INCOMPLETE` | 002 | Implementada: obligaciones independientes, INCOMPLETE y FAIL conocidos preservados. [Pruebas y límites](audit/hfs010/report.md). Cero checks, obligaciones ausentes y métodos no soportados no acreditan PASS. |
| HFS-011 | 1 | Endurecer Pydantic: campos extra, faltantes, finitud, dominios | 000 | Implementada para revisión antes de HFS-010 por autorización expresa; [evidencia y rupturas](audit/hfs011/report.md). Typos, NaN, inf, dominios y cortantes contradictorios rechazados; sin validación AISC exhaustiva. |
| HFS-012 | 1 | Corregir fallback indebido de F2 por esbeltez ausente | 010,011 | Implementada para revisión: ausencia no implica compacidad; derivación explícita B4.1 o bloqueo, ancho completo del canal, pendientes HFS-010 y regresiones. [Informe](audit/hfs012/report.md). |
| HFS-013 | 1 | Revisar convenciones `Pu,Mux,Muy,Vux,Vuy,Vu,Tu`, ejes y capacidades de cortante H3 | 011 | Ensayos direccionales no confunden ejes; si norma/caso no cubierto -> INCOMPLETE. |
| HFS-014 | 1 | Sustituir resumen de capacidades mezcladas, reglas de agregación de lote vacío | 010 | Implementada para revisión: DCR publicado, empates/FAIL conservados, sin inferir unidades; `cases=[]` rechazado. [Informe](audit/hfs014/report.md). |
| HFS-015 | 1 | Separar cálculo bruto/visualización, casos límite `DCR ≈ 1` y recomendaciones D1/E2 | 010 | Implementada para revisión: constructor único sin redondeo, trazas originales, no finitos diagnosticados, recomendaciones D1/E2 y migración HFS-014. Diez suites; [informe](audit/hfs015/report.md). |
| HFS-016 | 1 | Mitigación acotada F-13: identidad ambigua/duplicados de catálogo | 000,001 | Antes de G1, impedir selección silenciosa de geometrías distintas bajo una identidad. Decidir rechazo o identificación explícita con compatibilidad y pruebas de orden/carga; preservar filas/procedencia, no renombrar por suposición ni migrar catálogo completo. Implementación entregada para revisión: [contrato](contracts/hfs016-catalog.md) e [informe](audit/hfs016/report.md). Alcance integral sigue HFS-040; no autoriza avance de fase. |
| HFS-017 | 1, implementada para revisión | Blindaje LRFD/ASD antes de HFS-020 | 011,013,014,015 | Guardas canónicas en motor/router/reglas/evaluadores; F/I ASD bloqueados, conversores sin fallback desconocido, factores por disposición, F-43 preservado. Once suites sin regresiones; [evidencia](audit/hfs017/report.md). No habilita nuevos dominios ASD. |
| HFS-020 | 2, aprobada por el usuario | Empaquetado Python (`pyproject.toml`), CI, Ruff, pytest | 010-017 | Cierre posterior: workflow 40673575334, commit f3a5198, Windows y Ubuntu SUCCESS. Namespace, wheel/sdist, suites y comparación exacta preservados. [Evidencia histórica](audit/hfs020/report.md), [confirmación posterior](audit/hfs021/preparation.md). No certificación normativa. |
| HFS-021 | 2, aprobada por el usuario | Extraer servicios puros del CLI y centralizar geometría custom | 020 | Ejecución común y geometría única; 1762 pruebas +12 subpruebas. Run 40687160912 SUCCESS Windows/Ubuntu, commit 39a7614. [Informe histórico](audit/hfs021/report.md). No certificación AISC. |
| HFS-021A | 2, aprobada y cerrada | Paquete convencional steel_design y API pública mínima | 021 | Distribución 0.2.0; commit final 35dd7b8; CI 40736064324 SUCCESS Windows 2022/Ubuntu 24.04; corrección SVG aceptada y referencia local 1819 +12 subpruebas. [Cierre verificado](audit/hfs021b/report.md). Se preservan el [informe histórico](audit/hfs021a/report.md), el run fallido 40694129771 y su [corrección](audit/hfs021a/ci-fix/report.md). F-31 P0 y restantes defectos normativos siguen abiertos. |
| HFS-021B | 2, para revisión | Cierre documental y limpieza incremental controlada | 021A | Política permanente, inventario por símbolo/consumidor y retiro exclusivo de bindings sin contrato ni uso. Fachadas comprometidas conservadas, regresión exacta antes/después, sin cambios normativos ni versión nueva. [Informe](audit/hfs021b/report.md), [inventario](audit/hfs021b/cleanup-inventory.md). |
| HFS-022 | 2, base aprobada; suplemento 022R para revisión | Contratos versionados de entrada, plan normativo, checks y resultado | 021A | API optativa 1.0; base bae6463 con CI 40777094705 SUCCESS Windows/Ubuntu. [Informe histórico](audit/hfs022/report.md) preservado. [Suplemento HFS-022R](audit/hfs022/architecture-review/report.md): desacoplamiento, interoperabilidad y diagnósticos. Cierre del suplemento pendiente de revisión independiente y CI de su commit final. |
| HFS-023 | 2, implementado para revisión | Registro normativo declarativo mínimo, sin framework de plugins | 022 | RuleDefinition.metadata, 93 descriptores, referencias y pruebas de integridad; índice de implementación derivado, HFS-002 independiente. Sin cambios de cálculo/cobertura/transporte. [Evidencia](audit/hfs023/report.md). |
| HFS-024 | 2, implementación progresiva para revisión | Trazas canónicas desde ejecución; exportación auxiliar sin inferencias | 022,023 | 71 clases observadas; pasos numéricos progresivos y pendientes por regla. JSON 1.0/memorias legacy intactos. [Informe](audit/hfs024/report.md); no acredita nuevas disposiciones ni completa todas las subramas. |
| HFS-030 | 3, cotejo local entregado para revisión | AISC 360-22: base documental y erratas, tabla de trazabilidad | 023 | Comparación de PDF del repo con fuente oficial; versión/erratas registradas. Alcance acotado por usuario a copias locales: 22 grupos E25/E26 contrastados; autenticación remota y permisos pendientes. [Evidencia y límites](audit/hfs030/report.md). |
| HFS-031 | 3 | Auditoría normativa capítulos D y E (incl. E4/E5/E7) | 030 | Oráculos independientes, casos límite, clases geométricas y condiciones de uso. |
| HFS-032 | 3 | Auditoría capítulo F (F2–F11, rama F4, Cb, Lb) | 030 | Validación por familia/eje/región de frontera; evitar atajos no probados. |
| HFS-033 | 3 | Auditoría capítulo G y convenciones de ejes/cortante | 030,013 | Reglas direccionales contrastadas con norma y referencias independientes. |
| HFS-034 | 3 | Capítulo H: H1 para W y demás miembros elegibles; H2/H3 según alcance | 031-033 | Combinación Pu+Mx/My no queda sin evaluar silenciosamente; casos de verificación independientes. |
| HFS-035 | 3 | Capítulo I: auditar I1–I5, métodos, vigas y columnas compuestas | 030 | Ensayos independientes; I5 traza método, factores y dominios; sin extrapolación implícita. |
| HFS-036 | 3 | Modelo numérico compuesto: convergencia en discretización y equilibrio | 035 | Sensibilidad a franjas/iteraciones; tolerancias documentadas y regresiones reproducibles. |
| HFS-037 | 3 | Capítulo C y validez del modelo de estabilidad / procedencia de demandas | 030,022 | Métodos admitidos definidos; supuestos no verificados impiden certificación de miembro completo. |
| HFS-038 | 3 | Definir alcance no implementado de B/J/K y otros estados límite externos | 002,030 | No se declara cumplimiento global más allá de frontera explícita de producto. |
| HFS-039 | 3, futura | Habilitación ASD por dominios validados, después de auditorías D/E/F/G/H/I | 017,031-035 | Habilitar solo familias/ejes/estados con nominales, factores, contratos y oráculos independientes acreditados; conservar bloqueos restantes. F-43 no equivale a habilitación integral. No implementada en HFS-014. |
| HFS-040 | 4 | Catálogo canónico, importador Excel opcional, pruebas de unidades y duplicados | 020,022 | Catálogo versionado, sin sobrescrituras; origen trazable; Excel no es dependencia de runtime. |
| HFS-041 | 4 | Banco de casos oficiales y fixtures independientes con procedencia | 031-037 | Test por disposición crítica y fronteras; tolerancias declaradas, ninguna salida esperada derivada del motor. |
| HFS-042 | 4 | Pruebas de integración, propiedad/metamórficas y regresión | 041 | Cobertura por escenario técnico (no solo % de líneas); CI bloquea regresiones P0. |
| HFS-043 | 4 | Reporte profesional reproducible y exportaciones JSON/PDF | 024,041 | Página de resumen, entradas, hipótesis, tablas de checks, fuente, fórmulas, versiones, advertencias. |
| HFS-WEB-000 | 5 | Especificación de MVP web (sin cuentas, sin almacenamiento central) | 022,024 | API y navegación definidas con UX evaluable, sin reimplementar cálculo. |
| HFS-WEB-001 | 5 | Adaptador FastAPI con endpoints versionados | WEB-000,042 | Mismo resultado que CLI para mismo caso/versión; HTTP errores estructurados. |
| HFS-WEB-002 | 5 | Interfaz del verificador de una sección | WEB-001 | Selector de sección/material, longitudes, cargas por ejes, cálculo, DCR, alertas, JSON import/export. |
| HFS-WEB-003 | 5 | Vista SVG de sección y gráficos de estados límite | WEB-002 | Representación separada de ingeniería, etiquetado de ejes y unidades; pruebas de navegador. |
| HFS-WEB-004 | 5 | Vista de memoria, descarga PDF y despliegue opcional | WEB-002,043 | Reportes iguales a CLI, política de límites, protección de API, despliegue reproducible. |
| HFS-050 | 6 | Evaluación por lotes / combinaciones de carga | 042,WEB-002 | Demanda y estado gobernantes por miembro y por combinación, sin mezclar LRFD/ASD. |
| HFS-051 | 6 | Selector de perfil por cumplimiento + masa por longitud | 050,040 | Solo clasifica candidatos con cobertura completa y evidencia de cumplimiento. |
| HFS-060 | Futuro | Importación desde ETABS/SAP2000 y trazabilidad de ejes/casos | 050 | Mapeo verificable, sin suposiciones de ejes/cargas. |
| HFS-070 | Futuro | Módulo sísmico explícito AISC 341-22 | 038,041 | Alcance SFRS y requisitos sísmicos separados de los checks AISC 360. |

### Puertas de avance

- **G0 — línea base:** se conocen salidas actuales y suite que corre; cambios futuros comparables.
- **G1 — seguridad:** no existen falsos PASS por omisión, inputs ambiguos, estados o agregación incorrecta; HFS-016 debe mitigar F-13 antes de franquearla. PASS solo acredita el alcance verificable declarado y no certificación global AISC. Hasta entonces, no publicar web como verificador apto para diseño profesional.
- **G2 — integridad:** núcleo instalable, contratos versionados y traza de ejecución única.
- **G3 — validación normativa:** cada familia publicitada dispone de matriz de aplicabilidad y oráculos independientes, con huecos bloqueados.
- **G4 — web:** el servicio web produce exactamente el mismo resultado canónico y mantiene indicadores de cobertura/limitaciones.
- **G5 — selección:** solo recomendar secciones si todos los checks requeridos del alcance seleccionado han sido evaluados.

## 5. Arquitectura UX del MVP web

**Primera pantalla:** diseño/verificación individual. Columnas: (izquierda) perfil y catálogo, Fy/Fu, Lx/Ly/Lz/Lb, K/Cb con explicación, cargas en ejes locales; (centro) sección SVG orientada, resumen de condiciones; (derecha) resultado global PASS/FAIL/INCOMPLETE, DCR gobernante y tabla de estados límite.

**Vista secundaria:** memoria de cálculo: fuente AISC exacta, edición/errata, estados aplicables y excluidos, entradas, ecuaciones, sustitución, cálculos, redondeo, supuestos, archivo JSON y PDF.

**No incluir en MVP:** cuentas, base de datos, proyectos multiusuario, 3D global, optimización automatizada, conexiones sísmicas, tablas de compras y CAD. Se pueden añadir después sin tocar las reglas.

**Tecnología:** FastAPI + Python + HTML/CSS/JS nativos + SVG, siguiendo la separación conceptual de `StructureLab_RCWallDetailer`, no copiando su dominio, contratos o errores históricos.

## 6. Protocolo de trabajo obligatorio para Codex

Cada tarea debe producir:

1. **Diagnóstico:** código afectado, causa, evidencia, alternativas, decisión y riesgos.
2. **Contrato de cambio:** entradas/salidas, estados límite, normas, invariantes, pruebas, compatibilidad.
3. **Implementación acotada:** cambios mínimos a archivos pertinentes, sin rediseños no solicitados.
4. **Verificación:** `pytest`, lint, tipos cuando correspondan, ejemplos existentes, tests añadidos; evidencia de cálculos independientes cuando sea ingeniería.
5. **Cierre:** archivos cambiados, diferencias numéricas, limitaciones, referencias, reversibilidad, siguiente tarea desbloqueada.

Para cambios con efecto normativo:
- Presentar antes el artículo exacto y la lectura técnica propuesta.
- Distinguir **norma**, **Commentary**, **User Note**, referencia auxiliar e inferencia.
- No reemplazar un ejemplo independiente por comparaciones contra su propia salida.
- No marcar validado si solo pasaron tests estructurales.

## 7. Prompt inicial listo para Codex — HFS-000

```text
Actúa como auditor senior de software científico e ingeniero estructural especializado en diseño de acero según ANSI/AISC 360-22.

Repositorio: StructureLab_HFS. Tarea: HFS-000, baseline reproducible. NO cambies ecuaciones, reglas, comportamiento, contratos ni resultados. No refactorices y no implementes la web.

1. Inspecciona la estructura, dependencias, rama/SHA, estado de Git, CLI, catálogo, archivos normativos, scripts, tests y artefactos.
2. Ejecuta la suite existente con un entorno limpio; registra comando, versión de Python y número real de pruebas aprobadas/fallidas/omitidas. Si falla, identifica causa sin ocultarla.
3. Ejecuta los ejemplos representativos por familia de sección y los casos de error esperado. Registra hashes, resultados relevantes, estado y diferencias de comportamiento.
4. Identifica datos o estados límite que puedan quedar omitidos sin generar bloqueo. No los repares en esta tarea: registra reproducción mínima como casos de caracterización.
5. Crea docs/audit/baseline.md y docs/audit/findings.md con referencias a archivo y línea, severidad, certeza (observado/hipótesis), efecto físico potencial y prueba requerida.
6. Propón tests de caracterización y agrégalos solo si preservan, sin aprobar, el comportamiento observado. Marca explícitamente comportamientos inseguros como 'known defect' y evita que una prueba de regresión los legitime.
7. No borres PDFs normativos, catálogos ni archivos históricos. Si hay artefactos de salida versionados, haz inventario y plan de limpieza, no los borres todavía.
8. Entrega informe conciso: estado y comandos ejecutados, pruebas, riesgos P0, diferencias inesperadas, archivos cambiados y próxima tarea HFS-001. No afirmes validación AISC sin comparación numérica independiente.

Criterio de aceptación: baseline reproducible, evidencias de pruebas reales, matriz inicial de hallazgos y ningún cambio de comportamiento de ingeniería.
```

## 8. Fuentes documentales y verificación externa

- AISC 360-22 y AISC 341-22: PDF incluidos en raíz del repositorio como referencias de la edición aplicable; comprobar atribución/permisos de redistribución.
- AISC, erratas de AISC 360-22: https://www.aisc.org/aisc/publications/revisions-and-errata/ (incluye publicaciones de enero de 2025 y septiembre de 2026).
- AISC, Companion for 16th Edition: https://www.aisc.org/aisc/publications/steel-construction-manual/manual-companion-for-16th-edition/ (ejemplos y tablas independientes).
- AISC, 2022 Seismic Provisions: https://www.aisc.org/aisc/publications/current-standards/aisc-341
- Las propuestas de 2027 en revisión pública en octubre de 2026 NO sustituyen todavía la base vigente del motor: https://www.aisc.org/news/drafts-of-aisc-360-and-aisc-341-now-available-for-public-review/

## 9. Regla para cambiar de raíz

Una reescritura de módulo solo se permite si se demuestra al menos una de estas condiciones: (a) defectos sistémicos no corregibles localmente, (b) múltiples duplicaciones semánticas difíciles de mantener, (c) trazabilidad no representable sin rediseño, o (d) incompatibilidad persistente con validación reproducible. Antes de reescribir: ensayo de caracterización, oráculo de referencia, mapa de migración y rollback.

**Prioridad inmediata:** revisar técnicamente la entrega HFS-012. La base `main`
ya incorpora HFS-010/011/016 según la instrucción del usuario; HFS-012 queda
local, sin commit ni push automáticos. No iniciar otras tareas sin autorización.
Los nuevos dominios incompletos deben bloquearse por cobertura antes de su
reparación normativa profunda. La app web se inicia únicamente después de G1.
