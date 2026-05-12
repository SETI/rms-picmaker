"""Cover the enhance.py branches that the existing tests don't reach:
``get_limits`` corner cases (trim_zeros, footprint, trim with mask),
``apply_colormap`` invalid/below/above paths, named two-stop colormap,
and ``apply_gamma`` identity vs. squaring.
"""

import numpy as np
import pytest

from picmaker.enhance import apply_colormap, apply_gamma, get_limits


def test_get_limits_trim_zeros_recovers_when_all_zero() -> None:
    """``trim_zeros=True`` on an all-zero array falls back to the
    original trimmed array rather than returning empty bounds.
    """
    arr = np.zeros((4, 4), dtype='uint8')
    lo, hi = get_limits(arr, None, None, (0.0, 100.0), trim_zeros=True)
    # All-zero integer → array_min == array_max == 0; the
    # `array_min == array_max` branch returns (0, 1).
    assert lo == 0
    assert hi == 1


def test_get_limits_uniform_float_returns_unit_range() -> None:
    """A uniform float array of zero returns ``(0.0, 1.0)``."""
    arr = np.zeros((4, 4), dtype='float32')
    lo, hi = get_limits(arr, None, None, (0.0, 100.0))
    assert lo == 0.0
    assert hi == 1.0


def test_get_limits_uniform_negative_float_returns_negative_to_zero() -> None:
    """A uniform negative float array returns ``(value, 0.0)``."""
    arr = np.full((4, 4), -3.0, dtype='float32')
    lo, hi = get_limits(arr, None, None, (0.0, 100.0))
    assert lo == -3.0
    assert hi == 0.0


def test_get_limits_uniform_positive_float_doubles() -> None:
    """A uniform positive float array returns ``(value, 2*value)``."""
    arr = np.full((4, 4), 7.0, dtype='float32')
    lo, hi = get_limits(arr, None, None, (0.0, 100.0))
    assert lo == 7.0
    assert hi == 14.0


def test_get_limits_trim_zeros_strips_each_side() -> None:
    """``trim_zeros=True`` peels every all-zero exterior row and column."""
    arr = np.zeros((16, 16), dtype='uint16')
    arr[4:12, 4:12] = np.arange(64, dtype='uint16').reshape(8, 8) + 10
    lo, hi = get_limits(arr, None, None, (0.0, 100.0), trim_zeros=True)
    # After trimming the border, the inner values run from 10..73.
    assert lo == 10 - 0.5
    assert hi == 73 + 0.5


def test_get_limits_trim_zeros_with_mask() -> None:
    """``trim_zeros=True`` with a mask trims both arrays in lock-step."""
    arr = np.zeros((8, 8), dtype='uint16')
    arr[1:7, 1:7] = 100
    mask = np.zeros_like(arr, dtype=bool)
    mask[3, 3] = True
    lo, hi = get_limits(arr, mask, None, (0.0, 100.0), trim_zeros=True)
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
    lo, hi = get_limits(arr, None, None, (0.0, 100.0), footprint=3)
    # The 3x3 circular median of a single-outlier array is zero
    # everywhere (the outlier is outvoted), so the filtered min and
    # max both collapse to 0 and `hi` lands exactly at 0.
    assert lo == 0
    assert hi == 0


def test_get_limits_with_trim() -> None:
    """``trim=N`` excludes ``N`` pixels around the edge."""
    arr = np.arange(256, dtype='uint16').reshape(16, 16)
    lo, hi = get_limits(arr, None, None, (0.0, 100.0), trim=4)
    # After trimming the 4-pixel border, the inner 8x8 block runs from
    # arr[4, 4] = 68 to arr[11, 11] = 187; integer limits extend by
    # 0.5 on each side.
    assert lo == 67.5
    assert hi == 187.5


def test_apply_colormap_with_invalid_mask() -> None:
    """An ``invalid_mask`` paints the masked pixels with ``invalid_color``."""
    arr = np.arange(64, dtype='uint8').reshape(8, 8)
    mask = np.zeros_like(arr, dtype=bool)
    mask[0, 0] = True
    out = apply_colormap(
        arr,
        (0.0, 63.0),
        invalid_mask=mask,
        invalid_color='red',
    )
    # The masked pixel is the red triplet (1, 0, 0) in normalized form.
    assert out[0, 0, 0] == pytest.approx(1.0)
    assert out[0, 0, 1] == pytest.approx(0.0)
    assert out[0, 0, 2] == pytest.approx(0.0)


def test_apply_colormap_below_above_colors() -> None:
    """``below_color`` / ``above_color`` paint out-of-range pixels."""
    arr = np.array([[0, 50, 100, 200]], dtype='uint8')
    out = apply_colormap(
        arr,
        (50.0, 100.0),
        below_color='blue',
        above_color='red',
    )
    # arr[0, 0]=0 < lower → blue (0,0,1)
    np.testing.assert_allclose(out[0, 0], (0.0, 0.0, 1.0))
    # arr[0, 3]=200 > upper → red (1,0,0)
    np.testing.assert_allclose(out[0, 3], (1.0, 0.0, 0.0))


def test_apply_colormap_named_two_stop() -> None:
    """A named two-stop colormap (e.g. ``red-blue``) builds an RGB output."""
    arr = np.arange(8, dtype='uint8').reshape(2, 4)
    out = apply_colormap(arr, (0.0, 7.0), colormap='red-blue')
    assert out.shape == (2, 4, 3)
    assert out.dtype == np.float64
    # Two-stop ``'red-blue'`` linearly interpolates from
    # ``red = (1, 0, 0)`` at value 0 to ``blue = (0, 0, 1)`` at value 7
    # for each input pixel. The middle (green) channel stays at 0.
    frac = (arr / 7.0).astype(np.float64)
    expected = np.zeros((2, 4, 3), dtype=np.float64)
    expected[..., 0] = 1.0 - frac
    expected[..., 2] = frac
    np.testing.assert_allclose(out, expected)


def test_apply_gamma_identity_is_noop() -> None:
    """``gamma == 1.0`` returns the array unchanged."""
    arr = np.linspace(0, 1, 16).reshape(4, 4)
    out = apply_gamma(arr, 1.0)
    assert out is arr


def test_apply_gamma_two_squares() -> None:
    """``gamma == 2.0`` raises each value to the 2nd power."""
    arr = np.linspace(0, 1, 16).reshape(4, 4)
    out = apply_gamma(arr.copy(), 2.0)
    np.testing.assert_allclose(out, arr**2)
