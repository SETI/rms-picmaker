"""PIL filter dispatch helpers."""

from typing import Any

from PIL import ImageFilter

FILTER_DICT: dict[str, Any] = {
    'NONE': None,
    'BLUR': ImageFilter.BLUR,
    'CONTOUR': ImageFilter.CONTOUR,
    'DETAIL': ImageFilter.DETAIL,
    'EDGE_ENHANCE': ImageFilter.EDGE_ENHANCE,
    'EDGE_ENHANCE_MORE': ImageFilter.EDGE_ENHANCE_MORE,
    'EMBOSS': ImageFilter.EMBOSS,
    'FIND_EDGES': ImageFilter.FIND_EDGES,
    'SMOOTH': ImageFilter.SMOOTH,
    'SMOOTH_MORE': ImageFilter.SMOOTH_MORE,
    'SHARPEN': ImageFilter.SHARPEN,
    'MEDIAN_3': ImageFilter.MedianFilter(3),
    'MEDIAN_5': ImageFilter.MedianFilter(5),
    'MEDIAN_7': ImageFilter.MedianFilter(7),
    'MINIMUM_3': ImageFilter.MinFilter(3),
    'MINIMUM_5': ImageFilter.MinFilter(5),
    'MINIMUM_7': ImageFilter.MinFilter(7),
    'MAXIMUM_3': ImageFilter.MaxFilter(3),
    'MAXIMUM_5': ImageFilter.MaxFilter(5),
    'MAXIMUM_7': ImageFilter.MaxFilter(7),
}


def filter_image(image: Any, filter_name: str) -> Any:
    """Apply an arbitrary filter to a PIL image.

    Two-byte (16-bit) images are not supported and raise ``ValueError``.

    Parameters:
        image: A PIL image as 8-bit RGB or grayscale.
        filter_name: Name of the filter to be applied. Valid choices are the
            keys of ``FILTER_DICT`` (case-insensitive).

    Returns:
        The filtered PIL image (or the original image if the filter is
        ``'NONE'`` or unknown).

    Raises:
        ValueError: If ``image`` is a list (16-bit two-byte image).
    """
    if isinstance(image, list):
        raise ValueError('filtering of 2-byte images is not supported')

    filter_method = FILTER_DICT[filter_name.upper()]
    if filter_method:
        image = image.filter(filter_method)
    return image


__all__ = ['FILTER_DICT', 'filter_image']
