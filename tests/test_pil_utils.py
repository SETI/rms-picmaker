"""Tests for :func:`array_to_pil` and :func:`pil_to_array` round-trip conversion."""

import numpy as np

from picmaker import array_to_pil, pil_to_array


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

    def test_rescale_grayscale_returns_float_in_unit_range(self) -> None:
        """rescale=True returns a float array in [0, 1] for grayscale.

        Regression test for issue #10: ``_one_pil_to_array`` previously
        ignored ``rescale`` for ``'L'`` mode and returned a raw ``uint8``
        array.
        """
        arr = np.arange(64, dtype=np.float64).reshape(8, 8)
        img = array_to_pil(arr, rescale=True)
        back = pil_to_array(img, rescale=True)
        assert back.dtype == np.float64
        assert back.max() <= 1.0
