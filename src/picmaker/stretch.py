##########################################################################################
# picmaker/stretch.py
##########################################################################################
"""Support for stretch options."""

import numpy as np
from scipy.ndimage import median_filter


def get_limits(array, mask=None, *, limits=None, percentiles=None, trim=0,
               trim_zeros=False, footprint=0., **kwargs):
    """Compute stretch limits from numeric limits and/or percentiles.

    Parameters:
        array (array): A 2-D or 3-D array.
        mask (array, optional): mask array (True for invalid pixels), or None.
        limits (tuple[float, float], optional): Lower and upper limits of the pixel values
            to consider; values outside this range are masked. Use None for the full
            dynamic range.
        percentiles (tuple[float, float], optional): Percentage points between the
            identified extremes corresponding to the returned limits.
        trim (int, optional): The number of pixels around the image edge to exclude from
            the limits. Use this if the pixels near the edge of an image are unreliable or
            likely to be corrupted.
        trim_zeros (bool, optional): True to trim exterior rows/columns that contain all
            zeros before calculating limits.
        footprint (int, optional): Size of a 2-D median filter to be applied to the image
            before determining the limits. Use this option to suppress extreme pixels.
        **kwargs: Additional input parameters, ignored here.

    Returns:
        (tuple[float, float]): The lower and upper limits for the stretch.
    """

    if limits is None:

        if mask is None:
            mask = np.isnan(array)
        else:
            mask = mask | np.isnan(array)

        # Apply the trim
        if trim:
            array = array[..., trim:-trim, trim:-trim]
            mask = mask[..., trim:-trim, trim:-trim]

        # Apply trim_zeros
        antimask = np.logical_not(mask)
        if trim_zeros:
            nonzeros = (array != 0) & antimask
            if nonzeros.ndim == 3:
                nonzeros = np.any(nonzeros, axis=0)
            rows = np.flatnonzero(np.any(nonzeros, axis=1))
            cols = np.flatnonzero(np.any(nonzeros, axis=0))
            if len(rows) != 0:  # not all zeros
                array = array[..., rows[0]:rows[-1]+1, cols[0]:cols[-1]+1]
                antimask = antimask[..., rows[0]:rows[-1]+1, cols[0]:cols[-1]+1]

        # Apply footprint if any; leave antimask unchanged
        if footprint:
            # Confine masked (out-of-range or NaN) pixels to the valid data range first,
            # so the median filter cannot bleed extreme masked values into valid pixels.
            array = np.clip(array, np.min(array[antimask]), np.max(array[antimask]))
            circle_footprint = _circle_mask(footprint)
            if array.ndim == 3:
                if array.shape[0] > 3:  # for more than three bands, collapse to 2-D
                    array = np.median(array, axis=0)
                    array = median_filter(array, footprint=circle_footprint)
                else:                   # otherwise, process each band
                    array = array.copy()
                    for b in range(array.shape[0]):
                        array[b] = median_filter(array[b], footprint=circle_footprint)
            else:
                array = median_filter(array, footprint=circle_footprint)

        # Get the extrema
        unmasked = array[antimask]
        if not len(unmasked):   # fully masked
            return (0., 1.)

        array_min = np.min(array[antimask])
        array_max = np.max(array[antimask])

        # Return for the case of a single-valued array
        if array_min == array_max:
            if array_min == 0.:
                return (0., 1.)
            elif array_min < 0:
                return (array_min, 0.)
            elif array.dtype.kind in {'u', 'i'}:
                return (float(array_min), float(array_min + 1))
            else:
                return (array_min, array_min * 2.)

        # Derive limits, narrowing to the requested percentiles of the valid data
        if percentiles is None:
            limits = (array_min, array_max)
        else:
            limits = tuple(np.percentile(array[antimask], percentiles[:2]))

    return limits


def _circle_mask(diameter):
    """A boolean disk mask of the given diameter.

    Parameters:
        diameter (float): The disk diameter in pixels.

    Returns:
        array[bool]: A 2-D array where True marks pixels inside the circle.
    """

    size = int(np.ceil(diameter))
    center = 0.5 * (size - 1)

    r = np.arange(size) - center
    rsq = r**2
    mask = (rsq + rsq[:, np.newaxis]) <= (diameter / 2.)**2

    if np.sum(mask[0]) == 0:
        mask = mask[1:-1, 1:-1]

    return mask


__all__ = ['get_limits']

##########################################################################################
