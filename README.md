# StructureLab HFS

Motor de diseno estructural en acero basado en AISC 360-22 (`a360-22w.pdf`).

## Estado actual

- Resumen CLI/memoria: gobernantes observados por DCR publicado, conservando empates y fallos. Lotes vacíos rechazados antes de ejecutar/publicar. [Contrato y migración HFS-014](docs/contracts/hfs014-summary-bundles.md).
- Arquitectura por capas (`codes`, `domain`, `sections`, `engine`).
- Capitulo D (tension) implementado.
- Capitulo E (compresion) implementado para E3, E4, E5 y E7.
- Capitulo F implementado para F2, F3, F4, F5, F6, F7, F8, F10 y F11.
- Capitulo G: evaluaciones parciales G2/G4/G5/G6; G3 y G6 de canales bloqueados por correspondencia direccional no acreditada.
- Capitulo H: evaluaciones parciales H1/H3 en HSS; condiciones y bloqueos en [HFS-013](docs/audit/hfs013/report.md). Ejecutar un check no acredita cobertura completa.
- Capitulo I implementado (alcance actual) para I1, I2, I3-1, I3-3, I3-4 e I4 en miembros compuestos `ENCASED_MEMBER`, `FILLED_MEMBER` y `COMPOSITE_BEAM` (sin CPSW).
- Traccion con D3 estricto (`Ae = U*An`) para todos los perfiles.
- Secciones macizas custom por JSON (`SOLID_CIRCULAR`, `SOLID_RECTANGULAR`) con alcance axial (D2/E3).
- Datos faltantes o cobertura no acreditada impiden PASS: se informa INCOMPLETE o un error estructurado según la etapa.
- Los checks axiales reportan clasificacion de elementos (`non_slender`/`slender`) en `checks[].details.element_classification`.
- Flexion en alcance actual: solo `LRFD`; cuando hay `Mux` y `Muy` se reportan checks por eje (sin interaccion biaxial H1).

## Estructura

```text
data/sections.xlsx               Catalogo de perfiles
examples/*.json                  Casos CLI de referencia
src/steel_design/codes           Formulas normativas puras
src/steel_design/domain          Reglas, validaciones, enrutamiento, errores
src/steel_design/sections        Carga y modelos de secciones
src/steel_design/engine.py       Pipeline principal
src/steel_design/run.py          CLI
tests/                           Suite unitaria e integracion
docs/aisc_360_22_traceability.md Matriz de trazabilidad normativa
```

## Instalacion

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Contratos de entrada (HFS-011)

Se rechazan campos desconocidos (por ejemplo `loads.Mxu`), números no finitos,
cadenas/booleanos usados como magnitudes y entradas fuera de dominio. `loads: {}`
no es válido; las componentes omitidas en una carga parcial declaran cero.
`Vu` no se calcula ni sobrescribe: un `Vu` no nulo no puede coexistir con
`Vux`/`Vuy` no nulos. STUD exige `Fu`, `Rg` y `Rp` explícitos.

Revisar [contrato, defaults y migración JSON](docs/contracts/hfs011-inputs.md)
y [pruebas y riesgos residuales](docs/audit/hfs011/report.md).
HFS-002 fue aceptada como matriz documental y diagnóstico; no como validación
normativa exhaustiva. Entradas válidas no garantizan cobertura completa;
consultar el contrato HFS-010 siguiente. PASS no certifica cumplimiento global AISC.

## Integridad del catálogo (HFS-016)

Los nombres se consultan con una política única de mayúsculas y espacios ASCII.
Una identidad repetida, incluso con propiedades iguales, produce
`AMBIGUOUS_SECTION` al seleccionarla (CLI: exit 1), sin elegir una fila.
`HEA 100` y `PTEXXMM` quedan bloqueados; los demás perfiles siguen disponibles,
sujetos a la validación física de HFS-011. El Excel se conserva sin correcciones.
Consultar [contrato y migración del repositorio](docs/contracts/hfs016-catalog.md)
y [informe, pruebas y límites](docs/audit/hfs016/report.md). HFS-016 fue concluida
dentro de su alcance; no acredita la calidad integral del catálogo.

## Cobertura y resultados (HFS-010)

El motor construye obligaciones desde la matriz HFS-002 antes de consultar el
router. El estado global ahora admite **INCOMPLETE**: cero checks, omisiones,
condiciones desconocidas o rutas no acreditadas no producen PASS. Los checks
resistentes y sus números se conservan; `known_failures` identifica los FAIL
conocidos aun cuando la cobertura sea incompleta.

En esta entrega solo puede acreditarse cobertura completa para tracción axial
de macizos custom ordinarios, con `tension_scope` explícito y ambos estados D2
evaluados. Los demás dominios permanecen incompletos o mantienen errores de no
soporte. No añadir declaraciones para obtener PASS sin evidencia de ingeniería.
CLI conserva exit 0 cuando devuelve un resultado: es obligatorio leer `status`.

Ver [contrato y migración](docs/contracts/hfs010-coverage.md) e
[informe, estados de los 12 ejemplos y riesgos](docs/audit/hfs010/report.md).
HFS-010 se entrega para revisión; no implementa HFS-012/013/014 ni acredita G1.

## Uso CLI

```bash
python -m src.steel_design.run examples/w_shape_case.json
python -m src.steel_design.run examples/rectangular_hss_case.json
python -m src.steel_design.run examples/circular_hss_case.json
python -m src.steel_design.run examples/composite_encased_case.json
python -m src.steel_design.run examples/composite_filled_rectangular_hss_case.json
python -m src.steel_design.run examples/composite_filled_circular_hss_case.json
python -m src.steel_design.run examples/composite_beam_case.json
```

Salida por consola: resumen de checks (sin `details`).

Por cada ejecucion, el CLI crea carpeta por ejemplo y corrida:
- `results/<NOMBRE_DEL_JSON_DE_ENTRADA>/<TIMESTAMP>/`

Control desde el input JSON (opcional):
- `output.write_results_json` (`true` por defecto).
- Si es `false`, no se guarda JSON detallado (solo salida en terminal + diagrama de interaccion cuando aplique).

Salida detallada por ejecucion (cuando `output.write_results_json = true`): JSON en `results/<NOMBRE_DEL_JSON_DE_ENTRADA>/<TIMESTAMP>/<TIPO_PERFIL>/`.
Incluye `input`, `output` completo y `memory` tipo memoria de calculo:
- `memory.global_summary`: capacidad global gobernante (minima entre clausulas) y clausulas criticas.
- `memory.clause_results`: desarrollo por clausula con variables intermedias, factores de diseno y capacidad.

## Ejemplos

Casos actualmente ejecutables (exit code 0):

- `examples/w_shape_case.json`
- `examples/channel_case.json`
- `examples/single_angle_case.json`
- `examples/rectangular_hss_case.json`
- `examples/circular_hss_case.json`
- `examples/solid_circular_case.json`
- `examples/solid_rectangular_case.json`
- `examples/composite_encased_case.json`
- `examples/composite_filled_rectangular_hss_case.json`
- `examples/composite_filled_circular_hss_case.json`
- `examples/composite_beam_case.json`

Casos de error esperado (exit code != 0):

- `examples/double_angle_case.json` (faltan `J` y `Cw` en hoja `2L` para E4)

## Nota de entrada para E4

En `factors` se pueden incluir offsets de arriostramiento:

- `xa` (mm): bracing offset distance along x-axis
- `ya` (mm): bracing offset distance along y-axis

## Nota de entrada para traccion (D3 estricto)

Si `loads.Pu < 0`, en `connection` se requiere:

- `An` (mm2)
- `U` (0 < U <= 1)

El motor calcula `Ae = U*An` y valida que `Ae <= Ag`.

## Nota de entrada para flexion (Capitulo F)

Para evaluar flexion (`Mux` o `Muy`):

- `design_method` debe ser `LRFD`.
- se reportan checks por eje para `Mux` y `Muy`; la interaccion biaxial aun no esta implementada.
- para angulo simple (`F10`) en `connection` se requiere:
  - `angle_flexure_axis`
  - `angle_ltb_restraint`
  - `angle_max_tension_location` cuando `angle_flexure_axis = geometric_axis`.

## Nota de entrada para cortante (Capitulo G)

- Si se entregan `Vux` y/o `Vuy`, el motor evalua cortante por eje.
- `Vux` es cortante del plano de `Mux` (fuerza local y); `Vuy`, del plano de `Muy` (fuerza local x).
- `Vu` legacy es alias escalar de `Vux`, nunca resultante vectorial. No combinar representaciones activas.
- Para perfiles `RECTANGULAR_HSS`, el espesor de calculo es `tdes` (mm).
- Convención canónica, signos y migración de adaptadores: [ejes y cargas HFS-013](docs/contracts/hfs013-axes.md).

## Nota de entrada para torsion y combinaciones (Capitulo H)

- Se usa `loads.Tu` en `kN-m` como torsion requerida.
- `H3-1` evalua torsion HSS con datos y dominio acreditados: rectangular requiere C explícito; circular no infiere longitud real desde Kz/Lz.
- `H3-2` aplica H3-6 con máximo de cocientes direccionales y término axial-flexión lineal. La alternativa H1/G cuando Tr/Tc <= 0,20 queda pendiente.
- Para perfiles no-HSS con `Tu != 0`, registra H3.3 pendiente y conserva checks independientes; resultado INCOMPLETE. Leer cobertura, no solo exit del CLI.

## Nota de entrada para miembros compuestos (Capitulo I)

- Activacion explicita por `composite.role`:
  - `ENCASED_MEMBER`
  - `FILLED_MEMBER`
  - `COMPOSITE_BEAM`
- Metodo nominal por caso (`composite.nominal_strength_method`):
  - implementados: `PLASTIC`, `ELASTIC`
  - no implementados (fail-hard): `STRAIN_COMPAT`, `EFFECTIVE_STRAIN`
- `composite.concrete.fc` y `composite.concrete.wc` son obligatorios (sin defaults ocultos).
- Interaccion `I5` (axial + flexion) disponible en `ENCASED_MEMBER` y `FILLED_MEMBER` cuando `Pu != 0` y (`Mux` o `Muy`) != 0.
- Selector de metodo para `I5`:
  - `composite.i5.method = METHOD_1_H1_1`
  - `composite.i5.method = METHOD_2_PLASTIC_INTERACTION` (usa tablas 6-2/6-3/6-4 del Steel Construction Manual 16th para puntos A/E/C/D/B)
  - `composite.i5.method = METHOD_4_DIRECT_INTERACTION`
- Si corre `I5` con `METHOD_2`, se exporta un diagrama de interaccion en `results/<INPUT>/<TIMESTAMP>/<PROFILE>/`.
- Alcance actual fuera de implementacion:
  - `Composite Plate Shear Walls (CPSW)`
  - torsion en Chapter I
