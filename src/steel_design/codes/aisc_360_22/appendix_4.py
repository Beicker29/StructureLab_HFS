"""ANSI/AISC 360-22 Appendix 4, Section 4.2.3b: retention factors at elevated temperature. Temperatures in deg C."""
# T, kE, ky (Table A-4.2.1)
STEEL = ((20, 1.00, 1.00), (93, 1.00, 1.00), (200, 0.90, 1.00), (320, 0.78, 1.00), (400, 0.70, 1.00), (430, 0.67, 0.94),
         (540, 0.49, 0.66), (650, 0.22, 0.35), (760, 0.11, 0.16), (870, 0.07, 0.07), (980, 0.05, 0.04), (1100, 0.02, 0.02),
         (1200, 0.00, 0.00))
# T, kc normal weight, kc lightweight, kEc (Table A-4.2.2)
CONCRETE = ((20, 1.00, 1.00, 1.00), (93, 0.95, 1.00, 0.93), (200, 0.90, 1.00, 0.75), (290, 0.86, 1.00, 0.61),
            (320, 0.83, 0.98, 0.57), (430, 0.71, 0.85, 0.38), (540, 0.54, 0.71, 0.20), (650, 0.38, 0.58, 0.092),
            (760, 0.21, 0.45, 0.073), (870, 0.10, 0.31, 0.055), (980, 0.05, 0.18, 0.036), (1100, 0.01, 0.05, 0.018),
            (1200, 0.00, 0.00, 0.000))


def _interpolate(table, T, column) -> float:
    if T <= table[0][0]:
        return float(table[0][column])
    for low, high in zip(table, table[1:]):
        if T <= high[0]:
            return low[column] + (high[column] - low[column]) * (T - low[0]) / (high[0] - low[0])
    return float(table[-1][column])


def steel_factors(T) -> dict:
    return {"kE": _interpolate(STEEL, T, 1), "ky": _interpolate(STEEL, T, 2)}


def concrete_factors(T, *, lightweight) -> dict:
    return {"kc": _interpolate(CONCRETE, T, 2 if lightweight else 1), "kEc": _interpolate(CONCRETE, T, 3)}
