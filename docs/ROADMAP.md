# Hoja de ruta

El repositorio contiene los capítulos D, E, F, G, H (H1, H2 en ángulos simples, H4) e I (etapas 1 y 2) de
ANSI/AISC 360-22, solo por LRFD. El Capítulo I anterior sigue en el historial de Git (commit `d3a1b02`).

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
- Capítulo G (cortante): G2.1 sin rigidizadores, G3, G4, G5 y G6, verificado con
  cálculos independientes ([detalle](chapter-g.md)). Barras y platinas macizas por G4 (DG-4).
- Capítulo H, etapa 1: H1.1, H1.2 (con amplificación de Cb opcional) y H4, verificado
  con cálculos independientes ([detalle](chapter-h.md)).
- Capítulo H, etapa 2: H2 para ángulos simples en los puntos A, B y C, con compresión fuera de E5,
  verificado con cálculos independientes y los ejemplos E.14B y F.11C.
- Capítulo I, etapa 1: PTE rellenos, W embebidos y vigas compuestas (I2, I3, I4, I5 con H1.1 e I5-1, I8.2), verificado
  con cálculos independientes ([detalle](chapter-i.md)).
- Capítulo I, etapa 2: Método 2 de I5 (Commentary), anclajes de componentes (I8.3) y muros de placas planos (I1.6, I2.3,
  I3.5, I4.4, I5(c)), verificado con cálculos independientes.
- Contraste con 23 casos de AISC Design Guide 6 y 38 ([detalle](design-guides.md)).
- Contraste con 66 casos de los AISC Design Examples v16.0 (D, E, F, G, H, I): coincidencia
  dentro de ±1 % salvo dos diferencias explicadas ([detalle](design-examples.md)).

## Siguiente

1. Revisión ingenieril de las decisiones de [D](chapter-d.md), [E](chapter-e.md), [F](chapter-f.md), [G](chapter-g.md), [H](chapter-h.md) e [I](chapter-i.md);
   corregir en el catálogo la fila IPE 80 y completar los datos de IPE/HEA/HEB.
2. Aplicación web sobre `steel_design.execution.execute_payload`.
3. Capítulo I, etapa 3: transferencia de carga (I6).
4. Contenidos candidatos de AISC Design Guide 6 y 38, en el orden de [design-guides.md](design-guides.md).
