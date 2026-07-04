"""Spec tests for the image-pipeline helpers, derived from their docstrings.

Each test treats the function as a black box described by its docstring: the
documented parameters, return shapes, and raised exceptions — not the source.
"""

import numpy as np
import pytest
from PIL import Image

from picmaker import (
    apply_colormap,
    fill_zebra_stripes,
    filter_pil_image,
    get_limits,
    get_size,
    pad_pil_image,
    resize_pil_image,
    slice_array,
    wrap_pil_image,
)

# --- get_limits ------------------------------------------------------------


def _ramp(n: int = 10) -> np.ndarray:
    return np.arange(n * n, dtype=float).reshape(n, n)


def test_get_limits_returns_ordered_pair() -> None:
    """The stretch limits are a (lo, hi) pair with lo <= hi."""
    lo, hi = get_limits(_ramp())
    assert lo <= hi


def test_get_limits_honors_explicit_limits() -> None:
    """Explicit ``limits`` bound the returned stretch endpoints."""
    lo, hi = get_limits(_ramp(), limits=(10.0, 80.0))
    assert lo >= 10.0
    assert hi <= 80.0


def test_get_limits_percentiles_narrow_the_range() -> None:
    """An inner percentile cut yields a range no wider than the full one."""
    full_lo, full_hi = get_limits(_ramp(), percentiles=(0.0, 100.0))
    lo, hi = get_limits(_ramp(), percentiles=(25.0, 75.0))
    assert (hi - lo) <= (full_hi - full_lo)


def test_get_limits_accepts_trim_and_footprint() -> None:
    """``trim``, ``trim_zeros``, and ``footprint`` are accepted and honored."""
    lo, hi = get_limits(_ramp(), trim=1, trim_zeros=True, footprint=3)
    assert lo <= hi


def test_get_limits_accepts_mask() -> None:
    """An invalid-pixel mask is accepted."""
    arr = _ramp()
    mask = np.zeros_like(arr, dtype=bool)
    mask[0, 0] = True
    lo, hi = get_limits(arr, mask)
    assert lo <= hi


def test_get_limits_footprint_on_few_band_3d() -> None:
    """A footprint filter applies per-band to a 3-D array of up to three bands."""
    arr = np.linspace(0.0, 1.0, 300).reshape(3, 10, 10)
    lo, hi = get_limits(arr, footprint=3)
    assert lo <= hi


def test_get_limits_footprint_on_many_band_3d() -> None:
    """A footprint filter collapses a >3-band array before filtering."""
    arr = np.linspace(0.0, 1.0, 400).reshape(4, 10, 10)
    lo, hi = get_limits(arr, footprint=3)
    assert lo <= hi


def test_get_limits_trim_zeros_on_3d() -> None:
    """``trim_zeros`` trims all-zero exterior rows/columns of a 3-D array."""
    arr = np.ones((3, 6, 6))
    arr[:, 0, :] = 0.0
    lo, hi = get_limits(arr, trim_zeros=True)
    assert lo <= hi


def test_get_limits_fully_masked_returns_pair() -> None:
    """A fully-masked (all-NaN) array still yields a valid (lo, hi) pair."""
    lo, hi = get_limits(np.full((5, 5), np.nan))
    assert lo <= hi


# --- apply_colormap --------------------------------------------------------


def test_apply_colormap_grayscale_shape_and_range() -> None:
    """A plain grayscale mapping returns an (H, W, 1) array scaled to [0, 1]."""
    arr = np.linspace(0.0, 1.0, 100).reshape(10, 10)
    out = apply_colormap(arr, (0.0, 1.0))
    assert out.ndim == 3
    assert out.shape[:2] == (10, 10)
    assert out.shape[2] == 1
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_apply_colormap_three_stops_are_rgb() -> None:
    """A multi-color colormap produces a three-channel result."""
    arr = np.linspace(0.0, 1.0, 100).reshape(10, 10)
    out = apply_colormap(arr, (0.0, 1.0), colormap=['black', 'blue', 'white'])
    assert out.shape[2] == 3


def test_apply_colormap_single_color_is_shorthand() -> None:
    """A single color is shorthand for black/<color>/white, i.e. RGB."""
    arr = np.linspace(0.0, 1.0, 100).reshape(10, 10)
    out = apply_colormap(arr, (0.0, 1.0), colormap=['blue'])
    assert out.shape[2] == 3


def test_apply_colormap_histogram_and_gamma() -> None:
    """Histogram shading and a gamma factor are accepted."""
    arr = np.linspace(0.0, 1.0, 100).reshape(10, 10)
    out = apply_colormap(arr, (0.0, 1.0), histogram=True, gamma=2.0)
    assert out.ndim == 3
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_apply_colormap_special_case_colors() -> None:
    """``below``/``above``/``invalid`` colors apply to their pixels (RGB out)."""
    arr = np.linspace(0.0, 1.0, 100).reshape(10, 10)
    mask = np.zeros_like(arr, dtype=bool)
    mask[0, 0] = True
    out = apply_colormap(
        arr, (0.2, 0.8), invalid_mask=mask,
        below_color='red', above_color='green', invalid_color='white',
    )
    assert out.shape[2] == 3


def test_apply_colormap_tint_uses_default_tint() -> None:
    """With ``tint`` set and no colormap, the instrument default tint is used."""
    arr = np.linspace(0.0, 1.0, 100).reshape(10, 10)
    out = apply_colormap(arr, (0.0, 1.0), tint=True, default_tint=(200, 80, 80))
    assert out.shape[2] == 3


def test_apply_colormap_three_band_input_is_rgb() -> None:
    """A 3-D (bands, lines, samples) input maps its bands to the RGB channels."""
    arr = np.linspace(0.0, 1.0, 300).reshape(3, 10, 10)
    out = apply_colormap(arr, (0.0, 1.0))
    assert out.shape == (10, 10, 3)


def test_apply_colormap_histogram_with_mask() -> None:
    """Histogram shading works alongside an invalid-pixel mask."""
    arr = np.linspace(0.0, 1.0, 100).reshape(10, 10)
    mask = np.zeros_like(arr, dtype=bool)
    mask[0, 0] = True
    out = apply_colormap(arr, (0.0, 1.0), histogram=True, invalid_mask=mask)
    assert out.ndim == 3
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_apply_colormap_histogram_three_band() -> None:
    """Histogram shading works on a three-band (RGB) input."""
    arr = np.linspace(0.0, 1.0, 300).reshape(3, 10, 10)
    out = apply_colormap(arr, (0.0, 1.0), histogram=True)
    assert out.shape == (10, 10, 3)


# --- get_size --------------------------------------------------------------


def test_get_size_returns_four_part_tuple() -> None:
    """The result is (unwrapped_size, wrapped_size, sections, wrap_axis)."""
    unwrapped, wrapped, sections, axis = get_size((100, 200))
    assert len(unwrapped) == 2
    assert len(wrapped) == 2
    assert isinstance(sections, int)
    assert axis in (0, 1)


def test_get_size_explicit_size_is_respected() -> None:
    """An explicit ``size`` sets the output (width, height)."""
    unwrapped, _wrapped, _sections, _axis = get_size((100, 200), size=(80, 60))
    assert tuple(unwrapped) == (80, 60)


def test_get_size_scale_halves_dimensions() -> None:
    """A 50% scale halves both axes relative to the default."""
    base, *_ = get_size((100, 200))
    half, *_ = get_size((100, 200), scale=(50.0, 50.0))
    assert half[0] <= base[0] // 2 + 1
    assert half[1] <= base[1] // 2 + 1


def test_get_size_frame_constrains_output() -> None:
    """A frame is a firm outer limit; the image is scaled to fit inside it."""
    unwrapped, *_ = get_size((100, 200), frame=(50, 50))
    assert unwrapped[0] <= 50
    assert unwrapped[1] <= 50


def test_get_size_wrap_splits_elongated_image() -> None:
    """A very elongated image wraps into more than one section."""
    _unwrapped, _wrapped, sections, axis = get_size(
        (10, 1000), wrap=True, wrap_ratio=2.0)
    assert sections >= 2
    assert axis in (0, 1)


# --- slice_array -----------------------------------------------------------


def test_slice_array_sub_region_shape() -> None:
    """Line/sample limits select the corresponding sub-region."""
    arr = np.arange(100, dtype=float).reshape(10, 10)
    sliced, mask = slice_array(arr, lines=(2, 5), samples=(1, 4))
    assert sliced.shape == (3, 3)
    assert mask is None or not mask.any()      # nothing invalid in this slice


def test_slice_array_coadds_bands_to_2d() -> None:
    """A band range collapses a 3-D array to a 2-D band average."""
    arr = np.ones((3, 4, 4))
    sliced, _mask = slice_array(arr, bands=(0, 3))
    assert sliced.ndim == 2
    assert sliced.shape == (4, 4)


def test_slice_array_valid_range_masks_outliers() -> None:
    """Pixels outside the ``valid`` range are masked."""
    arr = np.arange(16, dtype=float).reshape(4, 4)
    _sliced, mask = slice_array(arr, valid=(5.0, 10.0))
    assert mask is not None
    assert mask.sum() > 0


def test_slice_array_nan_always_masked() -> None:
    """NaN pixels are always masked."""
    arr = np.ones((4, 4))
    arr[1, 1] = np.nan
    _sliced, mask = slice_array(arr)
    assert mask is not None
    assert bool(mask[1, 1]) is True


def test_slice_array_crop_removes_constant_border() -> None:
    """``crop`` removes border rows/columns that all equal the given value."""
    arr = np.ones((6, 6))
    arr[0, :] = arr[-1, :] = arr[:, 0] = arr[:, -1] = 0.0
    sliced, _mask = slice_array(arr, crop=0.0)
    assert sliced.shape == (4, 4)


def test_slice_array_zero_size_raises() -> None:
    """A zero-size slice raises ValueError."""
    with pytest.raises(ValueError):
        slice_array(np.ones((4, 4)), lines=(2, 2))


# --- filter_pil_image ------------------------------------------------------


def test_filter_none_returns_input_unchanged() -> None:
    """``filter='none'`` returns the input image unchanged."""
    img = Image.new('L', (8, 8))
    assert filter_pil_image(img, 'none') is img


def test_filter_is_case_insensitive() -> None:
    """Filter names are case-insensitive."""
    img = Image.new('L', (8, 8))
    assert isinstance(filter_pil_image(img, 'BLUR'), Image.Image)


def test_filter_unknown_name_raises_keyerror() -> None:
    """An unrecognized filter name raises KeyError."""
    with pytest.raises(KeyError):
        filter_pil_image(Image.new('L', (8, 8)), 'bogus')


def test_filter_rejects_16bit_list() -> None:
    """A 16-bit (list-of-three) image cannot be filtered."""
    img = Image.new('L', (8, 8))
    with pytest.raises(ValueError):
        filter_pil_image([img, img, img], 'blur')


# --- fill_zebra_stripes ----------------------------------------------------


def test_fill_zebra_stripes_leaves_input_unmodified() -> None:
    """The input array is never modified; a new float array is returned."""
    arr = np.arange(25, dtype=float).reshape(5, 5)
    before = arr.copy()
    out = fill_zebra_stripes(arr)
    assert np.array_equal(arr, before)
    assert out.shape == arr.shape
    assert out.dtype.kind == 'f'


# --- layout: wrap / pad ----------------------------------------------------


def test_pad_pil_image_fills_frame() -> None:
    """Padding produces an image of the requested frame size."""
    img = Image.new('RGB', (20, 10))
    out = pad_pil_image(img, frame=(40, 30), pad=True, pad_color='gray')
    assert out.size == (40, 30)


def test_wrap_pil_image_matches_wrapped_size() -> None:
    """Wrapping produces an image of the size that ``get_size`` reports."""
    unwrapped, wrapped, sections, axis = get_size(
        (10, 100), wrap=True, wrap_ratio=2.0)
    img = Image.new('RGB', tuple(unwrapped))
    out = wrap_pil_image(img, tuple(wrapped), sections, axis)
    assert out.size == tuple(wrapped)


def test_resize_pil_image_sets_new_size() -> None:
    """Resizing yields an image of the requested (width, height)."""
    out = resize_pil_image(Image.new('L', (20, 20)), (50, 40))
    assert out.size == (50, 40)


def test_resize_pil_image_list_of_three() -> None:
    """A list of three images (16-bit RGB) resizes to a list of three."""
    imgs = [Image.new('L', (20, 20)) for _ in range(3)]
    out = resize_pil_image(imgs, (50, 40))
    assert isinstance(out, (list, tuple))
    assert len(out) == 3
    assert all(i.size == (50, 40) for i in out)
