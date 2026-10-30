from ..evaluators.compression_evaluator import flexural_components, torsional_components, evaluate_compression

from ...tracing import traced_rule, emit_step, quantity
from ..design_methods import require_case_method
from ..evaluators.compression_domain import compression_classification, require_compression_domain
from ...codes.aisc_360_22 import axial_calc
from ...models import CheckResult, CheckStatus, SteelCase
from ...sections.models import Section


def _compression_demand(case: SteelCase) -> float:
    return max(0.0, case.loads.Pu)


def _pass_result(name: str, clause: str) -> CheckResult:
    return CheckResult(name=name, clause=clause, demand=0.0, capacity=0.0, dcr=0.0, status=CheckStatus.PASS)


def _result(name: str, clause: str, demand: float, capacity: float, details: dict | None = None) -> CheckResult:
    return CheckResult.from_values(
        unit='kN',
        name=name,
        clause=clause,
        demand=demand,
        capacity=capacity,
        details=details,
    )


# Compatibility alias; E1 owns both conversion and factor trace.
_design_factor = axial_calc.compression_design_factor




def _fcr_branch_info(Fy: float, Fe: float) -> dict:
    if Fy <= 0.0 or Fe <= 0.0:
        return {"fy_over_fe": None, "branch": "invalid"}
    ratio = Fy / Fe
    branch = "inelastic_E3_2" if ratio <= 2.25 else "elastic_E3_3"
    return {"fy_over_fe": ratio, "branch": branch}






def _compression_details(case: SteelCase, section: Section) -> dict:
    return {"element_classification": compression_classification(case, section)}


class AxialE3Rule:
    """Flexural buckling of members without slender elements (E3)."""

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case)
        demand = _compression_demand(case)
        if demand <= 0.0:
            return _pass_result("Axial Compression E3", "E3")

        require_compression_domain(case, section, reference="E3")
        components = flexural_components(case, section)
        fe = components["fe_governing_mpa"]
        fcr = axial_calc.calculate_Fcr(case.material.Fy, fe)
        pn = axial_calc.calculate_Pn(fcr, section.area)
        capacity = axial_calc.calculate_available_compressive_strength(pn, case.design_method)
        emit_step(producer=__name__+":AxialE3Rule.check", limit_state="flexural_buckling",
            branch=None, reference="E3", equation=None, expression=None, axis=components["governing_axis"],
            inputs=(quantity("Fy", case.material.Fy, "MPa", "case.material.Fy"),
                    quantity("Ag", section.area, "mm2", "section.area")),
            intermediates=(quantity("Fe", fe, "MPa"), quantity("Fcr", fcr, "MPa"), quantity("Pn", pn, "N")),
            outputs=(quantity("available", capacity, "kN"),),
            unknowns=("E3 stress branch/factors are not instrumented here; no branch reconstructed from Fy/Fe.",))
        details = _compression_details(case, section)
        details["memory"] = {
            "clause": "E3",
            "inputs": {
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "Ag_mm2": section.area,
                "Kx": case.factors.Kx,
                "Ky": case.factors.Ky,
                "Lx_mm": case.lengths.Lx,
                "Ly_mm": case.lengths.Ly,
                "rx_mm": section.rx,
                "ry_mm": section.ry,
            },
            "intermediate": {
                "KL_over_r_x": components["klr_x"],
                "KL_over_r_y": components["klr_y"],
                "governing_axis": components["governing_axis"],
                "Fex_mpa": components["fe_x_mpa"],
                "Fey_mpa": components["fe_y_mpa"],
                "Fe_mpa": components["fe_governing_mpa"],
                **_fcr_branch_info(case.material.Fy, components["fe_governing_mpa"]),
                "fcr_mpa": fcr,
                "pn_n": pn,
                "pn_kn": pn / 1000.0,
                "be_mm": None,
                "be_note": "Not required in current E3 implementation.",
            },
            "design_factor": _design_factor(case.design_method),
            "capacity_kn": capacity,
        }
        return _result(
            "Axial Compression (Flexural Buckling)",
            "E3-1",
            demand,
            capacity,
            details=details,
        )


class AxialE4Rule:
    """Torsional and flexural-torsional buckling (E4)."""

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case)
        demand = _compression_demand(case)
        if demand <= 0.0:
            return _pass_result("Axial Compression E4", "E4")

        require_compression_domain(case, section, reference="E4")
        components = torsional_components(case, section)
        fe = components["fe_governing_mpa"]
        fcr = axial_calc.calculate_Fcr(case.material.Fy, fe)
        pn = axial_calc.calculate_Pn(fcr, section.area)
        capacity = axial_calc.calculate_available_compressive_strength(pn, case.design_method)
        details = _compression_details(case, section)
        emit_step(producer=__name__+":AxialE4Rule.check", limit_state=components["e4_mode"],
            branch="channel_x_symmetry" if section.type.upper() == "CHANNEL" else "double_symmetry",
            reference="E4", equation="E4-3" if section.type.upper() == "CHANNEL" else "E4-2",
            expression=None, axis="x" if section.type.upper() == "CHANNEL" else "z",
            inputs=(quantity("Fex", components["fe_x_mpa"], "MPa"),
                    quantity("Fey", components["fe_y_mpa"], "MPa"),
                    quantity("Fez", components["fe_z_mpa"], "MPa")),
            intermediates=(quantity("Fe", fe, "MPa"), quantity("Fn", fcr, "MPa"), quantity("Pn", pn, "N")),
            outputs=(quantity("available", capacity, "kN"),),
            unknowns=("Local E4 mode does not discharge all member obligations.",))
        details["memory"] = {
            "clause": "E4",
            "inputs": {
                "Fy_mpa": case.material.Fy,
                "E_mpa": case.material.E,
                "G_mpa": axial_calc.NORMATIVE_G_MPA,
                "Ag_mm2": section.area,
                "Kz": case.factors.Kz,
                "Lz_mm": case.lengths.Lz,
                "Ky": case.factors.Ky,
                "Ly_mm": case.lengths.Ly,
                "ry_mm": section.ry,
                "J_mm4": section.j,
                "Cw_mm6": section.cw,
                "H": section.H,
                "xa_mm": case.factors.xa,
                "ya_mm": case.factors.ya,
            },
            "intermediate": {
                "KL_over_r_x": components["klr_x"],
                "KL_over_r_y": components["klr_y"],
                "KL_over_r_z": components["klr_z"],
                "ro_mm": components["ro_mm"],
                "ro_source": components["ro_source"],
                "Fex_mpa": components["fe_x_mpa"],
                "Fey_mpa": components["fe_y_mpa"],
                "Fez_mpa": components["fe_z_mpa"],
                "Fe_mpa": components["fe_governing_mpa"],
                "e4_mode": components["e4_mode"],
                "warping_term_n": components["warping_term_n"],
                "stvenant_term_n": components["stvenant_term_n"],
                "torsional_stiffness_n": components["torsional_stiffness_n"],
                "torsional_denominator_mm4": components["torsional_denominator_mm4"],
                "flexural_torsional_terms": components["flexural_torsional_terms"],
                **_fcr_branch_info(case.material.Fy, components["fe_governing_mpa"]),
                "fcr_mpa": fcr,
                "pn_n": pn,
                "pn_kn": pn / 1000.0,
                "be_mm": None,
                "be_note": "be is not explicitly modeled in current E4 implementation.",
            },
            "design_factor": _design_factor(case.design_method),
            "capacity_kn": capacity,
        }
        return _result("Axial Compression (Torsional/Flexural-Torsional)", "E4-1", demand, capacity, details=details)


class AxialE5Rule:
    """Single-angle compression members (E5)."""

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case)
        demand = _compression_demand(case)
        if demand <= 0.0:
            return _pass_result("Axial Compression E5", "E5")

        require_compression_domain(case, section, reference="E5")


class AxialE7Rule:
    """Members with slender elements (E7)."""

    @traced_rule
    def check(self, case: SteelCase, section: Section) -> CheckResult:
        require_case_method(case)
        demand = _compression_demand(case)
        if demand <= 0.0:
            return _pass_result("Axial Compression E7", "E7")

        require_compression_domain(case, section, reference="E7")
        evaluation = evaluate_compression(case, section)
        capacity = evaluation['available_kN']
        for mode, values in evaluation['modes'].items():
            emit_step(producer=__name__+':AxialE7Rule.check', limit_state='local_global_buckling',
                branch=mode, reference='E7.2' if section.type.upper() == 'CIRCULAR_HSS' else 'E7.1',
                equation='E7-1', expression='Pn = Fn * Ae', axis=values['elastic'].get('governing_axis', 'z'),
                inputs=(quantity('Fn', values['Fn_mpa'], 'MPa'), quantity('Ae', values['area']['Ae_mm2'], 'mm2')),
                intermediates=(quantity('Pn', values['Pn_N'], 'N'),),
                outputs=(quantity('available', values['available_kN'], 'kN'),), unknowns=())
        return _result('Axial Compression (Effective Area)', 'E7-1', demand, capacity, details={
            'element_classification': evaluation['classification'], 'compression_evaluation': evaluation,
            'memory': {'clause': 'E7', 'inputs': {'Fy_mpa': case.material.Fy, 'E_mpa': case.material.E,
                'Ag_mm2': section.area}, 'intermediate': evaluation['modes'],
                'design_factor': evaluation['design_factor'], 'capacity_kn': capacity,
                'governing_mode': evaluation['governing_mode']}})
