"""Cover the ``_filters.filter_image`` branches."""

import numpy as np
from PIL import Image

from picmaker._filters import filter_image


def test_filter_image_none_is_identity() -> None:
    """``filter='none'`` returns the input untouched."""
    im = Image.new('L', (8, 8))
    out = filter_image(im, 'none')
    assert out is im


def test_filter_image_blur() -> None:
    """A named filter (``blur``) actually changes pixel values."""
    # A non-uniform input is required because Pillow's BLUR on a
    # constant-color image is a no-op; a single bright pixel against
    # a black background gives blur something to do.
    im = Image.new('L', (8, 8), color=0)
    im.putpixel((4, 4), 255)
    out = filter_image(im, 'blur')
    assert out.size == (8, 8)
    in_pixels = np.asarray(im)
    out_pixels = np.asarray(out)
    assert not np.array_equal(in_pixels, out_pixels)
