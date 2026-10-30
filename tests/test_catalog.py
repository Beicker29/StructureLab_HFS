"""data/sections.xlsx import: families, AISC metric units, B4 ratios and identity."""
import pytest

from steel_design.domain.errors import AmbiguousSectionError
from steel_design.sections.repository import SectionRepository


def test_all_six_catalog_families_are_loaded(catalog):
    families = {s.type for s in catalog}
    assert families == {"W", "CHANNEL", "RECTANGULAR_HSS", "CIRCULAR_HSS", "SINGLE_ANGLE", "DOUBLE_ANGLE"}
    assert all(s.source is not None and s.source.sheet for s in catalog)


def test_aisc_metric_units_are_scaled_to_mm(sections):
    w = sections["W14X90"]  # AISC v16 metric: A mm2, Ix 10^6 mm4, J 10^3 mm4, Cw 10^9 mm6
    assert (w.area, w.ix, w.iy, w.j, w.cw) == (17100.0, 416e6, 151e6, 1690e3, 4300e9)
    assert w.rx == pytest.approx((w.ix / w.area) ** 0.5, rel=0.01)  # internal consistency


def test_hss_ratios_use_design_thickness_and_outside_diameter(sections):
    rect = sections["PTE50X30X1.5MM"]
    assert rect.b_tdes_ratio == pytest.approx(rect.b / rect.tdes)
    assert rect.b == pytest.approx(30 - 3 * rect.tdes)  # B4.1b(d), corner radius unknown
    rnd = sections['PTER4"X3.00MM']
    assert rnd.d_t_ratio == pytest.approx(rnd.od / rnd.tdes)  # B4.1b(g): D outside, t design


def test_channel_and_angle_shape_data(sections):
    channel = sections["C15X50"]
    assert channel.b_t_ratio == pytest.approx(channel.bf / channel.tf, rel=0.01)  # full flange width
    assert channel.ro > 0 and 0 < channel.H <= 1
    angle = sections["L8X4X1"]
    assert max(angle.d, angle.b) / angle.t == pytest.approx(angle.b_t_ratio, rel=0.01)  # longest leg
    assert angle.rx > angle.ry > angle.rz


def test_repository_rejects_ambiguous_identities(sections):
    repo = SectionRepository()
    w = sections["W14X90"]
    repo.load([w, w.model_copy(update={"area": 1.0})])
    with pytest.raises(AmbiguousSectionError):
        repo.get("w14x90")
    assert repo.get("W99X1") is None
