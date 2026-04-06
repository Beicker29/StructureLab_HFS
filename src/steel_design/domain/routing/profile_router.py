from typing import List

# These will be populated as we refactor/add the rules
from ..rules.flexure_rule import FlexureRule
from ..rules.tension_rule import TensionRule
from ..rules.axial_rules import AxialE3Rule, AxialE4Rule, AxialE5Rule, AxialE7Rule
from ..rules.placeholders import ShearRule, InteractionRule

# Definición de Nomenclatura Estándar para los Perfiles
class ProfileType:
    W_SHAPE = "W"
    DOUBLE_ANGLE = "DOUBLE_ANGLE"
    RECTANGULAR_HSS = "RECTANGULAR_HSS"
    CIRCULAR_HSS = "CIRCULAR_HSS"
    SINGLE_ANGLE = "SINGLE_ANGLE"
    WT_SHAPE = "WT"
    FILLED_RECTANGULAR = "FILLED_RECTANGULAR"
    FILLED_CIRCULAR = "FILLED_CIRCULAR"

# Registro de Reglas disponibles en la Aplicación
RULE_REGISTRY = {
    # Tensión
    "D2": TensionRule,
    
    # Compresión
    "E3": AxialE3Rule,
    "E4": AxialE4Rule,
    "E5": AxialE5Rule,
    "E7": AxialE7Rule,
    
    # Flexión
    "F2": FlexureRule, # To be refactored to F2
    # "F9": FlexureF9Rule,
    
    # Otros Limites Provisionales
    "G2": ShearRule,
    "H1": InteractionRule,
}

# Mapeo Declarativo: Asignación de Reglas por Perfil (Según AISC 360)
PROFILE_RULE_MAP = {
    ProfileType.W_SHAPE: ["D2", "E3", "E4", "E7", "F2", "G2", "H1"],
    ProfileType.DOUBLE_ANGLE: ["D2", "E3", "E4", "E7", "G2", "H1"], # Falta F9
    ProfileType.RECTANGULAR_HSS: ["D2", "E3", "E4", "E7", "G2", "H1"], # Falta F7, G4
    ProfileType.CIRCULAR_HSS: ["D2", "E3", "E4", "E7", "G2", "H1"], # Falta F8, G5
    ProfileType.SINGLE_ANGLE: ["D2", "E3", "E5", "E7", "G2", "H1"], # Falta F10
    ProfileType.WT_SHAPE: ["D2", "E3", "E4", "E7", "G2", "H1"], # Falta F9
    ProfileType.FILLED_RECTANGULAR: ["E3", "E4", "E7", "H1"], # Compresión Compuesta (I2)
    ProfileType.FILLED_CIRCULAR: ["E3", "E4", "E7", "H1"], # Compresión Compuesta (I2)
}

class ProfileRouter:
    """
    Ruteador puro declarativo: Configura y devuelve los checks aplicables dependindo del perfil.
    Asume que todos los rules en el registro siguen el contrato de instanciarse sin argumentos.
    """
    @staticmethod
    def get_rules(section) -> List:
        rule_ids = PROFILE_RULE_MAP.get(section.type.upper(), [])
        
        rules = []
        for r_id in rule_ids:
            rule_class = RULE_REGISTRY.get(r_id)
            if rule_class:
                rules.append(rule_class())
            else:
                # Opcional: Podría arrojar una excepción si la regla no existe en el registro
                pass
                
        return rules
