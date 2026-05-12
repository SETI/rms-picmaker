"""Cover the ``_filters.filter_image`` branches."""

from PIL import Image

from picmaker._filters import filter_image


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
