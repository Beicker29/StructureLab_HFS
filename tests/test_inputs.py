"""Input contract: invalid or ambiguous cases are rejected before any calculation."""
import pytest
from pydantic import ValidationError

from steel_design.errors import ValidationError as DomainValidationError
from steel_design.models import SteelCase

BASE = {"section_name": "W14X90", "material": {"Fy": 345}, "Pu": 100,
        "lengths": {"Lx": 1000, "Ly": 1000, "Lz": 1000}}
E5 = {"configuration": "a", "connected_leg": "long", "L": 2000, "loaded_at_ends_through_same_leg": True,
      "welded_or_two_bolts_min": True, "no_intermediate_transverse_loads": True}


def case(**changes):
    return SteelCase(**{**BASE, **changes})


def test_valid_case_defaults():
    c = case()
    assert (c.design_method.value, c.factors.Kx, c.material.E) == ("LRFD", 1.0, 200000.0)


@pytest.mark.parametrize("changes", [
    {"Pu": 0}, {"Pu": -10}, {"Pu": float("nan")}, {"Pu": "100"},          # compression demand only
    {"material": {"Fy": 0}}, {"lengths": {"Lx": 1000, "Ly": 1000}},
    {"factors": {"Kx": 0}}, {"factors": {"ya": -1}},
    {"design_method": "LFRD"}, {"Mux": 1}, {"loads": {"Pu": 1}},          # unknown fields
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
