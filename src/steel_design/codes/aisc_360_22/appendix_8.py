"""ANSI/AISC 360-22 Appendix 8, Section 8.1: approximate second-order elastic analysis. Units N, mm. LRFD (alpha = 1.0)."""
import math

ALPHA = 1.0


def cm_factor(*, M1_M2=None) -> float:
    """A-8-4; with transverse load between supports (no M1/M2 given), conservatively 1.0 (8.1.2(b))."""
    return 1.0 if M1_M2 is None else 0.6 - 0.4 * M1_M2


def member_buckling_load(*, EI_star, Lc1) -> float:
    """A-8-5."""
    return math.pi**2 * EI_star / Lc1**2


def b1_factor(*, Cm, Pr, Pe1) -> float:
    """A-8-3. Taken as 1.0 for members not subjected to compression."""
    return max(Cm / (1 - ALPHA * Pr / Pe1), 1.0) if Pr > 0 else 1.0


def story_buckling_load(*, Pstory, Pmf, H, L, drift) -> float:
    """A-8-7 and A-8-8."""
    return (1 - 0.15 * (Pmf / Pstory)) * H * L / drift


def b2_factor(*, Pstory, Pe_story) -> float:
    """A-8-6."""
    return max(1 / (1 - ALPHA * Pstory / Pe_story), 1.0)


def required_strengths(*, B1, B2, Mnt, Mlt, Pnt, Plt) -> dict:
    """A-8-1 and A-8-2."""
    return {"Mr": B1 * Mnt + B2 * Mlt, "Pr": Pnt + B2 * Plt}
