# StructureLab_HFS — Roadmap de auditoría crítica, modernización y aplicación web

**Estado:** propuesta técnica para ejecución incremental con Codex  
**Referencia de auditoría:** rama `main`, commit `80a9d3609d452ab3413ad632629b1fadcab8415c` de `Beicker29/StructureLab_HFS`.  
**Documento:** 26 de octubre de 2026.  
**Objetivo:** motor AISC 360-22 de diseño/verificación de miembros de acero, trazable, sencillo, testeable, con CLI y app web. AISC 341-22 se reserva como alcance normativo separado y optativo.

**Actualización HFS-001 (2026-10-26):** HFS-000 aceptada como línea base de comportamiento, no validación AISC. Las decisiones documentales de HFS-001 quedan para revisión en [ADR-001](adr/001-engine-architecture.md), [ADR-002](adr/002-contracts-errors.md) y [ADR-003](adr/003-traceability-testing.md). El estado vivo F-01–F-32 está en [seguimiento maestro](audit/tracking.md); el diagnóstico HFS-000 permanece inmutable. HFS-002 y tareas posteriores no se han iniciado.

> Esta es una auditoría estática de arquitectura y porciones representativas del código obtenidas del repositorio. NO se han ejecutado aquí las pruebas ni se han recalculado todos los ejemplos contra el texto normativo. Distinguir defectos confirmados de riesgos pendientes de validación numérica. El listado puede ampliarse durante los hitos de auditoría.

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
| F-05 | P0 | C | `run.py::_build_global_summary` | Elige la menor capacidad mezclando kN y kN·m. Sustituir por DCR gobernante y agrupar capacidades por dimensión y eje. |
| F-06 | P0 | C/R | `combined_hss_rules.py::_available_shear_strength` | Usa `max(Vcx,Vcy)` con una demanda `max(Vux,Vuy)` para interacción H3. La validez física/normativa requiere revisión; no combinar arbitrariamente capacidades direccionales. |
| F-07 | P0 | C | `run.py::_build_chapter_admissibility` | D1 (300) y E2 (200) se presentan como admisibilidad; separar recomendaciones de incumplimientos. Revisar semántica de aplicabilidad de D1/E2. |
| F-08 | P0 | C/R | `models.py::Loads.normalize_shear` | Sobrescribe `Vu` si hay Vux/Vuy y fabrica resultante vectorial; resolver contradicciones y definir transformación a ejes locales con física explícita. |
| F-09 | P0 | C | `domain/rules/*::_build_result`, `round(dcr,3)` | Umbral se evalúa sin redondeo pero DCR se publica redondeado; conservar precisión cruda y diferenciación display vs decisión, especialmente 0.9999/1.0001. |
| F-10 | P0 | C/R | `domain/routing/profile_router.py::_is_missing_numeric`, `sections/loader.py::_coerce_float` | Ausencia de validación explícita de finitud en varios lugares; probar y prohibir NaN, infinito, números negativos y dimensiones imposibles. |
| F-11 | P1 | C/R | `domain/rules/shear_rules.py::_axis_v_label` | Comentario indica inversión legacy de etiquetas respecto de routing; documentar y comprobar matemáticamente ejes, componentes y capacidades. No corregir solo nombres. |
| F-12 | P1 | C/R | `sections/loader.py`, selección `field_values['id']` para D/t | Revisar que D/t corresponda al diámetro exterior físico, no ID, según familia/convención de catálogo. |
| F-13 | P0 propuesto | C | `sections/repository.py::load`, `docs/audit/catalog-duplicates.json` | Duplicados reales HEA 100 con geometrías distintas; última fila sobrescribe. Priorizar identificación/rechazo antes de G1, sin esperar toda la fase 4. Ubicación de corrección acotada pendiente de revisión; justificación en seguimiento maestro. |
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
| F-29 | P1 | C | `run.py` modo lote: `aggregate_pass=True` y `cases=[]` | Lote vacío puede declararse PASS; exigir ≥1 caso válido y agregación completa, resultados por caso. |
| F-30 | P1 | R | `src/steel_design/codes/aisc_360_22` | Auditoría profunda de E4/E5/E7, F2–F11, G2–G6, H, I; revisar todos los factores, dominios, límites y errores numéricos. No asumir fidelidad por etiqueta de ecuación. |
| F-31 | P0 | C/R | `domain/routing/profile_router.py::_validate_flexure_selection`; caracterización HFS-000 | Un check F del eje menor evita bloqueo aunque la demanda mayor no se evalúe. Omisión confirmada en sonda sintética; contraste con canal real pendiente. Seguimiento HFS-002/010/032. |
| F-32 | P1 | C | `run.py::main`, ejemplos HFS-000 | FAIL estructural puede devolver exit 0. Es contrato observable, no regresión. Documentar separación ejecución/cumplimiento y revisar consumidores antes de cambiar exit; HFS-021/022. |

**Nota de rigor:** un defecto de diseño de software no demuestra por sí solo un resultado estructural incorrecto para un caso dado. Y un resultado correcto en una prueba no certifica todas las combinaciones del capítulo correspondiente.

## 3. Arquitectura objetivo mínima

**Revisión crítica HFS-001:** el árbol siguiente conserva la propuesta original como contexto, no prescribe crear todas esas capas. ADR-001 propone conservar `sections`, funciones en `codes` y reglas/routing en `domain`; extraer solo responsabilidades justificadas, sin `services` web obligatorio ni segundo motor. DRY y contratos compartidos son las fronteras requeridas; la aprobación técnica de esta revisión sigue pendiente. No hay migración de carpetas en HFS-001.

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

`ApplicabilityPlan` debe demostrar explícitamente: cuáles verificaciones son obligatorias para familia/geometría/solicitaciones, por qué se activan/no activan, y si todas las obligatorias están implementadas y se ejecutaron.

**Precisión:** `float` puede mantenerse para cálculo ingenieril si se prueba la estabilidad numérica y se rechazan valores no finitos. No imponer Decimal universalmente: la física del problema no exige la misma aritmética exacta del detallado geométrico de RCWallDetailer.

## 4. Roadmap de tareas ejecutables con Codex

Las tareas siguientes se implementan con una rama y PR independientes cuando sea posible. Ninguna tarea P0 debe incluir una reescritura integral del proyecto.

| ID | Fase | Tarea Codex | Depende de | Aceptación esencial |
| --- | --- | --- | --- | --- |
| HFS-000 | 0 | Inventario, baseline y congelación de resultados actuales | — | SHA, `pytest`, entornos, CLI ejemplos, hashes/fixtures y limitaciones reproducibles. Sin cambios normativos. |
| HFS-001 | 0 | `AGENTS.md`, guías de contribución, 3 ADR, matriz de hallazgos | 000 | Arquitectura aprobada, políticas simples, decisiones registradas, fuentes clasificadas como evidencia vs hipótesis. |
| HFS-002 | 0 | Matriz *familia × demandas × condiciones × estados límite* | 000 | Identifica todos los huecos y casos no implementados; revisión ingenieril requerida. |
| HFS-010 | 1 | Cierre de cobertura y estados de resultado `INCOMPLETE` | 002 | Cero checks, reglas obligatorias ausentes y métodos no soportados jamás entregan PASS. |
| HFS-011 | 1 | Endurecer Pydantic: campos extra, faltantes, finitud, dominios | 000 | Typos, NaN, inf, valores imposibles y cargas ambiguas rechazados. |
| HFS-012 | 1 | Corregir fallback indebido de F2 por esbeltez ausente | 010,011 | Falta de `bf/2tf` o `h/tw` no puede clasificar sección compacta automáticamente. |
| HFS-013 | 1 | Revisar convenciones `Pu,Mux,Muy,Vux,Vuy,Vu,Tu`, ejes y capacidades de cortante H3 | 011 | Ensayos direccionales no confunden ejes; si norma/caso no cubierto -> INCOMPLETE. |
| HFS-014 | 1 | Sustituir resumen de capacidades mezcladas, reglas de agregación de lote vacío | 010 | DCR gobernante con dimensión válida, `cases=[]` rechazado. |
| HFS-015 | 1 | Separar cálculo bruto/visualización, casos límite `DCR ≈ 1` y recomendaciones D1/E2 | 010 | Decisiones no cambian por redondeo; avisos no se confunden con incumplimientos. |
| HFS-020 | 2 | Empaquetado Python (`pyproject.toml`), CI, Ruff, pytest | 010-015 | Wheel limpio, `pip install .`, CLI y pruebas funcionan fuera del checkout. |
| HFS-021 | 2 | Extraer servicios puros del CLI y centralizar geometría custom | 020 | Web y CLI futuros utilizan la misma ejecución; no hay lógica duplicada. |
| HFS-022 | 2 | Contratos versionados de entrada, plan normativo, checks y resultado | 021 | JSON round-trip, migración explícita y esquemas generados reproducibles. |
| HFS-023 | 2 | Registro normativo declarativo mínimo, sin framework de plugins | 022 | Cada regla tiene ID, aplicabilidad, cita, implementación, conjunto de tests y estado de verificación. |
| HFS-024 | 2 | Trazas de cálculo canónicas y memorias sin inferencia por nombre de cláusula | 022,023 | Variables, unidades, expresiones, fuente y rama normativa recuperables en CLI/JSON/web. |
| HFS-030 | 3 | AISC 360-22: base documental y erratas, tabla de trazabilidad | 023 | Comparación de PDF del repo con fuente oficial; versión/erratas registradas. |
| HFS-031 | 3 | Auditoría normativa capítulos D y E (incl. E4/E5/E7) | 030 | Oráculos independientes, casos límite, clases geométricas y condiciones de uso. |
| HFS-032 | 3 | Auditoría capítulo F (F2–F11, rama F4, Cb, Lb) | 030 | Validación por familia/eje/región de frontera; evitar atajos no probados. |
| HFS-033 | 3 | Auditoría capítulo G y convenciones de ejes/cortante | 030,013 | Reglas direccionales contrastadas con norma y referencias independientes. |
| HFS-034 | 3 | Capítulo H: H1 para W y demás miembros elegibles; H2/H3 según alcance | 031-033 | Combinación Pu+Mx/My no queda sin evaluar silenciosamente; casos de verificación independientes. |
| HFS-035 | 3 | Capítulo I: auditar I1–I5, métodos, vigas y columnas compuestas | 030 | Ensayos independientes; I5 traza método, factores y dominios; sin extrapolación implícita. |
| HFS-036 | 3 | Modelo numérico compuesto: convergencia en discretización y equilibrio | 035 | Sensibilidad a franjas/iteraciones; tolerancias documentadas y regresiones reproducibles. |
| HFS-037 | 3 | Capítulo C y validez del modelo de estabilidad / procedencia de demandas | 030,022 | Métodos admitidos definidos; supuestos no verificados impiden certificación de miembro completo. |
| HFS-038 | 3 | Definir alcance no implementado de B/J/K y otros estados límite externos | 002,030 | No se declara cumplimiento global más allá de frontera explícita de producto. |
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
- **G1 — seguridad:** no existen falsos PASS por omisión, inputs ambiguos, estados o agregación incorrecta. Hasta entonces, no publicar web como verificador apto para diseño profesional.
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

**Prioridad inmediata:** ejecutar `HFS-000` y, con resultados, `HFS-001` y `HFS-002`; luego corregir los P0 mediante PRs pequeños `HFS-010` a `HFS-015`. La app web se inicia únicamente después de la puerta G1.
