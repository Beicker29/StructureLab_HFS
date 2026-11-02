"""E and G of structural steel, as ANSI/AISC 360-22 defines them (E3, E4, G2.1(a), I1.5, I2.1b). MPa."""
E_STEEL = 200000.0
G_STEEL = 77200.0


def is_standard_modulus(E: float) -> bool:
    return abs(E - E_STEEL) <= 1e-6
