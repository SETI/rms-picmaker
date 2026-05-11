"""slice_array, crop_array, circle_mask unit tests."""

from __future__ import annotations

import numpy as np

from picmaker.picmaker import circle_mask, crop_array, slice_array


class TestCircleMask:
    def test_diameter_1(self) -> None:
        # diameter=1: ceil(1) = size 1; r2[0,0]=0 <= 0.25 → True; mask[0].sum()=1.
        mask = circle_mask(1)
        assert mask.shape == (1, 1)
        assert mask[0, 0] == np.bool_(True)

    def test_diameter_3(self) -> None:
        # diameter=3: size=3, all radii <= 2 are <= 2.25, so mask is all True.
        mask = circle_mask(3)
        assert mask.shape == (3, 3)
        assert mask.all()

    def test_diameter_5(self) -> None:
        mask = circle_mask(5)
        assert mask.shape == (5, 5)
        assert mask[2, 2]
        assert not mask[0, 0]
        assert mask[2, 0] and mask[0, 2] and mask[4, 2] and mask[2, 4]

    def test_diameter_8(self) -> None:
        mask = circle_mask(8)
        assert mask.shape[0] == 8
        # center band True
        assert mask[3, 3] and mask[4, 4]

    def test_diameter_9(self) -> None:
        mask = circle_mask(9)
        assert mask.shape == (9, 9)
        assert mask[4, 4]
        assert not mask[0, 0]


class TestSliceArray:
    def test_band_average(self) -> None:
        arr = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
        out, mask = slice_array(arr, bands=(0, 2))
        assert mask is None
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
        out, mask = slice_array(arr, valid=(0.0, 50.0), bands=(0, 1))
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


class TestCropArray:
    def test_interior_kept(self) -> None:
        # Border zeros, nonzero interior.
        arr = np.zeros((5, 5), dtype=np.int16)
        arr[1:4, 1:4] = 1
        out = crop_array(arr, value=0)
        assert out.shape == (3, 3)
        assert int(out.min()) == 1

    def test_oversized_all_zero(self) -> None:
        arr = np.zeros((5, 5), dtype=np.int16)
        out = crop_array(arr, value=0)
        # All-zero arrays return unchanged.
        assert out.shape == arr.shape

    def test_only_samples_axis(self) -> None:
        arr = np.zeros((4, 6), dtype=np.int16)
        arr[:, 2:4] = 7
        out = crop_array(arr, value=0, samples=True, lines=False)
        assert out.shape == (4, 2)

    def test_only_lines_axis(self) -> None:
        arr = np.zeros((6, 4), dtype=np.int16)
        arr[2:4, :] = 7
        out = crop_array(arr, value=0, samples=False, lines=True)
        assert out.shape == (2, 4)
