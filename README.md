# StructureLab_HFS

Motor de cálculo de la **resistencia de miembros de acero** según ANSI/AISC 360-22,
solo LRFD: capítulos D (tracción), E (compresión), F (flexión), G (cortante), H
(interacción de fuerza axial y flexión) e I (miembros compuestos: PTE rellenos, W embebidos, vigas,
muros de placas y anclajes de componentes), con los Apéndices 2, 4 (incendio, método simple) y 8.1
(`a360-22w.pdf` y erratas de enero 2025 y septiembre 2026, copias locales en `references/` que no se versionan). Perfiles del catálogo
`src/steel_design/data/sections.xlsx` (base AISC v16 métrica + PTE) o barras macizas definidas en
la entrada.

El resultado es estructurado y en memoria: familia, clasificación B4.1a,
disposiciones aplicadas, cada modo de pandeo con sus variables y ecuaciones,
resistencia nominal gobernante, resistencia de diseño LRFD (φPn), obligaciones
normativas y limitaciones. Está pensado para que una futura aplicación web llame
directamente al motor.

> No es una certificación AISC global. `PASS` significa que se evaluaron todos los
> estados límite exigidos por los capítulos aplicables a cada demanda, que cada
> demanda no supera su resistencia de diseño y que la interacción (H1, H2 en ángulos simples, H4) es ≤ 1. El
> programa trabaja solo con LRFD. Las longitudes efectivas, el análisis de segundo orden
> (Capítulo C), las combinaciones de carga, las conexiones, la torsión y demás capítulos
> quedan fuera del alcance.

## Instalación

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\Activate.ps1
```

## Uso

```powershell
python -m steel_design.run examples/w_shape.json                 # imprime JSON
python -m steel_design.run examples/multi_member.json --output r.json
```

Hay una memoria por miembro, no por combinación: cada revisión muestra el case de mayor DCR y dice cuál es. Tiene siempre once capítulos: propiedades de los
materiales, propiedades geométricas (geometría y rigideces elásticas, efectivas y para método directo), solicitaciones (últimas, construcción, incendio y deflexiones),
requerimientos técnicos (materiales y geometría), funcionalidad y/o servicio (deflexiones y construcción), compresión, tracción, cortante y flexión (cada una de estas dos en
condiciones de construcción, últimas e incendio, respecto de los ejes X e Y), torsión e índices DCR, con la interacción de I5 y el diagrama de interacción de miembros compuestos. Un requerimiento obligatorio incumplido impide el PASS. Lo que no corresponde al
miembro dice «No aplica» y lo que el programa no calcula dice «Falta implementación». Cada símbolo va con su nombre en palabras y
cada valor calculado con su literal del documento de referencia.

No se escribe nada en disco salvo que se pida. Memoria de cálculo en texto o PDF
(el PDF requiere el extra `pdf`: `pip install -e ".[pdf]"`, incluido en `dev`):

```powershell
python -m steel_design.run examples/channel.json --pdf            # results/channel.pdf
python -m steel_design.run examples/channel.json --report m.txt --pdf m.pdf
```

Sin ruta, `--report` y `--pdf` escriben en `results/<nombre del JSON>`: carpeta local,
creada al pedirla, ignorada por Git y nunca leída por el motor. Los ejemplos y la
documentación no guardan memorias generadas (se regeneran con el comando).

### Resultados y PDF de los ejemplos

Desde la raíz del repositorio, con el entorno activado. `--output` no crea carpetas, por eso
se crea `results` primero. Cada ejemplo deja `results/<ejemplo>.json` (resultado),
`results/<ejemplo>.txt` (memoria) y `results/<ejemplo>.pdf` (memoria en PDF).

Todos a la vez:

```powershell
New-Item -ItemType Directory -Force results | Out-Null
Get-ChildItem examples\*.json | ForEach-Object {
    python -m steel_design.run $_.FullName --output "results\$($_.BaseName).json" --report --pdf | Out-Null
}
```

Uno por uno:

```powershell
New-Item -ItemType Directory -Force results | Out-Null
python -m steel_design.run examples/w_shape.json --output results/w_shape.json --report --pdf
python -m steel_design.run examples/channel.json --output results/channel.json --report --pdf
python -m steel_design.run examples/rectangular_hss.json --output results/rectangular_hss.json --report --pdf
python -m steel_design.run examples/rectangular_hss_slender.json --output results/rectangular_hss_slender.json --report --pdf
python -m steel_design.run examples/circular_hss.json --output results/circular_hss.json --report --pdf
python -m steel_design.run examples/single_angle.json --output results/single_angle.json --report --pdf
python -m steel_design.run examples/double_angle.json --output results/double_angle.json --report --pdf
python -m steel_design.run examples/solid_rectangular.json --output results/solid_rectangular.json --report --pdf
python -m steel_design.run examples/multi_member.json --output results/multi_member.json --report --pdf
python -m steel_design.run examples/composite_filled.json --output results/composite_filled.json --report --pdf
python -m steel_design.run examples/composite_encased.json --output results/composite_encased.json --report --pdf
python -m steel_design.run examples/composite_beam.json --output results/composite_beam.json --report --pdf
python -m steel_design.run examples/composite_wall.json --output results/composite_wall.json --report --pdf
python -m steel_design.run examples/composite_filled_bars.json --output results/composite_filled_bars.json --report --pdf
python -m steel_design.run examples/composite_high_strength.json --output results/composite_high_strength.json --report --pdf
python -m steel_design.run examples/composite_box.json --output results/composite_box.json --report --pdf
python -m steel_design.run examples/composite_c_wall.json --output results/composite_c_wall.json --report --pdf
python -m steel_design.run examples/composite_coupling_beam.json --output results/composite_coupling_beam.json --report --pdf
```

Quite `--output ...` si solo necesita las memorias; sin ningún argumento adicional el resultado se
imprime en pantalla y no se escribe nada.

Desde Python:

```python
from steel_design.execution import load_engine
from steel_design.models import SteelCase

result = load_engine().run(SteelCase(
    section_name="C15X50", material={"Fy": 345}, P=−300,
    lengths={"Lx_3": 4000, "Ly_2": 1000, "Lz_1": 4000}))
print(result.status, result.capacity_kN, result.compression["governing_mode"])  # PASS 2254.31 FTB
```

La memoria se obtiene del mismo resultado, sin recalcular:
`blocks = report_blocks([(nombre, case, result), ...])` con los cases de un miembro (modelo del documento), `render_text(blocks)`
(texto) y `pdf_bytes([blocks, ...])` (PDF en memoria, p. ej. para una respuesta web),
en `steel_design.reporting` (`document`, `text` y `pdf`). El PDF usa una fuente Unicode del sistema
(DejaVu Sans, Segoe UI o Arial) para φ, λ y Σ; sin ella recurre a Helvetica con
símbolos escritos en letras.

### Entrada (unidades: mm, MPa, kN)

Ejes y signos de ETABS ([detalle](docs/axes.md)): eje 1 a lo largo del miembro, eje 2 = y (vertical de la sección), eje 3 =
x (horizontal); `P > 0` es tracción, `Mx_3 > 0` comprime la cara +2 y `My_2 > 0` la cara +3. La parte comprimida (ala de una
I, alas o punta de un ángulo, lado del muro en C, sentido de la viga compuesta) sale del signo.

| Campo | Descripción |
| --- | --- |
| `section_name` | Nombre del catálogo, o nombre libre con `custom_section` |
| `material` | Nombre de un acero de `src/steel_design/data/Materiales.xlsx`, por ejemplo `"ASTM A36"`, de donde salen Fy y Fu; un JSON no admite Fy ni Fu numéricos ni un nombre fuera del catálogo. Las barras (`Fysr`) y los pernos (`Fu`) se indican en su bloque |
| `P` | Fuerza axial requerida de la combinación LRFD (kN): > 0 tracción (capítulo D), < 0 compresión (capítulo E) |
| `Mx_3`, `My_2` | Momentos requeridos (kN·m) respecto de x (eje 3) y de y (eje 2), con signo, capítulo F. En ángulos simples se llevan a los ejes principales w, z cuando F10 lo exige |
| `Vy_2`, `Vx_3` | Cortantes requeridos (kN) a lo largo de y (eje 2, acompaña a `Mx_3`; alma) y de x (eje 3, acompaña a `My_2`), capítulo G |
| `lengths.Lx_3/Ly_2/Lz_1` | Longitudes no arriostradas para pandeo respecto de x, de y y torsional (obligatorias en compresión) |
| `tension` | Tracción: `An` (área neta, B4.3b, mm²), `U` (Tabla D3.1) y opcional `fabricated_length` (nota D1); An y U los aporta el usuario |
| `factors.Kx_3/Ky_2/Kz_1` | Factores K (por defecto 1); `xa_3`, `ya_2`: desplazamiento del arriostramiento respecto al centro de corte (E4(d)/(e)) |
| `heel` | Ángulos con flexión: `axis_2` y `axis_3` (`+`/`-`), lado de cada eje donde queda el talón; en ángulos dobles, `axis_2` es el lado del dorso. Con el signo de los momentos define la parte comprimida |
| `single_angle_e5` | Ángulos simples comprimidos sin momentos: configuración E5(a)/(b), ala conectada, `L` entre puntos de trabajo y las condiciones E5(1)–(3). Fuera de E5 se omite y la excentricidad se da como `Mx_3` y `My_2`, que se combinan por H2 en los ejes principales |
| `double_angle_e6` | Requerido para ángulos dobles: `connectors` (`snug_tight`, `welded`, `pretensioned`), separación `a` entre conectores (mm) y `end_connection_welded_or_pretensioned` (E6.1). Contacto o separadores se leen del nombre AISC (`2L4X4X1/4` vs `2L4X4X1/4X3/4`) |
| `condition` | Condición del case: `ultimate` (por defecto), `construction` (acero solo; solo Mu y Vu) o `fire` (con `fire`) |
| `fire` | Temperaturas de un case de incendio, en °C (Apéndice 4, 4.2.4d): `steel_temperature` y, según el miembro, `concrete_temperature` o su perfil (`concrete_layers`, `web_layers` con `flange_layers`) y `bar_temperature`; cada material presente es obligatorio ([detalle](docs/appendix-4.md)) |
| `serviceability` | Deflexiones: `actual_span`, `effective_span` (L de los límites), `deflections` y `limit_divisors` con `live_short`, `dead_short`, `total_long`. Exceder L/n se reporta y no cambia el estado |
| `flexure` | Flexión: `Cb` (1.0 si se omite; Lb sale de `lengths`: eje x, min(Ly_2, Lz_1); eje y, min(Lx_3, Lz_1)), `tension_flange_holes` (obligatorio en I y canales, eje x), `Afn` (mm²); en ángulos simples `lateral_torsional_restraint` (`none`, `at_max_moment`, `continuous`; ejes geométricos); `tension_cb_amplification` (H1.2, opcional) |
| `tau_b` | Solo miembros compuestos: τb para las rigideces de método directo (0 < τb ≤ 1), dato obligatorio que el programa no calcula; sin él, el estado es INCOMPLETO. El capítulo 4 de la memoria lo compara con I1.5(d) y (f) (0.8 en rellenos y embebidos, 1.0 en muros); una diferencia se informa y no cambia el estado. En miembros no compuestos τb es siempre 1.0 (C2.3(c)) y otro valor se rechaza |
| `shear` | Cortante: `Lv` (mm, PTE redondos, G5-2a; opcional) |
| `custom_section` | `SOLID_RECTANGULAR` (`H`, `B`), `SOLID_CIRCULAR` (`diameter`) o `I_BUILT_UP`: I armada soldada con `d`, `tw`, `flange_plus2` y `flange_minus2` (`b`, `t`; alas de las caras +2 y −2); sus propiedades salen de las placas ([F4 y F5](docs/chapter-f.md)) |
| `composite` | Capítulo I: `kind` (`filled`, `encased`, `beam`, `wall`, `c_wall`, `coupling_beam`), `concrete` (`fc`, `wc`, `lightweight`), `pour_height` (rellenos y muros), `interaction` (`H1`, `I5`, `M2`, `M2S`), `filled`, `box`, `encased`, `beam`, `wall`, `c_wall` o `coupling_beam` según el tipo, `anchor` (I8.3), `second_order` (Apéndice 8.1), y `fire` (revisiones opcionales de muros), `biaxial_shape_factor` y `flexural_member` de las Design Guides ([detalle](docs/chapter-i.md), [guías](docs/design-guides.md)) |

**Un archivo por miembro.** Los campos de nivel superior describen el miembro (perfil,
material, longitudes `lengths: {ultimate: {Lx_3, Ly_2, Lz_1}, construction: {Lx_3, Ly_2, Lz_1}}`, `tension`, E5/E6) y `cases` lista sus combinaciones de
carga; cada combinación aporta su demanda y puede sobrescribir cualquier dato. La salida
trae un resultado por combinación, el estado global y la combinación `governing` (mayor
relación demanda/capacidad). Cada combinación lleva sus demandas simultáneas (P, M, V);
Pr y Mr deben venir de un análisis de segundo orden (Capítulo C, decisión DH-3).
Ver `examples/` (un archivo por familia, `multi_member.json` con varios perfiles y `built_up_i.json` con I armadas en F4 y F5).

### Salida

`status` (`PASS`/`FAIL`/`INCOMPLETE`), `ratio` (máximo), `errors` y `checks`: una
comprobación por demanda (`axial`, `flexure_x_3`, `flexure_y_2`, `flexure_w`, `flexure_z`,
`shear_y_2`, `shear_x_3`) más `interaction` (Capítulo H) cuando actúan juntas fuerza axial y
flexión o flexión en dos ejes, con `chapter`, `demand`,
`capacity` (φRn), `ratio`, `status`, `obligations` y `result` con `classification`, `provisions`, `modes`
(Fe, Fn, área, Pn y ecuaciones por modo), `governing_mode`, `Pn_kN`,
`available_kN` (φPn, LRFD), `notes` y `limitations`. Un dominio no soportado o con
datos faltantes devuelve `INCOMPLETE` con el motivo; nunca una resistencia supuesta.

## Documentación

- [Arquitectura](docs/architecture.md)
- [Ejes y signos (convención de ETABS)](docs/axes.md)
- [Capítulo D: alcance, verificación y decisiones](docs/chapter-d.md)
- [Capítulo E: alcance, familias, verificación y decisiones](docs/chapter-e.md)
- [Verificación con los AISC Design Examples v16.0](docs/design-examples.md)
- [Capítulo F: alcance, verificación, decisiones e incidencias del catálogo](docs/chapter-f.md)
- [Capítulo G: alcance, verificación y decisiones](docs/chapter-g.md)
- [Capítulo H: alcance, verificación y decisiones](docs/chapter-h.md)
- [Capítulo I: alcance, verificación y decisiones](docs/chapter-i.md)
- [Apéndice 4: incendio por el método simple](docs/appendix-4.md)
- [AISC Design Guides 6 y 38](docs/design-guides.md)
- [Pruebas y validación](CONTRIBUTING.md)
- [Hoja de ruta](docs/ROADMAP.md)
