# StructureLab HFS

Motor de diseno estructural en acero basado en AISC 360-22 (`a360-22w.pdf`).

## Estado actual

- Arquitectura por capas (`codes`, `domain`, `sections`, `engine`).
- Capitulo D (tension) implementado.
- Capitulo E (compresion) implementado para E3, E4, E5 y E7.
- Capitulo F implementado para F2, F3, F4, F5, F6, F7, F8, F10 y F11.
- Capitulo G (cortante) implementado para G2, G3, G4, G5 y G6.
- Capitulo H implementado para H1, H3-1 y H3-2 en perfiles HSS.
- Capitulo I implementado (alcance actual) para I1, I2, I3-1, I3-3, I3-4 e I4 en miembros compuestos `ENCASED_MEMBER`, `FILLED_MEMBER` y `COMPOSITE_BEAM` (sin CPSW).
- Traccion con D3 estricto (`Ae = U*An`) para todos los perfiles.
- Secciones macizas custom por JSON (`SOLID_CIRCULAR`, `SOLID_RECTANGULAR`) con alcance axial (D2/E3).
- Politica estricta: si una regla aplicable no puede evaluarse por datos faltantes, el caso falla con error estructurado.
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
normativa exhaustiva. HFS-010 sigue pendiente: entradas válidas no garantizan
cobertura completa y un PASS actual no certifica cumplimiento global AISC.

## Integridad del catálogo (HFS-016)

Los nombres se consultan con una política única de mayúsculas y espacios ASCII.
Una identidad repetida, incluso con propiedades iguales, produce
`AMBIGUOUS_SECTION` al seleccionarla (CLI: exit 1), sin elegir una fila.
`HEA 100` y `PTEXXMM` quedan bloqueados; los demás perfiles siguen disponibles,
sujetos a la validación física de HFS-011. El Excel se conserva sin correcciones.
Consultar [contrato y migración del repositorio](docs/contracts/hfs016-catalog.md)
y [informe, pruebas y límites](docs/audit/hfs016/report.md). HFS-016 está entregada
para revisión; no acredita el catálogo completo ni habilita HFS-010.

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
- Si solo se entrega `Vu` (legacy), se interpreta como demanda de cortante en eje mayor (`Vx`).
- Para perfiles `RECTANGULAR_HSS`, el espesor de calculo es `tdes` (mm).

## Nota de entrada para torsion y combinaciones (Capitulo H)

- Se usa `loads.Tu` en `kN-m` como torsion requerida.
- `H3-1` evalua torsion pura para `RECTANGULAR_HSS` y `CIRCULAR_HSS`.
- `H3-2` evalua combinacion de torsion con axial/flexion/cortante.
- Para perfiles no-HSS con `Tu != 0`, el motor retorna error estructurado (H3-3 fuera de alcance actual).

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
