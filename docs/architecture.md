# Arquitectura

```text
src/steel_design/
├── models.py                    entrada (SteelCase), resultado (DesignResult), tipos y política de entrada
├── errors.py                    errores estructurados
├── sections/                    catálogo: loader.py (hojas/cabeceras del Excel → Section, unidades),
│                                models.py, repository.py, geometry.py (macizos), identity.py (nombres, AISC_Manual_Label 2L)
├── codes/aisc_360_22/
│   ├── tension.py               fórmulas puras D2-1, D2-2, D3-1 y factores φt
│   ├── flexure.py               fórmulas puras F2–F13.1, Se de F7 y límites λp/λr de B4.1b
│   └── compression.py           fórmulas puras E1, E3–E7 y límites λr de B4.1a
├── domain/
│   ├── tension.py               capítulo D: fluencia y rotura, gobierno por resistencia de diseño φt·Pn
│   ├── flexure.py               capítulo F: clasificación B4.1b, sección F por familia y eje, estados límite
│   ├── compression.py           capítulo E: clasificación, selección, ejecución y resistencia gobernante
│   ├── coverage.py              obligaciones de D, E y F derivadas del texto, independientes
│   └── validation.py            validación de caso y sección
├── engine.py                    una comprobación por demanda (D/E por Pu, F por Mux/Muy/Mw/Mz) → estado
├── execution.py                 ejecución en memoria de un caso o un lote (para CLI y web)
├── reporting.py                 memoria de cálculo (texto y PDF) a partir del resultado, sin recalcular
└── run.py                       CLI (JSON en stdout; archivos solo con --output, --report, --pdf → results/ ignorado)
```

## Flujo

1. `engine.run(case)` valida el caso (`E = 200000 MPa`) y obtiene la sección del
   catálogo o la construye (macizos).
2. `domain/coverage.required_obligations` enumera los estados límite que el capítulo
   E exige para esa familia y esas longitudes. No importa `domain/compression`.
3. `domain/compression.compression_strength` clasifica (B4.1a), selecciona los modos
   aplicables, calcula cada uno con `codes/aisc_360_22/compression.py` y conserva
   todos; gobierna el menor Pn (E1).
4. `coverage.discharge` cruza obligaciones y modos. Si falta alguno, el estado es
   `INCOMPLETE`; si no, `PASS` o `FAIL` según `Pu / disponible`.

Los ángulos dobles leen su ángulo simple componente a través de la función
`catalog` que el motor pasa a `compression_strength` y `flexure_strength` (J del componente en F9).

Un dominio sin datos o sin decisión ingenieril lanza `RuleNotImplementedError` o
`IncompleteSectionDataError`; el motor lo convierte en `INCOMPLETE` con el motivo.

## Responsabilidades (una fuente de verdad por concepto)

| Concepto | Propietario |
| --- | --- |
| Ecuaciones D2-1, D2-2, D3-1, φt | `codes/aisc_360_22/tension.py` |
| Ecuaciones E3-2…E7-7, φc, λr | `codes/aisc_360_22/compression.py` |
| Estados límite de tracción y modo gobernante | `domain/tension.py` |
| Ecuaciones F2–F13.1, φb, λp/λr (B4.1b), Se de F7 | `codes/aisc_360_22/flexure.py` |
| Sección de F por familia y eje, estados límite de flexión | `domain/flexure.py` |
| Coherencia de datos del catálogo (r = √(I/A), S = I/c) | `domain/validation.py` |
| Elementos B4.1a por familia, selección de modos, E7 por modo | `domain/compression.py` |
| Estados límite obligatorios (comprobación independiente) | `domain/coverage.py` |
| Hojas, cabeceras y unidades del catálogo; b/tdes, h/tdes, D/t de PTE | `sections/loader.py` |
| Decisión PASS/FAIL/INCOMPLETE | `engine.py` |
| Presentación de la memoria de cálculo | `reporting.py` |

Ninguna interfaz (CLI, futura web) calcula capacidades: todas llaman a `engine`.

## Cómo añadir o modificar una disposición

1. Leer el artículo en `a360-22w.pdf` y las erratas; anotar edición, ecuación,
   condiciones y unidades. Distinguir Specification, User Note y Commentary.
2. Añadir la fórmula como función pura en `codes/aisc_360_22/compression.py`,
   devolviendo el identificador de ecuación. Una función por formulación.
3. Seleccionarla en `domain/compression.py` (familia, condiciones, datos requeridos).
   Si faltan datos o una decisión, bloquear con error estructurado.
4. Si cambia qué es obligatorio, actualizar `domain/coverage.py` desde el texto
   normativo, no desde la selección.
5. Añadir el caso al oráculo `tests/oracles/chapter_e.py` (cálculo independiente),
   regenerar `tests/fixtures/chapter_e/reference.json` y ejecutar las pruebas.
6. Actualizar [chapter-e.md](chapter-e.md).
