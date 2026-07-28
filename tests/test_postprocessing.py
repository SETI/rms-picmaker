"""Cover the ``picmaker.postprocessing.filter_pil_image`` branches."""

import pytest
from PIL import Image

from picmaker.postprocessing import filter_pil_image


def test_filter_pil_image_none_is_identity() -> None:
    """``filter='none'`` (and the ``None`` default) returns the input untouched."""
    im = Image.new('L', (8, 8))
    assert filter_pil_image(im, 'none') is im
    # The default ``filter=None`` is coerced to ``'none'`` and is also identity.
    assert filter_pil_image(im) is im
    # Filter names are case-insensitive.
    assert filter_pil_image(im, 'NONE') is im


def test_filter_pil_image_none_short_circuits_before_type_guard() -> None:
    """``filter='none'`` returns the input before the 2-byte type guard runs.

    Behavior change from the old ``_filters.filter_image``: a list (16-bit
    two-byte image) passed with ``filter='none'`` is no longer rejected; the
    ``'none'`` branch short-circuits and returns the input object unchanged.
    """
    assert filter_pil_image([], 'none') == []


def test_filter_pil_image_named_filter_applies() -> None:
    """A named filter is applied to a PIL image, changing its pixels."""
    im = Image.new('L', (8, 8), color=0)
    im.putpixel((4, 4), 255)
    out = filter_pil_image(im, 'blur')
    # The blur spreads the single bright pixel, so the output differs.
    assert list(out.get_flattened_data()) != list(im.get_flattened_data())
    # Filter names are case-insensitive.
    assert (list(filter_pil_image(im, 'BLUR').get_flattened_data())
            == list(out.get_flattened_data()))


def test_filter_pil_image_two_byte_list_raises_valueerror() -> None:
    """A named filter on a list (16-bit two-byte image) is rejected."""
    with pytest.raises(ValueError, match='2-byte'):
        filter_pil_image([], 'blur')


def test_filter_pil_image_unknown_filter_raises_keyerror() -> None:
    """An unrecognized filter name raises ``KeyError``."""
    im = Image.new('L', (8, 8))
    with pytest.raises(KeyError):
        filter_pil_image(im, 'bogus')
