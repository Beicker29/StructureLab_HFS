# HFS-002 — Matriz independiente de aplicabilidad

Estado: propuesta para revisión ingenieril sobre [S22 local](hfs002-sources.md); erratas pendientes. Es la fuente documental de requisitos **independiente del router**. El [contraste](hfs002-implementation.md) usa los mismos IDs N para informar implementación/evidencia sin redefinir la exigencia. Ningún ID N es un nuevo check ejecutable. Una fila puede requerir varios estados límite, ejes, posiciones o etapas.

## Cómo resolver un caso sin completar vacíos por suposición

1. Identificar familia física, fabricación, simetría, ejes, sección/conexión, material, etapa y combinación de carga; evaluar N01–N03. `W` o `HSS` por sí solo no acredita estas condiciones.
2. Seleccionar por la tabla de familias y **cada componente** de demanda; aplicar las condiciones de las filas N. Unir los requisitos, incluidas interacciones y complementos. No escoger solo la carga de mayor magnitud.
3. Registrar cada condición como verdadera, falsa o desconocida. Desconocida significa **pendiente**, nunca no aplicable. Una alternativa normativa permitida satisface su grupo solo si se justifican todos sus requisitos; no es necesario ejecutar todas las alternativas.
4. Consultar por N-ID el contraste: implementación parcial no satisface toda la fila. Si falta un dato, una regla, una validación exigida o una disposición estudiada, el resultado futuro será `INCOMPLETE` con motivo. Si el fenómeno excede el alcance declarado, se enumera como exclusión; si invalida una hipótesis interna o el usuario solicita evaluarlo, bloquea ese alcance.

**PASS** expresará únicamente cumplimiento del alcance verificable declarado, con sus hipótesis y exclusiones; nunca certificación global automática AISC 360-22. No hay cambios a los estados actuales en HFS-002.

Convenciones de esta matriz: N axial (compresión/tracción indicadas expresamente), Mx/My momentos alrededor de ejes principales/geométricos identificados; V en plano de alma o transversal, conservando dirección física; T torsión. No se presupone equivalencia entre esta convención y `Vux/Vuy` del JSON (F-08/11). Para círculo también deben conservarse las componentes y el criterio combinado; no sustituirlas automáticamente por checks independientes.

## Familias × demanda × condición

Todas las filas agregan N01–N03 y N35 cuando exista el desencadenante. «Compuesto» de acero armado no significa compuesto acero–concreto.

| Familia física / configuración | Tracción | Compresión | Mx / My | Cortantes | T / combinaciones |
|---|---|---|---|---|---|
| I doblemente simétrica laminada (W y equivalentes, propiedades acreditadas) | N04, N05 si armada | N06; N07 si aplica; N10 si elementos esbeltos | N11 + N12/13/14/15 según alma/ala; N16 menor; N22 | N23 alma, N27 transversal; N28 aberturas | N31 no HSS; N29 axial-flexión o biaxial; N32 agujeros |
| I fabricada o monosimétrica | N04/05 | N06/07/09/10 según construcción | N11 + N14/15 y N16; N22. No usar clasificación laminada automáticamente | N23/27/28 | N29 si simetría y restricción elegibles; en otro caso H2 de N29; N31/32 |
| Canal | N04/05 | N06/07/10 | N11+N12 solo mayor compacto; mayor fuera de ese dominio **pendiente de solución por análisis**, no F3/F4 automático; N16 menor; N22 | N23/27/28 | N29 condicionado a restricción de flexión, N31/32 |
| Ángulo simple | N04 | N08, N06/07/10 en sus dominios | N11+N20 por ejes, restricción y signo de tensiones | N24 por ala resistente | H2 de N29 cuando hay biaxialidad o N+M, N31 |
| Dos ángulos armados | N04+N05 | N09 + N06/07/10; distinguir contacto/separadores | N19 solo plano de simetría; otro eje/configuración pendiente de análisis, N11/N22 | N24 solo como contribución de cada ángulo con reparto acreditado; no inferir conjunto completo | N29 H1/H2 según simetría/restricción, N31 |
| HSS rectangular/cuadrado | N04 | N06/10; no activar torsional E4 por etiqueta sin condición | N11+N17 por cada eje | N25 por pared/dirección | N30 torsión; N29/N30 interacción |
| HSS circular | N04 | N06/10 con límite D/t | N11+N18, D/t < 0,45 E/Fy | N26 por dirección con Lv pertinente | N30; N29/N30 interacción |
| Barras macizas rectangulares/redondas | N04 | N06 | N11+N21; LTB solo rectangular mayor en dominio | Requisito de resistencia presente; solución analítica específica **pendiente**, no G5 de tubo hueco | N29/N31; no aceptar falta de regla como N/A |
| W encasado en concreto | N36+N37 tracción | N36+N37 compresión | N36+N39 por eje/etapa | N41 alternativa encasada por dirección | N42 combinación; torsión compuesta pendiente, no H3 HSS vacío |
| HSS relleno de concreto | N36+N38 tracción | N36+N38 compresión | N36+N40 por eje | N41 relleno | N42; torsión compuesta pendiente |
| Viga de acero + losa conectada | Axial fuera del alcance actual; resolver N42 y papel del miembro | Ídem | N36+N43, momentos positivo/negativo y etapa; menor/biaxial no extrapolar modelo de losa | N41 acero solo + N28 si aberturas | N42 si combinación; torsión pendiente |

N44 (transferencia/anclajes) se agrega a los tres roles compuestos según cómo se introducen fuerzas. Un material fuera de I1.3 conduce a evaluar Apéndice 2 cuando corresponda; esta matriz no habilita esa alternativa. Tees, cajas soldadas, secciones asimétricas arbitrarias, muros compuestos, diafragmas, colectores, barras roscadas, miembros con pasadores/ojales y sistemas sísmicos no forman parte del soporte declarado actual: N34/N35/N45 registran la frontera, no la inexistencia de requisitos.

## Datos comunes, clasificación y método

En todas las filas resistentes: combinación y demandas del mismo método, unidades, posición/segmento, propiedades con procedencia y Fy/Fu/E según uso. Unidades objetivo para trazabilidad: mm, mm², mm³, mm⁴, mm⁶, MPa, N/Nmm internos o conversión explícita a kN/kNm. No sumar dimensiones distintas.

LRFD/ASD se rigen por B3-1/B3-2. Códigos en la columna método: **D** = fluencia 0,90/1,67 y rotura 0,75/2,00; **E** = 0,90/1,67; **F** = 0,90/1,67; **G** = 0,90/1,67 salvo G2.1(a) 1,00/1,50; **T** = 0,90/1,67. Cada pareja es φ/Ω, no dos multiplicadores. **H** usa capacidades disponibles D/E/F/G/T del método, sin factor universal adicional. **IC** = compresión encasada/rellena 0,75/2,00; **IT/IF** = tracción/flexión compuesta 0,90/1,67. El método está disponible en la norma aunque el software lo rechace.

B4.1a se aplica en compresión; B4.1b en flexión por elemento y eje. Para I laminada/canal: casos 1/5 axial y 10/15 mayor, 13 menor; **b del canal es ancho completo**, no medio ancho de I (B4.1a(b), F6.2). I fabricada: caso 2 y 11, y alma 15/16 según simetría. Ángulo: 3 axial y 12 flexión; 2L: 1 si contacto continuo o 3 si separadores para alas correspondientes. HSS rectangular: 6 axial, 17 ala y 19 alma flexión; circular: 9 axial, 20 flexión. Barras macizas no tienen paredes esbeltas de HSS. I1.1a/b clasifica rellenos por separado y contiene **máximos permitidos**, no solo fronteras compacto/no compacto. La geometría y fabricación desconocidas impiden elegir fila.

## Catálogo canónico de verificaciones requeridas

Las referencias son S22 salvo `UN` explícito; páginas exactas en el [localizador](hfs002-sources.md). «Ambos» = LRFD y ASD admitidos normativamente, no implementados necesariamente. Las entradas listadas son requisitos técnicos, no afirmaciones de campos existentes. Su detalle por subrama se conserva en la cláusula citada; si una rama no está estudiada no puede declararse cubierta.

| ID | Disposición / estado o requisito | Condición de aplicabilidad y exclusión | Entradas adicionales necesarias | Método |
|---|---|---|---|---|
| N01 | B1–B3.3; B3-1/2, A3 | Todo caso: cargas y combinación compatibles con análisis, material y etapa | Origen de demandas/combinaciones, grado/norma material, geometría, método, unidades | Ambos; B3 |
| N02 | B4.1–B4.3, tablas B4.1a/b | Elementos comprimidos por N o M; espesor HSS según fabricación; áreas netas cuando procedan | Anchos normativos, espesores, radios/esquinas, laminado/soldado, norma ASTM, agujeros, simetría y ejes | Ambos; requisito previo |
| N03 | C1–C3, E2, F1; remisiones Ap.1/6/7/8 | Estabilidad del sistema/miembro y arriostramiento; alternativa de análisis debe justificarse | P-Δ/P-δ, imperfecciones, rigideces, método, L/K por modo, Lb, diagrama de M para Cb, apoyos/restricción de giro | Ambos; C1 usa nivel LRFD o 1,6 ASD |
| N04 | D2-1/2; D3-1 y tabla D3.1 | N tracción: fluencia bruta y rotura neta; U depende de transmisión a elementos conectados | Ag, An, U con configuración/longitud de conexión y área conectada | D |
| N05 | D4; J3.6 por remisión | Tracción en miembro de varias piezas; no basta sumar áreas | Separación/conectores, placas de enlace/celosía, espesores, juntas | Ambos; detallado |
| N06 | E1, E3-1 a 4 | Compresión sin elementos esbeltos: pandeo flexional por modos/ejes pertinentes; con esbeltos pasar a N10 | Ag, radios principales, longitudes efectivas, E/Fy | E |
| N07 | E4-1 a 12, E4(f) | Simetría y longitudes/restricciones que hagan aplicable torsión/flexotorsión; ángulo b/t > 0,71√(E/Fy); offsets exigen rama propia | J,Cw,Ix,Iy,ro,H,centro de cortante, Lcz, offsets y simetría; análisis cúbico para asimétrico | E |
| N08 | E5(a)/(b); E5-1 a 4 | Ángulo en compresión: alternativa de excentricidad despreciable solo con cinco condiciones y configuración de celosía; si no, N29 | Ala conectada, tornillos/soldadura, cargas intermedias, relación alas <1,7, L/ra, rz, esbeltez efectiva ≤200 | E + H si no cumple |
| N09 | E6.1/E6.2; E6-1/2 | Compresión armada: deslizamiento/deformación relativa, esbeltez modificada y conexión/detallado; alternativa análisis justificada | Componentes, a, ri, Ki, tipo/apriete de conexión, celosías/placas; modos globales | E; requisitos de conexión adicionales |
| N10 | E7-1 a 7, tabla E7.1 | Elementos esbeltos: Fn de modo global y área efectiva; circular solo dentro de E7.2, D/t <0,45E/Fy | Anchos efectivos por elemento, espesor, Ag, Fn E3/E4; ángulo usa Fn E3 en E7 | E |
| N11 | Introducción F, F1(a)–(d), F1-1 | Flexión simple: plano principal por centro de cortante o giro restringido; monosimétrica en doble curvatura revisar ambas alas | Cb/Lb con procedencia, diagrama y punto de aplicación, restricción lateral/torsional | F |
| N12 | F2.1/2, F2-1 a 8 | I doble simétrica/canal, alma y alas compactas, eje mayor: fluencia y LTB; Lb≤Lp excluye LTB | Zx,Sx,ry,Iy,J,Cw,ho; c específico canal/I, E/Fy, Lb/Cb | F |
| N13 | F3.1/2, F3-1/2, remisión F2.2 | I doble simétrica, alma compacta, alas no compactas/esbeltas: LTB y pandeo local ala; **no canal** | Datos N12, b/t, h/tw, kc, λp/λr | F |
| N14 | F4.1–4, F4-1 a 17 | I doble simétrica alma no compacta o I monosimétrica alma compacta/no compacta: fluencia ala comprimida, LTB, pandeo local, fluencia ala traccionada si Sxt<Sxc | Sxc/Sxt, Iyc/Iy, hc/hp, geometría de alas/alma, rt,J, Lb,Cb, Rpc/Rpt | F |
| N15 | F5.1–4, F5-1 a 10 | I doble/monosimétrica con alma esbelta centrada en alas: mismos cuatro estados con Rpg; N22 siempre | N14, aw, kc, h/tw, límites de proporción | F |
| N16 | F6.1/2, F6-1 a 4 | I/canal eje menor: fluencia y pandeo local ala si no compacta/esbelta; sin trasladar LTB mayor | Zy,Sy,b/tf correcto por familia, E/Fy | F |
| N17 | F7.1–4, F7-1 a 7 y F7-10 a 13 locales | HSS rectangular/caja por eje: fluencia, local ala/alma y LTB según dominio. Web esbelta+ala esbelta no resuelto por F7.3(c); UN señala límites y ausencia LTB cuadrado/menor | B/H,b/h,t, S/Z por eje, Se si ala esbelta, Ag,J, radio transversal, Lb/Cb; distinción HSS/caja | F |
| N18 | F8.1/2, F8-1 a 4 | Circular D/t <0,45 E/Fy: fluencia y local si no compacto/esbelto; igual al límite no está incluido | Diámetro exterior, t diseño, S/Z y clase | F |
| N19 | F9.1–4, F9-1 a 19; remisión F10.3 | Tee/2L **plano de simetría**: fluencia, LTB, local alas y alma según tensión/compresión; no generalizar a eje no simétrico | Orientación/signo, Z/S, Lb,Iy,J,d,b/t, ala/pata comprimida | F |
| N20 | F10.1–3, F10-1 a 8; H2 | Ángulo: ejes principales salvo permisos geométricos; LTB salvo restricción continua/menor principal; local si punta comprimida | Alas iguales/desiguales, βw, rz, Ag,t,Lb,Cb≤1,5 en F10-4, Sc y signo/toe, restricción | F; H2 combinado |
| N21 | F11-1 a 5 | Macizos: fluencia; LTB solo barra rectangular mayor cuando Lbd/t² >0,08 E/Fy; circular/menor excluidos | d,t,S,Z,Lb,Cb, eje | F |
| N22 | F13.1–4; F13-1 a 7 | Agujeros en ala traccionada: rotura si FuAfn<YtFyAfg; proporciones I/alas/alma, cubreplacas y vigas armadas si presentes | Afn/Afg,Yt, Sx, Iyc/Iy, a/h,h/tw, aw; conectores, cubreplacas, reparto de cargas | F; detallado adicional |
| N23 | G2.1–4; G2-1 a 19 | I/canal cortante alma: fluencia/pandeo; G2.1 base permitida; acción de campo de tracción G2.2/3 alternativa condicionada; comprobar rigidizadores usados | d,tw,h, laminado, a,kv; para alternativa: panel interior/extremo, alas, rigidizadores, M y resistencias | G, excepción solo G2.1(a) |
| N24 | G3-1, G2.2 Cv2 | Cada ala de ángulo/tee que resiste cortante; 2L requiere justificar reparto y ensamblaje, no una equivalencia nominal | b,t, dirección, Fy/E, Cv2 kv=1,2, fuerzas por componente | G |
| N25 | G4-1 | HSS rectangular/caja: fluencia/pandeo paredes en dirección de cortante; otras simétricas con geometría G4 aplicable | h resistente,t diseño, Aw,Cv2 kv=5; no intercambiar ejes | G |
| N26 | G5-1/2a/2b | HSS circular: fluencia/pandeo cortante | Ag,D exterior,t diseño, Lv=distancia de cortante máximo a cero; no asumir Lv=L de columna | G |
| N27 | G6-1 | Cortante menor de miembro mono/doble simétrico **sin torsión**, cada elemento resistente | bf,tf,b/t según I/canal, Cv2 kv=1,2, reparto de fuerza | G |
| N28 | G7 | Aberturas de alma en viga acero o compuesta | Geometría/posición abertura, refuerzo, V/M local, análisis de resistencia | Ambos; análisis requerido, sin ecuación única |
| N29 | H1.1/2, H1-1a/b; H1.3 opción; H2-1 | N+Mx/My, o biaxial sin N (introducción F remite H1–H3): H1 doble simétrica o monosimétrica restringida a ejes geométricos; H2 otras y alternativa permitida. H1.3 solo dominio restringido | Pc de D/E, Mcx/Mcy de F, ejes, signos; H2 tensiones en puntos críticos y ejes principales. H1.3 exige laminado compacto, Lcz≤Lcy y Mry/Mcy<0,05 | H; tracción H1.2 remite H1-1a/b, **H1-2 es Pey**, no interacción |
| N30 | H3.1/2, H3-1 a 6 | HSS con T: fluencia/pandeo torsional y combinación. Tr/Tc≤0,20 permite H1 omitiendo efectos torsionales; >0,20 exige H3-6. Rectangular h/t≤260 en última rama | C torsional,L,D/t o h/t,Fy/E; Pc,Mc por eje,Vc por dirección,Tc. Usar **max(Vrx/Vcx,Vry/Vcy)** | T y H |
| N31 | H3.3, H3-7 a 9 | No HSS con torsión y tensiones combinadas: fluencia normal/cortante y pandeo | Esfuerzos normales/tangenciales por torsión/alabeo y demás cargas, restricciones, Fcr por análisis | T |
| N32 | H4-1; D2(b), F13.1 | Agujeros en alas bajo axial+flexión mayor: cada ala con tensión, signos en punto considerado | Fuerzas en posición agujero, áreas netas, Pc rotura, Mc rotura/alternativa Mp según H4 | H, factores de D/F |
| N33 | D1 y UN D1; E2 y UN E2 | Recomendaciones 300 en tracción y 200/300 en compresión, no límites resistentes generales. E5≤200 **sí** condición de esa alternativa | Longitud fabricada/efectiva y radio; contexto de uso | Ambos; aviso, no FAIL automático |
| N34 | D5/D6; F12-1 a 4 | Pasadores/ojales y asimétricas no ángulo: fuera del producto; no asignar reglas de barra ordinaria sin detalle | Geometría especial, conexión, tensiones/pandeo por análisis | Ambos; F o D específico |
| N35 | B3.4–13, B5–B8; remisiones J/K,L–N, Ap.3–5 | Conexiones, fuerzas concentradas, servicio, fatiga, fuego, corrosión, integridad, tolerancias y fabricación según uso | Declaración de alcance/condiciones, evidencias externas y revisión de remisiones | Ambos; detalle no estudiado aquí |
| N36 | I1.1–5, I2.1a/2a, I3.3a/4a; tablas I1.1a/b | Todo compuesto: materiales, ≥1% acero cuando exigido, detallado y método; encasado sin local solo si cumple requisitos; relleno con máximos de esbeltez | fc,wc,Fy,Fysr, normas, geometría, barras/recubrimiento/estribos, método I1.2, etapas, EI y estabilidad | Ambos; ACI referido sobre cargas LRFD; no mezclar clasificaciones B/I |
| N37 | I2.1b/c; I2-2 a 8 | Encasado doble simétrico en compresión: pandeo flexional con EI efectivo; tracción: fluencia acero+barras; transferencia/detallado adicional | As,Asr,Ac,Is,Isr,Ic,Ec,K/L por eje; piso acero E permitido | IC / IT |
| N38 | I2.2b/c; I2-9 a 14 | Relleno doble simétrico: compresión por clase I y pandeo; tracción acero+barras | N37, λp/λr/máximo, forma circular/rectangular y Fn de local; piso E permitido | IC / IT |
| N39 | I3.3a/b | Encasado en flexión: seleccionar método permitido (elástico compuesto, plástico acero solo, plástico compuesto/compatibilidad con anclajes); detallado y control de tracción según caso | M por eje, etapas/apuntalamiento, sección/barras, anclajes y condición ACI | IF |
| N40 | I3.4b; I3-5a/b y remisión I2-10/11 | Relleno en flexión: plástico compacto, interpolación no compacto, primer flujo con límite local esbelto | Clase por eje, Mp,My, Fn, distribución de tensiones y fc; detallado I3.4a/c | IF |
| N41 | I4.1(a/b/c), I4.2 I4-1, I4.3 | Encasado: alternativa acero solo, RC solo o acero+estribos; relleno: contribución acero+concreto; viga losa: acero solo G | V por dirección, área resistente, estribos/ACI si usados; relleno Mu/Vu/d máximos del miembro y Kc por clase/forma | G para acero solo; RC/mixto 0,75/2,00; relleno 0,90/1,67 |
| N42 | I5(a/b), I5-1a/b, tabla I5.1; I1.2, C | N+M compuestos: elegir ruta según clase; encasado/compacto H1.1 o I1.2, no compacto/esbelto H1.1 o I1.2d o I5-1. Biaxialidad sin N debe justificarse, no dos PASS aislados | Pc con longitud, Mc por eje, clase/método, cp/cm/csr cuando corresponda, estabilidad y tratamiento biaxial | IC/IF e interacción del método; no factor universal |
| N43 | I3.1a/b; I3.2a–d; I3-1a/b/c, I3-2a/b | Viga con losa: ancho efectivo, etapa previa al 75% fc si sin puntales, M positivo/negativo, deck y transferencia; negativo acero solo o alternativa con sus requisitos | Luz, espaciamiento/borde, losa, deck/orientación, anclajes por región, shoring, cargas de construcción, barras desarrolladas; M requerido | IF; etapa acero F; transferencia nominal conforme I3.2d |
| N44 | I2.1d/2d, I6.1–4, I8 | Introducción de fuerza en encasado/relleno y anclajes de compuestos; no sustituir por I3-1a/b/c de vigas | Fuerza introducida a acero/concreto/ambos, región, mecanismos, conectores y detallado; capacidades de anclajes | Ambos; factor específico por mecanismo (p.ej. adherencia I6.3c 0,50/3,00); ramas I8 pendientes de detalle completo |
| N45 | I1.6/I2.3/I3.5/I4.4/I5(c)/I7; Ap.2; AISC341 A1 | Muros/diafragmas/alta resistencia/sismo u otro alcance especial: registrar y derivar a estudio específico | Sistema y alcance solicitados, materiales y contexto de edificio | Fuera del soporte; no declarar N/A por no tener código |

## Casos de decisión verificables en revisión

- W doble simétrica compacta, compresión y Mx: N01–03, N06, N07 solo si condiciones, N11/12 y N29; N22/32/35 según detalles. No basta E3+F2. Sin clasificación no se decide N12 frente a N13–15.
- Canal no compacto con Mx y My: N16 no resuelve el mayor. Su rama mayor permanece pendiente; el caso es incompleto aunque F6 pase. No adjudicar F3 a canal para tapar el hueco.
- HSS rectangular con T y cortante: N25+N30; si Tr/Tc>0,20 entra H3-6 con máximo de cocientes. Capacidad desconocida de un eje requerido impide evaluar; capacidad del otro no la reemplaza.
- W o HSS con Mx/My y N=0: F uniaxial no demuestra combinación; N29 debe resolver interacción. Ángulo requiere H2 expresamente (F10). Para compuestos, N42 exige resolver la trayectoria, sin extrapolación automática.
- Relleno con Mx únicamente: N36+N40+N44 según transferencia, más estabilidad/condiciones externas; una comprobación de cuantía de barras no satisface N40.

Estos ejemplos son razonamiento de aplicabilidad, no resultados numéricos del motor. La resolución de ramas pendientes es inequívoca a efectos de seguridad: **no hay evidencia para evaluar/cubrir ese caso**, por lo que se informa incompletitud y la información/estudio requerido. No se afirma que todas las disposiciones de AISC hayan sido estudiadas.
