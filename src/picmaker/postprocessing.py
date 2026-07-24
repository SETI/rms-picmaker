##########################################################################################
# picmaker/postprocessing.py
##########################################################################################
"""Post-stretch PIL-image processing: named filters and the adjustment operations."""

from PIL import Image, ImageEnhance, ImageFilter

_FILTER_DICT = {
    'none'             : None,
    'blur'             : ImageFilter.BLUR,
    'contour'          : ImageFilter.CONTOUR,
    'detail'           : ImageFilter.DETAIL,
    'edge_enhance'     : ImageFilter.EDGE_ENHANCE,
    'edge_enhance_more': ImageFilter.EDGE_ENHANCE_MORE,
    'emboss'           : ImageFilter.EMBOSS,
    'find_edges'       : ImageFilter.FIND_EDGES,
    'smooth'           : ImageFilter.SMOOTH,
    'smooth_more'      : ImageFilter.SMOOTH_MORE,
    'sharpen'          : ImageFilter.SHARPEN,
    'median_3'         : ImageFilter.MedianFilter(3),
    'median_5'         : ImageFilter.MedianFilter(5),
    'median_7'         : ImageFilter.MedianFilter(7),
    'minimum_3'        : ImageFilter.MinFilter(3),
    'minimum_5'        : ImageFilter.MinFilter(5),
    'minimum_7'        : ImageFilter.MinFilter(7),
    'maximum_3'        : ImageFilter.MaxFilter(3),
    'maximum_5'        : ImageFilter.MaxFilter(5),
    'maximum_7'        : ImageFilter.MaxFilter(7),
}

FILTER_CHOICES = list(_FILTER_DICT.keys())

# The Pillow ImageEnhance classes, keyed by the option that selects each one. The order
# is the order in which they are applied; see adjust_pil_image.
_ADJUSTERS = {
    'brighten'  : ImageEnhance.Brightness,
    'contrast'  : ImageEnhance.Contrast,
    'saturation': ImageEnhance.Color,
    'sharpen'   : ImageEnhance.Sharpness,
}

ADJUST_OPTIONS = list(_ADJUSTERS.keys())


def filter_pil_image(image, filter=None, **kwargs):
    """Apply an arbitrary filter to a PIL image.

    Two-byte (16-bit) images are not supported and raise ValueError.

    Parameters:
        image (PIL.Image): A PIL image as 8-bit RGB or grayscale.
        filter (str, optional): Name of the filter to be applied. Valid choices are:
            "none", "blur", "contour", "detail", "edge_enhance", "edge_enhance_more",
            "emboss", "find_edges", "smooth", "smooth_more", "sharpen", "median_3",
            "median_5", "median_7", "minimum_3", "minimum_5", "minimum_7", "maximum_3",
            "maximum_5", or "maximum_7". Values are case-insensitive. "none" returns the
            input image unchanged.
        **kwargs: Additional input options ignored here.

    Returns:
        PIL.Image: The filtered PIL image. For `filter` == "none", the input image is
            returned unchanged.

    Raises:
        ValueError: If `image` is a list (16-bit two-byte image).
        KeyError: If `filter` (ignoring case) is not recognized.
    """

    filter = (filter or 'none').lower()
    if filter == 'none':
        return image

    if not isinstance(image, Image.Image):
        raise ValueError('Image filters are not supported for 2-byte images')

    filter_method = _FILTER_DICT[filter]    # forward KeyError
    if filter_method:
        image = image.filter(filter_method)

    return image


def adjust_pil_image(image, **kwargs):
    """Apply the Pillow ImageEnhance adjustments to a PIL image.

    Each adjustment takes a factor, where 1.0 leaves the image unchanged, 0.0 reduces it
    to the degenerate case (black for `brighten`, solid gray for `contrast`, grayscale for
    `saturation`, blurred for `sharpen`), and values above 1.0 exaggerate the property. An
    option left at None is skipped entirely, so the common case of no adjustment does no
    work.

    When more than one is given they are applied in a fixed order -- `brighten`,
    `contrast`, `saturation`, then `sharpen` -- because these operations do not commute,
    and sharpening after the tonal and color adjustments is what a photo pipeline
    conventionally does.

    Two-byte (16-bit) images are not supported and raise ValueError, as for
    :func:`filter_pil_image`.

    Parameters:
        image (PIL.Image): A PIL image as 8-bit RGB or grayscale.
        **kwargs: Additional input options. The ones used here are `brighten`, `contrast`,
            `saturation`, and `sharpen`, each an optional float >= 0, where 1.0 is neutral
            and None means "leave alone".

    Returns:
        PIL.Image: The adjusted PIL image. If no adjustment option is set, the input
        image is returned unchanged.

    Raises:
        ValueError: If `image` is a list (16-bit two-byte image) and any adjustment was
            requested.
    """

    factors = [(name, kwargs.get(name)) for name in _ADJUSTERS]
    factors = [(name, factor) for name, factor in factors if factor is not None]
    if not factors:
        return image

    if not isinstance(image, Image.Image):
        raise ValueError('Image adjustments are not supported for 2-byte images')

    for name, factor in factors:
        image = _ADJUSTERS[name](image).enhance(factor)

    return image


__all__ = ['ADJUST_OPTIONS', 'FILTER_CHOICES', 'adjust_pil_image', 'filter_pil_image']

##########################################################################################
