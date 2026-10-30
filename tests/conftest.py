from pathlib import Path

import pytest

from steel_design.engine import SteelDesignEngine
from steel_design.models import SteelCase
from steel_design.sections.loader import load_sections_from_excel
from steel_design.sections.repository import SectionRepository

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/sections.xlsx"


@pytest.fixture(scope="session")
def catalog():
    return load_sections_from_excel(str(CATALOG))


@pytest.fixture(scope="session")
def sections(catalog):
    return {s.name: s for s in catalog}


@pytest.fixture(scope="session")
def engine(catalog):
    repository = SectionRepository()
    repository.load(catalog)
    return SteelDesignEngine(repository)


def steel_case(name="W14X90", *, Pu=100, L=3000, Ly=None, Lz=None, Fy=345, **extra):
    return SteelCase(section_name=name, material={"Fy": Fy}, Pu=Pu,
                     lengths={"Lx": L, "Ly": Ly or L, "Lz": Lz or L}, **extra)
