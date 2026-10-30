# StructureLab_HFS

Motor de cálculo de la **resistencia axial de miembros de acero** según
ANSI/AISC 360-22: capítulo D (tracción) y capítulo E (compresión) (`a360-22w.pdf`;
las erratas de enero 2025 y septiembre 2026 del repositorio no modifican D ni E). Perfiles del catálogo
`data/sections.xlsx` (base AISC v16 métrica + PTE) o barras macizas definidas en
la entrada.

El resultado es estructurado y en memoria: familia, clasificación B4.1a,
disposiciones aplicadas, cada modo de pandeo con sus variables y ecuaciones,
resistencia nominal gobernante, resistencia de diseño LRFD (φPn), obligaciones
normativas y limitaciones. Está pensado para que una futura aplicación web llame
directamente al motor.

> No es una certificación AISC global. `PASS` significa que se evaluaron todos los
> estados límite del capítulo aplicable (D o E) exigidos para el miembro y que
> `|Pu| ≤ φPn`. El programa trabaja solo con LRFD. Las longitudes efectivas, combinaciones de carga, conexiones y demás
> capítulos quedan fuera del alcance.

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
| `lengths.Lx/Ly/Lz` | Longitudes no arriostradas por eje y torsional (obligatorias en compresión) |
| `tension` | Tracción: `An` (área neta, B4.3b, mm²), `U` (Tabla D3.1) y opcional `fabricated_length` (nota D1); An y U los aporta el usuario |
| `factors.Kx/Ky/Kz` | Factores K (por defecto 1); `xa`, `ya`: desplazamiento del arriostramiento respecto al centro de corte (E4(d)/(e)) |
| `single_angle_e5` | Requerido para ángulos simples: configuración E5(a)/(b), ala conectada, `L` entre puntos de trabajo y las condiciones E5(1)–(3) |
| `double_angle_e6` | Requerido para ángulos dobles: `connectors` (`snug_tight`, `welded`, `pretensioned`), separación `a` entre conectores (mm) y `end_connection_welded_or_pretensioned` (E6.1). Contacto o separadores se leen del nombre AISC (`2L4X4X1/4` vs `2L4X4X1/4X3/4`) |
| `custom_section` | `SOLID_RECTANGULAR` (`H`, `B`) o `SOLID_CIRCULAR` (`diameter`) |

**Un archivo por miembro.** Los campos de nivel superior describen el miembro (perfil,
material, longitudes, `tension`, E5/E6) y `cases` lista sus combinaciones de
carga; cada combinación aporta su demanda y puede sobrescribir cualquier dato. La salida
trae un resultado por combinación, el estado global y la combinación `governing` (mayor
relación demanda/capacidad). Cuando se incorporen flexión, cortante e interacción, cada
combinación llevará sus demandas simultáneas (Pu, Mu, Vu) en el mismo archivo.
Ver `examples/` (un archivo por familia y `multi_member.json` con varios perfiles).

### Salida

`status` (`PASS`/`FAIL`/`INCOMPLETE`), `capacity_kN`, `ratio`, `obligations`,
`errors` y `compression` con `classification`, `provisions`, `modes`
(Fe, Fn, área, Pn y ecuaciones por modo), `governing_mode`, `Pn_kN`,
`available_kN` (φPn, LRFD), `notes` y `limitations`. Un dominio no soportado o con
datos faltantes devuelve `INCOMPLETE` con el motivo; nunca una resistencia supuesta.

## Documentación

- [Arquitectura](docs/architecture.md)
- [Capítulo D: alcance, verificación y decisiones](docs/chapter-d.md)
- [Capítulo E: alcance, familias, verificación y decisiones](docs/chapter-e.md)
- [Pruebas y validación](CONTRIBUTING.md)
- [Hoja de ruta](docs/ROADMAP.md)
