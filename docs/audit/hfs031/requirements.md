# HFS-031 — Matriz independiente de requisitos D/E

Fuente de requisitos: lectura de S22, PDF 100–117 (16.1-32–49), junto con
B4.1/B4.2/B4.3, PDF 87–93. No se obtiene esta matriz del router, del registro
ni de checks ejecutados. Los identificadores `DE-*` son filas documentales de
esta auditoría; no sustituyen N-ID, IDs de reglas ni cobertura operativa.
Interpretación por el agente, pendiente de revisión ingenieril humana.

S22 SHA-256 `25c4bf59b4c6fd00589e32a6ddac92cc9fd6be30dd5da07fc7c5f7fd475b2361`;
E25 `b2c8a9db622f583ebff013be1d1b4ffd3b992f7c7344d6cb815991ed400a1be6`;
E26 `d53ff5cc753cfcf6af70fd10355895b0120074527946f997084482fb626732e6`.
Se leyeron las tres páginas de erratas: ninguna modifica directamente una
ecuación D/E. E25 corrige L en Ap.7.3.1(b), referencia externa pertinente a E2;
E26 remite HSS a Tabla A3.1. La autenticación remota permanece pendiente.

Unidades SI: longitudes mm, áreas mm², inercias/J mm⁴, Cw mm⁶, E/G/Fy/Fu/Fe/Fn
MPa, Pn N, disponible kN (dividir N por 1000 una sola vez).
En toda E: φc=0,90, Ωc=1,67, disponible=φc·Pn o Pn/Ωc; demandas externas
deben corresponder al método. El programa no genera ni valida combinaciones.
`f(Fe)` significa Fy·0,658^(Fy/Fe) para Fy/Fe≤2,25; 0,877·Fe para Fy/Fe>2,25.
Es una abreviatura de lectura E3, no un nuevo evaluador productivo.

## Tracción y dominios externos

| Fila / fuente S22 (PDF) | Familia / condición y estado límite | Datos y requisito independiente |
|---|---|---|
| DE-D1 / D1 (100) | Todos los miembros a tracción | No hay límite máximo obligatorio de esbeltez. UN22 recomienda L fabricada/r mínimo≤300; exceptúa barras tipo rod. No usar KL/r como sustituto ni convertir recomendación en FAIL resistente. |
| DE-D2Y / D2(a), D2-1 (100) | Todos los miembros ordinarios en tracción axial; fluencia | Pn=Fy·Ag; φt=0,90, Ωt=1,67. Fy mínimo especificado y Ag físico. |
| DE-D2R / D2(b), D2-2 (101) | Rotura neta efectiva | Pn=Fu·Ae; φt=0,75, Ωt=2,00. Gobierna la menor resistencia **disponible** de fluencia/rotura. Soldaduras de tapón/ranura/filete en agujeros no autorizan ignorar la sección neta. |
| DE-D3A / D3-1 (101), B4.3 (92–93) | Todos; área efectiva | Ae=U·An. Ag total; An suma t·ancho neto. Agujero nominal+2 mm, cadenas diagonales con +s²/(4g), todos los caminos críticos; en ángulos g entre alas suma gramilajes menos t; HSS ranurado descuenta material retirado; metal de soldadura no repone An; sin agujeros An=Ag. |
| DE-D3MIN / D3 (101) | Secciones abiertas W/M/S/C/HP/T y ángulos simples/dobles | Puede usarse piso U≥Ag de elementos conectados/Ag total. No se aplica a HSS ni placas; requiere identificar elementos conectados. |
| DE-D3T1 / Tabla D3.1 caso 1 (102) | Carga transmitida a todos los elementos; excepto casos 4/5/6 | U=1; exige conexión correspondiente, no default universal. |
| DE-D3T2 / caso 2 (102) | Algunos elementos; todos salvo HSS; pernos o longitudinal+transversal | U=1−x̄/l. x̄ excentricidad de conexión, l longitud; alternativas 7 para W/M/S/HP y 8 para ángulos. |
| DE-D3T3 / caso 3 (102) | Solo soldadura transversal a parte de la sección | U=1; An solo de elementos directamente conectados. |
| DE-D3T4 / caso 4 y nota a (102) | Solo cordones longitudinales: placas, ángulos, canales con cordones en talones, T y elementos W conectados | U=[3l²/(3l²+w²)]·(1−x̄/l); l=(l1+l2)/2; cada l1/l2≥4 veces tamaño del cordón. Geometría de figura gobierna w/x̄. |
| DE-D3T5C / caso 5 (102) | HSS circular, cartela concéntrica única ranurada | x̄=R·sinθ/θ−tp/2; θ en radianes; U=[1+(x̄/l)^3,2]^−10. R, θ, tp, ranura y l según figura; no aplicar fórmula de sección abierta. |
| DE-D3T5R / caso 5 (102) | HSS rectangular, cartela concéntrica única ranurada | x̄=b−(2b²+tH−2t²)/(2H+4b−4t); U=1−x̄/l; b según figura, no asumir B exterior. |
| DE-D3T6 / caso 6 (102) | HSS rectangular, dos cartelas laterales | U=(B·UB+H·UH)/(H+B); UB=3l²/(3l²+B²), UH=3l²/(3l²+H²). B perpendicular y H paralelo al plano de conexión. |
| DE-D3T7 / caso 7 (103) | W/M/S/HP/T derivados | Ala con ≥3 pernos por línea longitudinal: U=0,90 si bf≥2d/3, 0,85 si menor. Alma con ≥4: U=0,70. Puede usarse mayor U calculado por caso 2. Para T, d del perfil original. |
| DE-D3T8 / caso 8 (103) | Ángulos simples/dobles | ≥4 pernos/línea: U=0,80; 3: U=0,60; <3 usar caso 2. Mayor U del caso 2 permitido. |
| DE-D4C / D4 (101) | Armados, elementos en contacto | Espaciado longitudinal de conectores remite J3.6. Datos de placas/perfiles, soldaduras/pernos y ambiente; externo, no sustituible por Ag agregado. |
| DE-D4T / D4 (101) | Lados abiertos de armados a tracción | Se permiten celosías, placas perforadas o presillas. Presillas largo≥2/3 distancia entre líneas de conexión; t≥distancia/50; paso longitudinal de pernos/cordones intermitentes en presilla≤150 mm. UN recomienda esbeltez entre conectores≤300. |
| DE-D5R / D5.1(a), D5-1 (103–104) | Miembro con pasador; rotura | Pn=Fu·2t·be; be=min(2t+16 mm, borde transversal real). φ=0,75, Ω=2. |
| DE-D5S / D5.1(b), D5-2 (103–104) | Pasador; rotura por cortante | Pn=0,6·Cr·Fu·Asf; Asf=2t(a+d/2); Cr=1 para dh−d≤1 mm, 0,95 para 1<dh−d≤2 mm; φsf=0,75, Ωsf=2. No extrapolar a holguras mayores. |
| DE-D5BY / D5.1(c/d) (104) | Pasador; aplastamiento/fluencia | Aplastamiento J7 y fluencia D2(a); mínimo con roturas. J7 no se audita aquí. |
| DE-D5DIM / D5.2(a–d) (104) | Pasador; detalle | Agujero centrado transversalmente; con movimiento a carga plena holgura≤1 mm si d<75 mm y≤2 mm si d≥75 mm; ancho≥2be+d; a≥1,33be. Corte a 45° permitido solo si área neta normal al corte suficiente. |
| DE-D6R / D6.1 (104) | Eyebar | D2, Ag del cuerpo; ancho de cálculo del cuerpo≤8t. No tratar cualquier barra rectangular como eyebar ordinario. |
| DE-D6DIM / D6.2(a–f) (105) | Eyebar; detalle | t uniforme sin refuerzo, cabeza circular concéntrica; radio de transición≥diámetro cabeza; d≥7/8 ancho cuerpo y dh−d≤1 mm; Fy>485 MPa exige dh≤5t; t<13 mm solo con tuercas externas para contacto ajustado; borde transversal>2/3 ancho cuerpo y para cálculo≤3/4. |
| DE-EXT / notas iniciales D/E (100/106) | Fatiga, conexiones, cargas combinadas, compuestos | D remite B3.11/Ap.3, J3 varillas roscadas, J4.1/J4.3 y H; E remite H, I2, J4.4. Registrar exclusión o evidencia externa, nunca declarar esos dominios comprobados por D2/E3. No se auditan F/G/H/I en HFS-031. |

## Compresión: clasificación, modos y condiciones

| Fila / fuente S22 (PDF) | Familia / condición | Requisito, ecuación y datos |
|---|---|---|
| DE-B41 / B4.1a, Tabla B4.1a (87–89) | Clasificación de **todos** los elementos comprimidos | Nonesbelto solo si cada λ≤λr. Ala I/T usa bf/2; canal/ángulo ancho completo; alma laminada altura libre menos filetes; T usa d total. I armado: λr=0,64√(kcE/Fy), kc=4/√(h/tw) limitado 0,35–0,76. No equiparar geometrías por etiqueta. |
| DE-B41CASES / Tabla B4.1a (89) | Casos 1…9 | (1) I laminada, canal, ala T y ángulos pareados en contacto continuo: 0,56√(E/Fy); (2) I armada: fórmula anterior; (3) ángulo simple/doble separado y otros no rigidizados:0,45√; (4) alma T:0,75√; (5) alma I doble simétrica/canal:1,49√; (6) pared HSS rect.:1,40√; (7) cubreplaca entre líneas:1,40√; (8) otros rigidizados:1,49√; (9) circular:0,11E/Fy. |
| DE-B42 / B4.1b/B4.2 (88,91–92) | HSS | Anchos planos entre radios; si radio desconocido se permite exterior−3t. t diseño=nominal para caja/A1065/A1085, 0,93nominal para otros HSS admitidos. No inferir especificación ASTM desde nombre comercial. |
| DE-E1 / E1 (106) | Todos en compresión | Pn mínimo de modos aplicables: flexión, torsión, flexotorsión, interacción local cuando procede; φ=0,90/Ω=1,67. Una sola resistencia positiva no demuestra suficiencia. |
| DE-E2 / E2 (108) | Todos | Lc=KL por modo, proveniente C o Ap.7; longitudes libres y factores con fundamento externo. UN: Lc/r preferible≤200 y L fabricada/r mínimo≤300; no límites resistentes generales. E25 corrige definición L de Ap.7.3.1(b) a longitud lateral no arriostrada. |
| DE-E3 / E3-1…4 (108–109) | Nonesbeltos; ejes principales pertinentes | Fe=π²E/(Lc/r)²; Fn=f(Fe); Pn=Fn·Ag. E=200000 MPa. Umbral Fy/Fe=2,25 (alternativa Lc/r=4,71√(E/Fy) publicada redondeada). Análisis elástico/Ap.7.2.3(b) son alternativas externas, no implícitas. |
| DE-E4A / E4-1/2/5…9 (109–110) | Doble simetría, torsión por centro de corte | Fe=(π²ECw/Lcz²+GJ)/(Ix+Iy); Fn=f(Fe), Pn=FnAg. E4 puede gobernar con L torsional mayor; también cruciformes/armados. G=77200 MPa. |
| DE-E4B / E4-3/5…9 (109–110) | Simetría simple, torsión por centro de corte | Con y simétrico: Fe=(Fey+Fez)/(2H)·[1−√(1−4FeyFezH/(Fey+Fez)²)]. Con x simétrico (canal), usar Fex (UN explicita transformación de etiquetas). Fez=(π²ECw/Lcz²+GJ)/(Ag·ro²); ro²=xo²+yo²+(Ix+Iy)/Ag; H=1−(xo²+yo²)/ro². |
| DE-E4C / E4-4 (110) | Sin simetría; ángulo cuando requiere flexotorsión | Menor raíz de (Fe−Fex)(Fe−Fey)(Fe−Fez)−Fe²(Fe−Fey)(xo/ro)²−Fe²(Fe−Fex)(yo/ro)²=0. Exige ejes principales y centro de corte consistentes. |
| DE-E4D / E4-10/11 (111) | I doble simétrica, arriostre lateral de eje menor desplazado | xa=0; ro²=rx²+ry²+ya²; Fe=[π²EIy/Lcz²·(ho²/4+ya²)+GJ]/(Agro²). |
| DE-E4E / E4-12/11 (111) | I doble simétrica, arriostre lateral de eje mayor desplazado | ya=0; ro²=rx²+ry²+xa²; Fe=[π²EIy/Lcz²·(ho²/4+(Ix/Iy)xa²)+GJ]/(Agro²). |
| DE-E4F / E4(f) (111) | Otros arriostres desplazados | Fe por análisis; no reutilizar sin más ecuación para centro de corte. |
| DE-E4UN / UN22 (111) | I doble simétrica / T y doble ángulo | Cw≈Iyho²/4 permitido para I; término Cw puede omitirse para T/dobles ángulos. Aproximación/permiso informativo, no exigencia Cw>0 universal. |
| DE-E5MODES / E5 (111) | Ángulo simple | Mínimo E3 o E7 y E4 según corresponda. Se puede omitir flexotorsión si b/t≤0,71√(E/Fy). En E7 ángulo, Fn se obtiene solo por E3 (116). |
| DE-E5COND / E5(1…5) (112) | Alternativa que ignora excentricidad | Carga por misma ala en ambos extremos; soldadura o≥2 pernos; sin cargas transversales intermedias; Lc/r de alternativa≤200; desigual requiere bl/bs<1,7. Si no se cumple, H; no inventar acciones/excentricidad. |
| DE-E5A / E5(a)(1), E5-1/2 (112) | Miembro individual o alma de cercha plana, vecinos al mismo lado; igual ala o ala larga conectada | s=L/ra; s≤80: Lc/r=72+0,75s; s>80:32+1,25s. L entre puntos de trabajo, ra geométrico paralelo al ala conectada; no max(KxLx/rx,KyLy/ry). |
| DE-E5AS / E5(a)(2) (112) | Desigual, ala corta conectada, contexto (a) | Sumar 4[(bl/bs)²−1] a rama anterior; Lc/r≥0,95L/rz (rz principal menor). |
| DE-E5B / E5(b)(1), E5-3/4 (112) | Alma de cercha espacial/cajón, vecinos mismo lado; igual o ala larga conectada | s≤75:60+0,8s; s>75:45+s. Mismas condiciones generales. |
| DE-E5BS / E5(b)(2) (112) | Desigual ala corta en contexto (b), bl/bs<1,7 | Sumar 6[(bl/bs)²−1]; Lc/r≥0,82L/rz. |
| DE-E6END / E6.1 (113) | Armado de dos perfiles conectados por pernos/cordones, o lados abiertos con placas perforadas/celosía | Extremos soldados o pernos pretensados superficies Clase A/B; deslizamiento no se resuelve con Ag total. |
| DE-E6A / E6-1 (113) | Modo produce deformación relativa y cortante en conectores intermedios, pernos snug-tight | sm=√(s0²+(a/ri)²). s0 esbeltez de conjunto en dirección del modo; a paso; ri radio mínimo de componente. Luego E3/E4/E7. Análisis más preciso es alternativa. |
| DE-E6B / E6-2a/b (113–114) | Conectores intermedios soldados o pretensados A/B | a/ri≤40: sm=s0; >40:sm=√(s0²+(Ki·a/ri)²). Ki=0,50 ángulos espalda con espalda;0,75 canales;0,86 otros. |
| DE-E6DET1 / E6.2(a/b) (114) | Dos o más componentes | a/ri≤0,75 esbeltez gobernante del conjunto. Extremos en apoyo: cordón largo≥ancho máximo o pernos paso≤4d por largo1,5 ancho máximo. Entre extremos: resistencia suficiente/J3.6; chapa exterior paso≤min(0,75t√(E/Fy),300mm), escalonados por línea≤min(1,12t√(E/Fy),450mm). |
| DE-E6DET2 / E6.2(c) (115) | Cubreplaca perforada | B4.1, agujero largo/ancho≤2; distancia libre longitudinal≥distancia transversal entre líneas; radio periferia≥38mm. UN permite caso7 y área neta en agujero máximo como opción conservadora. |
| DE-E6DET3 / E6.2(d) (115) | Celosía y presillas | Presillas en extremos/interrupciones; largo extremo≥distancia líneas, intermedio≥mitad; t≥distancia/50; cordón por línea≥1/3 largo; pernos paso≤6d y≥3 por segmento. |
| DE-E6DET4 / E6.2(e), UN (115–116) | Barras de celosía | Elemento entre uniones L/r≤0,75 conjunto; resistencia transversal celosía≥2% disponible compresión; L/r≤140 simple,≤200 doble; doble unida en cruces; L compresión=libre simple o0,70libre doble permitido. UN inclinación≥60°/45° preferida, doble/ángulos si separación>380mm. |
| DE-E7BASE / E7-1 (116) | Cualquier elemento esbelto B4.1 | Pn=Fn·Ae, mínimo modos aplicables; Fn de E3/E4, solo E3 para ángulos; Ae suma áreas efectivas. No equivale por definición a curva calculada con QFy multiplicada por Ag. |
| DE-E7WIDTH / E7-2…5 (116–117) | Esbeltos salvo HSS circular | Si λ≤λr√(Fy/Fn), be=b; si mayor be=b[1−c1√(Fel/Fn)]√(Fel/Fn). Fel=(c2λr/λ)²Fy; c2=[1−√(1−4c1)]/(2c1). E7.1 tabula c1/c2:0,18/1,31 rigidizados no-HSS;0,20/1,38 HSS rect.;0,22/1,49 otros. Reducir cada ancho por separado, Ae=Ag−Σ(b−be)t. |
| DE-E7ROUND / E7-6/7 (117) | HSS circular | D/t≤0,11E/Fy: Ae=Ag; 0,11E/Fy<D/t<0,45E/Fy: Ae=[0,038E/(FyD/t)+2/3]Ag. D exterior, t diseño. Igualdad al límite superior o fuera: no hay rama E7-7 autorizada. |

Las fórmulas tabuladas y E7-4 permiten diferencias pequeñas por redondeo de c2;
los oráculos identifican explícitamente qué representación utilizan. No se
alisan discontinuidades editoriales ni se limita Ae mediante un clamp inventado.
Las fórmulas de áreas de D3 y E7 comparten símbolo Ae pero no significado;
una no proporciona el área de la otra.

El [contraste](software-audit.md) registra por separado VERIFICADO / INCORRECTO /
NO IMPLEMENTADO / INDETERMINADO. Esta matriz no otorga acreditación al software.
