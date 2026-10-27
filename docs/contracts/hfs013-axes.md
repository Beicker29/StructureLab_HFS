# HFS-013 — Convención de ejes, cargas y dominios G/H3

Estado: implementado para revisión técnica; no certificación global AISC.
La definición siguiente aclara la asociación histórica conservada por el
software. No intercambia datos del usuario ni gira automáticamente ejes.

## Una convención para todos los consumidores

Miembro prismático con z longitudinal. Para W/canal/HSS rectangular, x es el
eje centroidal paralelo a las alas/ancho b y y atraviesa la altura/alma h.
Mux es flexión alrededor de x; Muy alrededor de y. Un círculo usa dos ejes
ortogonales declarados por el análisis externo. No se infiere una rotación de
perfil ni se ordenan b/h por magnitud para cortante. Para torsión rectangular,
H3.1 exige expresamente el **lado plano más largo**, de ahí max(h,b).

| Entrada | Unidad | Significado físico y signo |
|---|---|---|
| Pu | kN | Positivo compresión, negativo tracción. La capacidad dependiente se elige por ese signo |
| Mux | kN·m | Momento alrededor del eje local x, plano de flexión mayor declarado |
| Muy | kN·m | Momento alrededor del eje local y, plano de flexión menor declarado |
| Vux | kN | Cortante **asociado al plano Mux**, fuerza a lo largo de y local |
| Vuy | kN | Cortante **asociado al plano Muy**, fuerza a lo largo de x local |
| Vu | kN | Alias escalar legacy de Vux; fuerza local y. Nunca √(Vux²+Vuy²), máximo de componentes ni una fuerza sin dirección |
| Tu | kN·m | Momento torsor alrededor de z longitudinal; no es fuerza cortante |

Los sufijos de Vux/Vuy nombran el **plano de flexión**, no la dirección de un
vector fuerza. Esto conserva la ruta histórica: Vux/Vu→alma h/G2 o paredes h/G4;
Vuy→alas/G6 o paredes b/G4. La justificación física es el producto vectorial:
un brazo longitudinal z y una fuerza y producen momento alrededor de x; una
fuerza x produce momento alrededor de y. El signo del equilibrio depende de
la cara de corte elegida; no se deriva ni se modifica aquí. Los signos de las
entradas permanecen en el contrato y la traza; G/H3 usan magnitudes absolutas,
con Pu distinguiendo tracción/compresión. H3-6 exige cocientes positivos.

Por tanto, un exportador que llame Vx a la **fuerza** local x debe mapearla
explícitamente a Vuy, después de verificar su sistema de ejes y signos. No basta
copiar nombres. El análisis externo debe resolver posición de carga, centro de
cortante, torsión por excentricidad, combinaciones y efectos de segundo orden.
El motor no acredita esos hechos por leer un JSON. Usuarios anteriores que
interpretasen Vux como fuerza x deben revisar sus entradas; la documentación
antigua «x direction» era ambigua. No se han reinterpretado silenciosamente
sus números cambiando las paredes resistentes.

`Loads.validate_load_representation` sigue rechazando Vu no nulo junto con
cualquier componente direccional no nula. Omisiones de cargas siguen siendo
cero según HFS-011; no datos desconocidos. `domain/actions.py` es la fuente
ejecutable de demandas G/H3 y su metadata. Los adaptadores futuros deben usar
el mismo contrato. El capítulo I conserva sus algoritmos anteriores y su
cobertura pendiente; sus agregaciones de cortante no quedan validadas por
aclarar este contrato.

## Datos, fórmulas y bloqueos

Fuente: Specification ANSI/AISC 360-22 local, G1/G3–G6 (PDF143,148–149;
16.1-75,80–81), H3 (PDF153–155;16.1-85–87); detalle y hash en el
[informe](../audit/hfs013/report.md). Se distingue la User Note de C de los
requisitos de Specification.

| Verificación | Datos y decisión ejecutable |
|---|---|
| G2 W/canal | Ruta mayor histórica, Aw=d·tw. G2.1(a) solo en W con límite aplicable. No se modifica la resistencia existente; G7/posición de carga/fabricación quedan pendientes |
| G3 ángulos | Bloqueada: b/t único no demuestra qué ala resiste la componente, orientación ni reparto en doble ángulo |
| G4 HSS rectangular | Aw=2·h_resistente·tdes, h para plano x y b para plano y; kv=5. Sin sustituir una pared ausente por la otra ni tdes por t nominal |
| G5 HSS circular | OD y tdes explícitos. Lv es distancia de cortante máximo a cero; Lx/Ly de pandeo no la representan. Si G5-2b≥0,6Fy se demuestra fluencia sin conocer Lv; en otro caso queda pendiente. No se añade un campo Lv en este hito |
| G6 W | Dos alas iguales del dominio simétrico declarado, sin torsión. Se conserva el cálculo existente; verificación completa de carga/apoyos sigue pendiente |
| G6 canal | Bloqueada: la capacidad previa de una sola ala no representa una resistencia total acreditada sin reparto de cortante. No se inventa factor dos ni se añade formulación |
| H3.1 rectangular | tdes, ambos lados planos y C en mm³ explícitos. No reconstruir B/H exteriores como b+3t/h+3t. Coeficiente H3-5 corregido a 0,458π²; límite de su rama h/t≤260 |
| H3.1 circular | OD/tdes; C explícito o aproximación conservadora de la User Note π(D−t)²t/2. No sustituir C por 2J/D por mera disponibilidad de J. L es longitud real del miembro, no Kz·Lz. H3-2b≥0,6Fy permite probar fluencia sin L; de otro modo queda pendiente |
| H3.2, Tr/Tc>0,20 | (Pr/Pc+Mrx/Mcx+Mry/Mcy) + (max(Vrx/Vcx,Vry/Vcy)+Tr/Tc)². Se conserva demanda/capacidad de cada plano, sin redondear antes de combinar |
| H3.2, Tr/Tc≤0,20 | Permiso para alternativa H1 omitiendo efectos torsionales, no check resistente PASS. La alternativa completa H1/G no está acreditada: se registra pendiente; los checks independientes siguen ejecutándose |
| Torsión no HSS y cortante macizo | Sin resistencia implementada: diagnóstico explícito y obligación pendiente. No utilizar G5 para barra maciza; preservar otros checks |

Identidad que evita inventar longitudes: si a(L)≥0 y b≥c, entonces
min(max(a(L),b),c)=c para cualquier L>0. G5 usa b=0,78E/(D/t)^(3/2),
H3 circular b=0,60E/(D/t)^(3/2), c=0,6Fy. Es una demostración de una rama
independiente de L, no un default de longitud. Cuando no se cumple, la
incertidumbre no se reemplaza por una capacidad artificialmente conservadora.

`domain/evaluators/hss_shear.py` produce la capacidad bruta y su traza para G4/G5
y H3. La interacción nunca consume capacidades ya redondeadas de CheckResult.
Fórmulas y factores permanecen en `codes`; no hay un motor normativo alternativo.

## Salidas y migración

Los checks G incluyen `input_component`, `signed_demand_kN`, `bending_axis`,
`force_direction`, `axis_convention` y unidad. La memoria H3 conserva pares por
eje, cocientes y eje gobernante. `Vr_kN`/`Vrc_kN` son ahora el **par gobernante**,
que puede no contener ni la máxima fuerza ni la máxima capacidad. Los ejes
inactivos no necesitan capacidad y se representan como null, no un máximo
ficticio. Cambian nombres/trazas de checks HSS; no identificarlos solo por texto.

Un check bloqueado no se transforma en capacidad cero ni en FAIL resistente:
su error queda en `coverage.evaluation_errors`, las obligaciones quedan
pendientes y el caso INCOMPLETE. Algunos antiguos errores globales ahora dan
resultado parcial INCOMPLETE/exit 0; el consumidor debe leer el estado y la
cobertura. Las salidas FAIL parciales ejecutadas se conservan. No cambia la
semántica general del CLI ni se implementan HFS-014/015.

No se habilita nuevo dominio de PASS global. Pc/Mc de D/E/F, H1, geometría,
calidad de catálogo, ejes de ángulos, cortante circular oblicuo sin torsión,
detalles G7 y alcance de análisis mantienen pendientes de validación. **F-31
continúa abierto**: ni esta convención ni G6 implementan la resistencia mayor
faltante del canal. HFS-012 conserva sus funciones de selección y pruebas.
