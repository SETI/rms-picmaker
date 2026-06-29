##########################################################################################
# picmaker/processing.py
##########################################################################################
"""Image processing options."""

import numpy as np

from PIL import Image, ImageFilter

_FILTER_DICT = {
    'NONE'             : None,
    'BLUR'             : ImageFilter.BLUR,
    'CONTOUR'          : ImageFilter.CONTOUR,
    'DETAIL'           : ImageFilter.DETAIL,
    'EDGE_ENHANCE'     : ImageFilter.EDGE_ENHANCE,
    'EDGE_ENHANCE_MORE': ImageFilter.EDGE_ENHANCE_MORE,
    'EMBOSS'           : ImageFilter.EMBOSS,
    'FIND_EDGES'       : ImageFilter.FIND_EDGES,
    'SMOOTH'           : ImageFilter.SMOOTH,
    'SMOOTH_MORE'      : ImageFilter.SMOOTH_MORE,
    'SHARPEN'          : ImageFilter.SHARPEN,
    'MEDIAN_3'         : ImageFilter.MedianFilter(3),
    'MEDIAN_5'         : ImageFilter.MedianFilter(5),
    'MEDIAN_7'         : ImageFilter.MedianFilter(7),
    'MINIMUM_3'        : ImageFilter.MinFilter(3),
    'MINIMUM_5'        : ImageFilter.MinFilter(5),
    'MINIMUM_7'        : ImageFilter.MinFilter(7),
    'MAXIMUM_3'        : ImageFilter.MaxFilter(3),
    'MAXIMUM_5'        : ImageFilter.MaxFilter(5),
    'MAXIMUM_7'        : ImageFilter.MaxFilter(7),
}

FILTER_CHOICES = list(_FILTER_DICT.keys())


def filter_pil_image(image, filter=None, **kwargs):
    """Apply an arbitrary filter to a PIL image.

    Two-byte (16-bit) images are not supported and raise ``ValueError``.

    Parameters:
        image (PIL.Image): A PIL image as 8-bit RGB or grayscale.
        filter (str, optional): Name of the filter to be applied. Valid choices are:
            ``"NONE"``, ``"BLUR"``, ``"CONTOUR"``, ``"DETAIL"``, ``"EDGE_ENHANCE"``,
            ``"EDGE_ENHANCE_MORE"``, ``"EMBOSS"``, ``"FIND_EDGES"``, ``"SMOOTH"``,
            ``"SMOOTH_MORE"``, ``"SHARPEN"``, ``"MEDIAN_3"``, ``"MEDIAN_5"``,
            ``"MEDIAN_7"``, ``"MINIMUM_3"``, ``"MINIMUM_5"``, ``"MINIMUM_7"``,
            ``"MAXIMUM_3"``, ``"MAXIMUM_5"``, or ``"MAXIMUM_7"``. Values are
            case-insensitive. ``"NONE"`` returns the input image unchanged.
        **kwargs: Additional input options ignored here.

    Returns:
        (np.ndarray) The filtered PIL image. For ``filter='NONE'`` the input image is
            returned unchanged.

    Raises:
        ValueError: If ``image`` is a list (16-bit two-byte image).
        KeyError: If ``filter`` (ignoring case) is not recognized.
    """

    filter = (filter or 'NONE').upper()
    if filter == 'NONE':
        return image

    if not isinstance(image, Image):
        raise ValueError('image filters are not supported for of 2-byte images')

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
        array (np.ndarray): A 2-D or 3-D array (modified in place).
        **kwargs: Additional input options, ignored here.

    Returns:
        (np.ndarray[float]): The same array, modified in place if it is currently
        floating-point; converted from integers otherwise.
    """

    # Get the dimensions
    lines, samples = array.shape[-2:]

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


__all__ = ['FILTER_CHOICES', 'filter_pil_image', 'fill_zebra_stripes']

##########################################################################################
