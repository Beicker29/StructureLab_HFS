# Hoja de ruta

El repositorio contiene los capítulos D, E, F, G y H (H1, H2 en ángulos simples, H4) de ANSI/AISC 360-22, solo por LRFD. El capítulo
I se retiró (recuperable en el historial de Git, commit `d3a1b02`) y
se reincorporará con la misma estructura y oráculo independiente.

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
- Contraste con 48 casos de los AISC Design Examples v16.0 (D, E, F, G, H): coincidencia
  dentro de ±1 % salvo dos diferencias explicadas ([detalle](design-examples.md)).

## Siguiente

1. Revisión ingenieril de las decisiones de [D](chapter-d.md), [E](chapter-e.md), [F](chapter-f.md), [G](chapter-g.md) y [H](chapter-h.md);
   corregir en el catálogo la fila IPE 80 y completar los datos de IPE/HEA/HEB.
2. Aplicación web sobre `steel_design.execution.execute_payload`.
3. Incorporación del Capítulo I (miembros compuestos), con su oráculo independiente
   (`tests/oracles/chapter_i.py`) y su documento de alcance y decisiones (`docs/chapter-i.md`).
   Fuente en `a360-22w.pdf`: Specification, pp. 16.1-89 a 16.1-120, y Commentary del Capítulo I,
   pp. 16.1-418 a 16.1-472, como apoyo para interpretarla; revisar también las erratas del repositorio.
