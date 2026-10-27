# HFS-017 — Matriz de soporte LRFD/ASD

Fecha: 2026-10-27. Base main `7234df8`; implementación local HFS-017 para
revisión. Requisitos desde [HFS-002](../../normative/hfs002-applicability.md),
N01–N45; contraste del código actual, no una nueva matriz de aplicabilidad.

**I = implementada** dentro del alcance limitado acreditado previamente;
**P = pendiente de acreditación**, aunque haya cálculo ejecutable;
**B = bloqueada** explícitamente. En columnas LRFD/ASD se clasifica la ruta
pública. Una lista de familias o estados expande todas las combinaciones de
esa fila; no expresa equivalencia física de fórmulas. La columna de ejecución
distingue existencia de código de acreditación. P no significa NOT_APPLICABLE.
No existe acreditación integral AISC de una familia o un capítulo.

Familias: W (etiqueta de catálogo, no prueba de fabricación), CHANNEL,
SINGLE_ANGLE (L), DOUBLE_ANGLE (2L), RECTANGULAR_HSS (RHS), CIRCULAR_HSS (CHS),
SOLID_RECTANGULAR (SR), SOLID_CIRCULAR (SC). «Todas» incluye estas ocho.
FILLED_RECTANGULAR/CIRCULAR son alias legacy de macizos; no del rol compuesto
FILLED_MEMBER. Roles compuestos: núcleo W encasado (ENC), HSS relleno (FILL-R/C),
W+losa (BEAM). No se introducen equivalencias de catálogo.

## Miembros de acero

| Capítulo / referencia independiente | Familia / dominio | Estado límite o condición | LRFD | ASD | Ejecución y límite |
|---|---|---|---|---|---|
| A/B/C; N01–03 | Todas y roles I | Material, combinaciones, análisis, estabilidad, arriostramiento, clasificación | P | P | Datos externos y validaciones parciales; no análisis global C ni validación de cargas |
| D2/D3; N04 | SR/SC, tirante ordinario puro con todas las declaraciones HFS-010 | Fluencia bruta; rotura neta | I | I | Dominio acotado preexistente; An/U externos; dos factores distintos |
| D2/D3; N04 | Todas fuera del dominio acreditado anterior, alias legacy | Fluencia bruta; rotura neta | P | P | Dos reglas ejecutables; declaraciones/conexiones completas pendientes |
| D4; N05 | 2L y otros miembros armados | Conectores/detallado | P | P | Sin verificación; D2 no lo sustituye |
| D5/D6; N34 | Pasadores/ojales, no representados como configuración propia | Estados específicos de tracción | P | P | Fuera del alcance declarado; no inferir barra ordinaria |
| E3; N06 | Todas, alias legacy | Pandeo flexional x/y | P | P | Conversión E1 operativa; auditoría nominal/dominio pendiente |
| E4; N07 | W/CHANNEL/2L/RHS/CHS | Pandeo torsional y flexotorsional según condiciones | P | P | E1 operativo; offsets/simetría/modos no acreditados completamente |
| E4/E5; N07–08 | L | Pandeo torsional/flexotorsional y alternativa de ángulo | P | P | E5 ejecutable, no todas condiciones; E4 no tiene regla propia de L; F-36 abierto |
| E6; N09 | 2L y otros armados | Pandeo de conjunto/conectores | P | P | Ausente; E3/E4/E7 no acreditan E6 |
| E7; N10 | W/CHANNEL/2L/L/RHS/CHS esbeltos | Área efectiva/pandeo | P | P | E1 separado, nominal QFy/Ag discrepante F-35 sigue pendiente |
| F1; N11 | Todas con Mux o Muy | Condiciones generales de flexión | P | B | ASD público bloqueado antes de selección |
| F2; N12 | W/CHANNEL compactos eje mayor | Fluencia; LTB | P | B | LRFD ejecutable; selección HFS-012, sin acreditación integral |
| F3; N13 | W alma compacta/ala no compacta o esbelta | Fluencia reportada; LTB; pandeo local de ala | P | B | Código F3; etiquetas F-37 pendientes |
| F4; N14 | W alma no compacta | Fluencia ala comprimida/traccionada; LTB; pandeo local | P | B | Alternativa conservadora F5, no equivalencia normativa acreditada (F-19) |
| F5; N15 | W alma esbelta | Fluencia ala comprimida/traccionada; LTB; pandeo local | P | B | Código existente, condiciones/nominales pendientes |
| F6; N16 | W/CHANNEL eje menor | Fluencia; pandeo local | P | B | F6 no cubre flexión mayor pendiente; F-31 abierto |
| F2–F5; N12–15 | CHANNEL mayor no compacto/esbelto o clasificación desconocida | Selección/resistencia mayor | B | B | Bloqueo HFS-012, también en biaxial; motor puede continuar INCOMPLETE con otras evaluaciones |
| F7; N17 | RHS, x/y | Fluencia; pandeo local ala; pandeo local alma; LTB | P | B | F1 LRFD en reglas; nominales internos reutilizados por H |
| F8; N18 | CHS, x/y, D/t dentro de alcance | Fluencia; pandeo local | P | B | F1 LRFD en reglas; dominio D/t conserva guardas |
| F8; N18 | CHS fuera del límite o sin D/t | Selección/resistencia flexural | B | B | No extrapolación |
| F9; N19 | 2L | Fluencia/LTB/pandeo local según dominio | B | B | Regla no implementada, no sustituir por F10 |
| F10; N20 | L x/y y opciones de conexión | Fluencia; LTB; pandeo local de ala | P | B | Signo/ejes/condiciones no acreditados completamente |
| F11; N21 | SR/SC y alias legacy, x/y | Fluencia; LTB | P | B | No se declara compuesto por un alias |
| F12/F13; N22/34 | Asimétricas; todas cuando aplique | Flexión específica, agujeros, rigidizadores, proporciones | P | B | Sin verificación completa; ASD bloqueado por momentos |
| G1/G2; N23 | W/CHANNEL, Vux/Vu | Fluencia/pandeo por cortante alma | P | P | Factores G1 .90/1.67; excepción G2.1(a) 1/1.50 en rama W; fabricación aún por acreditar |
| G3; N24 | L/2L, Vux/Vuy | Cortante | B | B | Bloqueo HFS-013 por dirección/reparto, no nuevas fórmulas |
| G4; N25 | RHS, Vux/Vuy | Fluencia/pandeo cortante | P | P | Fuente compartida G/H3, pares por eje; Ω1.67/φ.90 |
| G5; N26 | CHS donde rama no depende de Lv desconocida | Fluencia/pandeo cortante | P | P | Fuente compartida G/H3; no derivar Lv de Lx/Ly |
| G5; N26 | CHS que requiere Lv no representada | Pandeo cortante | B | B | Falta dato físico explícito; INCOMPLETE en motor |
| G6; N27 | W, Vuy | Cortante eje menor | P | P | Conversión G1; condiciones nominales pendientes |
| G6; N27 | CHANNEL, Vuy | Cortante eje menor | B | B | Dirección/interpretación no acreditada, bloqueo HFS-013 |
| G; N23–28 | SR/SC/alias | Cortante | B | B | Ruta custom no soportada |
| G7; N28 | Familias con aberturas | Cortante con abertura | P | P | No representado/verificado; no se infiere ausencia |
| H1; N29 | RHS/CHS, axial+flexión | Interacción compresión o tracción/flexión | P | B | Internamente ambos métodos mediante D/E/F1; ASD público bloqueado por M. F-37 persiste |
| H1/H2; N29 | W/CHANNEL/L/2L/SR/SC; biaxial sin axial | Interacción axial/flexión o biaxial | P | B | Ausencia de cobertura mantiene INCOMPLETE LRFD; ASD con M rechazado |
| H3.1; N30 | RHS/CHS dentro del dominio | Fluencia/pandeo torsional | P | P | φT .90 / ΩT1.67; C explícito, sin inferencia geométrica nueva |
| H3.1; N30 | RHS h/t>260; CHS necesita L físico desconocido | Resistencia torsional | B | B | Conserva bloqueos HFS-013 |
| H3.2; N30 | RHS/CHS, Tr/Tc>0.20, sin momentos | Interacción cortante/torsión/axial | P | P | H3-6 con todas capacidades del mismo método; cobertura completa pendiente |
| H3.2; N30 | RHS/CHS, Tr/Tc>0.20, con momentos | Interacción completa | P | B | Internamente ambos métodos y F-43 correcto; no habilita F pública ASD |
| H3.2; N30 | RHS/CHS, Tr/Tc≤0.20 con otras acciones | Alternativa H1/G | B | B | Umbral no acredita resistencia; guarda HFS-013 |
| H3.3; N31 | Todas no HSS | Torsión y alabeo | B | B | Rechazo explícito, sin selección HSS artificial |
| H4; N32 | Familias con agujeros en alas | Rotura ala bajo tracción | P | P | No implementado, si ASD tiene M se aplica además bloqueo F |
| D1/E2; N33 | Todas | Recomendaciones de esbeltez | P | P | Avisos HFS-015, no estados resistentes ni acreditación |

## Compuestos y remisiones externas

| Capítulo / N-ID | Familia/rol | Estado límite o condición | LRFD | ASD | Ejecución y límite |
|---|---|---|---|---|---|
| I1; N36 | ENC/FILL-R/FILL-C/BEAM | Elegibilidad/material/clasificación | P | B | Chequeos parciales, ningún PASS I1 acredita resistencia |
| I2.1; N37 | ENC | Compresión/pandeo; tracción | P | B | φc=.75, φt=.90, piso acero E1 separado |
| I2.2; N38 | FILL-R/FILL-C | Compresión/pandeo; tracción | P | B | Mismos valores locales, disposiciones/nominales distintos |
| I3.3; N39 | ENC | Flexión x/y, cuantía | P | B | Capacidad interna acero solo φ=.90 en I5; cuantía no acredita M puro |
| I3.4; N40 | FILL-R/FILL-C | Flexión x/y, cuantía, plastificación/primer flujo | P | B | Solvers nominales + φ=.90 interno; M puro pendiente F-34 |
| I3.2; N43 | BEAM | Transferencia horizontal, flexión por etapa | P | B | Transferencia ejecutable, no resistencia M acreditada |
| I4.1(a)/(b)/(c); N41 | ENC | Cortante acero/concreto/estribos y agregación | P | B | φ=.90 acero, .75 alternativas concreto/estribos; no unificación |
| I4.1; N41 | FILL-R/FILL-C | Cortante relleno | P | B | φ=.90, geometría/ejes/nominales pendientes |
| I4.3; N41 | BEAM | Cortante acero con deck | P | B | φ=.90 helper acero; no ASD por bypass |
| I5; N42 | ENC/FILL-R/FILL-C, Pu≠0+M | Interacción métodos internos 1/2/4 donde seleccionables | P | B | Nominal/disponible y puntos tablas SCM requieren auditoría F-20/37; no alterados |
| I5; N42 | ENC/FILL-R/FILL-C, biaxial sin Pu | Interacción | P | B | Cobertura ausente F-33, no nuevo PASS |
| I6/I8; N44 | ENC/FILL/BEAM | Introducción/transferencia de fuerzas y anclajes | P | B | Candidatos nominales de anclajes no verifican I6 completo |
| I; N45 | Otros roles/familias o STRAIN_COMPAT/EFFECTIVE_STRAIN | Todos los estados del dominio rechazado | B | B | Contratos previos conservados |
| J/K/L/M/N, apéndices y otras remisiones; N35/45 | Todas cuando corresponda | Uniones, fatiga, servicio, fabricación, calidad, análisis/estabilidad | P | P | Sin acreditación; excluidos del alcance verificable actual, no obligación satisfecha por omisión |

Los coeficientes 0,85/0,95 de concreto, Q/Cv/Cp/Cm, parámetros de iteración y
límites de clasificación no se reclasifican como φ/Ω por coincidencia numérica.
Tampoco se transforma un valor nominal de tabla SCM en disponible por deducción
local. Sus reservas siguen F-18/20/30/35/37 y HFS-031–036.

## Fuentes y alcance de evidencia

S22 local `a360-22w.pdf`: D2 PDF100–101, E1 PDF106, F1 PDF120,
G1/G2 PDF143–144, H3 PDF153–155, capítulo I PDF157–188; paginación del archivo,
no numeración impresa. D/E/F/G/H son disposiciones Specification; las alternativas
de Commentary/User Note y tablas SCM se conservan identificadas como tales en
HFS-002, sin elevarlas a obligación. El hash local figura en scope-verification.

El [índice oficial AISC de erratas](https://www.aisc.org/aisc/publications/revisions-and-errata/)
consultado el 2026-10-27 lista publicaciones enero 2025 y septiembre 2026 para
360-22. HFS-017 no acredita reconciliación integral de esas erratas con el PDF
local: F-28/HFS-030 permanece abierto. No se cambia ninguna ecuación normativa.

Oráculos acotados HFS-017: factores D2/E1/F1/G1/G2/H3, D2, un caso E3,
G2 W/canal y G4/H3; pruebas F-43 previas en ambos HSS/métodos/ejes. La igualdad
antes/después es regresión de comportamiento, no un segundo oráculo normativo.
`coverage.py` y `coverage_evidence.py` permanecen idénticos a HEAD.
