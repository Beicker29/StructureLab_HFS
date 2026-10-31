"""Names, in words, of everything the calculation report prints; no calculation here.

PARAMETERS: key of a limit-state result -> (description, symbol, unit).
EQUATION_OF: value key -> key of the same result that holds its equation.
FIXED_LITERALS: values whose literal does not depend on the result, checked against a360-22w.pdf.
Every other value of a limit state takes the provision of that limit state.
"""

PARAMETERS = {
    # Chapter D
    "An_mm2": ("Área neta", "An", "mm²"), "U": ("Factor de rezago de cortante", "U", "–"),
    "Ae_mm2": ("Área neta efectiva", "Ae", "mm²"), "area_mm2": ("Área resistente", "A", "mm²"),
    "stress_mpa": ("Esfuerzo resistente", "F", "MPa"), "phi_t": ("Factor de resistencia en tracción", "φt", "–"),
    "Pn_kN": ("Resistencia nominal axial", "Pn", "kN"), "available_kN": ("Resistencia de diseño", "φ·Rn", "kN"),
    "available_kNm": ("Resistencia de diseño a flexión", "φb·Mn", "kN·m"),
    # Chapter E
    "Cw_mm6": ("Constante de alabeo", "Cw", "mm⁶"), "J_mm4": ("Constante torsional", "J", "mm⁴"),
    "Fe_mpa": ("Esfuerzo de pandeo elástico", "Fe", "MPa"), "Fe_torsion_mpa": ("Esfuerzo de pandeo elástico torsional", "Fe,t", "MPa"),
    "Few_mpa": ("Esfuerzo de pandeo elástico respecto del eje principal w", "Few", "MPa"),
    "Fex_mpa": ("Esfuerzo de pandeo elástico respecto de x", "Fex", "MPa"),
    "Fey_mpa": ("Esfuerzo de pandeo elástico respecto de y", "Fey", "MPa"),
    "Fez_mpa": ("Esfuerzo de pandeo elástico torsional", "Fez", "MPa"),
    "Fez_axis_mpa": ("Esfuerzo de pandeo elástico respecto del eje principal z", "Fez,eje", "MPa"),
    "Fn_mpa": ("Esfuerzo nominal", "Fn", "MPa"), "Fy_over_Fe": ("Relación entre fluencia y pandeo elástico", "Fy/Fe", "–"),
    "H": ("Constante flexotorsional", "H", "–"), "Ki": ("Factor de conectores", "Ki", "–"),
    "L_mm": ("Longitud entre puntos de trabajo", "L", "mm"), "Lc_mm": ("Longitud efectiva", "Lc", "mm"),
    "Lc_over_r": ("Esbeltez efectiva", "Lc/r", "–"), "Lc_over_r_o": ("Esbeltez del miembro armado sin modificar", "(Lc/r)o", "–"),
    "Lcz_mm": ("Longitud efectiva torsional", "Lcz", "mm"), "a_over_ri": ("Esbeltez del componente entre conectores", "a/ri", "–"),
    "connected_leg": ("Ala conectada", "", "–"), "leg_ratio": ("Relación entre alas larga y corta", "bl/bs", "–"),
    "r_mm": ("Radio de giro", "r", "mm"), "ra_mm": ("Radio de giro respecto del eje paralelo al ala conectada", "ra", "mm"),
    "ro2_mm2": ("Radio de giro polar respecto del centro de corte, al cuadrado", "r̄o²", "mm²"),
    "ro_mm": ("Radio de giro polar respecto del centro de corte", "r̄o", "mm"),
    "ro_from_geometry_mm": ("Radio de giro polar obtenido de la geometría", "r̄o,geom", "mm"),
    "rw_mm": ("Radio de giro respecto del eje principal w", "rw", "mm"), "rz_mm": ("Radio de giro respecto del eje principal z", "rz", "mm"),
    "symmetry_axis": ("Eje de simetría", "", "–"), "wo_mm": ("Coordenada w del centro de corte", "wo", "mm"),
    "zo_mm": ("Coordenada z del centro de corte", "zo", "mm"), "xa_mm": ("Desplazamiento del arriostramiento en x", "xa", "mm"),
    "ya_mm": ("Desplazamiento del arriostramiento en y", "ya", "mm"),
    # Chapter F
    "Afg_mm2": ("Área bruta del ala traccionada", "Afg", "mm²"), "Afn_mm2": ("Área neta del ala traccionada", "Afn", "mm²"),
    "B": ("Coeficiente de pandeo lateral-torsional del ángulo doble", "B", "–"),
    "Cb": ("Factor de modificación por pandeo lateral-torsional", "Cb", "–"), "Cb_used": ("Factor de modificación usado, limitado a 1.5", "Cb", "–"),
    "Fcr_mpa": ("Esfuerzo crítico", "Fcr", "MPa"), "FuAfn": ("Resistencia a rotura del ala neta", "Fu·Afn", "N"),
    "I_eff": ("Momento de inercia efectivo", "Ieff", "mm⁴"), "Lb_d_over_t2": ("Parámetro de esbeltez de la barra", "Lb·d/t²", "–"),
    "Lb_mm": ("Longitud no arriostrada lateralmente", "Lb", "mm"), "Lp_mm": ("Longitud límite para fluencia", "Lp", "mm"),
    "Lr_mm": ("Longitud límite para pandeo inelástico", "Lr", "mm"), "Mcr": ("Momento de pandeo elástico", "Mcr", "N·mm"),
    "Mcr_factor": ("Factor sobre el momento de pandeo elástico", "", "–"), "My": ("Momento de fluencia", "My", "N·mm"),
    "My_factor": ("Factor sobre el momento de fluencia", "", "–"), "Sc": ("Módulo elástico a la punta comprimida", "Sc", "mm³"),
    "Se": ("Módulo elástico efectivo", "Se", "mm³"), "Yt": ("Coeficiente de rotura del ala", "Yt", "–"),
    "YtFyAfg": ("Resistencia a fluencia del ala bruta", "Yt·Fy·Afg", "N"), "area_removed_mm2": ("Área no efectiva", "(b−be)·t", "mm²"),
    "b_mm": ("Ancho del elemento", "b", "mm"), "be_mm": ("Ancho efectivo", "be", "mm"),
    "beta_w_mm": ("Propiedad de sección del ángulo, con signo", "βw", "mm"), "c": ("Coeficiente de pandeo lateral-torsional", "c", "–"),
    "c_compression_mm": ("Distancia a la fibra comprimida", "c", "mm"), "d_web_leg_mm": ("Ancho del ala vertical", "d", "mm"),
    "neutral_axis_shift_mm": ("Desplazamiento del eje neutro", "", "mm"), "note": ("Observación", "", "–"),
    "rts_mm": ("Radio de giro efectivo", "rts", "mm"), "t_mm": ("Espesor del elemento", "t", "mm"),
    # Chapter G
    "Ag_mm2": ("Área bruta", "Ag", "mm²"), "Aw_mm2": ("Área del alma", "Aw", "mm²"),
    "Cv1": ("Coeficiente de resistencia a cortante del alma", "Cv1", "–"), "Cv2": ("Coeficiente de pandeo por cortante del alma", "Cv2", "–"),
    "D_t": ("Relación diámetro-espesor", "D/t", "–"), "Fcr": ("Esfuerzo crítico a cortante", "Fcr", "MPa"),
    "Fcr_G5_2a": ("Esfuerzo crítico por Ec. G5-2a", "Fcr", "MPa"), "Fcr_G5_2b": ("Esfuerzo crítico por Ec. G5-2b", "Fcr", "MPa"),
    "Lv_mm": ("Distancia del cortante máximo al cortante nulo", "Lv", "mm"), "Vn_kN": ("Resistencia nominal a cortante", "Vn", "kN"),
    "Vn_per_flange_N": ("Resistencia nominal de un ala", "Vn", "N"), "flanges": ("Alas que resisten", "", "–"),
    "h_mm": ("Ancho que resiste el cortante", "h", "mm"), "legs": ("Alas del ángulo que resisten", "", "–"),
    "phi_v": ("Factor de resistencia a cortante", "φv", "–"),
    # Chapter H
    "Mcw_kNm": ("Resistencia de diseño a flexión en w", "Mcw", "kN·m"), "Mcx_basis": ("Base de la resistencia a flexión", "", "–"),
    "Mcx_kNm": ("Resistencia de diseño a flexión en x", "Mcx", "kN·m"), "Mcy_kNm": ("Resistencia de diseño a flexión en y", "Mcy", "kN·m"),
    "Mcz_kNm": ("Resistencia de diseño a flexión en z", "Mcz", "kN·m"), "Mrw_Mcw": ("Razón de flexión en w", "Mrw/Mcw", "–"),
    "Mrw_kNm": ("Resistencia requerida a flexión en w", "Mrw", "kN·m"), "Mrx_Mcx": ("Razón de flexión en x", "Mrx/Mcx", "–"),
    "Mrx_kNm": ("Resistencia requerida a flexión en x", "Mrx", "kN·m"), "Mry_Mcy": ("Razón de flexión en y", "Mry/Mcy", "–"),
    "Mry_kNm": ("Resistencia requerida a flexión en y", "Mry", "kN·m"), "Mrz_Mcz": ("Razón de flexión en z", "Mrz/Mcz", "–"),
    "Mrz_kNm": ("Resistencia requerida a flexión en z", "Mrz", "kN·m"), "Pc_kN": ("Resistencia axial de diseño", "Pc", "kN"),
    "Pr_Pc": ("Razón axial", "Pr/Pc", "–"), "Pr_kN": ("Resistencia axial requerida", "Pr", "kN"), "axial": ("Sentido de la fuerza axial", "", "–"),
    "coefficients_axis": ("Eje del que se toman cp y cm", "", "–"), "Mr_Mc_sum": ("Suma de razones de flexión", "Mrx/Mcx + Mry/Mcy", "–"),
    "location": ("Ubicación", "", "–"), "point": ("Punto de la sección", "", "–"), "ratio": ("Valor de la interacción", "", "–"),
    # Chapter I, Appendix 2, Design Guides
    "Ac_mm2": ("Área de concreto", "Ac", "mm²"), "Asr_mm2": ("Área de barras de refuerzo", "Asr", "mm²"),
    "Icx_mm4": ("Momento de inercia del concreto respecto de x", "Icx", "mm⁴"), "Icy_mm4": ("Momento de inercia del concreto respecto de y", "Icy", "mm⁴"),
    "Isrx_mm4": ("Momento de inercia de las barras respecto de x", "Isrx", "mm⁴"), "Isry_mm4": ("Momento de inercia de las barras respecto de y", "Isry", "mm⁴"),
    "Asa_mm2": ("Área del anclaje", "Asa", "mm²"), "Asw_mm2": ("Área de placas en la dirección del cortante", "Asw", "mm²"),
    "Av_mm2": ("Área de cortante del acero", "Av", "mm²"), "C1": ("Coeficiente de rigidez de embebidos", "C1", "–"),
    "C3": ("Coeficiente de rigidez de rellenos", "C3", "–"), "C_I1_1": ("Coeficiente de rigidez de muros", "0.35", "–"),
    "C_kN": ("Fuerza de compresión en la losa", "C", "kN"), "C_mm": ("Profundidad del bloque comprimido", "C", "mm"),
    "EI_eff": ("Rigidez efectiva a flexión", "(EI)eff", "N·mm²"), "EI_eff_T": ("Rigidez efectiva a flexión a temperatura elevada", "(EI)eff(T)", "N·mm²"),
    "Ec_mpa": ("Módulo de elasticidad del concreto", "Ec", "MPa"), "Kc": ("Factor de cortante del concreto", "Kc", "–"),
    "Ks_N": ("Rigidez a cortante de las placas", "Ks", "N"), "Ksc_N": ("Rigidez a cortante de placas y concreto", "Ksc", "N"),
    "L_over_tsc": ("Relación altura-espesor del muro", "L/tsc", "–"), "MB_kNm": ("Momento en el punto B", "MB", "kN·m"),
    "MD_kNm": ("Momento en el punto D", "MD", "kN·m"), "Mc_at_Pr_kNm": ("Resistencia de diseño a flexión con Pr", "Mc", "kN·m"),
    "Mc_kNm": ("Resistencia de diseño a flexión", "Mc", "kN·m"), "Mcr_kNm": ("Momento de agrietamiento o pandeo", "Mcr", "kN·m"),
    "Md_kNm": ("Momento de la sección a la distribución plástica", "Md", "kN·m"), "Mn_at_Pr_kNm": ("Resistencia nominal a flexión con Pr", "Mn", "kN·m"),
    "Mn_kNm": ("Resistencia nominal a flexión", "Mn", "kN·m"), "Mp_kNm": ("Momento plástico", "Mp", "kN·m"),
    "Mr_kNm": ("Resistencia requerida a flexión", "Mr", "kN·m"), "Msd_kNm": ("Momento de sección", "Msd", "kN·m"),
    "My_kNm": ("Momento de fluencia", "My", "kN·m"), "PA_kN": ("Carga en el punto A de interacción", "PA", "kN"),
    "PC_kN": ("Carga en el punto C de interacción", "PC", "kN"), "PNA": ("Posición del eje neutro plástico", "PNA", "–"),
    "Pe_T_kN": ("Carga de pandeo elástico a temperatura elevada", "Pe(T)", "kN"), "Pe_kN": ("Carga de pandeo elástico", "Pe", "kN"),
    "Pn_T_kN": ("Resistencia nominal a temperatura elevada", "Pn(T)", "kN"), "Pno_T_kN": ("Resistencia sin efectos de longitud a temperatura elevada", "Pno(T)", "kN"),
    "Pno_kN": ("Resistencia sin efectos de longitud", "Pno", "kN"), "Pno_over_Pe": ("Relación de resistencia y pandeo", "Pno/Pe", "–"),
    "Pu_over_Pn": ("Relación de carga en incendio", "Pu/Pn", "–"), "Pu_unit_kN": ("Carga por unidad de muro", "Pu", "kN"),
    "Qct_kN": ("Resistencia a tracción del anclaje en diseño", "Qct", "kN"), "Qcv_kN": ("Resistencia a cortante del anclaje en diseño", "Qcv", "kN"),
    "Qn_stud_kN": ("Resistencia nominal de un conector", "Qn", "kN"), "Qnt_kN": ("Resistencia nominal a tracción del anclaje", "Qnt", "kN"),
    "Qnv_kN": ("Resistencia nominal a cortante del anclaje", "Qnv", "kN"), "Qrt_kN": ("Tracción requerida del anclaje", "Qrt", "kN"),
    "Qrv_kN": ("Cortante requerido del anclaje", "Qrv", "kN"), "R_hours": ("Resistencia al fuego", "R", "h"),
    "Rg": ("Factor de grupo de conectores", "Rg", "–"), "Rp": ("Factor de posición de conectores", "Rp", "–"),
    "SumQn_kN": ("Resistencia total de los conectores", "ΣQn", "kN"), "Vp_crushing_kN": ("Fuerza de aplastamiento de la losa", "V'", "kN"),
    "Vp_steel_kN": ("Fuerza de fluencia del acero", "V'", "kN"), "Vr_kN": ("Fuerza longitudinal requerida", "Vr", "kN"),
    "Ycon_mm": ("Distancia del ala superior a la cara de la losa", "Ycon", "mm"), "a_cr_mm": ("Profundidad del bloque a Mcr", "acr", "mm"),
    "a_mm": ("Profundidad del bloque de compresión", "a", "mm"), "a_y_mm": ("Profundidad del bloque a My", "ay", "mm"),
    "alpha": ("Factor de forma", "α", "–"), "anchors_kN": ("Resistencia de transferencia por anclajes", "", "kN"),
    "bearing_kN": ("Resistencia de transferencia por aplastamiento", "", "kN"), "bond_kN": ("Resistencia de transferencia por adherencia", "", "kN"),
    "cm": ("Coeficiente de interacción de flexión", "cm", "–"), "cp": ("Coeficiente de interacción axial", "cp", "–"),
    "csr": ("Coeficiente de interacción de resistencia", "csr", "–"), "construction_available_kNm": ("Resistencia de diseño en construcción", "", "kN·m"),
    "degree_of_composite_action": ("Grado de acción compuesta", "", "–"), "epsilon_limit": ("Deformación límite controlada por tracción", "εlím", "–"),
    "epsilon_t": ("Deformación neta de tracción", "εt", "–"), "hn_mm": ("Posición del eje neutro plástico", "hn", "mm"),
    "lambda": ("Parámetro de resistencia", "λ", "–"), "mechanism": ("Mecanismo de transferencia", "", "–"),
    "phi_Pn_T_wall_kN": ("Resistencia de diseño del muro en incendio", "φPn(T)", "kN"), "ratio_design": ("Razón con resistencias de diseño", "", "–"),
    "ratio_nominal": ("Razón con resistencias nominales", "", "–"), "vent_area_mm2": ("Área de ventilación", "", "mm²"),
    "vent_required_d_mm": ("Diámetro requerido de ventilación", "d", "mm"), "x_mm": ("Posición del eje neutro plástico", "x", "mm"),
    "yn_mm": ("Posición del eje neutro elástico", "yn", "mm"), "b_eff_mm": ("Ancho efectivo de la losa", "b", "mm"),
}

EQUATION_OF = {
    "Ae_mm2": "Ae_equation", "Fe_torsion_mpa": "Fe_torsion_equation", "Fez_mpa": "Fez_equation", "Fe_mpa": "Fe_equation",
    "Fn_mpa": "Fn_equation", "Pn_kN": "Pn_equation", "Lc_over_r": "slenderness_equation", "B": "B_equation", "Mcr": "Mcr_equation",
    "be_mm": "be_equation", "Cv1": "Cv_equation", "Cv2": "Cv_equation", "Fcr": "Fcr_equation", "Pno_kN": "Pno_equation",
}

# Value key -> literal. Definitions printed in the text of a360-22w.pdf.
FIXED_LITERALS = {
    "Lc_mm": "E2", "Cb": "F1, Ec. F1-1", "Cb_used": "F10.2(1)", "rts_mm": "F2.2, Ec. F2-7", "c": "F2.2, Ec. F2-8",
    "C1": "I2.1b, Ec. I2-6", "C3": "I2.2b, Ec. I2-13", "C_I1_1": "I1.5(e), Ec. I1-1", "Ec_mpa": "I2.1b",
    "phi_t": "D2", "U": "D3, Tabla D3.1", "An_mm2": "B4.3b",
}

SECTION_PROPERTIES = {
    "area": ("Área bruta", "Ag"), "d": ("Peralte total", "d"), "h": ("Altura plana de la pared o del alma", "h"), "bf": ("Ancho del ala", "bf"),
    "b": ("Ancho plano de la pared o ancho del ala", "b"), "od": ("Diámetro exterior", "D"), "tf": ("Espesor del ala", "tf"),
    "t": ("Espesor nominal", "t"), "tdes": ("Espesor de diseño", "tdes"), "tw": ("Espesor del alma", "tw"),
    "ho": ("Distancia entre centroides de las alas", "ho"), "h_out": ("Altura exterior", "Ht"), "b_out": ("Ancho exterior", "B"),
    "ix": ("Momento de inercia respecto de x", "Ix"), "iy": ("Momento de inercia respecto de y", "Iy"),
    "iw": ("Momento de inercia respecto del eje principal w", "Iw"), "iz": ("Momento de inercia respecto del eje principal z", "Iz"),
    "sx": ("Módulo elástico respecto de x", "Sx"), "sy": ("Módulo elástico respecto de y", "Sy"),
    "zx": ("Módulo plástico respecto de x", "Zx"), "zy": ("Módulo plástico respecto de y", "Zy"),
    "sw_a": ("Módulo elástico en w, punto A", "SwA"), "sw_b": ("Módulo elástico en w, punto B", "SwB"), "sw_c": ("Módulo elástico en w, punto C", "SwC"),
    "sz_a": ("Módulo elástico en z, punto A", "SzA"), "sz_b": ("Módulo elástico en z, punto B", "SzB"), "sz_c": ("Módulo elástico en z, punto C", "SzC"),
    "rx": ("Radio de giro respecto de x", "rx"), "ry": ("Radio de giro respecto de y", "ry"), "rz": ("Radio de giro respecto de z", "rz"),
    "j": ("Constante torsional", "J"), "cw": ("Constante de alabeo", "Cw"), "ro": ("Radio de giro polar respecto del centro de corte", "r̄o"),
    "H": ("Constante flexotorsional", "H"), "x": ("Distancia del talón al centroide en x", "x̄"), "y": ("Distancia del talón al centroide en y", "ȳ"),
    "tan_alpha": ("Tangente del ángulo entre los ejes y, z", "tan α"), "beta_w": ("Propiedad de sección del ángulo, valor absoluto", "|βw|"),
    "bf_2tf_ratio": ("Esbeltez del ala", "bf/2tf"), "b_t_ratio": ("Relación ancho-espesor", "b/t"), "b_tdes_ratio": ("Relación ancho-espesor de diseño", "b/tdes"),
    "h_tw_ratio": ("Esbeltez del alma", "h/tw"), "h_tdes_ratio": ("Relación altura-espesor de diseño", "h/tdes"), "d_t_ratio": ("Relación diámetro-espesor", "D/t"),
}

STIFFNESS_NAMES = {
    "EA": "Rigidez axial", "EIx": "Rigidez a flexión respecto de x", "EIy": "Rigidez a flexión respecto de y",
    "EIw": "Rigidez a flexión respecto del eje principal w", "EIz": "Rigidez a flexión respecto del eje principal z",
    "GA": "Rigidez a cortante", "GJ": "Rigidez torsional", "ECw": "Rigidez de alabeo",
    "(EI)eff,x": "Rigidez efectiva a flexión respecto de x", "(EI)eff,y": "Rigidez efectiva a flexión respecto de y",
    "(EA)eff": "Rigidez axial efectiva", "(GA)eff": "Rigidez efectiva a cortante",
    "EA*": "Rigidez axial reducida para análisis directo", "GA*": "Rigidez a cortante reducida para análisis directo",
    "EI*x": "Rigidez a flexión reducida respecto de x", "EI*y": "Rigidez a flexión reducida respecto de y",
    "EA, EI, GA, GJ": "Rigideces elásticas",
    "τb": "Parámetro de reducción de rigidez",
    "GAs": "Rigidez a cortante del acero solo", "GAc": "Rigidez a cortante del concreto solo",
    "GJs": "Rigidez torsional del acero solo", "GJc": "Rigidez torsional del concreto solo",
    "GJs*": "Rigidez torsional del acero solo para análisis directo", "GJc*": "Rigidez torsional del concreto solo para análisis directo",
    "EI*w": "Rigidez a flexión reducida respecto del eje principal w", "EI*z": "Rigidez a flexión reducida respecto del eje principal z",
    "GJ*": "Rigidez torsional reducida para análisis directo", "ECw*": "Rigidez de alabeo reducida para análisis directo",
    "EA*, EI*, GA*, GJ*": "Rigideces reducidas para análisis directo", "(EI)eff, (EA)eff": "Rigideces efectivas", "(EI)eff, (EA)eff, (GA)eff": "Rigideces efectivas", "(EI)eff, EA": "Rigideces efectivas",
}

MODE_NAMES = {
    "FB-x": "pandeo por flexión respecto de x", "FB-y": "pandeo por flexión respecto de y", "FB-E5": "pandeo por flexión con la esbeltez de E5",
    "TB": "pandeo torsional", "FTB": "pandeo flexotorsional", "LB": "pandeo local", "TY": "fluencia en la sección bruta",
    "TR": "rotura en la sección neta", "V": "fluencia y pandeo por cortante",
}


def parameter_label(key: str) -> str:
    """Words and symbol: Área bruta (Ag). A key out of the glossary stays visible as it is, and a test forbids that case."""
    entry = PARAMETERS.get(key)
    if entry is None:
        return key
    description, symbol, _ = entry
    return f"{description} ({symbol})" if symbol else description
