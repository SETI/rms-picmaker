"""Enhancement-stage tests: get_limits, _percentile_lookup, apply_colormap."""

from __future__ import annotations

import numpy as np

from picmaker.picmaker import (
    _percentile_lookup,
    apply_colormap,
    get_limits,
)


class TestGetLimits:
    """Test get_limits function for histogram range calculation."""

    def test_full_range_integer_extends_half_pixel(self, tiny_array) -> None:
        """Verify that integer arrays extend histogram by 0.5 on each side."""
        # For integer arrays, get_limits extends the histogram from 0.5 below
        # min to 0.5 above max so the histogram is bucketed correctly.
        lo, hi = get_limits(tiny_array, mask=None)
        assert lo == -0.5
        assert hi == 255.5

    def test_explicit_limits_passes_through(self, tiny_array) -> None:
        """Verify that explicit limits parameter is passed through unchanged."""
        lo, hi = get_limits(tiny_array, mask=None, limits=(10, 200))
        assert (lo, hi) == (10, 200)

    def test_percentile_band(self) -> None:
        """Test percentile-based limit calculation on a 0-255 ramp."""
        # Deterministic 256-pixel uint8 ramp: 0..255.
        arr = np.arange(256, dtype=np.uint8).reshape(16, 16)
        lo, hi = get_limits(arr, mask=None, percentiles=(5.0, 95.0))
        # 5/95 percentiles of 0..255 land at 12.3 and 242.7 (verified).
        assert abs(lo - 12.3) < 0.5
        assert abs(hi - 242.7) < 0.5


class TestPercentileLookup:
    """Test _percentile_lookup interpolation function."""

    def test_p_below_zero_returns_low(self) -> None:
        """Verify that percentiles below 0 clamp to the low value."""
        assert _percentile_lookup(-1.0, [0, 50, 100], [10, 50, 90], (10, 90)) == 10

    def test_p_above_hundred_returns_high(self) -> None:
        """Verify that percentiles above 100 clamp to the high value."""
        assert _percentile_lookup(150.0, [0, 50, 100], [10, 50, 90], (10, 90)) == 90

    def test_interpolation_midpoint(self) -> None:
        """Test exact match at 50% percentile."""
        # 50% maps exactly to 50 (the table value)
        v = _percentile_lookup(50.0, [0, 50, 100], [10, 50, 90], (10, 90))
        assert v == 50

    def test_interpolation_between_points(self) -> None:
        """Test linear interpolation between percentile table points."""
        # 25% between [0, 50] → np.interp gives 30 (10 + 25/50 * 40)
        v = _percentile_lookup(25.0, [0, 50, 100], [10, 50, 90], (10, 90))
        assert v == 30.0


class TestApplyColormap:
    """Test apply_colormap function for grayscale and color LUT application."""

    def test_grayscale_no_colormap_returns_float_3d_one_band(self) -> None:
        """Test that grayscale input without colormap returns 3D float array."""
        arr = np.linspace(0.0, 1.0, 9, dtype=np.float64).reshape(3, 3)
        out = apply_colormap(arr, limits=(0.0, 1.0), histogram=False, colormap=None)
        # apply_colormap returns 3-D float in 0-1; one band when grayscale.
        assert out.dtype == np.float64
        assert out.shape == (3, 3, 1)
        # 0 → 0, 1 → 1 at the endpoints
        assert out[0, 0, 0] == 0.0
        assert out[-1, -1, 0] == 1.0

    def test_three_entry_grayscale_lut_applied(self) -> None:
        """Test that a grayscale LUT produces single-band output."""
        # 3-entry LUT (black/gray/white) is all-grayscale, so result shape is
        # (1, 3, 1) and values are 0..1 (scaled).
        arr = np.array([[0.0, 1.0, 2.0]])
        lut = [(0, 0, 0), (128, 128, 128), (255, 255, 255)]
        out = apply_colormap(arr, limits=(0.0, 2.0), histogram=False, colormap=lut)
        assert out.shape == (1, 3, 1)
        assert out[0, 0, 0] == 0.0
        assert out[0, -1, 0] == 1.0

    def test_three_entry_color_lut_returns_rgb(self) -> None:
        """Test that a color LUT produces 3-band RGB output."""
        # A LUT with at least one non-grayscale entry triggers a 3-band output.
        arr = np.array([[0.0, 0.5, 1.0]])
        lut = [(0, 0, 0), (255, 0, 0), (255, 255, 255)]
        out = apply_colormap(arr, limits=(0.0, 1.0), histogram=False, colormap=lut)
        assert out.shape == (1, 3, 3)
        # First pixel → black; last → white.
        np.testing.assert_allclose(out[0, 0], [0.0, 0.0, 0.0])
        np.testing.assert_allclose(out[0, -1], [1.0, 1.0, 1.0])
        # Middle pixel → pure red (255, 0, 0) → (1.0, 0.0, 0.0).
        np.testing.assert_allclose(out[0, 1], [1.0, 0.0, 0.0])
