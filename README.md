# StructureLab_HFS

Motor de cálculo de la **resistencia a compresión de miembros de acero** según
ANSI/AISC 360-22, capítulo E (`a360-22w.pdf`, erratas de enero 2025 y septiembre
2026 en el repositorio; ninguna modifica el capítulo E). Perfiles del catálogo
`data/sections.xlsx` (base AISC v16 métrica + PTE) o barras macizas definidas en
la entrada.

El resultado es estructurado y en memoria: familia, clasificación B4.1a,
disposiciones aplicadas, cada modo de pandeo con sus variables y ecuaciones,
resistencia nominal gobernante, resistencias disponibles LRFD y ASD, obligaciones
normativas y limitaciones. Está pensado para que una futura aplicación web llame
directamente al motor.

> No es una certificación AISC global. `PASS` significa que se evaluaron todos los
> estados límite del capítulo E exigidos para el miembro y que `Pu ≤ φPn` (o
> `Pn/Ω`). Las longitudes efectivas, combinaciones de carga, conexiones y demás
> capítulos quedan fuera del alcance.

## Instalación

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Uso

```powershell
python -m steel_design.run examples/w_shape_case.json            # imprime JSON
python -m steel_design.run examples/bundle_case.json --output r.json
```

No se escribe nada en disco salvo con `--output`. Desde Python:

```python
from steel_design.engine import SteelDesignEngine
from steel_design.models import SteelCase
from steel_design.sections.loader import load_sections_from_excel
from steel_design.sections.repository import SectionRepository

repo = SectionRepository()
repo.load(load_sections_from_excel("data/sections.xlsx"))
result = SteelDesignEngine(repo).run(SteelCase(
    section_name="C15X50", design_method="LRFD", material={"Fy": 345}, Pu=300,
    lengths={"Lx": 4000, "Ly": 1000, "Lz": 4000}))
print(result.status, result.capacity_kN, result.compression["governing_mode"])  # PASS 2254.31 FTB
```

### Entrada (unidades: mm, MPa, kN)

| Campo | Descripción |
| --- | --- |
| `section_name` | Nombre del catálogo, o nombre libre con `custom_section` |
| `material.Fy`, `material.E` | `E` debe ser 200000 MPa (definición de E3) |
| `Pu` | Resistencia requerida a compresión (> 0) |
| `lengths.Lx/Ly/Lz` | Longitudes no arriostradas por eje y torsional |
| `factors.Kx/Ky/Kz` | Factores K (por defecto 1); `xa`, `ya`: desplazamiento del arriostramiento respecto al centro de corte (E4(d)/(e)) |
| `design_method` | `LRFD` (φc = 0,90) o `ASD` (Ωc = 1,67) |
| `single_angle_e5` | Requerido para ángulos simples: configuración E5(a)/(b), ala conectada, `L` entre puntos de trabajo y las condiciones E5(1)–(3) |
| `custom_section` | `SOLID_RECTANGULAR` (`H`, `B`) o `SOLID_CIRCULAR` (`diameter`) |

Un lote `{"cases": [...]}` comparte los campos de nivel superior.

### Salida

`status` (`PASS`/`FAIL`/`INCOMPLETE`), `capacity_kN`, `ratio`, `obligations`,
`errors` y `compression` con `classification`, `provisions`, `modes`
(Fe, Fn, área, Pn y ecuaciones por modo), `governing_mode`, `Pn_kN`,
`available` (LRFD y ASD), `notes` y `limitations`. Un dominio no soportado o con
datos faltantes devuelve `INCOMPLETE` con el motivo; nunca una resistencia supuesta.

## Documentación

- [Arquitectura](docs/architecture.md)
- [Alcance normativo del capítulo E, familias, decisiones y pendientes](docs/chapter-e.md)
- [Pruebas y validación](CONTRIBUTING.md)
- [Hoja de ruta](docs/ROADMAP.md)
