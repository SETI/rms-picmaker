"""Cover the geometry.py branches that the existing tests don't reach:
``get_size`` wrap-ratio search, ``wrap_image`` axis variants and gap
promotion, ``pad_image`` edge cases, ``slice_array`` masking, and the
``rotate_array_rgb`` rotation chain.
"""

import numpy as np
import pytest
from PIL import Image

from picmaker.geometry import (
    crop_array,
    get_size,
    pad_image,
    resize_image,
    rotate_array_rgb,
    slice_array,
    wrap_image,
)


def test_get_size_wrap_ratio_wide_image() -> None:
    """``wrap_ratio`` on a horizontally-elongated image picks horizontal
    sectioning.
    """
    # lines=4, samples=40 → array_size=[40, 4] → wide → axis 0 wrap.
    res = get_size((4, 40, 3), wrap_ratio=4.0)
    _, _, sections, axis = res
    assert sections >= 2
    assert axis == 0


def test_get_size_wrap_ratio_tall_image() -> None:
    """``wrap_ratio`` on a vertically-elongated image picks vertical
    sectioning.
    """
    # lines=40, samples=4 → array_size=[4, 40] → tall → axis 1 wrap.
    res = get_size((40, 4, 3), wrap_ratio=4.0)
    _, _, sections, axis = res
    assert sections >= 2
    assert axis == 1


def test_get_size_scale_passes_through() -> None:
    """``scale=(50, 50)`` halves the array size in both dimensions."""
    unwrapped, _, _, _ = get_size((16, 16, 3), scale=(50.0, 50.0))
    assert unwrapped == [8, 8]


def test_get_size_size_scalar() -> None:
    """A scalar ``size`` is broadcast to both dimensions."""
    unwrapped, _, _, _ = get_size((8, 8, 3), size=64)
    assert unwrapped == [64, 64]


def test_get_size_frame_max_caps_upscale() -> None:
    """``frame_max=PCT`` caps how far the input can be enlarged."""
    unwrapped, _, _, _ = get_size((8, 8, 3), frame=(64, 64), frame_max=200)
    # The exact integer result depends on the floor + cap; verify it's
    # strictly below the un-capped 64x64 target.
    assert max(unwrapped) < 64


def test_get_size_wrap_with_frame_searches_axes() -> None:
    """``wrap=True`` with a frame exercises the per-axis search."""
    res = get_size((4, 40, 3), frame=(40, 4), wrap=True)
    _, _, sections, _ = res
    assert sections >= 1


def test_wrap_image_basic_two_horizontal_sections() -> None:
    """``wrap_image`` produces an output of the requested wrapped size."""
    im = Image.new('L', (24, 4), color=128)
    out = wrap_image(
        im,
        wrapped_size=(12, 9),
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
        gap_color='red',
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
