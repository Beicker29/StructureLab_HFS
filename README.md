# StructureLab_HFS

Motor de cálculo de la **resistencia de miembros de acero** según ANSI/AISC 360-22,
solo LRFD: capítulos D (tracción), E (compresión), F (flexión), G (cortante), H
(interacción de fuerza axial y flexión) e I (miembros compuestos: PTE rellenos, W embebidos, vigas,
muros de placas y anclajes de componentes)
(`a360-22w.pdf` y erratas de enero 2025 y septiembre 2026 del repositorio). Perfiles del catálogo
`data/sections.xlsx` (base AISC v16 métrica + PTE) o barras macizas definidas en
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
python -m steel_design.run examples/composite_method2.json --output results/composite_method2.json --report --pdf
python -m steel_design.run examples/composite_wall.json --output results/composite_wall.json --report --pdf
python -m steel_design.run examples/composite_anchor.json --output results/composite_anchor.json --report --pdf
```

Quite `--output ...` si solo necesita las memorias; sin ningún argumento adicional el resultado se
imprime en pantalla y no se escribe nada.

Desde Python:

```python
from steel_design.engine import SteelDesignEngine
from steel_design.models import SteelCase
from steel_design.sections.loader import load_sections_from_excel
from steel_design.sections.repository import SectionRepository

repo = SectionRepository()
repo.load(load_sections_from_excel("data/sections.xlsx"))
result = SteelDesignEngine(repo).run(SteelCase(
    section_name="C15X50", material={"Fy": 345}, Pu=300,
    lengths={"Lx": 4000, "Ly": 1000, "Lz": 4000}))
print(result.status, result.capacity_kN, result.compression["governing_mode"])  # PASS 2254.31 FTB
```

La memoria se obtiene del mismo resultado, sin recalcular:
`blocks = report_blocks(case, result)` (modelo del documento), `render_text(blocks)`
(texto) y `pdf_bytes([blocks, ...])` (PDF en memoria, p. ej. para una respuesta web),
todos en `steel_design.reporting`. El PDF usa una fuente Unicode del sistema
(DejaVu Sans, Segoe UI o Arial) para φ, λ y Σ; sin ella recurre a Helvetica con
símbolos escritos en letras.

### Entrada (unidades: mm, MPa, kN)

| Campo | Descripción |
| --- | --- |
| `section_name` | Nombre del catálogo, o nombre libre con `custom_section` |
| `material.Fy`, `material.Fu`, `material.E` | Fu es obligatorio en tracción; `E` debe ser 200000 MPa en compresión (definición de E3) |
| `Pu` | Resistencia requerida de la combinación LRFD: > 0 compresión (capítulo E), < 0 tracción (capítulo D) |
| `Mux`, `Muy` | Momentos requeridos de la combinación (kN·m) respecto de los ejes geométricos, capítulo F |
| `Mw`, `Mz` | Solo ángulos simples: momentos respecto de los ejes principales mayor y menor (kN·m), F10 |
| `Vux`, `Vuy` | Cortantes requeridos (kN) que acompañan a `Mux` (paralelo a y, alma) y a `Muy` (paralelo a x), capítulo G |
| `lengths.Lx/Ly/Lz` | Longitudes no arriostradas por eje y torsional (obligatorias en compresión) |
| `tension` | Tracción: `An` (área neta, B4.3b, mm²), `U` (Tabla D3.1) y opcional `fabricated_length` (nota D1); An y U los aporta el usuario |
| `factors.Kx/Ky/Kz` | Factores K (por defecto 1); `xa`, `ya`: desplazamiento del arriostramiento respecto al centro de corte (E4(d)/(e)) |
| `single_angle_e5` | Ángulos simples comprimidos sin `Mw` ni `Mz`: configuración E5(a)/(b), ala conectada, `L` entre puntos de trabajo y las condiciones E5(1)–(3). Fuera de E5 se omite y la excentricidad se da como `Mw` y `Mz` (H2) |
| `double_angle_e6` | Requerido para ángulos dobles: `connectors` (`snug_tight`, `welded`, `pretensioned`), separación `a` entre conectores (mm) y `end_connection_welded_or_pretensioned` (E6.1). Contacto o separadores se leen del nombre AISC (`2L4X4X1/4` vs `2L4X4X1/4X3/4`) |
| `flexure` | Flexión: `Lb` (mm), `Cb` (1.0 si se omite), `tension_flange_holes` (obligatorio en I y canales, eje x), `Afn` (mm²); en ángulos simples `lateral_torsional_restraint` (`none`, `at_max_moment`, `continuous`; ejes geométricos) y `beta_w` (mm, F10-4, alas desiguales); `tension_cb_amplification` (H1.2, opcional) |
| `shear` | Cortante: `Lv` (mm, PTE redondos, G5-2a; opcional) |
| `angle_flexure` | Por combinación: `web_legs` (2L: alas verticales en `tension`/`compression`), `toe` (L: punta en `compression`/`tension`), `leg_in_compression` (L, eje w: `long`/`short`). En H2 fijan el signo de las tensiones en A, B y C |
| `custom_section` | `SOLID_RECTANGULAR` (`H`, `B`) o `SOLID_CIRCULAR` (`diameter`) |
| `composite` | Capítulo I: `kind` (`filled`, `encased`, `beam`, `wall`), `concrete` (`fc`, `wc`, `lightweight`), `interaction` (`H1`, `I5`, `M2`, `M2S`), `encased`, `beam` o `wall` según el tipo, y `anchor` para un anclaje I8.3 ([detalle](docs/chapter-i.md)) |

**Un archivo por miembro.** Los campos de nivel superior describen el miembro (perfil,
material, longitudes, `tension`, E5/E6) y `cases` lista sus combinaciones de
carga; cada combinación aporta su demanda y puede sobrescribir cualquier dato. La salida
trae un resultado por combinación, el estado global y la combinación `governing` (mayor
relación demanda/capacidad). Cada combinación lleva sus demandas simultáneas (Pu, Mu, Vu);
Pr y Mr deben venir de un análisis de segundo orden (Capítulo C, decisión DH-3).
Ver `examples/` (un archivo por familia y `multi_member.json` con varios perfiles).

### Salida

`status` (`PASS`/`FAIL`/`INCOMPLETE`), `ratio` (máximo), `errors` y `checks`: una
comprobación por demanda (`axial`, `flexure_x`, `flexure_y`, `flexure_w`, `flexure_z`,
`shear_x`, `shear_y`) más `interaction` (Capítulo H) cuando actúan juntas fuerza axial y
flexión o flexión en dos ejes, con `chapter`, `demand`,
`capacity` (φRn), `ratio`, `status`, `obligations` y `result` con `classification`, `provisions`, `modes`
(Fe, Fn, área, Pn y ecuaciones por modo), `governing_mode`, `Pn_kN`,
`available_kN` (φPn, LRFD), `notes` y `limitations`. Un dominio no soportado o con
datos faltantes devuelve `INCOMPLETE` con el motivo; nunca una resistencia supuesta.

## Documentación

- [Arquitectura](docs/architecture.md)
- [Capítulo D: alcance, verificación y decisiones](docs/chapter-d.md)
- [Capítulo E: alcance, familias, verificación y decisiones](docs/chapter-e.md)
- [Verificación con los AISC Design Examples v16.0](docs/design-examples.md)
- [Capítulo F: alcance, verificación, decisiones e incidencias del catálogo](docs/chapter-f.md)
- [Capítulo G: alcance, verificación y decisiones](docs/chapter-g.md)
- [Capítulo H: alcance, verificación y decisiones](docs/chapter-h.md)
- [Pruebas y validación](CONTRIBUTING.md)
- [Hoja de ruta](docs/ROADMAP.md)
