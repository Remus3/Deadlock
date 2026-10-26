"""vw_dpi: DPI from counts, nearest R110 step, sensitivity for eDPI 1920."""
import vw_dpi as D


def test_dpi_from_counts_10cm():
    assert round(D.dpi_from_counts(3150, 10)) == 800
    assert round(D.dpi_from_counts(-4724, 10)) == 1200


def test_nearest_step():
    assert D.nearest_step(760) == 800
    assert D.nearest_step(1310) == 1200
    assert D.nearest_step(1500) == 1600


def test_sensitivity_for_edpi_1920():
    assert D.sensitivity_for(800) == 2.4
    assert D.sensitivity_for(1200) == 1.6
    assert D.sensitivity_for(1600) == 1.2
