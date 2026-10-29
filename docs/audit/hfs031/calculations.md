# HFS-031 — Banco y desarrollos independientes

Fuente y hashes: [matriz normativa](requirements.md). Autor: agente Codex,
derivación independiente de los archivos productivos; **sin revisión humana
atribuida**. Son cálculos manuales desarrollados aquí y evaluados con Decimal
a 50 dígitos por [oracles.py](oracles.py), exclusivamente stdlib. No importan
motor, reglas, router, fixtures previas ni capturas del programa. El JSON
[oracles.json](../../../tests/fixtures/hfs031/oracles.json) conserva **95 hojas**,
entradas, unidades implícitas SI aquí definidas, referencias e intermedios.
[probe.py](probe.py) realiza después la confrontación; no escribe esperados.

No son ejemplos publicados por AISC, ni aprobación de propiedades comerciales.
Todos los casos son analíticos estipulados. La incertidumbre de una propiedad
real no se elimina aumentando dígitos. Salvo indicación contraria: E=200000MPa,
G=77200MPa, Fy=345MPa; fuerza N convertida una vez a kN; factores E1 y D2
separados por disposición y método. Las tolerancias del contraste son
relativa1e−10 y absoluta1e−8kN (para nominales/intermedios,1e−8 de su unidad).
Cubren conversión Decimal→float y operaciones transcendentes, no diferencias
de modelo, redondeo editorial o cambios PASS/FAIL. Decisión sin epsilon.

## D2/D3 — dos resistencias y área suministrada

S22 D2-1/2, D3-1, PDF100–101. Ag=1000mm², An=800mm², U=0,8,
Fu=450MPa. Ae=800×0,8=640mm².

- Fluencia nominal:345×1000=345000N; LRFD310,5kN; ASD345/1,67=206,586826347kN.
- Rotura nominal:450×640=288000N; LRFD216kN; ASD144kN.
- Gobierna rotura en ambos métodos. Para An=1000,U=1, LRFD gobierna fluencia
  (310,5 frente337,5); ASD fluencia (206,586826347 frente225).

El motor coincide. El oráculo **no** justifica U de una conexión: Tabla D3.1
y B4.3 requieren información externa que el contrato no representa. Ejemplo
de cálculo externo distinto: placa200×10mm con dos agujeros nominales22mm
en la sección crítica, sin stagger: An=[200−2(22+2)]10=1520mm². Con conexión
que cumple caso1,U=1,Ae=1520. Sin esa condición, no se adopta U=1.

D4/D5/D6 no tienen implementación. Como control independiente de lo que falta,
para pasador t=10mm,d=50mm,dh=51mm,a=50mm,borde transversal real40mm,
Fu=450MPa: be=min(36,40)=36mm; Asf=2·10(50+25)=1500mm²; Cr=1.
D5-1 produce324000N; D5-2 produce405000N; LRFD243/303,75kN;
ASD162/202,5kN. Además se requieren ancho≥122mm,a≥47,88mm y J7/D2:
estos dos números **no** constituyen resistencia final del miembro con pasador.
Se incluye el desarrollo como pendiente, no como prueba de una función ausente.

## E3 — Euler, curva y factores

S22 E3-1…4, PDF108–109. Seis valores de Fy/Fe:
0,1;1;2,249999;2,25;2,250001;4,3125. Se construye s=π√(E/Fe),
Ag=5000mm². En igualdad2,25:

Fe=345/2,25=153,333333333MPa;
s=113,460993495;
Fn=345·0,658^2,25=134,532544297MPa;
Pn=672662,721482970N;
φPn=605,396449335kN;
Pn/Ω=402,792048792kN.

Para Fy/Fe=4,3125,Fe=80MPa: Fn=0,877·80=70,16MPa;
Pn=350800N; LRFD315,72kN; ASD210,059880240kN.
Las dos ramas coinciden con el código; se prueban ambos lados del umbral
sin exigir una continuidad exacta que los coeficientes redondeados no tienen.
El límite4,71√(E/Fy) es una alternativa editorial redondeada; el software
elige consistentemente la condición Fy/Fe, no combina umbrales diferentes.

Los ensayos de regla alternan el eje principal gobernante; el eje restante
tiene menor KL/r. Esto no valida que rx/ry de cualquier catálogo sean los
ejes principales ni calcula K. F-48 demuestra que una llamada directa puede
ignorar ry ausente, mientras la ruta pública lo rechaza.

## E4 — simetría, raíz inferior, ejes y offsets

### Doble simetría por centro de corte

S22 E4-2/7/9, PDF109–110. Ag=10000mm², Ix=100·10⁶mm⁴,
Iy=20·10⁶mm⁴,J=200000mm⁴,ho=300mm,Lcz=6000mm.
Se estipula Cw=Iyho²/4=450·10⁹mm⁶ (aproximación UN22 identificada).
ro²=(Ix+Iy)/Ag=12000mm².

Fe=[π²·200000·450·10⁹/6000²+77200·200000]/(120·10⁶)
=334,283425023MPa. Fn por E3, Pn=2239843,169781216N;
LRFD2015,858852803kN; ASD1341,223454959kN. Coincidencia demostrada.

### Canal: acoplamiento respecto al eje de simetría

S22 E4-3 y nota de ejes, PDF109–110. Canal simétrico en x:
Ag=5000,Ix=50·10⁶,Iy=10·10⁶,ro²=24000,H=0,5; esto exige
distancia cuadrada centroide–centro de corte12000mm², consistente con E4-8/9.
Lx/Ly se fijan para Fex=50 y Fey=200MPa; J,Cw,Lz para Fez=100MPa.
Las propiedades completas están en `probes.json`; no se atribuyen a un perfil comercial.

La ecuación con Fex tiene raíz inferior de0,5Fe²−150Fe+5000=0:
Fe=38,196601125MPa. Se evalúa de forma racionalizada para evitar copiar la
forma sustractiva del programa. Fn=33,498419187MPa;
LRFD150,742886340kN; ASD100,294668223kN.
El código usa Fey=200 y obtiene Fe=76,393202250MPa, exactamente el doble
en este caso; LRFD301,485772680kN. E3 limita a197,325kN, que todavía excede
150,742886340kN: una demanda intermedia pasa ambos checks y es normativamente
insuficiente. El estado global permanece `INCOMPLETE`.

La misma raíz inferior, pasando el **eje correcto**, sí coincide con el helper.
No es un defecto de álgebra de la cuadrática, sino de la selección y datos.
H ausente se reemplaza por1; no puede inferirse H de la etiqueta CHANNEL.

### Arriostramiento desplazado

S22 E4-10/11/12, PDF111. Mismas propiedades del caso doble simétrico.
Para ya=200mm, xa=0:
ro²=52000; Fe=[π²EIy/Lcz²·(ho²/4+200²)+GJ]/(Ag·52000).
Disponible LRFD1269,832966188kN. El código conserva2015,858852803kN:
**+58,7499%**. Para xa=100,ya=0, E4-12 produce2222,029174794kN
y el código2015,858852803 (−9,2785%). El defecto no tiene signo universal.

E4-4 general está **NO IMPLEMENTADO**. Hoja de control independiente:
Fex=Fey=100,Fez=200,(xo/ro)²=(yo/ro)²=0,25. La cúbica factoriza en
(Fe−100)[0,5Fe²−300Fe+20000]; raíz mínima76,393202250MPa.
Esto no valida un solucionador cúbico inexistente ni reemplaza el estudio
de un ángulo real.

## F-36 / E5 — condiciones y todas las ramas

S22 E5, PDF111–113. Para alternativa (a), ángulo igual o ala larga conectada,
suponiendo **las cinco condiciones** y configuración de cercha verificadas:
s=L/ra=120; Lc/r=32+1,25·120=182 (E5-2), no72+0,75·120=162.
Con Ag=2000, Fe=π²E/182²; LRFD94,071715418kN; ASD62,589963685kN.
La regla devuelve118,733100957kN LRFD: **+26,2155%**.

En s=80 las ramas(a) coinciden en132; en s=75 las ramas(b) coinciden en120.
El banco conserva ambos lados±0,001. No se transforma `both_legs` en
contexto(b): es otra información. Para(b),s120 requiere165, y da
114,454784261kN LRFD frente118,733100957 del código (+3,7380%).

Ángulo desigual bl/bs=1,5, s100:

- (a) ala corta: base157+4(1,5²−1)=162; si L/rz=200, el piso0,95·200=190
  gobierna; disponible86,316662092kN LRFD.
- (b) ala corta: base145+6(1,5²−1)=152,5; con L/rz=200, piso164;
  disponible115,854829771kN LRFD.

El límite200 se alcanza en (a) ala larga con s134,4 y en(b) con s155.
Valores mayores no autorizan la alternativa. Las hojas con s180 conservan
la prolongación algebraica **solo para detectar el límite incumplido**;
no son resistencias normativas utilizables. No hay datos de pernos/ala/contexto
en el contrato que permitan certificar las demás condiciones. `INDETERMINADO`
debe conducir a pendiente/rechazo, no a escoger(a) silenciosamente.

### Ángulo concéntrico y eje principal

No basta corregir E5-2. Ángulo ideal100×100×10mm, sin filetes:
dos rectángulos no superpuestos100×10 y10×90; Ag1900;
x̄=ȳ=28,684210526mm; Ix=Iy=1800043,859649mm⁴;
Ixy=−1065789,473684mm⁴. Autovalor menor Imin=734254,385965mm⁴;
rz=√(Imin/Ag)=19,658323347mm; radio geométrico30,779725552mm.
L=100·rgeom=3077,972555236mm; K=1 para pandeo principal estipulado;
Fe=80,518041607MPa. b/t10<0,71√(200000/345) permite omitir E4;
no permite ignorar el eje principal menor.

Disponible LRFD120,750491456kN frente283,865206512 usando radios geométricos
en `both_legs`: **+135,0841%**. El catálogo contiene rx/ry/rz separados;
la etiqueta del modo no acredita conexión concéntrica ni transforma los ejes.

## E6 — ausencia demostrada, no acreditación por E3

S22 E6-1/2, PDF113–114. Conjunto s0=100, a/ri=60:

- Pernos snug-tight: sm=√(100²+60²)=116,619037897.
- Intermedios soldados/pretensados, ángulos espalda a espalda:
  sm=√(100²+(0,5·60)²)=104,403065089.
- Con Ag5000, las capacidades LRFD son572,799908366 y699,415566252kN.

Los16 escenarios incluyen a/ri39,999/40/40,001/60 y Ki0,5/0,75/0,86,
además de snug-tight. El caso(a) no tiene excepción a40; en(b) sm=s0 para≤40.
Estas hojas no verifican conexiones/extremos/celosías. El test del E3 directo
contra la capacidad E6 necesaria falla de forma prevista (F-38); N09 sigue
pendiente. No hay una implementación E6 que pueda declararse correcta.

## F-35 / E7 — demostración de no equivalencia

### Prueba algebraica

Sea qA=Ae/Ag<1. Incluso si se sustituyera el Q actual por qA, en rama inelástica:

Pn prescrito = Ag·qA·Fy·0,658^(Fy/Fe).

Pn con QFy = Ag·qA·Fy·0,658^(qA·Fy/Fe).

Su cociente es0,658^[(qA−1)Fy/Fe]>1. Si ambas curvas están en rama elástica,
el cociente es1/qA. Por tanto, desplazar la reducción al argumento Fy no es
una transformación algebraica legítima. El Q implementado además no es qA:
usa límites/razones, productos en W/canal y máximo de paredes HSS.

La equivalencia se limita, por ejemplo, a Q=1,Ae=Ag y mismos modos/Fe;
puede haber coincidencias particulares en ramas elásticas de elementos no
circulares con Ae=Ag, pero no una equivalencia general del dominio esbelto.

### Circular: sobrestimación y PASS local falso

S22 E7-1/7, PDF116–117. D/t100 está entre63,768115942 y260,869565217.
Ag5000,Fe80: Fn70,16MPa.

Ae/Ag=0,038·200000/(345·100)+2/3=0,886956521739;
Ae4434,782608696mm²;
Pn311144,347826087N;
LRFD280,029913043kN; ASD186,313980734kN.

Código: Q=0,637681159420; QFy=220MPa, QFy/Fe=2,75;
Fn legado=0,877·80=70,16, pero multiplica Ag5000;
LRFD315,72kN; ASD210,059880240kN. Exceso **12,7451%**.
Demanda LRFD297,874956522kN produce PASS de E7 donde debería fallar la
resistencia prescrita. El motor conserva `INCOMPLETE`, no PASS global.

La sección de integración es un anillo exacto: t=√[5000/(π·99)],D=100t;
I=π[D⁴−(D−2t)⁴]/64,J=2I,Cw=0,r=√(I/Ag),ro²=2r².
L=π√(E/80)r; Fez=G, por lo que gobierna flexión con Fe80.
No se confunde diámetro interior con exterior en este oráculo.

Con mismo D/t100 y Fe500, LRFD normativa1031,596373766 frente823,482904764
(−20,1739%). D/t250 y Fe5000:1138,442447568 frente393,093589656
(−65,4709%). Hay diferencias de ambos signos, no un método conservador
universal. Los métodos LRFD/ASD preservan el mismo error relativo porque
convierten el mismo Pn con sus factores correctos.

### No circular: cada elemento cuenta

S22 E7-2…5/Tabla E7.1, PDF116–117. HSS rectangular ideal con exteriores
424×274mm,t6mm,radio exterior12mm/interior6mm. Planos400 y250mm;
Ag=2·6(400+250)+π(12²−6²)=8139,292006588mm².
Se estipula Fe500MPa del modo global aplicable; Fn258,460965105MPa.
λr=1,40√(200000/345)=33,708038864. Se usan c1=0,20,c2 tabulado1,38.

Pared400:λ66,6667,Fel167,96808MPa,be270,469794229mm;
dos paredes pierden1554,362469254mm².
Pared250:λ41,6667,Fel429,9982848MPa,be239,275653029mm;
dos paredes pierden128,692163646mm².
Ae6456,237373688mm²; LRFD1501,816808293kN.
La reducción Q a partir de una sola razón máxima da1104,220881536kN
(−26,4743%), aunque no representa ninguna de esas áreas.

Las hojas W, canal y ángulo usan rectángulos definidos explícitamente en
`oracles.py`; no equivalen a acreditar su clasificación de fabricación ni
propiedades reales. Ag de W12800, canal6800 y ángulo2375mm²; elemento(s)
ancho/t, multiplicidad y c1/c2 registrados. El ángulo con Fe80 da exceso
16,3691%: la no equivalencia no se limita al tubo circular.

### Fronteras y precisión editorial

Se conservan9 hojas de E7-2/3 con Fn/Fy=0,25 y λ/λr=1,999999/2/2,000001,
para las tres clases de c1/c2. En igualdad be=b; por encima se usa E7-3.
E7-4 da c2 no redondeado y la tabla da1,31/1,38/1,49: el banco declara la
tabla y no oculta su diferencia mediante tolerancias. No existe productor
de be con el cual comparar estas9 hojas; siguen **NO IMPLEMENTADO**.

E7-7 usa límite superior estricto D/t<0,45E/Fy; se prueba que el software
todavía calcula en igualdad y más allá, sin crédito de cobertura. En el
límite inferior los coeficientes publicados también requieren distinguir
las desigualdades; no se añade clamp Ae≤Ag ni continuidad artificial.

F-12 se reproduce con archivo Excel mínimo independiente: OD100,ID90,tdes5;
el importador deriva18 en lugar de20. No se alteran el catálogo ni su fuente;
no se atribuye ese error a todos sus registros sin investigación específica.
