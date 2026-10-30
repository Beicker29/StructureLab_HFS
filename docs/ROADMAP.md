# Hoja de ruta

El repositorio contiene los capítulos D, E y F de ANSI/AISC 360-22, solo por LRFD. Los capítulos
G, H e I se retiraron (recuperables en el historial de Git, commit `d3a1b02`) y
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
- Capítulo F, etapa 1: W/I, canal compacto, PTE rectangular y redondo, barras
  (F2, F3, F6, F7, F8, F11, F13.1), verificado con cálculos independientes
  ([detalle](chapter-f.md)). Resultado por comprobación (axial, flexión x, flexión y).
- Capítulo F, etapa 2: F9 ángulos dobles (eje x) y F10 ángulos simples en ejes
  geométricos y principales (`Mw`, `Mz`), verificado con cálculos independientes.
- Contraste con 33 casos de los AISC Design Examples v16.0 (D, E, F): coincidencia
  dentro de ±1 % salvo dos diferencias explicadas ([detalle](design-examples.md)).

## Siguiente

1. Revisión ingenieril de las decisiones de [D](chapter-d.md), [E](chapter-e.md) y [F](chapter-f.md);
   corregir en el catálogo la fila IPE 80 y completar los datos de IPE/HEA/HEB.
2. Capítulo G (cortante), con oráculo independiente.
3. Capítulo H (interacción), que cierra las combinaciones con más de una demanda.
4. Aplicación web sobre `steel_design.execution.execute_payload`.
