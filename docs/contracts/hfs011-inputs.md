# HFS-011 — Contrato de entrada y migración

Fecha: 2026-10-27. Implementación para revisión técnica. Alcance: validación de datos; no validación normativa AISC ni implementación de HFS-010/016. Base documental: [ADR-002](../adr/002-contracts-errors.md), [matriz HFS-002](../normative/hfs002-applicability.md) y [contraste](../normative/hfs002-implementation.md). Evidencia y diferencias en el [informe](../audit/hfs011/report.md).

## Política común

`InputModel` y los tipos de `input_contracts.py` son la fuente de verdad para campos permitidos, números finitos, dominios locales y revalidación. `models.py` y `sections/models.py` declaran esos contratos. `domain/validation.py` resuelve relaciones con el caso y la sección seleccionada. El CLI solo adapta transporte; futuros consumidores deben usar los mismos modelos y `SteelDesignEngine.run`.

- Se rechazan campos extra en todos los objetos, incluidos listas de barras/anclajes y opciones CLI. No existe alias de `Mxu`: el campo es `Mux`.
- Magnitudes: números JSON, admitiendo enteros como `345` y reales como `345.0`. Se rechazan booleanos, cadenas numéricas, NaN y ±infinito. No se aplican redondeos, clamps ni conversiones de unidad al validar.
- Conteos: enteros estrictos ≥1; no `true`, `2.0` o `"2"`. `deck_present` y opciones de salida requieren booleanos JSON reales.
- Un campo opcional `null` significa dato ausente; no se sustituye por cero en la validación. Cuando ese dato es obligatorio para el caso, se rechaza. Los campos numéricos no opcionales rechazan `null`.
- Los nombres no pueden estar vacíos ni contener solo espacios. No se recortan o reinterpretan nombres de perfiles. La identidad/duplicidad del catálogo sigue pendiente de HFS-016.
- El motor revalida instancias, incluidos objetos mutados y copias creadas con `model_copy(update=...)`. `model_construct` y `model_copy` no son APIs de entrada confiables. Las funciones escalares AISC no se convierten en interfaces de transporte.

## Inventario completo de modelos auditados

Son 17 modelos ingenieriles de entrada existentes y un modelo nuevo de opciones CLI. `CheckResult` y `EngineResult` son salidas y conservan sus contratos.

| Modelo / campos | Dominio y obligatoriedad | Ausencia/default |
|---|---|---|
| `Material`: Fy, Fu, E | MPa positivos y finitos; Fu≥Fy. Fy/Fu obligatorios | E=200000 MPa, default histórico. El motor conserva su exigencia global E≈200000 con tolerancia absoluta existente 1e-6 MPa; no se amplía el alcance |
| `Loads`: Pu, Mux, Muy, Tu, Vux, Vuy, Vu | Finitos con signo. Pu positivo=compresión, negativo=tracción; kN y kN·m. Al menos un campo explícito | Contrato parcial histórico: componente omitida=0, **no** demanda desconocida. `loads` ausente, `null` o `{}` se rechaza; cero explícito se conserva |
| `Lengths`: Lx, Ly, Lz, Lb | Las cuatro obligatorias, finitas y >0 mm en todo caso | No default ni interpretación de 0 como arriostramiento continuo. Se conserva el requisito conservador existente incluso en tracción; relajar por análisis requiere otra decisión |
| `Factors`: Kx, Ky, Kz, Cb; xa, ya | K/Cb >0; offsets ≥0 mm, finitos | Kx=Ky=Kz=Cb=1; xa=ya=0. Hipótesis históricas explícitas, **no** prueba de estabilidad ni procedencia del análisis. No se añade un máximo normativo universal para Cb |
| `Connection`: An, U y cuatro opciones de ángulo | An>0 mm², 0<U≤1 si se suministran, también si están inactivos; An≤Ag. En tracción de acero solo se requieren An y U | Todos `None`. Se mantienen las condiciones existentes E5/F10 para opciones de ángulo, sin elegirlas por defecto |
| `CustomSection`: type, diameter, H, B | Circular: diameter>0 y sin H/B. Rectangular: H/B>0 y sin diameter | Dimensiones `None` hasta completar el tipo. Desbordamiento de construcción custom se rechaza; no se modifica su fórmula |
| `CompositeConcrete`: fc, wc | Ambos obligatorios, >0; MPa y kg/m³ | Sin defaults; no se presume que positividad acredite rangos normativos I1.3 |
| `CompositeLongitudinalBar`: count, db, fy, x, y | Todos obligatorios; count entero≥1, db/fy>0, x/y finitos con signo | Sin defaults ni coordenadas inferidas |
| `CompositeTransverseReinforcement`: db, spacing, fy, type | Positivos; type en `ties/hoops/spirals/stirrups` | Sin defaults. La etiqueta no acredita detallado ACI |
| `CompositeReinforcement`: longitudinal_bars, transverse | Lista validada recursivamente; objeto transversal opcional | Lista vacía y transverse=None. Encasado exige barras no vacías y transversal; en otros roles la lista vacía conserva la declaración histórica de ausencia de refuerzo |
| `CompositeGeometry`: B,H,cover,slab_effective_width,slab_thickness,deck_present | Dimensiones suministradas >0 mm. Encasado exige B/H/cover; viga exige ancho/espesor de losa y deck_present explícito | Todos None. `deck_present=None` no se interpreta como `false` en viga. Se comprueba envolvente física, no detallado normativo |
| `CompositeAnchorGroup`: type,count,segment,d,Fu,Rg,Rp,la,tf,tw | STUD exige d/Fu>0 y 0<Rg,Rp≤1 explícitos; CHANNEL exige la/tf/tw>0. Se rechazan propiedades del otro tipo. count entero≥1 | segment=`positive` histórico; restantes opcionales=None. **Eliminados** los defaults Rg=1/Rp=.75 para STUD y el fallback Fu del perfil por falta de dato |
| `CompositeAnchors`: groups | Lista de grupos validada, incluidos índices de error | Lista vacía: ausencia declarada, no capacidad inferida. El comportamiento de transferencia sin anclajes sigue siendo el existente |
| `CompositeI5Config`: method y ratios método 2 | Enum existente; 0<pc_ratio<1 y mc_ratio>0 cuando se aportan; ratios solo con METHOD_2_PLASTIC_INTERACTION | method=METHOD_1_H1_1; ratios=None conserva cálculo tabulado existente del método 2. No se cambia ninguna interacción ni se habilitan métodos |
| `CompositeConfig`: role,nominal_strength_method,concrete,reinforcement,geometry,anchors,i5 | Primeros tres obligatorios; objetos anidados con contrato común | Reinforcement/geometry/anchors/i5 usan los defaults arriba. Se mantienen rechazos de STRAIN_COMPAT/EFFECTIVE_STRAIN, torsión compuesta y familias fuera del soporte |
| `SteelCase`: section_name,material,loads,lengths,factors,connection,custom_section,composite,design_method | Nombre y primeros tres objetos obligatorios. Motor revalida antes de buscar/calcular la sección | factors/connection por sus defaults; custom_section/composite=None; design_method=LRFD histórico |
| `Section`: name,type,A y propiedades opcionales | Números finitos; magnitudes geométricas no negativas; x/y/eo/tan_alpha con signo. Alias existentes conservados. Al seleccionar se rechazan propiedades físicas cero salvo Cw/Iw y offsets/tan_alpha; H≤1, espesores no pueden cerrar OD o altura del alma | name/A obligatorios, type=`W` histórico; resto None. Ceros de catálogo se retienen para diagnóstico, nunca se calculan si se seleccionan. None no se convierte en cero |
| `OutputOptions` (solo CLI) | Booleano estricto, extras prohibidos; admite un solo nombre entre write_results_json/write_detailed_json/save_results_json | write_results_json=true histórico. `output:null` o no objeto se rechaza |

`model_fields_set` y `model_dump(exclude_unset=True)` permiten conservar la distinción entre valores aportados y defaults para consumidores Python. No se añade un modelo de procedencia estructural ni se infiere el análisis que justificó K/Cb/demandas (F-22 sigue abierto). Si una componente es desconocida, el llamador debe completar los datos antes de usar el contrato parcial; omitirla declara cero. Un cero explícito todavía puede obtener PASS sin checks: F-02/HFS-010 sigue abierto.

## Cortante: política contractual acotada

Se conservan dos representaciones **activas** alternativas:

1. Direccional: Vux/Vuy con al menos una componente no nula. Vu debe omitirse o ser cero. Se conservan componentes y signos; no se fabrica resultante.
2. Legacy: Vu no nulo, Vux=Vuy=0 (omitidos o explícitos). Conserva la ruta x histórica del software. No significa que se haya validado la correspondencia física del eje, ni que Vu sea una resultante vectorial.

Si Vu y alguna componente direccional son no nulos, se rechaza incluso si `Vu=sqrt(Vux²+Vuy²)`. Todos cero es una representación válida de demanda cero, sin afirmar cobertura resistente. Ningún campo se sobrescribe. Ejemplos: `{Vux:3,Vuy:4}` conserva Vu=0; `{Vu:99,Vux:3,Vuy:4}` y `{Vu:5,Vux:3,Vuy:4}` se rechazan; `{Vu:9,Vux:0,Vuy:0}` conserva Vu=9.

Alternativas descartadas: inferir una norma vectorial; exigir coincidencia con esa norma; renombrar componentes o transformar ejes sin fuente física. Todas introducirían una interpretación que HFS-013 todavía debe resolver. Los ceros explícitos se permiten como campos inactivos para preservar JSON serializados y consumidores históricos; el criterio es por valores activos, no por orden o prioridad de campos. F-08 se corrige en pérdida/sobrescritura; F-06/11 no se corrigen aquí.

## Requisitos entre caso y sección

Se conserva la lista existente de propiedades por regla en el router, sin cambiar selección, tablas de aplicabilidad o ecuaciones. Su guarda defensiva rechaza también no finitos al invocarse directamente. El fallo F-03 sobre razones de esbeltez ausentes sigue visible: pertenece a HFS-012, no se legitima como dato compacto.

En compuestos se evita que propiedades indispensables ausentes entren como cero: Ix/Iy para compresión o flexión, rx/ry para compresión y S/Z del eje solicitado para flexión. Encasados exigen bf/d para comprobar que el núcleo cabe dentro de B/H; barras deben caber en la envolvente por coordenada y radio. Se comprueba que cover deje dimensión interior positiva, sin suponer si el recubrimiento normativo se mide al estribo o a la barra longitudinal. No se validan interferencias entre barras ni detallado completo. Rellenos requieren espesor tdes o t y las dimensiones que usan actualmente sus constructores (b/h rectangular; OD o d circular). Se conservan las alternativas existentes sin declarar que b+3t reconstruya una dimensión exterior acreditada.

Los placeholders de catálogo de área cero se conservan intactos; la sección seleccionada se bloquea. El parser Excel usa el mismo tipo finito antes de derivar razones y después del escalado; incluye sección/campo/fila en errores. Sus reglas de unidades, alias de encabezados, placeholders Excel y duplicados permanecen fuera de esta tarea. Las propiedades `None` necesarias según una regla siguen produciendo su error existente.

LRFD/ASD: D/E/G y torsión HSS sin flexión conservan el soporte anterior; flexión ASD y todo compuesto ASD siguen rechazados. No se implementan nuevos métodos ni se comprueba que el origen externo de las cargas corresponda al método declarado.

## Rupturas y consecuencias para consumidores

- Corregir typos; eliminar campos extra, también anidados. Escribir números y booleanos JSON reales. Claves JSON duplicadas se rechazan en el CLI antes de que el parser pierda el primer valor.
- Sustituir `loads:{}` por las demandas reales; usar ceros explícitos solo si son conocidos. No añadir ceros para ocultar datos desconocidos.
- Escoger una representación activa de cortante; retirar Vu calculado por clientes que ya suministran Vux/Vuy. Una serialización antigua que guardaba simultáneamente la resultante y las componentes ya no se acepta.
- Proporcionar Fu/Rg/Rp de STUD desde su fuente real, no copiar automáticamente los viejos defaults. Declarar deck_present en vigas. Revisar conteos, enums y ratios I5.
- Completar longitudes/materiales/dimensiones requeridos. Corregir U/An, geometrías imposibles y propiedades negativas/cero; no sustituir ausencias por ceros de catálogo.
- Errores locales ahora pueden ocurrir al construir modelos, antes de `engine.run`. Para JSON/CLI, `error.code=VALIDATION_ERROR`, `details.fields[].loc/type/msg` ubican el campo y el motivo; relaciones incluyen required_field/fields, sección, rol o valores pertinentes. No se serializa NaN dentro del error. En Python se conserva Pydantic ValidationError al construir y SteelDesignError en las guardas del motor.
- Exit CLI se conserva: 1 ante error, 0 si terminó, **incluso con FAIL resistente**. Consumidores deben leer el estado JSON. No se añaden INCOMPLETE ni un contrato HTTP.
- Los esquemas se obtienen de `SteelCase.model_json_schema()`; no hay otro esquema editable. El catálogo y el transporte CLI tienen contratos separados con la misma política local. Un esquema JSON estático no expresa por sí solo todas las relaciones entre campos: ejecutar la validación común sigue siendo necesario.

Ninguna positividad, aceptación de un JSON o igualdad de snapshots certifica AISC 360-22. Revisión ingenieril de defaults, ejes, catálogos, aplicabilidad y cobertura permanece pendiente según el [seguimiento](../audit/tracking.md).
