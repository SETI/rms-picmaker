"""Tests for picmaker.stretch: get_limits histogram-range calculation."""

from typing import Any

import numpy as np

from picmaker.stretch import _circle_mask, get_limits


class TestGetLimits:
    """Test get_limits function for histogram range calculation."""

    def test_full_range_integer_returns_exact_min_max(self, tiny_array: Any) -> None:
        """With no limits or percentiles, get_limits returns the exact data
        min and max."""
        lo, hi = get_limits(tiny_array, mask=None)
        assert lo == 0
        assert hi == 255

    def test_explicit_limits_passes_through(self, tiny_array: Any) -> None:
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


class TestCircleMask:
    """Test the _circle_mask disk helper used by the footprint median filter."""

    def test_diameter_1(self) -> None:
        # diameter=1: ceil(1) = size 1; r2[0,0]=0 <= 0.25 → True; mask[0].sum()=1.
        mask = _circle_mask(1)
        assert mask.shape == (1, 1)
        assert mask[0, 0] == np.bool_(True)

    def test_diameter_3(self) -> None:
        # diameter=3: size=3, all radii <= 2 are <= 2.25, so mask is all True.
        mask = _circle_mask(3)
        assert mask.shape == (3, 3)
        assert mask.all()

    def test_diameter_5(self) -> None:
        mask = _circle_mask(5)
        assert mask.shape == (5, 5)
        assert mask[2, 2]
        assert not mask[0, 0]
        assert mask[2, 0]
        assert mask[0, 2]
        assert mask[4, 2]
        assert mask[2, 4]

    def test_diameter_8(self) -> None:
        mask = _circle_mask(8)
        assert mask.shape == (8, 8)
        # center band True
        assert mask[3, 3]
        assert mask[4, 4]

    def test_diameter_9(self) -> None:
        mask = _circle_mask(9)
        assert mask.shape == (9, 9)
        assert mask[4, 4]
        assert not mask[0, 0]


def test_get_limits_trim_zeros_recovers_when_all_zero() -> None:
    """``trim_zeros=True`` on an all-zero array falls back to the
    original trimmed array rather than returning empty bounds.
    """
    arr = np.zeros((4, 4), dtype='uint8')
    lo, hi = get_limits(arr, None, percentiles=(0.0, 100.0), trim_zeros=True)
    # All-zero integer → array_min == array_max == 0; the
    # `array_min == array_max` branch returns (0, 1).
    assert lo == 0
    assert hi == 1


def test_get_limits_uniform_float_returns_unit_range() -> None:
    """A uniform float array of zero returns ``(0.0, 1.0)``."""
    arr = np.zeros((4, 4), dtype='float32')
    lo, hi = get_limits(arr, None, percentiles=(0.0, 100.0))
    assert lo == 0.0
    assert hi == 1.0


def test_get_limits_uniform_negative_float_returns_negative_to_zero() -> None:
    """A uniform negative float array returns ``(value, 0.0)``."""
    arr = np.full((4, 4), -3.0, dtype='float32')
    lo, hi = get_limits(arr, None, percentiles=(0.0, 100.0))
    assert lo == -3.0
    assert hi == 0.0


def test_get_limits_uniform_positive_float_doubles() -> None:
    """A uniform positive float array returns ``(value, 2*value)``."""
    arr = np.full((4, 4), 7.0, dtype='float32')
    lo, hi = get_limits(arr, None, percentiles=(0.0, 100.0))
    assert lo == 7.0
    assert hi == 14.0


def test_get_limits_trim_zeros_strips_each_side() -> None:
    """``trim_zeros=True`` peels every all-zero exterior row and column."""
    arr = np.zeros((16, 16), dtype='uint16')
    arr[4:12, 4:12] = np.arange(64, dtype='uint16').reshape(8, 8) + 10
    lo, hi = get_limits(arr, None, percentiles=(0.0, 100.0), trim_zeros=True)
    # After trimming the border, the inner values run from 10..73; with
    # percentiles (0, 100) the limits are the exact min and max.
    assert lo == 10
    assert hi == 73


def test_get_limits_trim_zeros_with_mask() -> None:
    """``trim_zeros=True`` with a mask trims both arrays in lock-step."""
    arr = np.zeros((8, 8), dtype='uint16')
    arr[1:7, 1:7] = 100
    mask = np.zeros_like(arr, dtype=bool)
    mask[3, 3] = True
    lo, hi = get_limits(arr, mask, percentiles=(0.0, 100.0), trim_zeros=True)
    # The border rows / columns are trimmed away, leaving a 6x6 inner
    # block that is uniform 100 except for the single masked cell. The
    # ``array_min == array_max`` branch in get_limits returns
    # ``(value, value + 1)`` for integer dtypes.
    assert lo == 100
    assert hi == 101


def test_get_limits_with_footprint_filter() -> None:
    """``footprint=N`` applies a median filter that narrows the limits."""
    arr = np.zeros((16, 16), dtype='uint16')
    arr[8, 8] = 200  # single outlier
    lo, hi = get_limits(arr, None, percentiles=(0.0, 100.0), footprint=3)
    # The 3x3 circular median of a single-outlier array is zero everywhere
    # (the outlier is outvoted), so array_min == array_max == 0 and the
    # single-value-zero branch returns (0, 1).
    assert lo == 0
    assert hi == 1


def test_get_limits_with_trim() -> None:
    """``trim=N`` excludes ``N`` pixels around the edge."""
    arr = np.arange(256, dtype='uint16').reshape(16, 16)
    lo, hi = get_limits(arr, None, percentiles=(0.0, 100.0), trim=4)
    # After trimming the 4-pixel border, the inner 8x8 block runs from
    # arr[4, 4] = 68 to arr[11, 11] = 187; percentiles (0, 100) give the
    # exact min and max.
    assert lo == 68
    assert hi == 187
