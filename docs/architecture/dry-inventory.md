# HFS-001 — Inventario DRY y fuentes canónicas

## Actualización HFS-020: distribución y verificación instalada

- `pyproject.toml` posee identidad/versión, requisitos directos de runtime/dev,
  backend, descubrimiento de namespace, entry point y reglas Ruff.
  `requirements.txt` delega en el proyecto; no mantiene otra lista de runtime.
- `requirements/ci-constraints.txt` es una resolución fijada de auditoría, no
  otra definición del alcance de dependencias. Un paquete allí no se instala
  salvo que lo requiera runtime/dev; las plataformas no ejecutadas no se dan
  por soportadas. El freeze real acompaña cada verificación.
- `structurelab-hfs` llama directamente `src.steel_design.run:main`, igual que
  el comando histórico. No se introduce otro parser, motor ni regla de catálogo.
  `data/sections.xlsx` permanece externo y canónico, sin copia en la distribución.
- `scripts/verify_hfs020.py` es el verificador común para desarrollo y CI:
  construcción/inspección, entornos limpios e imports fuera del checkout, once
  suites separadas y regresión de ejemplos/CLI. Reutiliza utilidades de captura
  históricas sin copiar código productivo a la carpeta externa.

No cambian responsabilidades normativas, geométricas ni de resultados. La
distribución preserva íntegros los fuentes; no hay migración general de imports.
[Evidencia, limitaciones y deuda Ruff](../audit/hfs020/report.md).

## Actualización HFS-017: método y factores por disposición

- **DRY-21 / contrato de método:** `design_methods.DesignMethod` es el enum único,
  reexportado por `models` para compatibilidad. `require_design_method` reconoce
  tokens en conversores D/E/G/H; F1 conserva su interfaz estricta previa.
  `domain/design_methods.require_case_method` posee la guarda de casos y el
  límite LRFD F/I; `validate_method_scope` combina el alcance público para
  `validate_case` y `ProfileRouter`. Reglas/evaluadores/helpers directos llaman
  esa guarda antes del cálculo y de retornos inactivos. CLI no replica política.
- **DRY-02/03, factores D2/E1:** `tension_calc.tension_design_factor` y
  `axial_calc.compression_design_factor` son dueños de sus propios factores y
  trazas, consumidos por conversión disponible y reglas. El helper axial
  `_design_factor` es un alias de compatibilidad, no otra definición.
- **DRY-15/F-43:** F1 permanece en `flexure_calc.available_flexural_strength`;
  reglas F y `FlexureEvaluator` pasan el método validado. H1/H3 conservan uso
  interno de F1 ASD sin habilitar F pública. Las constantes F1 de traza/cálculo
  comparten propietario. D/E/G/H/I no se fusionan por igualdad numérica.
- **DRY-17/19:** las ecuaciones de interacción y nominales E7/I siguen separadas
  hasta su acreditación; HFS-017 no propaga una corrección normativa supuesta.
  Los factores fijos I quedan detrás de guardas LRFD, sin extrapolarlos a ASD.

Beneficio y mapa de consumidores: [contrato](../contracts/hfs017-design-method.md).
Evidencia: [informe](../audit/hfs017/report.md), once suites, 12 ejemplos y 24
consumidores CLI/memoria sin diferencias; AST de H/I idéntico salvo guardas.
La separación en dos módulos pequeños evita que conversores puros importen
Pydantic/casos para reconocer un método; no añade una jerarquía de evaluadores.

## Actualización HFS-015: números originales y recomendaciones

- **DRY-12/13, F-09:** `models.CheckResult.from_values` posee la división y decisión
  común de resultados resistentes. Los seis grupos D/E/F/G/H/I entregan demanda,
  capacidad sin redondear y unidad explícita; conservan sus fórmulas y memorias.
  `demand/capacity/dcr` son la única terna numérica original; `display` es derivado.
  H1/H3/F-43 conservan sus evaluadores y valores originales. I5 e I4 consumen ahora
  capacidades originales de los checks I2/I4, eliminando el redondeo intermedio.
- `models.finite_json_payload` es la proyección común de no finitos a null con
  ubicación/tipo. Consumidores: serialización CheckResult y memoria completa CLI.
  No muta cálculos ni reemplaza indefinidos por capacidad cero o PASS.
- `_build_dcr_trace` consume el check; no divide valores publicados ni extrae una
  capacidad alternativa de memoria. `_build_global_summary` conserva su lugar y
  consumidores HFS-014, ordenando ahora por los DCR originales publicados.
- **F-07:** `domain/recommendations.py::slenderness_recommendations` es la única
  fuente de avisos D1/E2. CLI compacto y memoria la consumen. Las declaraciones
  opcionales `SlendernessAdviceBasis` distinguen longitud fabricada, radio mínimo
  y excepción rod; no se duplican como reglas resistentes ni se usan en coverage.

No se unifican ecuaciones normativas ni se crean servicios/interfaces genéricos.
Los wrappers por capítulo conservan preparación de trazas y dimensiones.
Beneficio verificado: una razón/decisión, sin reconstrucción aproximada ni pérdida
de precisión entre consumidores; avisos separados de resistencia. [Contrato](../contracts/hfs015-precision-advice.md)
y [evidencia](../audit/hfs015/report.md). HFS-022/024, la consolidación física de
capacidades y la validación normativa integral siguen pendientes.

## Actualización HFS-014: resumen y cardinalidad de lotes

- **DRY-13/F-05:** `run.py::_build_global_summary` sigue como fuente única, ahora
  ordena por DCR publicado. Consumidores: CLI por caso, `output.global_summary`
  y `memory.global_summary`. No recalcula DCR desde checks redondeados ni llama
  al inferidor de unidades. La traza detallada legacy queda pendiente HFS-015/024.
- **DRY-14/F-29:** `results_model.aggregate_case_statuses` conserva la política
  única de estados, añadiendo rechazo de lista vacía. CLI la invoca también en
  la guarda previa de vacío; no mantiene otra decisión de cumplimiento. La
  validación de tipo de `cases`/objetos es responsabilidad de transporte del CLI.
- Para distinguir checks resistentes, el resumen consume los vínculos de
  ejecución ya existentes de coverage (`resistance`, `executed_checks`), sin
  replicar `_CLAIMS`, inferir roles de cláusulas ni acreditar obligaciones. Sin
  coverage, los candidatos numéricos son provisionales y se declaran así.

No se crea módulo/framework de reporting ni se reorganiza el CLI (HFS-021).
No se consolidan capacidades o ecuaciones. Pruebas de consumidores y
[contrato/migración](../contracts/hfs014-summary-bundles.md), con evidencia en el
[informe HFS-014](../audit/hfs014/report.md).

Actualización acotada HFS-011 (2026-10-27): el diagnóstico histórico de abajo se conserva. Se aplican únicamente los cambios de propiedad indicados en esta sección; [informe](../audit/hfs011/report.md) y [contrato](../contracts/hfs011-inputs.md).

- **DRY-07:** `input_contracts.py::InputModel` y tipos anotados poseen extras, finitud, tipos numéricos y dominios locales. Consumidores: 16 modelos en `models.py`, `Section` y opciones CLI. El loader usa `TypeAdapter(FiniteNumber)` antes de derivar razones y tras escalar. Se retiran comprobaciones positivas repetidas de concreto/barras/caso. `validate_case` revalida el modelo para defender al motor frente a mutaciones y luego comprueba relaciones.
- **DRY-10:** `Loads.validate_load_representation` es la política única de representaciones activas. Elimina resultante/sobrescritura. Predicados y agregaciones G/H/I se conservan con sus responsabilidades y defectos físicos F-06/11; no se consolidan capacidades ni se transforman ejes.
- **Geometría:** `validate_section` distingue registro de catálogo de sección seleccionada; `validate_case_section` posee requisitos entre objetos (An/Ag y datos compuestos). No construye geometría ni calcula capacidades. DRY-05/06 siguen pendientes.
- **Guardas directas:** `_is_missing_numeric` rechaza también no finitos; es disponibilidad de dato, no selección normativa. Guardas de funciones AISC/reglas y sus helpers `_positive` se conservan: llamadas directas pueden eludir el motor y sus dominios no son intercambiables. No se retiran clamps ni se implementa DRY-08.
- **Transporte:** `OutputOptions` solo valida opciones CLI; `SteelCase` sigue como contrato ingenieril compartido. Las claves JSON duplicadas se detectan antes de perderlas al construir el diccionario. No se añade otra interfaz de cálculo.

Evidencia: regresión por caso/traza completa, igualdad exacta en los 12 ejemplos, suite original, caracterización y pruebas de contrato separadas. Entradas ahora rechazadas son cambios intencionales, no refactorizaciones neutras. La igualdad de snapshots no es referencia normativa independiente.

Fecha: 2026-10-26. Base inspeccionada: `dae8d76507810362c4e31484a00b8d664525f2e6`; runtime sin cambios respecto a HFS-000. Diagnóstico y decisiones, **ninguna consolidación ejecutada**. DRY significa una fuente de verdad por concepto, no menos líneas ni una función universal. Aplican simplicidad, responsabilidad única y separación de responsabilidades del [ADR-001](../adr/001-engine-architecture.md).

## Propietarios por responsabilidad

Actualización HFS-010 (2026-10-27, para revisión): la matriz HFS-002 permanece como
única fuente documental de requisitos. `domain/coverage.py` es su proyección
conservadora ejecutable, sin imports del router ni capacidades; no se mantiene
otra tabla normativa editable. `domain/coverage_evidence.py` vincula clases
concretas ejecutadas con obligaciones parciales, sin construir el esperado.
`results_model.py` es el propietario de cobertura, estado global y propagación
de INCOMPLETE; CLI serializa esos resultados. `models.TensionScope` centraliza
las declaraciones externas del único dominio completo de v1. Las guardas físicas
siguen en HFS-011; no se duplica An<=Ag. [Contrato](../contracts/hfs010-coverage.md)
e [informe](../audit/hfs010/report.md) detallan consumidores, pruebas y cambios.
DRY-14 queda resuelto solo para cobertura de caso y propagación del nuevo estado;
lote vacío F-29, resumen F-05, ecuaciones y consolidaciones de capacidades siguen
en sus tareas. No se trasladan reglas ni se añade motor/DSL/servicio.

Actualización HFS-016 (2026-10-27, para revisión): `sections/identity.py::section_identity`
es la única política de nombres para importación y consulta. `SectionRepository`
conserva registros por identidad y decide unicidad; `SectionSource` define la
procedencia, que aporta el loader. Motor y CLI consumen `get`, sin otra selección.
Se sustituyen las dos conversiones de nombre independientes del loader/repositorio
por esa función; las conversiones de familia y nombres de reportes no son identidad.
No se añaden servicios ni dependencias. Mapa de consumidores, compatibilidad y
pruebas antes/después: [contrato](../contracts/hfs016-catalog.md) e
[informe](../audit/hfs016/report.md). Las demás consolidaciones siguen pendientes.

Esta tabla es el mapa canónico de propiedad arquitectónica; los ADR explican sus razones. «Objetivo» designa responsabilidad, no una nueva carpeta/clase obligatoria.

| Concepto | Fuente actual que se conserva | Fuente canónica objetivo y consumidores |
|---|---|---|
| Formulación y factores normativos | Funciones de `codes/aisc_360_22/*_calc.py`; algunas expresiones aún están en reglas | Función identificada por disposición y dominio en ese capítulo. Reglas y trazas usan el valor/factor calculado; no redefinirlo en reporte. La autoridad normativa sigue siendo el documento fuente. |
| Evaluación de capacidad por estado límite | Funciones de `codes`, evaluadores y secuencias dentro de reglas | Evaluación común por capacidad, eje, método y condiciones dentro del núcleo existente. Check aislado e interacción consumen el mismo valor bruto y traza; no recomputan una selección distinta. |
| Geometría/materialización de Section | `sections/models.py`, loader y constructores custom duplicados | `sections`: constructor geométrico puro y propiedades normalizadas con origen. Motor, CLI y reportes consumen la misma Section; hipótesis normativas de geometría siguen identificadas por cláusula. |
| Contrato de entrada/salida | `models.py`, `results_model.py`, `sections/models.py` | Esos modelos compartidos; esquemas derivados. CLI/API/web no mantienen modelos ingenieriles propios. |
| Validación local y entre campos | Validadores de modelos y `domain/validation.py` | Modelo para estructura/finitud/dominio local; validación de dominio para relaciones entre entradas. Guardas reutilizan la política; el adaptador solo interpreta transporte. |
| Requisitos normativos y cobertura esperada | Fuente AISC identificada; matriz HFS-002 | [Matriz independiente](../normative/hfs002-applicability.md) revisada desde la norma, jamás derivada del router. Una fuente documental editable; futuras vistas estructuradas conservarán esa independencia. |
| Selección ejecutable y soporte | `domain/routing/profile_router.py` y guardas dispersas | Registro/aplicabilidad ejecutable en routing, contrastado con requisitos independientes; UI no crea otro selector. |
| Unidades y conversiones | `sections/loader.py` para Excel, conversiones en cálculos; `docs/unidades.md` como documentación | Metadatos de importación por fuente en loader; conversiones físicas con funciones simples compartidas cuando se justifique su extracción; modelos/resultados declaran unidades. No mezclar escalado de catálogo con factores AISC. |
| Construcción/decisión de resultado | `CheckResult`, constructores repetidos en reglas, `EngineResult` | Constructor común de check bruto y agregador en núcleo, conservando semántica por tipo de check. Traza emitida por evaluación. |
| Presentación | Funciones de `run.py` | Formateadores que consumen resultado/traza; futura extracción de reporting con consumidores concretos. CLI/API/web no recalculan DCR, capacidades ni estados. |
| Ejecución de caso/lote | `SteelDesignEngine.run`, lote en CLI | Una ejecución común; adaptadores solo entregan entradas y presentan salidas. No un segundo motor web. |
| Seguimiento/documentación viva | Roadmap y diagnóstico HFS-000 | ROADMAP para tareas/prioridades resumidas; tracking para estado de F-ID; informes HFS-000 como evidencia inmutable, no otra lista viva. |

## Duplicaciones y decisiones concretas

Rutas relativas a `src/steel_design/`, excepto docs/tests. Los símbolos identifican ubicaciones sin depender de desplazamientos de línea. Las consecuencias numéricas no ensayadas se marcan como riesgos, no como defectos de formulación probados.

| ID / área | Archivos y símbolos involucrados | Causa / evidencia observada | Riesgo | Decisión y consolidación concreta | Verificación antes de aplicar |
|---|---|---|---|---|---|
| DRY-01 / formulación | `codes/aisc_360_22/axial_calc.py::calculate_Fcr`; `composite_calc.py::composite_buckling_strength_i2` | Se repiten coeficientes 0.658/0.877 en pandeo de acero y compuesto. Parecido algebraico; variables/dominio distintos. | Fusionar puede borrar condición E/I, dimensiones o factores. | **Conservar justificadamente** funciones por disposición. No hay equivalencia normativa demostrada ni necesidad de un helper de dos líneas. | Oráculos E/I y lectura de dominios antes de reconsiderar; conservar IDs y ramas. |
| DRY-02 / factores y memoria | `axial_calc.py::calculate_available_compressive_strength`; `domain/rules/axial_rules.py::_design_factor`; `combined_hss_rules.py::_torsion_capacity_h3` y memoria de `HssTorsionH3_1Rule` | Cálculo y texto de memoria declaran factores por separado. | Reporte puede mostrar factor distinto del usado. | **Consolidar** el factor y la expresión como parte de la evaluación de esa disposición; memoria consume el mismo objeto/datos. No reunir todo 0.90 en una constante normativa universal. | Comparar capacidad, método y factor de traza para LRFD/ASD por cláusula. |
| DRY-03 / capacidad axial | `axial_rules.py::AxialE3Rule/AxialE4Rule/AxialE7Rule`; `combined_hss_rules.py::_available_axial_strength`; `composite_rules.py::_bare_steel_compression_capacity_k_n` | Reutilizan `axial_calc`, pero recomponen Fe, clasificación, estados aplicables y mínimo en varias rutas. | Interacción/piso de acero y check aislado pueden usar distinta capacidad o fallback (F-20). | **Consolidar** evaluaciones de acero por dominio validado; interacción y piso consumen resultados brutos con procedencia. Conservar selección normativa distinta cuando corresponda; no usar un mínimo global de checks. | Casos por familia/eje/método, datos faltantes, comparación por componente y referencias independientes; separar corrección de extracción. |
| DRY-04 / capacidad cortante | `shear_rules.py::ShearG4Rule/ShearG5Rule`; `combined_hss_rules.py::_rectangular_hss_shear_capacity/_round_hss_shear_capacity`; `composite_rules.py::_steel_shear_capacity_k_n` | Secuencias geométricas/factores se recomponen; G4 usa tdes mientras H admite fallback a t. Reutilizar `shear_calc` no elimina esa divergencia. | Distinta resistencia en G e interacción; combinar ejes agrava F-06/11. | **Consolidar** evaluaciones direccionales después de resolver dominio/fallback; conservar el envoltorio de la disposición I cuando exija otra participación del acero. | Oráculo direccional asimétrico, t/tdes ausentes, unidades/factores y trazas; no considerar equivalentes todas las rutas. |
| DRY-05 / geometría custom | `engine.py::_build_custom_section`; `run.py::_build_case_section` | Área, inercias, radios y módulos del mismo macizo se calculan dos veces (F-15). | Cálculo y memoria pueden representar secciones distintas. | **Consolidar** en una función pura de `sections`; **eliminar después** la copia aritmética del CLI, que recibirá Section ya construida. | Regresión de ambos macizos y geometría calculada independientemente; entradas inválidas. |
| DRY-06 / geometría HSS | `combined_hss_rules.py::_round_hss_dimensions/_rectangular_hss_outside_dimensions`; `composite_rules.py::_round_dimensions/_filled_outside_rect_dimensions`; `shear_rules.py::_round_hss_diameter/_round_hss_thickness`; loader | Recuperación de dimensiones/fallback repetida; en rectangular se repite b+3t/h+3t; la hipótesis geométrica puede depender del uso. | Una misma Section cambia de dimensión efectiva según ruta; F-12/27. | **Consolidar** recuperación de datos físicos en `sections` con origen. **Conservar separadas** aproximaciones normativas con nombre/condición hasta probar equivalencia; no adoptar automáticamente b+3t como dimensión física exacta. | Fuente del catálogo, geometría conocida, radios/espesores y oráculos de cada disposición. |
| DRY-07 / validación | `models.py::CompositeConcrete.validate_concrete_values`; `domain/validation.py::validate_case` | fc/wc positivos se comprueban en dos sitios. `_positive` aparece además en varios cálculos/reglas convirtiendo inválidos a cero. | Políticas dispares y valores inválidos ocultos; F-10. | **Consolidar** restricción local en modelo; guardas directas invocan política común si son necesarias. **Conservar provisionalmente** helpers locales hasta distinguir saneamiento, clamp normativo y validación; no reemplazar todos con una utilidad genérica. | Rechazo finito/positivo en entradas y llamadas directas; probar que un clamp físicamente requerido no se elimina. |
| DRY-08 / alcance de método | `domain/routing/profile_router.py::_validate_composite_scope`; `composite_rules.py::_ensure_supported_method`; restricciones en `domain/validation.py` | PLASTIC/ELASTIC y métodos no implementados se comprueban más de una vez. | Mensajes/alcance divergentes al habilitar un método. | **Consolidar** política de soporte del método junto a aplicabilidad; conservar guardas de invocación directa que consulten esa misma política. Validación LRFD del caso es una restricción diferente. | Routing y llamada directa rechazan lo mismo, sin activar métodos por efecto de refactor. |
| DRY-09 / clasificación y selección | `profile_router.py::_w_or_channel_major_flexure_selection/_classify_element`; `flexure_calc.py::evaluate_f3/evaluate_f6`; `_section_slenderness_values` del router y `_slenderness_values` en reglas H/E | Límites/clasificaciones y empaquetado de razones se repiten. La similitud de clasificación compresión/flexión no implica mismo dominio. | Router selecciona una rama incompatible con la evaluación; F-03/31. | **Consolidar** clasificación por disposición que selección y cálculo compartan; usar una vista de razones de Section. **Conservar** clasificaciones diferentes E/F/I explícitas, sin clasificador global de sección. | Fronteras por elemento y disposición, faltantes y cobertura por eje; matriz futura HFS-002. |
| DRY-10 / demandas y ejes | `models.py::Loads.normalize_shear`; `profile_router.py::_has_major_shear/_has_minor_shear`; `shear_rules.py::_shear_demand/_axis_v_label`; H/I `_required_shear*` | Interpretación legacy, activación y resumen se distribuyen; no todos responden a la misma pregunta. | Pérdida de componente o mezcla demanda/capacidad (F-08/11). | **Consolidar** normalización y convención de componente en contrato compartido; selección consulta componentes normalizados. **Conservar** agregación de una disposición si tiene fundamento distinto, sin identificarla con normalización. | Oráculos físicos y tests direccionales; no corregir solo etiquetas. |
| DRY-11 / unidades | `sections/loader.py::UNIT_SCALE_BY_VARIABLE/_scaled_float`; divisiones en `tension_calc`, `axial_calc`, reglas; `composite_calc.py::_n_to_kn/_nmm_to_kn_m`; `run.py::_infer_check_units` | Conversión física repetida y unidad de salida inferida de cláusula; escalado Excel es conocimiento de fuente diferente. | Doble escala, unidades incorrectas o mezcla de capacidades (F-05/14/21). | **Consolidar** conversiones N↔kN/Nmm↔kNm en funciones explícitas si se extraen; loader conserva su mapa por fuente. **Eliminar después** inferencia de unidades del reporte al disponer de resultados tipados. | Ejemplos dimensionales independientes, no doble conversión y metadata de todo tipo de check. |
| DRY-12 / resultados | `_result` de axial; `_build_result` de shear/H/I; `_build_flexure_result`; construcción en `tension_rule.py` | DCR, redondeo y PASS/FAIL repetidos en constructores casi iguales. | Divergencia de umbral/precisión o trato de capacidad cero (F-09/21). | **Consolidar** construcción de check bruto común; regla aporta demanda/capacidad o interacción ya calculada. Formatear después. No hacer de todo check una razón resistente idéntica (I1 tiene otra semántica). | Fronteras, infinito/no disponible, interacción y checks de alcance; equivalencia y correcciones documentadas. |
| DRY-13 / presentación y traza | `run.py::_build_dcr_trace/_extract_capacity_from_memory/_build_global_summary`; constructores de reglas | CLI recalcula DCR desde datos reportados/memoria e infiere unidad. | Dos verdades sobre el cálculo y gobernante; F-05/09. | **Eliminar** recomputación al migrar a traza canónica del núcleo; presentación solo formatea. | Paridad valor/decisión/traza, precisión, dimensiones y comparación CLI/API futura. |
| DRY-14 / ausencia y agregación | `_nominal_pass/_pass_result` en reglas E/F/G/H/I/D; `engine.py::run`; `run.py::main` lote | Múltiples lugares construyen PASS vacío o agregan desde True. No es solo texto repetido. | Falso cumplimiento F-02/29. | **Sustituir** política en tarea de estados/cobertura; no extraer un helper común que legitime PASS vacío. Agregador canónico para caso/lote con razones conservadas. | Cero checks, fuera de alcance, errores parciales y lote vacío. Es cambio de comportamiento, nunca refactor «neutro». |
| DRY-15 / evaluadores existentes | `TensionEvaluator` usado por reglas D/H; `FlexureEvaluator` y `flexure_calc.evaluate_f2` | Tracción ya centraliza dos resistencias; otros evaluadores no forman una capa uniforme. | Crear una clase Evaluator para cada fórmula sin consumidor real. | **Conservar justificadamente** reutilización existente. No generalizar la jerarquía; revisar wrappers de flexión solo cuando una extracción concreta elimine repetición. | Mapa de llamadas e igualdad de resultados; no eliminar wrappers por número de líneas. |
| DRY-16 / documentos y referencias | `docs/ROADMAP.md`; copia `StructureLab_HFS_Roadmap_Codex.md` mencionada en HFS-000, ya ausente del checkout actual; findings histórico y seguimiento; tests frente a cálculos productivos | Duplicación documental histórica, no dos roadmaps actuales. Las pruebas independientes pueden repetir razonamiento intencionalmente. | Recrear autoridades editables contradictorias o validación circular si se «deduplica» el oráculo. | **Conservar** ROADMAP como único plan vivo; no recrear la copia ausente. Separar snapshot de seguimiento vivo. **Conservar** el cálculo independiente del oráculo. | Hash/mapa de procedencia de evidencia; revisión de independencia del esperado. |

## Orden y condiciones de aplicación

### Relaciones adicionales diagnosticadas en HFS-002

No se consolida código. Los N-ID pertenecen a la [matriz independiente](../normative/hfs002-applicability.md), no al router.

| ID / archivos | Causa y riesgo | Decisión concreta / fuente canónica futura | Norma y prueba requerida |
|---|---|---|---|
| DRY-17: `combined_hss_rules._compute_h1_interaction` y `composite_rules._i5_method_1_h1_interaction` | Repiten rama de tracción lineal y etiqueta H1-2; puede propagarse una referencia/método incorrectos (F-37) | **Consolidar** solo el evaluador adimensional H1 tras confirmar dominio y tratamiento de tracción; capacidades D/E/F e I2/I3 conservan sus propietarios y factores. No fusionar I5 completo con H | N29/N42; H1.2 remite H1-1a/b; I5 rutas por clase. Oráculos de umbral 0,2, tensión/compresión y biaxialidad |
| DRY-18: clasificación en `axial_calc`, `flexure_calc`, router y `composite_calc` | Coinciden razones b/t, pero difieren anchos, límites y máximos B4/I1; factor dos canal/I y materiales importan | **Conservar** clasificaciones por disposición; **consolidar** datos geométricos con procedencia en sections y clasificación del mismo dominio repetida en selección/cálculo. Complementa DRY-09, no clasificador universal | N02/N08/N10/N12–20/N36; tablas B4.1a/b e I1.1a/b, casos límite por elemento/eje, falta de datos |
| DRY-19: copias de capacidad E7 en consumidores D/E/H/I vía helpers (DRY-03) | Compartir fórmula Q actual propagaría discrepancia F-35 | **Conservar provisionalmente** separación hasta resolver E7; después **consolidar** evaluación E por estado, área efectiva y eje. Piso de acero I sigue alternativa normativa explícita | N10/N29/N37/38; E7-1 a 7, I2.1b/2b, cálculo independiente de Ae/Fn y regresión por consumidor |
| DRY-20: metadatos `RuleDefinition`, `CheckResult.clause`, memoria y `docs/aisc_360_22_traceability.md` | ID de software confundido con sección/ecuación (F-37), duplicaciones editoriales | **Consolidar** vínculos ejecutables ID→fuente→función y generar vistas de implementación; **conservar independiente** matriz de requisitos N y oráculos. No derivar obligación desde código | Todos N; pruebas de correspondencia, hueco deliberado en registro detectado por plan independiente |

DRY-04/10 se precisan con N25/26/30: compartir pares demanda/capacidad por dirección y aplicar máximo de **cocientes** H3.2; no reutilizar un resumen `max` genérico. DRY-06 se acota con B4.1b(d): dimensión exterior menos 3t es aproximación permitida del ancho plano cuando falta radio; invertirla para reconstruir dimensión exterior exacta necesita acreditar procedencia. Ninguna de estas decisiones convierte una prueba de regresión en validación normativa.

No usar este inventario como autorización de refactorización. Primero resolver el defecto o la interpretación en su tarea; después extraer con regresión demostrable. Cambios de seguridad que alteran resultados se identifican como tales, no se esconden bajo DRY. Mapa de tareas/F-ID en [tracking](../audit/tracking.md).

Antes de consolidar: enumerar consumidores, fijar dominio/unidades/factores, seleccionar propietario, comparar cada salida y traza, aportar oráculo independiente si afecta cálculo, conservar ID de ecuación/estado límite, explicar divergencias esperadas y retirar la copia solo tras verificar consumidores. Mantener funciones de cláusulas distintas si la equivalencia sigue sin demostrar.

Este inventario cubre las duplicaciones representativas inspeccionadas; no es una prueba exhaustiva de todas las ecuaciones ni el plan de cobertura de HFS-002. La fuente única reduce divergencias, pero no garantiza que la fuente sea correcta: por eso permanecen las validaciones independientes.

## Aplicación acotada HFS-012

DRY-09/18: el selector existente sigue siendo el propietario de la selección
F2–F5. `_flexure_ratio` resuelve datos dentro de ese mismo módulo y reutiliza
`_classify_element`; no hay segundo clasificador ni motor. La selección mayor
se resuelve una vez por llamada del router. El loader no cambia: su derivación
de columnas es importación; el selector contrasta el significado B4.1 y no
rellena Section ni el catálogo. La consolidación general de geometrías y de
clasificación entre router/evaluadores permanece pendiente, sin mezclar E/F/I.

`coverage_evidence.record_selection_errors` solo vincula diagnósticos a
obligaciones ya construidas por el plan independiente; no calcula límites ni
genera requisitos desde el router. CLI consume el resultado común. El beneficio
concreto es conservar checks independientes sin perder la causa de una demanda
no evaluada. Pruebas numéricas y límites en [informe HFS-012](../audit/hfs012/report.md).

## Aplicación acotada HFS-013

| ID / copias | Decisión aplicada y propietario | Consumidores / evidencia / pendiente |
|---|---|---|
| DRY-10: demandas legacy en router, G y H3 | **Consolidar** en `domain/actions.py::shear_demand/shear_trace`; Loads conserva validación de representaciones. Convención canónica en `docs/contracts/hfs013-axes.md` | Router consulta demanda; G/H3 comparten valor firmado, magnitud, plano y dirección. Capítulo I conserva agregaciones de otra disposición pendientes de auditoría; no se fusionan por parecido |
| DRY-04: capacidades G4/G5 copiadas en `combined_hss_rules` | **Consolidar** en función simple `domain/evaluators/hss_shear.py::evaluate_hss_shear` | Dos consumidores reales: reglas G4/G5 y H3. Cálculo bruto, factores y traza comunes; fórmulas numéricas siguen en `shear_calc`. No reutilizar CheckResult redondeado |
| DRY-06: dimensiones circulares/G/H y rectángulo reconstruido | **Consolidar** validación explícita de OD/tdes en `round_hss_dimensions`; **eliminar** inferencia geométrica no acreditada de C rectangular y sustitución de pared/espesor | G5/H3 comparten dimensiones; H3 rectangular exige C declarada. Constructor geométrico general no creado. `calculate_rectangular_hss_torsional_constant` se conserva como fórmula pura de User Note que exige B/H exteriores explícitos; el motor no inventa esos datos |
| DRY-02: G4/G5 cálculo vs memoria | **Consolidar** capacidad/factores en la evaluación compartida | LRFD/ASD contrastados por oráculo; memoria de H3 usa esa misma evaluación |
| G5 y H3 circular: expresiones semejantes con longitud | **Conservar justificadamente** funciones distintas | G5 usa Lv y coeficientes 1,60/0,78; H3 usa L y 1,23/0,60. No helper genérico que borre dominio. Cada una prueba su rama de fluencia sin longitud por identidad matemática |

Los módulos nuevos son funciones sin clases ni registro genérico. Se eliminan
dos evaluadores H3 de cortante duplicados y sus fallbacks. El beneficio es que
un cociente H3 conserva exactamente la misma capacidad bruta que su check G.
No se duplica clasificación ni se toca el selector HFS-012. DRY-03/09/12/13/17/19
siguen pendientes: no se generaliza esta extracción a D/E/F/H1/I ni al reporte.
Pruebas independientes y diferencias antes/después en el
[informe HFS-013](../audit/hfs013/report.md); los oráculos se conservan separados
del código productivo deliberadamente.

### Revisión final HFS-013 — F-43 y conversión F1

Fuente canónica actual de **Mn→Mc por método**:
`codes/aisc_360_22/flexure_calc.py::available_flexural_strength`.
Define una vez φb=0,90 y Ωb=1,67 (F1(a)), convierte N·mm a kN·m y rechaza
métodos desconocidos. No es otro evaluador de resistencia nominal.

Mapa de consumidores: `_available_flexural_strength` de `combined_hss_rules`
elige F7/F8 y transmite `case.design_method.value`; H3 y H1 comparten esa función.
`available_flexural_strength_lrfd` conserva su firma como delegación al mismo
conversor, por compatibilidad con `_build_flexure_result` y `FlexureEvaluator`,
cuyas rutas siguen limitadas a LRFD. No se copia 0,90/1,67 en H1/H3 ni se
recalculan nominales en otro módulo. Los factores de D/E/G/H3 no se fusionan con
F1 por coincidencia numérica. No se modifican fórmulas nominales F7/F8.

DRY-02 queda aplicado a esta conversión concreta; no cierra las duplicaciones
restantes de capacidades/clasificación DRY-03/09/19. Oráculos separados y prueba
de identidad de nominales/LRFD en [suplemento F-43](../audit/hfs013/f1-correction/report.md).
