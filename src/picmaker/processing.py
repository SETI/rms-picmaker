##########################################################################################
# picmaker/processing.py
##########################################################################################
"""Image processing options."""

import numpy as np
from PIL import Image, ImageFilter

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


def fill_zebra_stripes(array, **kwargs):
    """Fill zero zebra stripes around the edges of rows.

    Fills lines of zeros at the beginning and end of each row when the rows immediately
    above and below have nonzero values at the same columns. This removes an artifact
    associated with some spacecraft compression procedures.

    Parameters:
        array (array): A 2-D or 3-D array. It is not modified.
        **kwargs: Additional input options, ignored here.

    Returns:
        array[float]: A new floating-point array with the zebra stripes filled. The input
        is never modified, so a caller may reuse it (e.g. for a following version in which
        "--zebra" is not set).
    """

    # Get the dimensions
    lines, samples = array.shape[-2:]
    if lines <= 2:
        return array

    # Work on a float copy; the caller's array (shared across versions) is left untouched.
    array = array.astype('float')
    if array.ndim == 2:
        arrays = [array]
    else:
        arrays = [array[b] for b in range(array.shape[0])]

    # Loop through lines
    # lprev starts at 1 (row 0 peeks at row 1 as its "above" neighbor)
    for array2d in arrays:
        lprev = 1
        for line in range(lines):
            lnext = line + 1 if line + 1 < lines else line - 1

            row = array2d[line]
            above = array2d[lprev]
            below = array2d[lnext]

            nonzero = np.flatnonzero(row)
            if len(nonzero):
                ranges = [(0, nonzero[0]), (nonzero[-1]+1, samples)]
            else:
                ranges = [(0, samples)]

            for (s0, s1) in ranges:
                srange = np.arange(s0, s1)
                srange = srange[(above[srange] != 0) & (below[srange] != 0)]
                row[srange] = (above[srange] + below[srange]) / 2

            lprev = line

    return array


__all__ = ['FILTER_CHOICES', 'fill_zebra_stripes', 'filter_pil_image']

##########################################################################################
