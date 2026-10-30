# Hoja de ruta

El repositorio contiene los capítulos D y E de ANSI/AISC 360-22. Los capítulos
F, G, H e I se retiraron (recuperables en el historial de Git, commit `d3a1b02`) y
se reincorporan, uno por vez, con la misma estructura y oráculos independientes.

## Hecho

- Capítulo E para W, canal, PTE rectangular y redondo, ángulo simple (E5 + E4),
  ángulo doble (E6) y barras macizas, verificado con cálculos independientes
  ([detalle](chapter-e.md)).
- Comprobación de obligaciones independiente de la selección.
- Ejecución en memoria; CLI sin escritura por defecto.
- Memoria de cálculo en texto y PDF generada desde el resultado estructurado.
- Capítulo D (tracción): D2 y D3 con An y U del usuario, verificado con cálculos
  independientes en las seis familias ([detalle](chapter-d.md)).

## Siguiente

1. Revisión ingenieril de las decisiones de [chapter-e.md](chapter-e.md) y [chapter-d.md](chapter-d.md).
2. Reincorporar los capítulos siguientes por orden (F, G, H) con oráculos independientes.
3. Aplicación web sobre `steel_design.execution.execute_payload`.
