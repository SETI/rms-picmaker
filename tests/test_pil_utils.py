"""Tests for :func:`array_to_pil` and :func:`pil_to_array` round-trip conversion."""

import numpy as np

from picmaker.picmaker import array_to_pil, pil_to_array


class TestRoundTrip:
    """Test round-trip conversion between numpy arrays and PIL images."""

    def test_grayscale_round_trip(self) -> None:
        """Verify grayscale array converts to PIL and back unchanged."""
        arr = np.arange(64, dtype=np.uint8).reshape(8, 8)
        img = array_to_pil(arr, rescale=False)
        back = pil_to_array(img, rescale=False)
        np.testing.assert_array_equal(back, arr)

    def test_rgb_round_trip(self) -> None:
        """Verify RGB array converts to PIL and back unchanged."""
        arr = np.zeros((8, 8, 3), dtype=np.uint8)
        arr[..., 0] = np.arange(64).reshape(8, 8)
        arr[..., 1] = 128
        arr[..., 2] = 200
        img = array_to_pil(arr, rescale=False)
        back = pil_to_array(img, rescale=False)
        np.testing.assert_array_equal(back, arr)

    def test_rescale_grayscale_returns_uint8_bug(self) -> None:
        """Document bug where rescale=True is ignored for grayscale images."""
        # Pre-PR3 bug at picmaker.py:3029-3034: _one_pil_to_array returns BEFORE
        # the `if rescale: array.astype(float)/255` line, so for 'L' mode
        # images, rescale=True is a no-op. Document the current behavior here.
        arr = np.arange(64, dtype=np.float64).reshape(8, 8)
        img = array_to_pil(arr, rescale=True)
        back = pil_to_array(img, rescale=True)
        assert back.dtype == np.uint8
        assert back.max() == 255  # not 1.0
