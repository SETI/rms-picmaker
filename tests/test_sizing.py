"""Tests for picmaker.sizing: get_size dimensioning and resize_pil_image."""

from PIL import Image

from picmaker.sizing import get_size, resize_pil_image


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


def test_resize_pil_image_noop_when_size_matches() -> None:
    """``resize_pil_image`` returns the input untouched when sizes match."""
    im = Image.new('L', (8, 8))
    out = resize_pil_image(im, (8, 8))
    assert out is im


def test_resize_pil_image_upscale() -> None:
    """Upscaling lands on the requested size."""
    im = Image.new('L', (4, 4), color=10)
    out = resize_pil_image(im, (16, 16))
    assert out.size == (16, 16)


class TestGetSize:
    def test_size_specified(self) -> None:
        # get_size returns (unwrapped, wrapped, sections, wrap_axis).
        unwrapped, _, sections, axis = get_size((100, 200), size=(50, 100))
        assert sections == 1
        assert axis == 0
        # width=50, height=100 was requested; get_size should choose those.
        assert tuple(unwrapped) == (50, 100)

    def test_scale_default(self) -> None:
        unwrapped, _, sections, axis = get_size((100, 200))
        # default scale=(100,100) means no change; width=array_shape[1]=200,
        # height=array_shape[0]=100.
        assert unwrapped == [200, 100]
        assert sections == 1
        assert axis == 0

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
        assert unwrapped[0] <= 256
        assert unwrapped[1] <= 256


class TestResizePilImage:
    def test_resize_grayscale(self) -> None:
        img = Image.new('L', (10, 10), color=128)
        out = resize_pil_image(img, (20, 20))
        assert out.size == (20, 20)

    def test_resize_rgb(self) -> None:
        img = Image.new('RGB', (10, 10), color='red')
        out = resize_pil_image(img, (5, 5))
        assert out.size == (5, 5)
