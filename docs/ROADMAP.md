# Hoja de ruta

El repositorio contiene únicamente el capítulo E de ANSI/AISC 360-22. Los
capítulos D, F, G, H e I se retiraron (recuperables en el historial de Git,
commit `d3a1b02`) y se reincorporarán, uno por vez, con la misma estructura.

## Hecho

- Capítulo E para W, canal, PTE rectangular y redondo, ángulo simple (E5 + E4),
  ángulo doble (E6) y barras macizas, verificado con cálculos independientes
  ([detalle](chapter-e.md)).
- Comprobación de obligaciones independiente de la selección.
- Ejecución en memoria; CLI sin escritura por defecto.

## Siguiente

1. Revisión ingenieril de las decisiones D-1 a D-12 de [chapter-e.md](chapter-e.md).
2. Memoria de cálculo legible (texto/PDF) a partir del resultado estructurado.
3. Reincorporar capítulos por orden (D, F, G, H) con oráculos independientes.
4. Aplicación web sobre `steel_design.execution.execute_payload`.
