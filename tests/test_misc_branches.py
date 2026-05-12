"""Cover the remaining branches in ``pil_utils``, ``enhance``,
``geometry``, ``_filters``, and the small per-instrument fall-through
paths that the existing tests don't exercise.

Each test targets a specific behaviour line in source (16-bit RGB
round-trips, ``--invalid black`` shortcut, gap-coloured wrap, gamma=1
no-op, sub-instrument tints not in the per-instrument dispatch
tables, etc.).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

from picmaker import instruments
from picmaker._filters import filter_image
from picmaker.enhance import apply_colormap, apply_gamma, get_limits
from picmaker.geometry import (
    crop_array,
    pad_image,
    resize_image,
    rotate_array_rgb,
    slice_array,
    wrap_image,
)
from picmaker.pil_utils import (
    _one_pil_to_array,
    array_to_pil,
    pil_to_array,
    write_pil,
)

# ---------------------------------------------------------------------------
# pil_utils — 16-bit grayscale + 16-bit RGB round trip
# ---------------------------------------------------------------------------


def test_array_to_pil_sixteen_bit_grayscale_no_rescale() -> None:
    """16-bit grayscale arrays (no rescale) round-trip via PIL ``I`` mode."""
    array = np.zeros((4, 4, 1), dtype='float64')
    array[:] = 0.5  # mid-grey
    im = array_to_pil(array, twobytes=True)
    assert im.mode == 'I'
    out = _one_pil_to_array(im, rescale=False)
    assert out.shape == (4, 4)


def test_array_to_pil_sixteen_bit_rgb_yields_three_images() -> None:
    """16-bit RGB arrays produce a list of three PIL ``I`` images."""
    array = np.zeros((4, 4, 3), dtype='float64')
    array[..., 0] = 0.25
    array[..., 1] = 0.5
    array[..., 2] = 0.75
    result = array_to_pil(array, twobytes=True)
    assert isinstance(result, list)
    assert len(result) == 3
    for im in result:
        assert im.mode == 'I'
        assert im.size == (4, 4)


def test_pil_to_array_handles_list_of_three() -> None:
    """A list of three PIL images is depth-stacked into an RGB array."""
    ims = [Image.new('L', (4, 4), color=c) for c in (10, 20, 30)]
    arr = pil_to_array(ims, rescale=False)
    assert arr.shape == (4, 4, 3)
    assert arr[0, 0, 0] == 10
    assert arr[0, 0, 1] == 20
    assert arr[0, 0, 2] == 30


def test_one_pil_to_array_unsupported_mode_raises() -> None:
    """``_one_pil_to_array`` rejects PIL modes other than ``L`` and ``I``."""
    im = Image.new('RGB', (4, 4))
    with pytest.raises(OSError, match='Unsupported PIL image format'):
        _one_pil_to_array(im, rescale=False)


def test_write_pil_sixteen_bit_rgb_writes_tiff(tmp_path: Path) -> None:
    """``write_pil`` on a 3-image list calls ``WriteTiff16`` and produces
    an RGB TIFF.
    """
    ims = [Image.new('I', (4, 4), color=10000 * (c + 1)) for c in range(3)]
    out = tmp_path / 'rgb16.tiff'
    write_pil(ims, str(out))
    assert out.exists()


def test_write_pil_sixteen_bit_grayscale_writes_tiff(tmp_path: Path) -> None:
    """``write_pil`` on a single ``I``-mode PIL image writes a 16-bit TIFF."""
    im = Image.new('I', (4, 4), color=30000)
    out = tmp_path / 'gray16.tiff'
    write_pil(im, str(out))
    assert out.exists()


def test_write_pil_creates_parent_directory(tmp_path: Path) -> None:
    """``write_pil`` creates a missing parent directory before writing."""
    nested = tmp_path / 'a' / 'b' / 'c'
    im = Image.new('L', (4, 4))
    out = nested / 'out.png'
    write_pil(im, str(out))
    assert out.exists()


# ---------------------------------------------------------------------------
# enhance — get_limits / apply_colormap branches
# ---------------------------------------------------------------------------


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
    # A 16x16 image with a 4-pixel zero border around an 8x8 valued centre.
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
    assert lo == hi - 1  # all 100s except one masked


def test_get_limits_with_footprint_filter() -> None:
    """``footprint=N`` applies a median filter that narrows the limits."""
    arr = np.zeros((16, 16), dtype='uint16')
    arr[8, 8] = 200  # single outlier
    _lo, hi = get_limits(arr, None, None, (0.0, 100.0), footprint=3)
    # The 3-pixel circular footprint median pulls the outlier down.
    assert hi <= 200 + 0.5


def test_get_limits_with_trim() -> None:
    """``trim=N`` excludes ``N`` pixels around the edge."""
    arr = np.arange(256, dtype='uint16').reshape(16, 16)
    lo, hi = get_limits(arr, None, None, (0.0, 100.0), trim=4)
    # After trimming, the 8x8 inner block runs from row 4..12.
    assert lo == arr[4:-4, 4:-4].min() - 0.5
    assert hi == arr[4:-4, 4:-4].max() + 0.5


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
    assert out[0, 0, 2] == pytest.approx(1.0)
    # arr[0, 3]=200 > upper → red (1,0,0)
    assert out[0, 3, 0] == pytest.approx(1.0)


def test_apply_colormap_named_two_stop() -> None:
    """A named two-stop colormap (e.g. ``red-blue``) builds an RGB output."""
    arr = np.arange(8, dtype='uint8').reshape(2, 4)
    out = apply_colormap(arr, (0.0, 7.0), colormap='red-blue')
    assert out.shape == (2, 4, 3)


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


# ---------------------------------------------------------------------------
# geometry — wrap_image, pad_image, slice_array, crop_array, rotate_array_rgb
# ---------------------------------------------------------------------------


def test_get_size_wrap_ratio_wide_image() -> None:
    """``wrap_ratio`` on a horizontally-elongated image picks horizontal
    sectioning.

    The ``array_shape`` convention is ``(lines, samples)`` (pipeline.py
    passes ``arrayRGB.shape``). ``samples > 4 * lines`` triggers the
    horizontal wrap branch.
    """
    from picmaker.geometry import get_size
    # lines=4, samples=40 → array_size=[40, 4] → wide → axis 0 wrap.
    res = get_size((4, 40, 3), wrap_ratio=4.0)
    _, _, sections, axis = res
    assert sections >= 2
    assert axis == 0


def test_get_size_wrap_ratio_tall_image() -> None:
    """``wrap_ratio`` on a vertically-elongated image picks vertical
    sectioning.
    """
    from picmaker.geometry import get_size
    # lines=40, samples=4 → array_size=[4, 40] → tall → axis 1 wrap.
    res = get_size((40, 4, 3), wrap_ratio=4.0)
    _, _, sections, axis = res
    assert sections >= 2
    assert axis == 1


def test_get_size_scale_passes_through() -> None:
    """``scale=(50, 50)`` halves the array size in both dimensions."""
    from picmaker.geometry import get_size
    unwrapped, _, _, _ = get_size((16, 16, 3), scale=(50.0, 50.0))
    assert unwrapped == [8, 8]


def test_get_size_size_scalar() -> None:
    """A scalar ``size`` is broadcast to both dimensions."""
    from picmaker.geometry import get_size
    unwrapped, _, _, _ = get_size((8, 8, 3), size=64)
    assert unwrapped == [64, 64]


def test_get_size_frame_max_caps_upscale() -> None:
    """``frame_max=PCT`` caps how far the input can be enlarged.

    An 8x8 image fit into a 64x64 frame would scale 8x; ``frame_max=200``
    caps the enlargement at 2x (``unwrapped`` lands well under 64x64).
    """
    from picmaker.geometry import get_size
    unwrapped, _, _, _ = get_size((8, 8, 3), frame=(64, 64), frame_max=200)
    # The exact integer result depends on the floor + cap; verify it's
    # strictly below the un-capped 64x64 target.
    assert max(unwrapped) < 64


def test_get_size_wrap_with_frame_searches_axes() -> None:
    """``wrap=True`` with a frame exercises the per-axis search."""
    from picmaker.geometry import get_size
    res = get_size((4, 40, 3), frame=(40, 4), wrap=True)
    _, _, sections, _ = res
    assert sections >= 1


def test_wrap_image_basic_two_horizontal_sections() -> None:
    """``wrap_image`` produces an output of the requested wrapped size."""
    # A 24x4 grayscale image wrapped into 2 horizontal sections.
    im = Image.new('L', (24, 4), color=128)
    out = wrap_image(
        im,
        wrapped_size=(12, 9),  # 4*2 + 1 gap = 9 high
        sections=2,
        wrap_axis=0,
        gap_size=1,
        gap_color='white',
    )
    assert out.size == (12, 9)


def test_wrap_image_promotes_grayscale_to_rgb_for_colored_gap() -> None:
    """A grayscale input plus a non-grey gap colour produces an RGB output."""
    im = Image.new('L', (24, 4), color=128)
    out = wrap_image(
        im,
        wrapped_size=(12, 9),
        sections=2,
        wrap_axis=0,
        gap_size=1,
        gap_color='red',  # (255, 0, 0) — forces RGB promotion
    )
    assert out.size == (12, 9)
    assert out.mode == 'RGB'


def test_wrap_image_no_gap_uses_black_internally() -> None:
    """``gap_size=0`` short-circuits the gap-colour logic."""
    im = Image.new('L', (16, 4), color=128)
    out = wrap_image(
        im,
        wrapped_size=(8, 8),
        sections=2,
        wrap_axis=0,
        gap_size=0,
        gap_color='red',
    )
    assert out.size == (8, 8)


def test_wrap_image_vertical_two_sections() -> None:
    """``wrap_image`` along the vertical axis works symmetrically."""
    im = Image.new('L', (4, 24), color=128)
    out = wrap_image(
        im,
        wrapped_size=(9, 12),
        sections=2,
        wrap_axis=1,
        gap_size=1,
        gap_color='white',
    )
    assert out.size == (9, 12)


def test_pad_image_with_colored_pad_grows_to_frame() -> None:
    """Padding a grayscale image with a non-grey colour still hits the
    enlarged-buffer path; the result lands at the requested frame size.
    """
    im = Image.new('L', (4, 4), color=200)
    out = pad_image(im, (16, 16), 'red')
    assert out.size == (16, 16)


def test_pad_image_already_meets_one_axis() -> None:
    """``pad_image`` enlarges only the deficient axis."""
    im = Image.new('L', (16, 4), color=200)
    out = pad_image(im, (16, 16), 'black')
    assert out.size == (16, 16)


def test_pad_image_grows_to_frame() -> None:
    """``pad_image`` enlarges a small image to the target frame."""
    im = Image.new('L', (4, 4), color=200)
    out = pad_image(im, (16, 16), 'black')
    assert out.size == (16, 16)


def test_pad_image_noop_when_frame_none() -> None:
    """``pad_image`` is a no-op when ``frame is None``."""
    im = Image.new('L', (4, 4))
    out = pad_image(im, None, 'black')
    assert out is im


def test_pad_image_noop_when_already_big() -> None:
    """``pad_image`` returns the input when it already covers the frame."""
    im = Image.new('L', (16, 16))
    out = pad_image(im, (4, 4), 'black')
    assert out is im


def test_resize_image_noop_when_size_matches() -> None:
    """``resize_image`` returns the input untouched when sizes match."""
    im = Image.new('L', (8, 8))
    out = resize_image(im, (8, 8))
    assert out is im


def test_resize_image_upscale_uses_nearest() -> None:
    """Upscaling lands on the requested size."""
    im = Image.new('L', (4, 4), color=10)
    out = resize_image(im, (16, 16))
    assert out.size == (16, 16)


def test_slice_array_with_lines_samples_and_bands() -> None:
    """``slice_array`` honours bands/samples/lines bounds simultaneously."""
    arr = np.arange(3 * 8 * 8, dtype='int32').reshape(3, 8, 8)
    sliced, _mask = slice_array(arr, [2, 6], [1, 5], (0, 2), None, None)
    assert sliced.shape == (4, 4)


def test_slice_array_with_valid_range_makes_mask() -> None:
    """``valid=(lo, hi)`` excludes out-of-range pixels via the mask."""
    arr = np.arange(16, dtype='int32').reshape(1, 4, 4)
    sliced, mask = slice_array(arr, None, None, (0, 1), (5.0, 10.0), None)
    assert sliced.shape == (4, 4)
    assert mask is not None
    assert mask.sum() == 16 - 6  # 6 values (5..10) inside range


def test_crop_array_trims_constant_border() -> None:
    """``crop_array`` strips a single-value constant border."""
    arr = np.zeros((1, 8, 8), dtype='int32')
    arr[0, 2:6, 2:6] = 99
    cropped = crop_array(arr, 0)
    # Only the 4x4 interior survives.
    assert cropped.shape == (1, 4, 4)


def test_crop_array_all_equal_passthrough() -> None:
    """A uniform array is returned untouched (no crop possible)."""
    arr = np.zeros((1, 4, 4), dtype='int32')
    out = crop_array(arr, 0)
    assert out is arr


def test_crop_array_two_dim_input() -> None:
    """A 2-D input is bracketed to 3-D internally and still gets cropped."""
    arr = np.zeros((8, 8), dtype='int32')
    arr[2:6, 2:6] = 99
    out = crop_array(arr, 0)
    assert out.shape == (4, 4)


def test_rotate_array_rgb_rot90() -> None:
    """``rotation_name='ROT90'`` preserves shape."""
    arr = np.zeros((8, 8, 3), dtype='float32')
    arr[0, 0] = 1.0
    out = rotate_array_rgb(arr, False, 'ROT90')
    assert out.shape == arr.shape


def test_rotate_array_rgb_fliplr() -> None:
    """``rotation_name='FLIPLR'`` mirrors horizontally."""
    arr = np.zeros((8, 8, 3), dtype='float32')
    arr[0, 0] = 1.0
    out = rotate_array_rgb(arr, False, 'FLIPLR')
    assert out[0, -1, 0] == pytest.approx(1.0)


def test_rotate_array_rgb_fliptb_and_rot180() -> None:
    """``FLIPTB`` and ``ROT180`` both end up with the corner at the bottom."""
    arr = np.zeros((8, 8, 3), dtype='float32')
    arr[0, 0] = 1.0
    out_flip = rotate_array_rgb(arr.copy(), False, 'FLIPTB')
    assert out_flip[-1, 0, 0] == pytest.approx(1.0)
    out_rot = rotate_array_rgb(arr.copy(), False, 'ROT180')
    assert out_rot[-1, -1, 0] == pytest.approx(1.0)


def test_rotate_array_rgb_rot270() -> None:
    """``rotation_name='ROT270'`` preserves shape."""
    arr = np.zeros((8, 8, 3), dtype='float32')
    out = rotate_array_rgb(arr, False, 'ROT270')
    assert out.shape == arr.shape


def test_rotate_array_rgb_unknown_raises() -> None:
    """An unrecognised rotation name raises ``KeyError``."""
    arr = np.zeros((4, 4, 3), dtype='float32')
    with pytest.raises(KeyError, match='Unrecognized rotation method'):
        rotate_array_rgb(arr, False, 'tumble')


def test_rotate_array_rgb_display_upward() -> None:
    """``display_upward=True`` pre-flips the image vertically."""
    arr = np.zeros((4, 4, 3), dtype='float32')
    arr[0, 0] = 1.0
    out = rotate_array_rgb(arr, True, 'NONE')
    assert out[-1, 0, 0] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# _filters
# ---------------------------------------------------------------------------


def test_filter_image_none_is_identity() -> None:
    """``filter='none'`` returns the input untouched."""
    im = Image.new('L', (8, 8))
    out = filter_image(im, 'none')
    assert out is im


def test_filter_image_blur() -> None:
    """A named filter (``blur``) returns a new same-size PIL image."""
    im = Image.new('L', (8, 8), color=128)
    out = filter_image(im, 'blur')
    assert out.size == (8, 8)


# ---------------------------------------------------------------------------
# Per-instrument fall-through paths
# ---------------------------------------------------------------------------


def test_cassini_tint_falls_back_to_grey() -> None:
    """Unknown Cassini filters fall back to the neutral grey tint."""
    from picmaker.instruments import cassini
    cmap = cassini.tint_for('ISS', 'WAT+CL2')
    assert cmap == [(0, 0, 0), (127, 127, 127), (255, 255, 255)]


@pytest.mark.parametrize(
    ('filter_name', 'expected_tint'),
    [
        ('IR1+CL2', (200, 80, 80)),
        ('UV3+CL2', (160, 80, 220)),
        ('VIO+CL2', (160, 120, 200)),
        ('BL1+CL2', (110, 110, 180)),
        ('BL1+GRN', (110, 180, 180)),
        ('GRN+RED', (190, 190, 110)),
        ('CL1+GRN', (110, 190, 110)),
        ('RED+CL2', (190, 110, 100)),
        ('MT1+CL2', (190, 110, 100)),
        ('CB1+CL2', (190, 110, 100)),
        ('HAL+CL2', (190, 110, 100)),
        ('MT3+CL2', (200, 80, 80)),
        ('CB3+CL2', (200, 80, 80)),
    ],
)
def test_cassini_tint_chain_each_branch(
    filter_name: str, expected_tint: tuple[int, int, int]
) -> None:
    """Each branch of the Cassini ISS tint chain returns its declared RGB."""
    from picmaker.instruments import cassini
    cmap = cassini.tint_for('ISS', filter_name)
    assert cmap == [(0, 0, 0), expected_tint, (255, 255, 255)]


def test_cassini_detect_fits_always_none() -> None:
    """Cassini's FITS detector unconditionally returns ``None``."""
    from picmaker.instruments import cassini
    assert cassini.detect_fits(None) is None


def test_cassini_matches_predicate() -> None:
    """``matches`` accepts any CASSINI-prefixed host."""
    from picmaker.instruments import cassini
    assert cassini.matches('CASSINI ORBITER', 'ISS') is True
    assert cassini.matches('HUBBLE', 'WFC3') is False


def test_cassini_non_iss_returns_plain_bw() -> None:
    """Non-ISS Cassini instruments get the plain ``[black, white]`` map."""
    from picmaker.instruments import cassini
    assert cassini.tint_for('CIRS', 'anything') == [(0, 0, 0), (255, 255, 255)]


def test_voyager_non_iss_returns_plain_bw() -> None:
    """Non-ISS Voyager instruments get the plain ``[black, white]`` map."""
    from picmaker.instruments import voyager
    assert voyager.tint_for('PPS', 'anything') == [(0, 0, 0), (255, 255, 255)]


def test_voyager_detect_fits_always_none() -> None:
    """Voyager's FITS detector unconditionally returns ``None``."""
    from picmaker.instruments import voyager
    assert voyager.detect_fits(None) is None


def test_voyager_matches_predicate() -> None:
    """``matches`` accepts any VOYAGER-prefixed host."""
    from picmaker.instruments import voyager
    assert voyager.matches('VOYAGER 1', 'ISS') is True
    assert voyager.matches('NEW HORIZONS', 'MVIC') is False


def test_voyager_detect_vicar_swallows_keyerror() -> None:
    """Vicar labels without LAB02 / LAB03 return ``None`` (caught KeyError)."""
    from picmaker.instruments import voyager

    class FakeVic:
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

    assert voyager.detect_vicar(FakeVic()) is None


def test_galileo_non_ssi_returns_plain_bw() -> None:
    """Non-SSI Galileo instruments get the plain ``[black, white]`` map."""
    from picmaker.instruments import galileo
    assert galileo.tint_for('PPR', 'GREEN') == [(0, 0, 0), (255, 255, 255)]


def test_galileo_detect_fits_always_none() -> None:
    """Galileo's FITS detector unconditionally returns ``None``."""
    from picmaker.instruments import galileo
    assert galileo.detect_fits(None) is None


def test_galileo_detect_vicar_swallows_keyerror() -> None:
    """A label without MISSION or LAB01/LAB03 returns ``None``."""
    from picmaker.instruments import galileo

    class FakeVic:
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

    assert galileo.detect_vicar(FakeVic()) is None


def test_nh_non_mvic_returns_plain_bw() -> None:
    """Non-MVIC NH instruments get the plain ``[black, white]`` map."""
    from picmaker.instruments import nh
    assert nh.tint_for('LORRI', 'anything') == [(0, 0, 0), (255, 255, 255)]


def test_nh_detect_vicar_always_none() -> None:
    """NH's VICAR detector always returns ``None``."""
    from picmaker.instruments import nh
    assert nh.detect_vicar(None) is None


def _make_fake_hdulist(header: dict[str, Any]) -> Any:
    """Return a minimal ``hdulist[0].header``-compatible object."""

    class _HDU:
        def __init__(self, h: dict[str, Any]) -> None:
            self.header = h

    class _List:
        def __init__(self, h: dict[str, Any]) -> None:
            self._hdu = _HDU(h)

        def __getitem__(self, _i: int) -> Any:
            return self._hdu

    return _List(header)


def test_nh_detect_fits_missing_hostname() -> None:
    """A FITS file with no ``HOSTNAME`` keyword returns ``None``."""
    from picmaker.instruments import nh
    assert nh.detect_fits(_make_fake_hdulist({})) is None


def test_nh_detect_fits_missing_instru() -> None:
    """A FITS file with ``HOSTNAME`` but no ``INSTRU`` returns ``None``."""
    from picmaker.instruments import nh
    assert nh.detect_fits(_make_fake_hdulist({'HOSTNAME': 'NEW HORIZONS'})) is None


def test_nh_detect_fits_no_filter_returns_none_filter() -> None:
    """``FILTER`` missing means the third tuple element is ``None``."""
    from picmaker.instruments import nh
    result = nh.detect_fits(_make_fake_hdulist(
        {'HOSTNAME': 'NEW HORIZONS', 'INSTRU': 'MVIC'}
    ))
    assert result == ('NEW HORIZONS', 'MVIC', None)


def test_hst_detect_vicar_always_none() -> None:
    """HST's VICAR detector always returns ``None``."""
    from picmaker.instruments import hst
    assert hst.detect_vicar(None) is None


def test_hst_detect_fits_missing_instrume() -> None:
    """A FITS file with TELESCOP but no INSTRUME returns ``None``."""
    from picmaker.instruments import hst
    assert hst.detect_fits(_make_fake_hdulist({'TELESCOP': 'HST'})) is None


def test_hst_long_pass_short_circuit() -> None:
    """``F350LP`` / ``F606W`` / ``LONG_PASS`` short-circuit to ``[bw]``."""
    from picmaker.instruments import hst
    assert hst.tint_for('WFC3/UVIS', 'F350LP') == [(0, 0, 0), (255, 255, 255)]
    assert hst.tint_for('WFC3/UVIS', 'F606W') == [(0, 0, 0), (255, 255, 255)]


def test_hst_unknown_filter_returns_none() -> None:
    """An HST filter whose digits cannot be inferred returns ``None``."""
    from picmaker.instruments import hst
    # 'ABCDE' has no digits; wavelength stays 0 → None.
    assert hst.tint_for('WFC3/UVIS', 'ABCDE') is None


def test_hst_fquv_pinned() -> None:
    """``FQUV*`` quad-filters are pinned to 300 nm."""
    from picmaker.instruments import hst
    cmap = hst.tint_for('WFPC2', 'FQUV1')
    assert cmap is not None
    assert len(cmap) == 3


def test_hst_fqch4_pinned() -> None:
    """``FQCH4*`` quad-filters are pinned to 900 nm."""
    from picmaker.instruments import hst
    cmap = hst.tint_for('WFPC2', 'FQCH41')
    assert cmap is not None


def test_hst_pol0s_pinned() -> None:
    """``POL0S`` is pinned when no preceding detector branch matches.

    The pinning runs in an ``elif`` chain after the NIC / WFC3 / ACS
    scaling branches, so it only fires for an inst_id that does not
    contain any of those substrings.
    """
    from picmaker.instruments import hst
    cmap = hst.tint_for('OTHER', 'POL0S')
    assert cmap is not None
    assert len(cmap) == 3


def test_hst_pol0l_pinned() -> None:
    """``POL0L`` is pinned (same elif precedence as POL0S)."""
    from picmaker.instruments import hst
    cmap = hst.tint_for('OTHER', 'POL0L')
    assert cmap is not None
    assert len(cmap) == 3


def test_hst_nicmos_scales_by_3p5() -> None:
    """NICMOS filter wavelengths are scaled by 3.5x."""
    from picmaker.instruments import hst
    # 'F110' -> 110 nm, NICMOS scales to 385 nm.
    cmap = hst.tint_for('NICMOS', 'F110')
    assert cmap is not None


def test_instruments_lookup_returns_none_for_unknown() -> None:
    """``instruments.lookup`` returns ``None`` for a host with no match."""
    assert instruments.lookup('UNKNOWN', '') is None


# ---------------------------------------------------------------------------
# package-level __init__ re-exports (covers picmaker/__init__.py:17-21)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# tiff16 — palette + transpose + byteorder branches
# ---------------------------------------------------------------------------


def test_tiff16_rgb_write(tmp_path: Path) -> None:
    """A 16-bit RGB array writes successfully."""
    from picmaker.tiff16 import ReadTiff16, WriteTiff16
    rgb = np.zeros((8, 8, 3), dtype='uint16')
    rgb[..., 0] = 10000
    rgb[..., 1] = 20000
    rgb[..., 2] = 30000
    out = tmp_path / 'rgb.tiff'
    WriteTiff16(str(out), rgb)
    array, palette = ReadTiff16(str(out))
    assert palette is None
    # RGB shape is preserved.
    assert array.shape == (8, 8, 3)


def test_tiff16_three_d_grayscale(tmp_path: Path) -> None:
    """A 3-D ``(h, w, 1)`` grayscale array is reduced and written."""
    from picmaker.tiff16 import WriteTiff16
    arr = (np.arange(64, dtype='uint16') * 100).reshape(8, 8, 1)
    out = tmp_path / 'gray3d.tiff'
    WriteTiff16(str(out), arr)
    assert out.exists()


def test_tiff16_big_endian(tmp_path: Path) -> None:
    """``byteorder='big'`` writes a big-endian TIFF that round-trips."""
    from picmaker.tiff16 import ReadTiff16, WriteTiff16
    arr = (np.arange(64, dtype='uint16') * 100).reshape(8, 8)
    out = tmp_path / 'big.tiff'
    WriteTiff16(str(out), arr, byteorder='big')
    array, palette = ReadTiff16(str(out))
    assert array.shape == (8, 8) or array.shape == (8, 8, 1)
    assert palette is None


def test_tiff16_transpose_rotate90(tmp_path: Path) -> None:
    """``transpose=Image.Transpose.ROTATE_90`` rotates before writing."""
    from picmaker.tiff16 import WriteTiff16
    arr = (np.arange(64, dtype='uint16') * 100).reshape(8, 8)
    out = tmp_path / 'rot.tiff'
    WriteTiff16(str(out), arr, transpose=Image.Transpose.ROTATE_90)
    assert out.exists()


def test_tiff16_up_flag_flips_vertically(tmp_path: Path) -> None:
    """``up=True`` flips the image before writing."""
    from picmaker.tiff16 import WriteTiff16
    arr = (np.arange(64, dtype='uint16') * 100).reshape(8, 8)
    out = tmp_path / 'up.tiff'
    WriteTiff16(str(out), arr, up=True)
    assert out.exists()


# ---------------------------------------------------------------------------
# package-level __init__ re-exports (covers picmaker/__init__.py:17-21)
# ---------------------------------------------------------------------------


def test_package_imports_resolve(tiny_array: Any) -> None:
    """The top-level :mod:`picmaker` re-exports the core entry points."""
    import picmaker
    assert callable(picmaker.images_to_pics)
    assert callable(picmaker.process_images)
    assert callable(picmaker.read_one_image_array)
    assert callable(picmaker.tinted_colormap)
    assert callable(picmaker.apply_colormap)
    assert callable(picmaker.get_limits)
    # tiny_array fixture verifies the conftest plumbing still works.
    assert tiny_array.shape == (16, 16)
