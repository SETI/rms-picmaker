"""Tests for picmaker.slicing: slice_array band/line/sample selection."""

import numpy as np

from picmaker.slicing import slice_array


class TestSliceArray:
    def test_band_average(self) -> None:
        arr = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
        out, mask = slice_array(arr, bands=(0, 2))
        # A clean array yields an all-False mask (no invalid pixels).
        assert mask is None or not mask.any()
        # average of bands 0 and 1 element-wise
        expected = (arr[0] + arr[1]) / 2.0
        np.testing.assert_array_equal(out, expected)
        assert out.shape == (3, 4)

    def test_single_band_no_average(self) -> None:
        arr = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
        out, _ = slice_array(arr, bands=(0, 1))
        np.testing.assert_array_equal(out, arr[0])

    def test_samples_slice(self) -> None:
        arr = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
        out, _ = slice_array(arr, samples=(1, 3), bands=(0, 1))
        np.testing.assert_array_equal(out, arr[0, :, 1:3])

    def test_lines_slice(self) -> None:
        arr = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
        out, _ = slice_array(arr, lines=(0, 2), bands=(0, 1))
        np.testing.assert_array_equal(out, arr[0, 0:2, :])

    def test_valid_mask_applied(self) -> None:
        arr = np.zeros((1, 2, 2), dtype=np.float64)
        arr[0, 0, 0] = 100
        _, mask = slice_array(arr, valid=(0.0, 50.0), bands=(0, 1))
        assert mask is not None
        assert mask[0, 0]  # masked
        assert not mask[0, 1]

    def test_nan_handled(self) -> None:
        arr = np.zeros((1, 2, 2), dtype=np.float64)
        arr[0, 0, 0] = np.nan
        out, mask = slice_array(arr, bands=(0, 1))
        assert mask is not None
        assert mask[0, 0]
        # the data slot for the NaN gets zeroed by slice_array
        np.testing.assert_array_equal(np.ma.getdata(out), [[0.0, 0.0], [0.0, 0.0]])


def test_slice_array_with_lines_samples_and_bands() -> None:
    """``slice_array`` honours bands/samples/lines bounds simultaneously."""
    arr = np.arange(3 * 8 * 8, dtype='int32').reshape(3, 8, 8)
    sliced, _mask = slice_array(arr, samples=[2, 6], lines=[1, 5], bands=(0, 2))
    assert sliced.shape == (4, 4)


def test_slice_array_with_valid_range_makes_mask() -> None:
    """``valid=(lo, hi)`` excludes out-of-range pixels via the mask."""
    arr = np.arange(16, dtype='int32').reshape(1, 4, 4)
    sliced, mask = slice_array(arr, bands=(0, 1), valid=(5.0, 10.0))
    assert sliced.shape == (4, 4)
    assert mask is not None
    assert mask.sum() == 16 - 6  # 6 values (5..10) inside range
