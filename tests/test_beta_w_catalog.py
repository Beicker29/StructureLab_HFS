"""Catalog column βw (sheet L) against Commentary Table C-F10.1, whose averages are in mm for each pair of legs."""
import pytest

TABLE_C_F10_1 = {(203, 152): 84.1, (203, 102): 139, (178, 102): 111, (152, 102): 79.8, (152, 88.9): 93.7, (127, 88.9): 61.0,
                 (127, 76.2): 75.9, (102, 88.9): 22.1, (102, 76.2): 41.9, (88.9, 76.2): 22.1, (88.9, 63.5): 41.1,
                 (76.2, 63.5): 21.8, (76.2, 50.8): 39.6, (63.5, 50.8): 21.6, (63.5, 38.1): 37.8}


def test_catalog_beta_w_matches_the_commentary_table(catalog):
    angles = [s for s in catalog if s.type == "SINGLE_ANGLE"]
    assert all(s.beta_w is not None for s in angles)
    for section in angles:
        legs = (max(section.d, section.b), min(section.d, section.b))
        if legs[0] == legs[1]:
            assert section.beta_w == 0, section.name
        else:
            assert section.beta_w == pytest.approx(TABLE_C_F10_1[legs], rel=0.02), section.name


def test_other_families_have_no_beta_w(catalog):
    assert all(s.beta_w is None for s in catalog if s.type != "SINGLE_ANGLE")
