"""Load convention shared by selection and checks (docs/contracts/hfs013-axes.md).

Historical suffixes x/y identify bending planes, not force-vector directions:
Vux acts along local y and accompanies Mux; Vuy acts along local x and
accompanies Muy. Vu is the scalar alias of the first plane, never a resultant.
"""


def shear_component(case, axis: str) -> str:
    if axis not in {"x", "y"}:
        raise ValueError("Shear bending-plane axis must be x or y")
    if axis == "x" and not (case.loads.Vux or case.loads.Vuy):
        return "Vu"
    return "Vux" if axis == "x" else "Vuy"


def shear_demand(case, axis: str) -> float:
    return abs(getattr(case.loads, shear_component(case, axis)))


def shear_trace(case, axis: str) -> dict:
    component = shear_component(case, axis)
    return {"input_component": component, "signed_demand_kN": getattr(case.loads, component),
            "bending_axis": axis, "force_direction": "local_y" if axis == "x" else "local_x",
            "axis_convention": "HFS-013-bending-plane-suffix", "demand_unit": "kN"}
