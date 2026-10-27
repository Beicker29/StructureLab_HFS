# HFS-017 — Contrato de método de diseño

Base: `main`, `7234df8ba3de88db0f57de7f09e7d1b33c089d93`. Implementación para
revisión técnica independiente; no amplía dominios ASD. Véanse la
[matriz](../audit/hfs017/support-matrix.md) y el [informe](../audit/hfs017/report.md).

## Entrada y procedencia de demandas

`SteelCase.design_method` continúa aceptando únicamente `"LRFD"` o `"ASD"`.
Su valor por defecto sigue siendo **LRFD**, heredado y documentado en HFS-011.
Conviene declararlo expresamente en cualquier intercambio. No se infiere desde
el nombre del caso, la magnitud de la carga, el perfil ni el método nominal I.

`Pu`, `Mux`, `Muy`, `Vu`, `Vux`, `Vuy` y `Tu` son demandas externas finales,
en kN/kN·m y con la convención HFS-013. El productor debe suministrar las
combinaciones y los efectos de análisis compatibles con el método elegido:
demandas LRFD frente a φRn, demandas ASD frente a Rn/Ω. Seleccionar ASD **no
convierte demandas LRFD a ASD**, ni multiplica/divide cargas por 1,6. Tampoco
verifica las combinaciones, segundo orden, análisis global, procedencia de K/Cb,
norma de cargas, apoyos o materiales. Un cambio de método exige revisar o
recalcular externamente las demandas. Mantener los mismos números en los tests
cruzados aísla la conversión de resistencia; no acredita una combinación real.

`tension_scope.demand_reference` conserva su propósito de declaración externa,
sin validación automática de su veracidad. No se inventa un campo de procedencia
para todos los casos en este hito. `composite.nominal_strength_method` y
`composite.i5.method` son decisiones distintas de LRFD/ASD.

## Alcance público e interno

| Recorrido | Contrato |
|---|---|
| Motor y CLI, acero sin momentos | D/E/G/H según familia/dominio previo, LRFD o ASD; cobertura incompleta sigue INCOMPLETE |
| Motor y router, cualquier Mux/Muy no nulo con ASD | `ValidationError`, código `VALIDATION_ERROR`, capítulo F; no cálculo flexural |
| Motor y router, configuración compuesta ASD | Mismo error, capítulo I (F conserva prioridad si hay momentos) |
| Reglas F y `FlexureEvaluator`, llamados directamente | Solo LRFD, incluso con demanda cero; rechazo antes de nominales/resultados |
| Reglas I y helpers de resistencias disponibles/interacción I | Solo LRFD, incluso con demanda cero o sin rol activo |
| Reglas D/E/G/H y evaluadores propios directos | Método válido obligatorio antes de retornos inactivos; no sustituyen la validación física completa del motor |
| H1/H3 internos con momentos | Conservan F-43: Mc=0,90Mn o Mn/1,67. No autorizan una ruta pública de flexión ASD |
| `flexure_calc.evaluate_f*`, `composite_calc`, solvers nominales I | Cálculo nominal sin selección LRFD/ASD; no son verificaciones completas ni acreditan soporte público |

La política pública tiene una sola implementación:
`domain/design_methods.py::validate_method_scope`, usada por validación y router.
`require_case_method` protege reglas, evaluadores y helpers que pueden invocarse
sin pasar por el motor. La repetición de llamadas es defensiva; la decisión de
soporte no se duplica en cada consumidor ni en CLI.

`design_methods.DesignMethod` es ahora la definición canónica ligera;
`models.DesignMethod` sigue importándola y conserva el acceso existente.
Un `SteelCase` válido contiene ese enum. Una llamada directa con un caso
alterado mediante `model_copy/model_construct` y un string crudo, aun `"ASD"`,
recibe error de contrato: debe validar de nuevo `SteelCase`. No se muta el caso
para repararlo. El motor conserva la revalidación Pydantic de HFS-011.

## Conversores y errores

Los conversores D/E/G/H conservan sus firmas, unidades y aceptación histórica de
tokens sin sensibilidad a mayúsculas. Rechazan método vacío, desconocido,
`None`, booleano, número o espacios añadidos con `ValueError`, aun si la
resistencia nominal es cero. Antes podían tratar esos valores como ASD o
devolver cero antes de examinar el método. F1 ya era estricto y mantiene su
contrato de tokens en mayúsculas y su wrapper explícito LRFD.

Los errores de dominio son estructurados, por ejemplo:

```json
{
  "type": "ValidationError",
  "code": "VALIDATION_ERROR",
  "message": "Chapter F flexural checks are implemented only for LRFD in the current scope.",
  "details": {
    "field": "design_method",
    "chapter": "F",
    "design_method_received": "ASD",
    "design_method_required": "LRFD"
  }
}
```

CLI conserva stderr JSON y exit 1 para entradas rechazadas. Los fallos
estructurales de cálculos ejecutados mantienen su contrato previo, incluido
F-32 (FAIL puede salir con exit 0). Un rechazo de método no se transforma en
un check PASS ni se captura como obligación satisfecha.

## Resistencias, resultados y migración

D2 conserva factores distintos para fluencia y rotura. E1 conserva los suyos.
Cada módulo posee su conversión y su traza; no se unifican D2/E1/F1/G1/H3/I
por compartir 0,90 o 1,67. G2.1(a) conserva 1,00/1,50 frente a 0,90/1,67 de
G1. I mantiene sus factores LRFD locales detrás de las guardas; sus diferencias
normativas y las reservas sobre nominales/interacciones no se resuelven aquí.
No cambia el orden aritmético de las conversiones válidas.

El resultado global y CLI identifican el método en `coverage.method`; la
memoria detallada conserva también el input. Las trazas activas D2 añaden
`details.memory.design_factor` (en memoria CLI,
`memory.clause_results[].calculations.design_factor`): método, φ u Ω activo,
factor inactivo `null` y expresión. E/F/G/H/I mantienen sus trazas. Los factores
inactivos que G/H muestran como referencia no se ejecutan simultáneamente.
`TensionEvaluator.evaluate` añade `design_method` a su dict interno.
Los placeholders directos de demanda cero no calculan capacidad ni constituyen
una acreditación de cobertura; conservan el formato anterior tras validar método.

Cambios incompatibles intencionales:

1. Clientes de reglas F/I directas que usaban ASD, incluso sin demanda, reciben
   error en vez de capacidad LRFD o PASS inactivo.
2. Consumidores de conversores que dependían de fallback ASD deben enviar un
   método válido. Los strings desconocidos nunca son un tercer método.
3. Clientes del router directo encuentran ahora el mismo bloqueo F/I del motor.
4. Deserializadores cerrados deben admitir los nuevos metadatos D2 y los campos
   adicionales `field/chapter` de errores. No cambia el JSON válido de entrada,
   el esquema numérico HFS-015 ni la versión de sus valores/display.

Los doce ejemplos actuales no contienen la traza D2 nueva y permanecen
literalmente iguales. Los casos dirigidos de tracción verifican la adición en
motor/evaluador/CLI/memoria. No se añade acreditación a HFS-010 ni se elimina
ninguna exclusión. HFS-039 sigue siendo responsable de habilitar ASD por dominios.
