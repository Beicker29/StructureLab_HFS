# HFS-031R0 — Dominios operativos y contenidos

Fuente: lectura íntegra de [HFS-031](../hfs031/report.md), su
[matriz independiente](../hfs031/requirements.md), cálculos, confrontación,
hallazgos y suite. Se conserva S22+E25+E26 por sus hashes. Esta decisión es
contención de software para revisión; no acreditación normativa ni reparación
de las ecuaciones. Ambos métodos tienen las mismas precondiciones E; factores
LRFD/ASD y restricciones públicas F/I no cambian.

| Dominio con compresión activa | Decisión R0 | Fundamento / límite |
|---|---|---|
| D2/D3 y tracción | Operativo sin cambios | R0 no altera estos capítulos ni justifica An/U externos |
| E3 W, canal, HSS rectangular/circular no esbeltos | Operativo con ambos radios, longitudes, K, Ag, E/Fy y clasificación completa | E3-1…4 contrastados en HFS-031; radii/ejes y procedencia físicos declarados, no autenticados. El PASS del modo E3 no acredita E1/E4 |
| E3 sólidos rectangular/circular | Operativo con ambos ejes completos | No hay pared delgada que clasificar B4.1a; no se inventa una clasificación de pared |
| E3/E4 con elemento esbelto | Bloqueado F-35 | FnAg no sustituye FnAe; desaparece también el check concurrente E3 favorable sobre sección esbelta |
| E3/E4 con clasificación parcial o no finita | Bloqueado F-48 | Cualquier elemento desconocido hace `overall=unknown`; `is_slender` solo informa si hay algún elemento conocido esbelto |
| E4 W/HSS de doble simetría, sin offsets, datos completos | Operativo, fórmula y valores preservados | J positivo, Cw explícito no negativo; ro positivo suministrado o derivado de Ix/Iy/Ag positivos en esta familia. H suministrado debe ser1 y eo suministrado0; no aceptar contradicción explícita |
| E4 canal, cualquier H | Bloqueado F-46 | Selección de eje incorrecta; disponer H no repara el llamador |
| E4 con xa/ya no cero | Bloqueado F-47 | E4-10…12/análisis no implementados; tampoco en consumidores H/I |
| Ángulo simple, E3/E5/E7 | Bloqueado F-36/F-35 | `one_leg`/`both_legs` no representan todas las condiciones ni los ejes principales; no escoger una rama |
| Doble ángulo, compresión | Bloqueado F-38/F-48 | Contacto/fabricación y E6 no representados. Clasificador devuelve unknown, no decide B4.1a caso1/3 |
| E7 directo, cualquier familia | Bloqueado F-35 | Sin FnAe implementado. Para no esbeltos usar modo E3/E4 pertinente; no producir un check E7 nominalmente favorable |
| Capacidad axial de H1/H3 y piso de acero de I | Misma guarda E4 antes de calcular | Protege dependencia D/E; no audita ni cambia fórmulas H/I. Cero Pu en H retorna su marcador inactivo previo; una capacidad solicitada por I pasa la guarda aunque Pu=0 |
| Otras familias no representadas | Rechazo explícito | Sin ampliación del dominio normativo |

Los checks E inactivos (Pu≤0) conservan el resultado cero histórico, después
de validar método. No evalúan compresión ni descargan obligaciones. Pu>0,
por pequeño que sea, activa las guardas. No hay tolerancia de demanda.

El modelo ya define xa=ya=0 por defecto. Se preserva ese contrato documentado;
R0 no agrega hipótesis. La simetría se limita a familias ya declaradas W/HSS:
no se transforma una sección fabricada, una orientación angular o un centro
de corte desconocido en esos tipos. Las propiedades suministradas deben ser
coherentes y tener procedencia externa; R0 no valida integralmente el catálogo.
En particular F-12/14/27 siguen pendientes. No se recalculan ni corrigen
propiedades redondeadas de catálogo sin fuente verificable.

Alternativas descartadas: corregir solamente Fey→Fex, extrapolar E5-1,
reemplazar Q por Ae/Ag dentro de Fcr, omitir E4 por falta de J/Cw, o adoptar
Cw=0/H=1 al faltar. Todas requieren una justificación que R0 no introduce.
