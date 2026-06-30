"""Tests for picmaker.enhancement: apply_colormap LUT application."""

import numpy as np
import pytest

from picmaker.enhancement import apply_colormap


class TestApplyColormap:
    """Test apply_colormap function for grayscale and color LUT application."""

    def test_grayscale_no_colormap_returns_float_3d_one_band(self) -> None:
        """Test that grayscale input without colormap returns 3D float array."""
        arr = np.linspace(0.0, 1.0, 9, dtype=np.float64).reshape(3, 3)
        out = apply_colormap(arr, (0.0, 1.0), histogram=False, colormap=None)
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
        out = apply_colormap(arr, (0.0, 2.0), histogram=False, colormap=lut)
        assert out.shape == (1, 3, 1)
        assert out[0, 0, 0] == 0.0
        assert out[0, -1, 0] == 1.0

    def test_three_entry_color_lut_returns_rgb(self) -> None:
        """Test that a color LUT produces 3-band RGB output."""
        # A LUT with at least one non-grayscale entry triggers a 3-band output.
        arr = np.array([[0.0, 0.5, 1.0]])
        lut = [(0, 0, 0), (255, 0, 0), (255, 255, 255)]
        out = apply_colormap(arr, (0.0, 1.0), histogram=False, colormap=lut)
        assert out.shape == (1, 3, 3)
        # First pixel → black; last → white.
        np.testing.assert_allclose(out[0, 0], [0.0, 0.0, 0.0])
        np.testing.assert_allclose(out[0, -1], [1.0, 1.0, 1.0])
        # Middle pixel → pure red (255, 0, 0) → (1.0, 0.0, 0.0).
        np.testing.assert_allclose(out[0, 1], [1.0, 0.0, 0.0])


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


def test_apply_colormap_two_stop_list() -> None:
    """A two-stop colormap ``['red', 'blue']`` builds an RGB output that
    interpolates along the red-blue line."""
    arr = np.arange(8, dtype='uint8').reshape(2, 4)
    out = apply_colormap(arr, (0.0, 7.0), colormap=['red', 'blue'])
    assert out.shape == (2, 4, 3)
    assert out.dtype == np.float64
    # Every pixel lies on the red <-> blue line: the green channel is zero
    # and the red and blue channels sum to one.
    np.testing.assert_allclose(out[..., 1], 0.0)
    np.testing.assert_allclose(out[..., 0] + out[..., 2], 1.0)
    # Red fades out and blue grows monotonically as the input ramps up.
    red = out[..., 0].ravel()
    blue = out[..., 2].ravel()
    assert np.all(np.diff(red) < 0)
    assert np.all(np.diff(blue) > 0)
