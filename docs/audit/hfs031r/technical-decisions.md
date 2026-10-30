# HFS-031R — consultas y decisiones técnicas

Estado: trabajo en curso. Estas decisiones no acreditan por sí mismas un
dominio, ni sustituyen requisitos obligatorios de ANSI/AISC 360-22.
Fuentes locales S22/E25/E26 por hash en [sources.json](evidence/sources.json).

## TD-01 — c₂ de E7-4

S22 p.16.1-48 define c₂ con E7-4; la tabla E7.1 (p.16.1-49) imprime
1,31/1,38/1,49. Commentary p.16.1-368 explica que c₂ depende únicamente
de c₁. Los valores tabulados redondeados pueden producir be>b cerca del
cambio de rama. Consulta respondida: **«Usar c₂ de E7-4 sin redondear»**.

Se utiliza c₁ de la tabla y c₂ sin redondear; el código emplea la forma
algebraica racionalizada 2/(1+√(1−4c₁)). Los oráculos históricos HFS-031
con c₂ tabulado se conservan. El banco suplementario calcula E7-4 con
Decimal a 60 dígitos; no importa funciones productivas.

## TD-02 — familias y selección previa a las ecuaciones

El usuario precisa que el catálogo contiene PTE rectangular/redondo, además
de W/IPE/HEA/HEAB, 2L y L; solicita definir primero los subcapítulos aplicables.
`RECTANGULAR_HSS` y `CIRCULAR_HSS` son los identificadores internos existentes
de geometrías tubulares; no se renombra el catálogo ni se infiere su norma de
fabricación por el nombre comercial.

Mapa indicado para confrontación normativa:

| Familia | Sin elementos esbeltos | Con elementos esbeltos |
| --- | --- | --- |
| PTE rectangular/redondo | E3 | E7 |
| W/IPE/HEA/HEAB | E3/E4 | E7 (modos E3/E4) |
| 2L | E6 y E3/E4 | E6 y E7 |
| L | E3/E4/E5 | E5/E7 |

Cada fila requiere comprobar las condiciones particulares: E4 por simetría,
restricciones y longitudes; exención de E4 para L con b/t≤0,71√(E/Fy);
E5 para conexión excéntrica y su alternativa; E6 por montaje/conectores;
E7 con Fn de E3 solamente para L. La lista no autoriza ejecutar E3/E4 sobre
Ag como sustituto de E7, ni ejecutar las ramas simplificadas de E5 sin datos.
El alcance literal de E4 para condiciones especiales en perfiles cerrados
debe conservarse visible; no se declara resuelto únicamente por E1.1.

## TD-03 — límite de área efectiva circular

S22 E7-7 (p.16.1-49) produce Ae/Ag = 0,038/(Fy·D/t/E)+2/3.
En 0,11·E/Fy < D/t < 0,114·E/Fy resulta Ae>Ag; el límite derecho
de la primera frontera da 167/165 ≈1,0121212. Commentary E7.2
(p.16.1-369) describe una reducción de área. E25/E26 revisadas no
modifican esta ecuación. La búsqueda en fuentes técnicas AISC no proporcionó
una aclaración específica del intervalo; no se atribuye a AISC un límite
explícito que no aparece en la ecuación.

Alternativas consultadas: fórmula literal, límite Ae≤Ag o espera de aclaración.
Respuesta del usuario: **«Limitar Ae a Ag, documentando el criterio»**.
Se implementa min(Ae_ecuación,Ag), conservando ambos valores y el indicador
de límite aplicado. Es un criterio ingenieril explícito y conservador respecto
de la fórmula literal, pendiente de confirmación normativa independiente.
No se presenta como errata oficial ni como autorización para alterar otros
límites. D/t=0,45·E/Fy sigue fuera del dominio de E7-7.

## Datos que no se suponen

No se equiparan espesor nominal y de diseño ni diámetro interior/exterior.
No se reconstruyen conexiones E5, contacto 2L, H, restricciones laterales o
propiedades principales a partir del nombre comercial. Una decisión pendiente
suspende únicamente el cálculo afectado; no constituye una exclusión definitiva.
