# HFS-015 — Valores originales, JSON estricto y recomendaciones

Contrato entregado para revisión sobre `main` / `dbd87cb`. Sustituye la precisión
y la semántica de recomendaciones del transporte previo; no amplía cobertura
normativa ni soporte ASD. [Informe](../audit/hfs015/report.md).

## Un valor original y una decisión

`CheckResult.demand`, `capacity` y `dcr` contienen los **valores originales sin
redondear**. No se añade una segunda terna editable `*_raw`: los campos actuales
son la fuente canónica. Cada regla entrega su capacidad y demanda originales a
`CheckResult.from_values`; este calcula una sola razón y decide `dcr <= 1.0`, sin
epsilon. Las reglas conservan ecuaciones, nominales, factores y trazas propias.

La presentación derivada está en `display`:

```json
{
  "demand": 310.53105,
  "capacity": 310.5,
  "dcr": 1.0001,
  "unit": "kN",
  "numeric_issue": null,
  "status": "FAIL",
  "display": {
    "demand": "310.531",
    "capacity": "310.500",
    "dcr": "1.000",
    "dcr_label": "1.000 (FAIL; raw=1.0001)"
  }
}
```

Usar `display.dcr_label` o mostrar siempre DCR **junto con su estado**. La cadena
abreviada `display.dcr` no es una decisión; no presentarla sola como cumplimiento.
Para ordenar/exportar/operar usar los números originales, nunca analizar las
cadenas visuales ni dividir demanda/capacidad redondeadas. Se conserva `float`,
su precisión binaria real y su representación JSON; no se promete decimal exacto.

La unidad procede del productor: D/E/G y acciones de fuerza I usan `kN`, F y
torsión H3.1 `kN-m`, H1/H3.2/I5 y checks I de configuración/proporción `ratio`.
No se decide por prefijo de cláusula. Un resultado legacy/inactivo sin unidad
declara `unit=null`; la traza explica que el productor no suministró la unidad.

La construcción directa histórica `CheckResult(...)` continúa disponible:
representa valores declarados por quien la invoca, sin reconstruir una razón
distinta ni certificar su procedencia. Los productores resistentes del motor
usan `from_values`. HFS-022 podrá definir importación/round-trip de resultados;
esta entrega no lo implementa.

## No finitos y ausencia de resistencia

Una capacidad no positiva/no finita o una razón indefinida no acredita PASS.
El constructor devuelve `FAIL` con `numeric_issue=UNDEFINED_OR_NONFINITE_RATIO`;
este diagnóstico distingue imposibilidad numérica de un incumplimiento resistente
numéricamente demostrado. En la ejecución actual, la cobertura correspondiente
no puede acreditarse con ese dato. No se cambian los estados ni las obligaciones
HFS-010. Los fillers históricos inactivos 0/0 con DCR=0 no son una división válida
ni una resistencia: siguen excluidos del resumen y no acreditan cobertura.

La proyección de serialización transforma **cada número no finito en `null`**,
registrando `nonfinite_values` con ubicación relativa al objeto que lo contiene
y tipo (`NaN`, `Infinity`, `-Infinity`). En `details` los diagnósticos se ubican
dentro de `details`; en la memoria completa se registran en la raíz si el valor
aparece en cálculos/contexto. No reemplazar null por cero ni usarlo en aritmética.
Las cadenas de diagnóstico pueden nombrar Infinity, pero no hay tokens numéricos
JSON no estándar. `json.dumps(..., allow_nan=False)` se exige en salidas CLI.

Los valores de cálculo en memoria Python no se mutan por serializar. Un infinito
usado históricamente para una componente inactiva queda identificado; **no** se
interpreta como una capacidad física acreditada. Un diagnóstico en una variable
auxiliar no invalida automáticamente un check finito independiente. Esto no es
una reparación normativa de todas las fórmulas que producen esos sentinelas.

El JSON proyectado con null y diagnósticos es un resultado de lectura. No se
promete cargarlo sin transformación mediante `CheckResult.model_validate`: la
reconstrucción de resultados indefinidos y sus estados ampliados queda en HFS-022.

## Resumen HFS-014 y memoria

El resumen conserva los nombres `max_dcr_published`, `dcr_published`, índices,
listas de gobernantes/fallos y ámbito `executed_checks_only`. **Ahora el número
publicado es el DCR original**. Su versión cambia a `HFS-015-v2` y `ranking_basis`
lo declara. No se reinterpreta un snapshot `HFS-014-v1` como si tuviera precisión
bruta: se conserva histórico y su contrato anterior.

Se ordena por el DCR original; todos los empates exactos de ese valor permanecen.
Dos checks con display `1.000` y razones `.9999` / `1.0001` ya no empatan. No hay
tolerancia añadida al ranking. Todos los FAIL siguen presentes aun con INCOMPLETE;
ausencia de candidatos sigue como null/lista vacía. El resumen utiliza los mismos
vínculos de ejecución HFS-010 sin acreditar obligaciones nuevas.

`check_trace` pasa a `HFS-015-raw-v1`: demanda, capacidad y `value_raw` salen del
check original; la razón de interacción ya calculada también se conserva. Se
retiran `value_from_rule_memory`, `value_rounded_3dec`, `is_infinite` y las
sustituciones reconstruidas. Se publican fuente, unidad, diagnóstico numérico y
display. Las ecuaciones/factores permanecen en `calculations`, no se recalculan
desde la traza. Los helpers antiguos de inferencia/extracción permanecen sin
consumidores productivos, para no adelantar la reorganización del CLI.

## D1/E2: recomendaciones separadas del cumplimiento

El contenedor legacy `admissibility` conserva su ubicación por compatibilidad
de transporte. **Su contenido cambia** a `HFS-015-advice-v1`, con
`resistance=false`. Se retiran los booleanos `admissible`/D1/E2 y el texto SI/NO.
D1/E2 son objetos con fuente `User Note`, razón, límite recomendado, expresión,
aplicabilidad y uno de estos estados:

- `WITHIN_RECOMMENDATION`: datos disponibles dentro de la recomendación.
- `EXCEEDS_RECOMMENDATION`: advertencia; no FAIL resistente general.
- `UNKNOWN`: evidencia necesaria ausente; no equivale a incumplimiento ni a exención.
- `NOT_APPLICABLE`: no hay axial del signo pertinente o consta la excepción D1 de rods.

D1 usa **longitud fabricada / radio mínimo de la sección** y la excepción de rods.
E2 presenta `max(Kx Lx/rx, Ky Ly/ry)` para los dos ejes locales suministrados, más
la recomendación independiente de esbeltez fabricada. No se asume equivalencia
entre longitud fabricada y no arriostrada, ni que los ejes locales suministrados
sean todos los ejes principales/estados de estabilidad. Si falta un eje, la
advertencia E2 es UNKNOWN; se conserva el máximo parcial observado con sus ejes.

Entrada **opcional y aditiva**, consumida únicamente para estas recomendaciones:

```json
{
  "slenderness_advice_basis": {
    "fabricated_length": 4000,
    "least_radius": 10,
    "is_rod": false
  }
}
```

Longitudes/radios en mm, positivos y finitos; `is_rod` es booleano estricto.
Los datos son declaraciones externas, no verificación documental automática.
Ausentes quedan desconocidos. No se deduce rod desde forma circular/maciza.
Las cargas, factores, catálogo, geometrías resistentes y `tension_scope` no cambian.

Para ángulos comprimidos se recuerda separadamente E5(4) como condición de la
**Specification**, con `assessment=NOT_EVALUATED`: el Lc/r de la alternativa E5
no puede exceder 200 y deben cumplirse las demás condiciones E5. No se sustituye
ese dato por el KL/r general, ni se habilita la alternativa desde el aviso.
N08 y las carencias de E5 permanecen pendientes; no se implementa HFS-031.

CLI compacto y memoria consumen la misma función de dominio
`slenderness_recommendations`; no hay una segunda política de recomendaciones.
Ni estas advertencias ni sus entradas participan en checks resistentes, ranking,
agregación PASS/FAIL o plan independiente de cobertura.

## Diferencias y compatibilidad explícitas

- Cambian cifras publicadas antes redondeadas y sus snapshots: comparar originales
  o presentación deliberadamente, sin redondear el resultado de vuelta para decidir.
- I5 e I4 reciben ahora capacidades originales de checks I2/I4; se elimina ese
  redondeo intermedio, sin cambiar ecuaciones. Casos fronterizos pueden cambiar
  legítimamente de decisión por ese defecto previo; las diferencias se registran.
- Consumidores de `admissible`, SI/NO y campos retirados de `check_trace` deben
  migrar. La clave externa `admissibility` no significa autorización normativa.
- F-29 y los códigos de salida F-32 no cambian. No interpretar exit 0 como PASS.
- Las 72 regresiones HFS-014 continúan ejecutándose sin modificar sus expectativas;
  HFS-015 agrega casos donde el empate visual se separa por precisión original.
