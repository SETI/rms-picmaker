"""Tests for picmaker.slicing: slice_array band/line/sample selection."""

from typing import Any

import numpy as np
import pytest

from picmaker.instruments import ImageData
from picmaker.slicing import slice_array


def _slice(arr: np.ndarray, **options: Any) -> tuple[np.ndarray, np.ndarray | None]:
    """Slice a bare array through ``slice_array`` and return ``(array, mask)``.

    The input carries no masks of its own, so ``hmask`` and ``imask`` both come back
    as the invalid-pixel mask (or None) and must agree.
    """
    result = slice_array(ImageData(arr, None, None, True, None), **options)
    if result.hmask is None:
        assert result.imask is None
    else:
        np.testing.assert_array_equal(result.hmask, result.imask)
    return (result.array, result.imask)


class TestSliceArray:
    def test_band_average(self) -> None:
        arr = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
        out, mask = _slice(arr, bands=(0, 2))
        # A clean array yields an all-False mask (no invalid pixels).
        assert mask is None or not mask.any()
        # average of bands 0 and 1 element-wise
        expected = (arr[0] + arr[1]) / 2.0
        np.testing.assert_array_equal(out, expected)
        assert out.shape == (3, 4)

    def test_single_band_no_average(self) -> None:
        arr = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
        out, _ = _slice(arr, bands=(0, 1))
        np.testing.assert_array_equal(out, arr[0])

    def test_samples_slice(self) -> None:
        arr = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
        out, _ = _slice(arr, samples=(1, 3), bands=(0, 1))
        np.testing.assert_array_equal(out, arr[0, :, 1:3])

    def test_lines_slice(self) -> None:
        arr = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
        out, _ = _slice(arr, lines=(0, 2), bands=(0, 1))
        np.testing.assert_array_equal(out, arr[0, 0:2, :])

    def test_valid_mask_applied(self) -> None:
        arr = np.zeros((1, 2, 2), dtype=np.float64)
        arr[0, 0, 0] = 100
        _, mask = _slice(arr, valid=(0.0, 50.0), bands=(0, 1))
        assert mask is not None
        assert mask[0, 0]  # masked
        assert not mask[0, 1]

    def test_nan_handled(self) -> None:
        arr = np.zeros((1, 2, 2), dtype=np.float64)
        arr[0, 0, 0] = np.nan
        out, mask = _slice(arr, bands=(0, 1))
        assert mask is not None
        assert mask[0, 0]
        # the data slot for the NaN gets zeroed by slice_array
        np.testing.assert_array_equal(np.ma.getdata(out), [[0.0, 0.0], [0.0, 0.0]])


def test_slice_array_with_lines_samples_and_bands() -> None:
    """``slice_array`` honours bands/samples/lines bounds simultaneously."""
    arr = np.arange(3 * 8 * 8, dtype='int32').reshape(3, 8, 8)
    sliced, _mask = _slice(arr, samples=[2, 6], lines=[1, 5], bands=(0, 2))
    assert sliced.shape == (4, 4)


def test_slice_array_with_valid_range_makes_mask() -> None:
    """``valid=(lo, hi)`` excludes out-of-range pixels via the mask."""
    arr = np.arange(16, dtype='int32').reshape(1, 4, 4)
    sliced, mask = _slice(arr, bands=(0, 1), valid=(5.0, 10.0))
    assert sliced.shape == (4, 4)
    assert mask is not None
    assert mask.sum() == 16 - 6  # 6 values (5..10) inside range


def test_slice_array_mask_range_is_inclusive() -> None:
    """``mask_ranges=[(lo, hi)]`` masks pixels inside the range, including both ends."""
    arr = np.arange(16, dtype='int32').reshape(4, 4)
    _, mask = _slice(arr, mask_ranges=[(3.0, 5.0)])
    assert mask is not None
    np.testing.assert_array_equal(np.flatnonzero(mask), [3, 4, 5])


def test_slice_array_mask_range_zero() -> None:
    """``mask_ranges=[(0, 0)]`` masks exactly the zero-valued pixels."""
    arr = np.array([[0., 1.], [0., -1.]])
    _, mask = _slice(arr, mask_ranges=[(0.0, 0.0)])
    assert mask is not None
    np.testing.assert_array_equal(mask, arr == 0)


def test_slice_array_mask_range_combines_with_valid_and_nan() -> None:
    """``mask_ranges`` adds to, rather than replaces, the ``valid`` and NaN masks."""
    arr = np.array([[0., 5., 50.], [np.nan, 7., 8.]])
    _, mask = _slice(arr, valid=(0.0, 10.0), mask_ranges=[(0.0, 0.0)])
    assert mask is not None
    np.testing.assert_array_equal(mask, [[True, False, True], [True, False, False]])


def test_slice_array_mask_range_excluded_from_band_coadd() -> None:
    """Masked values do not contribute to a band average; a pixel masked in every
    band stays masked."""
    arr = np.array([[[0., 0.]], [[4., 0.]]])        # 2 bands, 1 line, 2 samples
    out, mask = _slice(arr, bands=(0, 2), mask_ranges=[(0.0, 0.0)])
    assert mask is not None
    assert out[0, 0] == 4.0                         # the zero in band 0 is skipped
    np.testing.assert_array_equal(mask, [[False, True]])


def test_slice_array_multiple_mask_ranges() -> None:
    """Every range in ``mask_ranges`` is masked."""
    arr = np.arange(10, dtype='int32').reshape(2, 5)
    _, mask = _slice(arr, mask_ranges=[(0.0, 0.0), (7.0, 9.0)])
    assert mask is not None
    np.testing.assert_array_equal(np.flatnonzero(mask), [0, 7, 8, 9])


# --- ImageData clone and hmask / imask -----------------------------------------------

def test_slice_array_returns_a_clone_of_the_same_subclass() -> None:
    """The result is a new object of the input's subclass, carrying its other
    attributes, with only the sliced array replaced; the input is not modified."""
    from picmaker.instruments.hst_wfpc2 import HST_WFPC2

    class _TaggedWFPC2(HST_WFPC2):
        extra: str

    arr = np.arange(16, dtype=float).reshape(4, 4)
    image_data = _TaggedWFPC2(arr, None, None, True, (1, 2, 3))
    image_data.extra = 'kept'

    result = slice_array(image_data, lines=(1, 3), valid=(0.0, 6.0))

    assert type(result) is _TaggedWFPC2
    assert result is not image_data
    assert result.default_upward is True
    assert result.default_tint == (1, 2, 3)
    assert result.extra == 'kept'
    np.testing.assert_array_equal(result.array, arr[1:3])

    assert image_data.array is arr
    assert image_data.hmask is None
    assert image_data.imask is None


def test_slice_array_no_invalid_pixels_leaves_masks_none() -> None:
    """Masks that were None stay None when no pixel is invalid."""
    result = slice_array(ImageData(np.ones((3, 3)), None, None, True, None))
    assert result.hmask is None
    assert result.imask is None


def test_slice_array_none_masks_become_independent_copies() -> None:
    """None masks are replaced by the invalid-pixel mask, as two separate arrays."""
    arr = np.array([[0., 1.], [2., 3.]])
    result = slice_array(ImageData(arr, None, None, True, None), valid=(1.0, 2.0))
    expected = [[True, False], [False, True]]
    np.testing.assert_array_equal(result.hmask, expected)
    np.testing.assert_array_equal(result.imask, expected)
    assert result.hmask is not result.imask


def test_slice_array_ors_into_existing_masks() -> None:
    """Existing boolean masks are sliced like the array and or-ed with the invalid
    mask; each keeps its own extra pixels."""
    arr = np.arange(16, dtype=float).reshape(4, 4)
    hmask = np.zeros((4, 4), dtype=bool)
    imask = np.zeros((4, 4), dtype=bool)
    hmask[1, 1] = True
    imask[2, 2] = True
    imask[0, 0] = True              # outside the slice; must be dropped
    image_data = ImageData(arr, hmask, imask, True, None)

    result = slice_array(image_data, lines=(1, 4), samples=(1, 4),
                         mask_ranges=[(15.0, 15.0)], desnow=True)

    invalid = np.zeros((3, 3), dtype=bool)
    invalid[2, 2] = True            # value 15 at original (3, 3)
    expected_h = invalid.copy()
    expected_h[0, 0] = True         # original hmask (1, 1)
    expected_i = invalid.copy()
    expected_i[1, 1] = True         # original imask (2, 2)
    np.testing.assert_array_equal(result.hmask, expected_h)
    np.testing.assert_array_equal(result.imask, expected_i)

    assert not hmask[3, 3]          # inputs untouched
    assert not imask[3, 3]


def test_slice_array_existing_masks_follow_crop_and_band_squeeze() -> None:
    """Existing masks are cropped with the array, and lose a singleton band axis."""
    arr = np.zeros((1, 5, 5))
    arr[0, 1:4, 1:4] = 1.0
    hmask = np.zeros((1, 5, 5), dtype=bool)
    hmask[0, 2, 2] = True
    result = slice_array(ImageData(arr, hmask, None, True, None), crop=0.0)
    assert result.array.shape == (3, 3)
    assert result.hmask.shape == (3, 3)
    assert result.hmask[1, 1]
    assert result.imask is None


def test_slice_array_existing_masks_collapse_on_band_coadd() -> None:
    """When bands are coadded, an existing mask stays set only where every band is
    masked."""
    arr = np.ones((2, 1, 3))
    imask = np.array([[[True, True, False]], [[True, False, False]]])
    result = slice_array(ImageData(arr, None, imask, True, None), bands=(0, 2),
                         desnow=True)
    np.testing.assert_array_equal(result.imask, [[True, False, False]])
    assert result.hmask is None


def test_slice_array_zero_size_still_raises() -> None:
    """An empty slice is rejected before any masks are built."""
    with pytest.raises(ValueError, match='size zero'):
        slice_array(ImageData(np.ones((4, 4)), None, None, True, None), lines=(2, 2))


def test_slice_array_without_desnow_drops_the_input_imask() -> None:
    """By default (``desnow`` False) the input ``imask`` is discarded, so ``imask`` holds
    only the invalid pixels (here the ``mask_ranges`` value); ``hmask`` is kept."""
    arr = np.arange(9, dtype=float).reshape(3, 3)
    dq = np.zeros((3, 3), dtype=bool)
    dq[0, 0] = True
    image_data = ImageData(arr, dq, dq.copy(), True, None)

    result = slice_array(image_data, mask_ranges=[(8.0, 8.0)])
    invalid = arr == 8
    np.testing.assert_array_equal(result.hmask, dq | invalid)
    np.testing.assert_array_equal(result.imask, invalid)

    result = slice_array(image_data)
    np.testing.assert_array_equal(result.hmask, dq)
    assert result.imask is None

    result = slice_array(image_data, mask_ranges=[(8.0, 8.0)], desnow=True)
    np.testing.assert_array_equal(result.imask, dq | invalid)
