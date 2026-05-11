"""Geometry helpers — wrap_image, pad_image, get_size, resize_image, rotate."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from picmaker.picmaker import (
    get_size,
    pad_image,
    resize_image,
    rotate_array_rgb,
    wrap_image,
)


class TestWrapImage:
    def test_two_horizontal_sections(self) -> None:
        # 40-wide strip wrapped horizontally (axis=0) into 2 sections produces
        # a roughly square output with a gap. Use 100x10 input → wrap into
        # wrapped_size (50, 21) with 2 sections (10 lines + 1 gap + 10 lines).
        img = Image.new('L', (100, 10), color=128)
        out = wrap_image(img, (50, 21), 2, 0, gap_size=1, gap_color='white')
        assert out.size == (50, 21)

    def test_two_vertical_sections(self) -> None:
        # Tall image (10x100) wrapped vertically into 2 sections.
        img = Image.new('L', (10, 100), color=128)
        out = wrap_image(img, (21, 50), 2, 1, gap_size=1, gap_color='white')
        assert out.size == (21, 50)

    def test_gap_color_named_lookup(self) -> None:
        img = Image.new('L', (40, 10), color=128)
        # Should not raise — 'white' resolves through ColorNames.
        out = wrap_image(img, (21, 21), 2, 0, gap_size=1, gap_color='white')
        assert out.size == (21, 21)


class TestPadImage:
    def test_interior_pad(self) -> None:
        img = Image.new('RGB', (10, 10), color='red')
        out = pad_image(img, frame=(20, 20), pad_color='white')
        assert out.size == (20, 20)

    def test_no_pad_needed_returns_same(self) -> None:
        img = Image.new('RGB', (10, 10), color='red')
        out = pad_image(img, frame=(10, 10), pad_color='white')
        assert out.size == (10, 10)

    def test_named_pad_color(self) -> None:
        img = Image.new('RGB', (4, 4), color='red')
        out = pad_image(img, frame=(8, 8), pad_color='blue')
        # Corner pixel was added by padding — must be blue, not the
        # red interior.
        corner = out.getpixel((0, 0))
        assert corner != (255, 0, 0)


class TestGetSize:
    def test_size_specified(self) -> None:
        # get_size returns (unwrapped, wrapped, sections, wrap_axis).
        unwrapped, wrapped, sections, axis = get_size(
            (100, 200), size=(50, 100)
        )
        assert sections == 1 and axis == 0
        # width=50, height=100 was requested; get_size should choose those.
        assert tuple(unwrapped) == (50, 100)

    def test_scale_default(self) -> None:
        unwrapped, wrapped, sections, axis = get_size((100, 200))
        # default scale=(100,100) means no change; width=array_shape[1]=200,
        # height=array_shape[0]=100.
        assert unwrapped == [200, 100]
        assert sections == 1 and axis == 0

    def test_scale_factor_half(self) -> None:
        unwrapped, *_ = get_size((100, 200), scale=(50.0, 50.0))
        assert unwrapped == [100, 50]

    def test_frame_limits_proportionally(self) -> None:
        unwrapped, _wrapped, _sections, _axis = get_size(
            (1000, 2000), frame=(100, 100)
        )
        # Both dimensions must fit within 100.
        assert max(unwrapped) <= 100

    def test_frame_max_caps_upscale(self) -> None:
        # 16x16 input + 512x512 frame; default frame_max=None scales to fit,
        # frame_max=50 caps at 50% of frame (256).
        unwrapped, *_ = get_size((16, 16), frame=(512, 512), frame_max=50)
        assert unwrapped[0] <= 256 and unwrapped[1] <= 256


class TestResizeImage:
    def test_resize_grayscale(self) -> None:
        img = Image.new('L', (10, 10), color=128)
        out = resize_image(img, (20, 20))
        assert out.size == (20, 20)

    def test_resize_rgb(self) -> None:
        img = Image.new('RGB', (10, 10), color='red')
        out = resize_image(img, (5, 5))
        assert out.size == (5, 5)


class TestRotateArrayRgb:
    def _make(self) -> np.ndarray:
        return np.arange(12, dtype=np.uint8).reshape(3, 4)

    def test_no_rotation_downward(self) -> None:
        arr = self._make()
        out = rotate_array_rgb(arr.copy(), display_upward=False, rotation_name='NONE')
        np.testing.assert_array_equal(out, arr)

    def test_upward_flips(self) -> None:
        arr = self._make()
        out = rotate_array_rgb(arr.copy(), display_upward=True, rotation_name='NONE')
        np.testing.assert_array_equal(out, np.flipud(arr))

    @pytest.mark.parametrize('name', ['FLIPLR', 'FLIPTB', 'ROT90', 'ROT180', 'ROT270'])
    def test_named_rotations_run(self, name: str) -> None:
        arr = self._make()
        out = rotate_array_rgb(arr.copy(), display_upward=False, rotation_name=name)
        # All shapes either match input or swap dims for ROT90/ROT270.
        assert out.shape in ((3, 4), (4, 3))

    def test_unknown_rotation_raises(self) -> None:
        arr = self._make()
        with pytest.raises(KeyError, match='Unrecognized rotation'):
            rotate_array_rgb(arr.copy(), display_upward=False, rotation_name='BAD')
