"""Tests for picmaker.layout: wrap_pil_image and pad_pil_image."""

from PIL import Image

from picmaker.layout import pad_pil_image, wrap_pil_image


def test_wrap_pil_image_basic_two_horizontal_sections() -> None:
    """``wrap_pil_image`` produces an output of the requested wrapped size."""
    im = Image.new('L', (24, 4), color=128)
    out = wrap_pil_image(
        im,
        wrapped_size=(12, 9),
        sections=2,
        wrap_axis=0,
        gap_size=1,
        gap_color='white',
    )
    assert out.size == (12, 9)


def test_wrap_pil_image_promotes_grayscale_to_rgb_for_colored_gap() -> None:
    """A grayscale input plus a non-grey gap colour produces an RGB output."""
    im = Image.new('L', (24, 4), color=128)
    out = wrap_pil_image(
        im,
        wrapped_size=(12, 9),
        sections=2,
        wrap_axis=0,
        gap_size=1,
        gap_color='red',
    )
    assert out.size == (12, 9)
    assert out.mode == 'RGB'


def test_wrap_pil_image_no_gap_uses_black_internally() -> None:
    """``gap_size=0`` short-circuits the gap-colour logic."""
    im = Image.new('L', (16, 4), color=128)
    out = wrap_pil_image(
        im,
        wrapped_size=(8, 8),
        sections=2,
        wrap_axis=0,
        gap_size=0,
        gap_color='red',
    )
    assert out.size == (8, 8)


def test_wrap_pil_image_vertical_two_sections() -> None:
    """``wrap_pil_image`` along the vertical axis works symmetrically."""
    im = Image.new('L', (4, 24), color=128)
    out = wrap_pil_image(
        im,
        wrapped_size=(9, 12),
        sections=2,
        wrap_axis=1,
        gap_size=1,
        gap_color='white',
    )
    assert out.size == (9, 12)


def test_pad_pil_image_with_colored_pad_grows_to_frame() -> None:
    """Padding a grayscale image with a non-grey colour still hits the
    enlarged-buffer path; the result lands at the requested frame size.
    """
    im = Image.new('L', (4, 4), color=200)
    out = pad_pil_image(im, (16, 16), pad=True, pad_color='red')
    assert out.size == (16, 16)


def test_pad_pil_image_already_meets_one_axis() -> None:
    """``pad_pil_image`` enlarges only the deficient axis."""
    im = Image.new('L', (16, 4), color=200)
    out = pad_pil_image(im, (16, 16), pad=True, pad_color='black')
    assert out.size == (16, 16)


def test_pad_pil_image_grows_to_frame() -> None:
    """``pad_pil_image`` enlarges a small image to the target frame."""
    im = Image.new('L', (4, 4), color=200)
    out = pad_pil_image(im, (16, 16), pad=True, pad_color='black')
    assert out.size == (16, 16)


def test_pad_pil_image_noop_when_frame_none() -> None:
    """``pad_pil_image`` is a no-op when ``frame is None``."""
    im = Image.new('L', (4, 4))
    out = pad_pil_image(im, None, pad=True, pad_color='black')
    assert out is im


def test_pad_pil_image_noop_when_already_big() -> None:
    """``pad_pil_image`` returns the input when it already covers the frame."""
    im = Image.new('L', (16, 16))
    out = pad_pil_image(im, (4, 4), pad=True, pad_color='black')
    assert out is im


class TestWrapPilImage:
    def test_two_horizontal_sections(self) -> None:
        # 40-wide strip wrapped horizontally (axis=0) into 2 sections produces
        # a roughly square output with a gap. Use 100x10 input → wrap into
        # wrapped_size (50, 21) with 2 sections (10 lines + 1 gap + 10 lines).
        img = Image.new('L', (100, 10), color=128)
        out = wrap_pil_image(img, (50, 21), 2, 0, gap_size=1, gap_color='white')
        assert out.size == (50, 21)

    def test_two_vertical_sections(self) -> None:
        # Tall image (10x100) wrapped vertically into 2 sections.
        img = Image.new('L', (10, 100), color=128)
        out = wrap_pil_image(img, (21, 50), 2, 1, gap_size=1, gap_color='white')
        assert out.size == (21, 50)

    def test_gap_color_named_lookup(self) -> None:
        img = Image.new('L', (40, 10), color=128)
        # Should not raise — 'white' resolves through ColorNames.
        out = wrap_pil_image(img, (21, 21), 2, 0, gap_size=1, gap_color='white')
        assert out.size == (21, 21)


class TestPadPilImage:
    def test_interior_pad(self) -> None:
        img = Image.new('RGB', (10, 10), color='red')
        out = pad_pil_image(img, frame=(20, 20), pad=True, pad_color='white')
        assert out.size == (20, 20)

    def test_no_pad_needed_returns_same(self) -> None:
        img = Image.new('RGB', (10, 10), color='red')
        out = pad_pil_image(img, frame=(10, 10), pad=True, pad_color='white')
        assert out.size == (10, 10)

    def test_named_pad_color(self) -> None:
        img = Image.new('RGB', (4, 4), color='red')
        out = pad_pil_image(img, frame=(8, 8), pad=True, pad_color='blue')
        # Corner pixel was added by padding — exact X11 'blue' is (0, 0, 255).
        assert out.getpixel((0, 0)) == (0, 0, 255)
