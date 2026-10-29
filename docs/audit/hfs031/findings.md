# HFS-031 — Hallazgos y plan de correcciones verificables

Estado: **abiertos para revisión independiente**, no aprobación del agente.
Evidencia normativa: [matriz](requirements.md); demostración:
[cálculos](calculations.md), [sondas](evidence/probes.json),
[suite](../../../tests/test_hfs031_de_audit.py).
Severidades propuestas por consecuencia técnica; `INCOMPLETE` mitiga la
declaración global, pero no corrige resistencias ni protege una llamada directa.

| F-ID / severidad | Certeza y estado | Consecuencia demostrada | Corrección propuesta y condición de cierre |
|---|---|---|---|
| F-35 / P0 | **INCORRECTO**, demostrado algebraica y numéricamente; abierto | QFy/Ag difiere de FnAe, con sobre/subestimación. Circular D/t100,Fe80: +12,7451% en ambos métodos; PASS local falso. W/canal/HSS rectangular/ángulo también divergen | Sustituir método por E7-1…7: Fn desde modo acreditado, Ae por cada elemento, c1/c2/fuente de anchos; circular límite superior estricto. Validar E7-2/3, tres tipos de elemento, desigualdades, factores y consumidores. No basta cambiar Q por Ae/Ag dentro de curva. Convertir xfail solo tras demostrar cada dominio. |
| F-36 / P0 | **INCORRECTO** E5-2 y radios; **NO IMPLEMENTADO** condiciones/otras ramas; abierto | +26,2155% a s120 en E5(a); ángulo concéntrico ideal +135,0841% por omitir radio principal menor. E5(a)/(b) no equivale a one_leg/both_legs | Primero representar/recibir evidencia de mismas alas, conexión≥2 pernos o soldadura, carga intermedia, contexto/ala/radios y longitudes. Resolver 75/80/200 y ratio<1,7. Para datos insuficientes, rechazo/pendiente explícito; nunca default(a). Separar pandeo concéntrico principal, alternativa E5 y E7; E4 angular cuando aplique. |
| F-46 / P0 nuevo | **INCORRECTO**, demostrado para canal convencional; abierto | Acoplamiento E4 usa Fey en lugar de Fex. Caso sintético E4 +100%; mínimo E3/E4 aún sobrestima. H desconocido se sustituye por1 | Propietario E4 debe elegir eje según simetría acreditada; exigir H/ro coherentes o derivarlos de centro de corte declarado, nunca de etiqueta sola. Pruebas con Fex<Fey y Fex>Fey, ambos métodos, H=1/0<H<1 y ausencia. No corregir simplemente todos los Fey a Fex: doble ángulo/T requieren su propia orientación. |
| F-47 / P0 nuevo | **INCORRECTO** al aceptar offset y calcular centro de corte; abierto | xa/ya cambian memoria, no resistencia. ya200: +58,7499%; xa100:−9,2785% | Implementar E4-10/11/12 solo tras identificar I doble simétrica y modo de restricción; rechazar otros desplazamientos hasta análisis E4(f). Guardas también en llamadas directas. Conservar ID, publicar cambio de memoria/resultados y oráculo separado por rama. |
| F-48 / P0 propuesto nuevo | **INCORRECTO** en clasificación incompleta/2L contacto y E3 directo; abierto | Ausencia parcial → non_slender; 2L continuo tratado como separado; E3 sin ry emite PASS. W/canal pueden mezclar razones en Q | Asegurar clasificación completa con fabricación/contacto y anchos correctos. Incompleto→unknown con guarda canónica. No inferir contacto desde DOUBLE_ANGLE. E3 directo debe exigir ambos modos o evidencia explícita de dominio. Regresión por familia, falta de dato, λr± y revisión de selector/consumidores. |
| F-12 / P1 existente | **INCORRECTO** fallback de importación, reproducción nueva; abierto | Excel OD100,ID90,tdes5 deriva D/t18 en vez20; cambia clasificación E7 si cerca de umbral | Dar prioridad al diámetro exterior físico y espesor de diseño con procedencia. No corregir filas del catálogo sin fuente; distinguir columna D/t ya suministrada del fallback. Casos OD+ID, soloID (rechazo/pendiente), espesores y unidades. |
| F-38 / P1 existente, efecto resistente potencial P0 | **NO IMPLEMENTADO** D4–D6/E6/E4(c), condiciones externas; abierto | E6 s0=100,a/ri60 requiere sm116,619; E3 aislado no lo incluye. D2 no demuestra conexión ni pasador | Mantener exclusiones/cobertura pendiente. Crear contrato de datos de cada dominio antes de fórmulas. Evaluar E6 extremos/detalle y todos los modos, no solo modificación s. D5 necesita J7 externo, D6 detalle. No elevar un check aislado a aptitud global. |
| F-37 / P1 existente | **INCORRECTO** localizador E5-1a/b; abierto | IDs legacy no son ecuaciones E5 de S22; trazas pueden aparentar rama no implementada | Conservar identificadores estables, separar referencia normativa correcta de ID; actualizar índice derivado y expectativas solo con migración documentada. No cerrar el resto de F-37 (fuera D/E). |
| F-28 / P2 documental | **INDETERMINADO** autenticación remota; abierto | Copias locales verificadas por hash, sitio AISC403; CI de software no autentica PDF | Descargar/autenticar con editor y comparar bytes/versiones; conservar originales/erratas y permisos. El dictamen actual queda condicionado a esta base documental. |

## Secuencia de reparación propuesta, no ejecutada

1. Someter hallazgos y oráculos a revisión ingenieril. Confirmar procedencia
   de S22/E25/E26 y las convenciones de eje/catálogo. No iniciar F/G/H/I.
2. Contener llamadas directas en dominios indeterminados: no entregar PASS
   de una capacidad sin datos/método soportado. Documentar diferencia de contrato
   Python y efecto en checks. Mantener cobertura pendiente; no aprovechar la
   corrección de una ecuación para descargar toda obligación.
3. Reparar E4 por dominio antes de compartirlo con E7. E5 exige datos que JSON1.0
   no expresa: alternativas son nueva versión explícita, declaración externa
   tipada fuera del contrato congelado o rechazo del dominio. Elegir en revisión,
   no añadir defaults ni campos silenciosos a1.0.
4. Reparar E7 con Fn y áreas efectivas por elemento. Probar primero cada área,
   luego resistencia/método/selección. Analizar las dos representaciones de c2
   y límites impresos; no suavizar ramas por conveniencia numérica.
5. Inventariar/revisar impacto en consumidores axiales de H/I sin auditar sus
   ecuaciones en este hito. Una sustitución central cambia esos valores aunque
   sus archivos no se editen; requiere autorización y evidencias por consumidor.
6. Migrar únicamente expectativas cuyo defecto se corrija y demuestre. Los
   xfail son estrictos y limitados a AssertionError; un XPASS obliga revisión,
   no se silencia. Capturas históricas y oráculos independientes permanecen.

Cada reparación debe registrar antes/después: nominal, disponible, demanda,
DCR, estado local/global, cobertura, traza, memoria y código CLI, con caso,
método, unidades y causa de diferencia. El objetivo no es preservar capacidades
incorrectas: este hito entrega el diagnóstico y los esperados que permitirán
corregirlas sin adoptar hipótesis de conexión/arriostramiento no disponibles.

No se ha realizado una sustitución productiva en esta entrega de auditoría:
ninguna eliminación de código/fachada ni cambio normativo escondido. La ausencia
de cambios de runtime es una decisión explícita ante la amplitud de contratos
pendientes, **no** un dictamen favorable sobre el código actual. F-35/F-36 no se
cierran; F-31 continúa P0 y reservado prioritariamente para HFS-032.
