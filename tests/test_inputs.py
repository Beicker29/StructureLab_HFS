"""Input contract: invalid or ambiguous cases are rejected before any calculation."""
import pytest
from pydantic import ValidationError

from steel_design.errors import SteelDesignError
from steel_design.errors import ValidationError as DomainValidationError
from steel_design.execution import prepare_cases
from steel_design.materials import material_catalog
from steel_design.models import SteelCase

BASE = {"section_name": "W14X90", "material": {"Fy": 345}, "Pu": 100,
        "lengths": {"Lx": 1000, "Ly": 1000, "Lz": 1000}}
E5 = {"configuration": "a", "connected_leg": "long", "L": 2000, "loaded_at_ends_through_same_leg": True,
      "welded_or_two_bolts_min": True, "no_intermediate_transverse_loads": True}


def case(**changes):
    return SteelCase(tau_b=1.0, **{**BASE, **changes})


def test_valid_case_defaults():
    c = case()
    assert (c.factors.Kx, c.material.E) == (1.0, 200000.0)


@pytest.mark.parametrize("changes", [
    {"Pu": 0}, {"Pu": float("nan")}, {"Pu": "100"},                      # nonzero finite number
    {"lengths": None},                                                    # compression needs lengths
    {"material": {"Fy": 345, "Fu": 300}},                                 # Fu < Fy
    {"Pu": -10, "tension": {"An": 1000, "U": 1.2}},                       # U <= 1
    {"material": {"Fy": 0}}, {"lengths": {"Lx": 1000, "Ly": 1000}},
    {"factors": {"Kx": 0}}, {"factors": {"ya": -1}},
    {"design_method": "ASD"}, {"Mt": 1}, {"loads": {"Pu": 1}},            # unknown fields (LRFD only)
    {"custom_section": {"type": "SOLID_CIRCULAR", "H": 10, "B": 10}},
    {"single_angle_e5": {**E5, "configuration": "c"}},
])
def test_invalid_inputs_are_rejected(changes):
    with pytest.raises(ValidationError):
        case(**changes)


@pytest.mark.parametrize("missing", sorted(E5))
def test_single_angle_e5_basis_requires_every_fact(missing):
    with pytest.raises(ValidationError):
        case(single_angle_e5={k: v for k, v in E5.items() if k != missing})


def test_engine_requires_e_200000(engine):
    with pytest.raises(DomainValidationError):
        engine.run(case(material={"Fy": 345, "E": 210000}))


CATALOG = {"ASTM A572 Gr 50": (345, 448), "ASTM A36": (248, 410), "ASTM A709 Gr 50": (345, 448), "ASTM A588": (345, 448),
           "ASTM A500 Gr C (SREC)": (345, 425), "ASTM A500 Gr B (SREC)": (315, 400), "ASTM A500 Gr C (SRED)": (345, 425),
           "ASTM A500 Gr B (SRED)": (290, 400), "ASTM A53 Gr B": (241, 413)}


@pytest.mark.parametrize("name, values", CATALOG.items())
def test_json_material_is_a_name_of_the_catalog(name, values):
    (_, case), = prepare_cases({"section_name": "W14X90", "material": name, "Vux": 1})
    assert (case.material.Fy, case.material.Fu) == values and case.material.name == name


def test_catalog_has_exactly_the_expected_materials():
    assert set(material_catalog()) == set(CATALOG)


@pytest.mark.parametrize(
    "material, code",
    [
        ("ASTM A992", "UNKNOWN_MATERIAL"),
        ({"Fy": 345}, "INVALID_MATERIAL"),
        ({"name": "ASTM A36", "Fy": 248, "Fu": 410}, "INVALID_MATERIAL"),
        (345, "INVALID_MATERIAL"),
    ],
)
def test_json_rejects_other_materials_and_numeric_values(material, code):
    with pytest.raises(SteelDesignError) as error:
        prepare_cases({"section_name": "W14X90", "material": material, "Vux": 1})
    assert error.value.code == code


def test_a_load_case_can_name_another_material():
    cases = prepare_cases(
        {"section_name": "W14X90", "material": "ASTM A36", "cases": [{"Vux": 1}, {"Vux": 1, "material": "ASTM A572 Gr 50"}]}
    )
    assert [c.material.Fy for _, c in cases] == [248, 345]


def test_a_named_material_meets_the_row_of_table_a31(engine):
    (_, case), = prepare_cases({"section_name": "W14X90", "material": "ASTM A36", "Vux": 1})
    row = next(r for r in engine.run(case).requirements["materials"] if r["provision"] == "A3.1a")
    assert row["status"] == "cumple" and row["value"] == "ASTM A36"
