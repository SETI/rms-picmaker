"""Pixel-value enhancement: stretch limits, gamma, colormap lookup, zebra fill.

These functions take 2-D numpy arrays (post slicing/cropping) and adjust
intensity or map intensity to color. None of them resize or rotate.
"""

from typing import Any

import numpy as np
from scipy.ndimage import median_filter
from scipy.stats import rankdata

from picmaker.colornames import ColorNames
from picmaker.geometry import circle_mask

HISTOGRAM_BINS = 1024


def fill_zebra_stripes(array2d: Any) -> Any:
    """Fill zero zebra stripes around the edges of rows.

    Fills lines of zeros at the beginning and end of each row when the
    rows immediately above and below have nonzero values at the same
    columns. This removes an artifact associated with some spacecraft
    compression procedures.

    Args:
        array2d: A 2-D numpy array (modified in place).

    Returns:
        The same array, modified in place.
    """
    (lines, samples) = array2d.shape

    lprev = 1
    for line in range(lines):
        lnext = line + 1
        if lnext == lines:
            lnext = line - 1

        for s in range(samples):
            if array2d[line, s] != 0:
                break

            array_above = int(array2d[lprev, s])
            array_below = int(array2d[lnext, s])

            if array_above and array_below:
                array2d[line, s] = (array_above + array_below) / 2

        for s in range(samples - 1, -1, -1):
            if array2d[line, s] != 0:
                break

            array_above = int(array2d[lprev, s])
            array_below = int(array2d[lnext, s])

            if array_above and array_below:
                array2d[line, s] = (array_above + array_below) / 2

        # Safe to update in place: we only touch zero pixels with non-zero
        # neighbors above and below.
        lprev = line

    return array2d


def get_limits(
    array2d: Any,
    mask: Any,
    limits: Any = None,
    percentiles: tuple[float, float] = (0.0, 100.0),
    *,
    assume_int: bool = False,
    trim: int = 0,
    trim_zeros: bool = False,
    footprint: int = 0,
) -> Any:
    """Compute stretch limits from numeric limits and/or percentiles.

    Args:
        array2d: The 2-D numpy array, which may be masked.
        mask: 2-D mask array (True for masked pixels), or ``None``.
        limits: Numeric ``(lower, upper)`` to confine the histogram, or
            ``None`` for the full dynamic range.
        percentiles: ``(lower%, upper%)`` corresponding to the returned
            limits.
        assume_int: Treat the array as integers even if it isn't.
            Integer histograms extend from 0.5 below the minimum to
            0.5 above the maximum.
        trim: Number of pixels around the image edge to exclude.
        trim_zeros: If True, trim exterior rows/columns that contain
            all zeros before calculating limits.
        footprint: Size of the 2-D median filter applied as an
            alternative way to set limits.

    Returns:
        The ``(lower, upper)`` stretch limits.
    """
    is_int = array2d.dtype.kind in ('i', 'u')
    if assume_int:
        is_int = True

    if trim != 0:
        trimmed = array2d[trim:-trim, trim:-trim]
        if mask is None:
            tmask: Any = np.zeros(trimmed.shape, dtype='bool')
        else:
            tmask = mask[trim:-trim, trim:-trim]
    else:
        trimmed = array2d
        tmask = mask

    trimmed_v1 = trimmed
    tmask_v1 = tmask
    if trim_zeros:
        if tmask is None:
            tmask = np.zeros(trimmed.shape, dtype='bool')

        while trimmed.size and np.all(trimmed[0] == 0):
            trimmed = trimmed[1:]
            tmask = tmask[1:]
        while trimmed.size and np.all(trimmed[-1] == 0):
            trimmed = trimmed[:-1]
            tmask = tmask[:-1]
        while trimmed.size and np.all(trimmed[:, 0] == 0):
            trimmed = trimmed[:, 1:]
            tmask = tmask[:, 1:]
        while trimmed.size and np.all(trimmed[:, -1] == 0):
            trimmed = trimmed[:, :-1]
            tmask = tmask[:, :-1]

        if trimmed.size == 0:
            trimmed = trimmed_v1
            tmask = tmask_v1

    if tmask is None:
        non_nans = trimmed
    else:
        non_nans = trimmed[~tmask]

    if non_nans.size:
        array_min = non_nans.min()
        array_max = non_nans.max()
    else:
        array_min = 0
        array_max = 0

    if array_min == array_max:
        if is_int:
            return (array_min, array_min + 1)
        elif array_min == 0.0:
            return (0.0, 1.0)
        elif array_min < 0.0:
            return (array_min, 0.0)
        else:
            return (array_min, array_min * 2.0)

    if limits is None:
        if is_int:
            limits = (array_min - 0.5, array_max + 0.5)
        else:
            limits = (array_min, array_max)

    if not percentiles:
        percentiles = (0.0, 100.0)

    if percentiles != (0.0, 100.0):
        if is_int:
            dn0 = np.floor(limits[0] + 0.5) - 0.5
            dn1 = np.ceil(limits[1] - 0.5) + 0.5

            hbins: Any = dn1 - dn0
            hrange = (dn0, dn1)

            if hbins > HISTOGRAM_BINS:
                hbins = HISTOGRAM_BINS

        else:
            hbins = HISTOGRAM_BINS
            hrange = limits

        hbins = int(hbins)
        hist = np.histogram(non_nans, bins=hbins, range=hrange)

        cumhist = np.array([0] * (hbins + 1), 'float64')
        np.cumsum(hist[0], out=cumhist[1:])

        dnlist = hist[1]

        cumvals = np.interp(limits, dnlist, cumhist)
        percentlist = 100.0 * ((cumhist - cumvals[0]) / (cumvals[1] - cumvals[0]))

        limits = (
            _percentile_lookup(percentiles[0], percentlist, dnlist, limits),
            _percentile_lookup(percentiles[1], percentlist, dnlist, limits),
        )

    if footprint:
        circle_footprint = circle_mask(footprint)
        filtered = median_filter(trimmed, footprint=circle_footprint)

        if tmask is None:
            limits = (
                max(filtered.min(), limits[0]),
                min(filtered.max(), limits[1]),
            )
        else:
            limits = (
                max(filtered[~tmask].min(), limits[0]),
                min(filtered[~tmask].max(), limits[1]),
            )

    return limits


def _percentile_lookup(
    p: float, percentlist: Any, dnlist: Any, limits: tuple[Any, Any]
) -> Any:
    """Look up a single percentile in a cumulative histogram.

    Uses :func:`numpy.interp` (which uses ``searchsorted`` internally)
    so the lookup is vectorized when called by ``get_limits``.
    """
    if p <= 0.0:
        return limits[0]
    if p >= 100.0:
        return limits[1]

    dn = np.interp(p, percentlist, dnlist)

    if dn <= limits[0]:
        return limits[0]
    if dn >= limits[1]:
        return limits[1]

    if np.isnan(dn):
        return np.mean(dnlist[np.where(percentlist == p)])

    return dn


def apply_colormap(
    array2d: Any,
    limits: tuple[Any, Any],
    histogram: bool = False,
    colormap: Any = None,
    invalid_mask: Any = None,
    below_color: Any = None,
    above_color: Any = None,
    invalid_color: Any = 'black',
) -> Any:
    """Apply a colormap to a grayscale image.

    Produces a 3-D array with one band (grayscale) or three bands (RGB),
    in axis order ``(line, sample, band)``.

    Args:
        array2d: A 2-D numpy array.
        limits: The values that correspond to the first and last
            colors of the mapping.
        histogram: True to use histogram shading (uniform DN
            distribution).
        colormap: An N-tuple of colors or color names (e.g.
            ``"red-blue"``). ``None`` keeps the image grayscale.
        invalid_mask: Boolean mask of invalid pixels.
        below_color: Color for pixels below the lower limit. Defaults
            to the first color of the colormap.
        above_color: Color for pixels above the upper limit. Defaults
            to the last color of the colormap.
        invalid_color: Color for invalid pixels.

    Returns:
        A 3-D array in axis order ``(line, sample, band)`` scaled 0-1.
    """
    is_gray = True
    mapcolors = 2

    highlights: list[Any] = [below_color, above_color, invalid_color]
    for i in range(len(highlights)):
        if highlights[i]:
            if isinstance(highlights[i], str):
                highlights[i] = ColorNames.lookup(highlights[i])  # type: ignore[no-untyped-call]

            highlights[i] = np.array(highlights[i][:], 'float') / 255.0

            if (
                highlights[i][0] != highlights[i][1]
                or highlights[i][0] != highlights[i][2]
            ):
                is_gray = False

    if highlights[2] is None:
        highlights[2] = np.zeros((3), 'float')

    if colormap:
        if isinstance(colormap, str):
            names = colormap.split('-')
            colormap = [ColorNames.lookup(name) for name in names]  # type: ignore[no-untyped-call]

        if len(colormap) == 1:
            colormap = [(0, 0, 0), colormap[0], (255, 255, 255)]

        mapcolors = len(colormap)

        for c in colormap:
            if c[0] != c[1] or c[0] != c[2]:
                is_gray = False

        if isinstance(colormap, tuple):
            colormap = list(colormap)
        colormap.append(colormap[-1])
        colormap.append(colormap[-1])

        colormap = np.array(colormap, 'float') / 255.0

    if is_gray:
        channels = 1
    else:
        channels = 3

    if histogram:
        normalized = rankdata(array2d)
        normalized = normalized.reshape(array2d.shape)
        mask = (limits[0] <= array2d) & (array2d <= limits[1])
        limits = (np.min(normalized[mask]), np.max(normalized[mask]))
    else:
        normalized = array2d

    scaled = normalized.astype('float')
    denom = limits[1] - limits[0]
    if denom == 0:
        denom = 1.0
    scaled = (mapcolors - 1) * ((scaled - limits[0]) / float(denom))
    scaled = scaled.clip(0, mapcolors - 1)

    if colormap is not None:
        (indices, fracs) = np.divmod(scaled, 1.0)
        indices = indices.astype('int')

        result = np.zeros((array2d.shape[0], array2d.shape[1], channels))
        for c in range(channels):
            below = np.take(colormap[:, c], indices)
            above = np.take(colormap[:, c], indices + 1)
            result[:, :, c] = below + fracs * (above - below)
    else:
        if channels == 1:
            result = np.atleast_3d(scaled)
        else:
            result = np.dstack((scaled, scaled, scaled))

    for c in range(channels):
        channel = result[:, :, c]

        if highlights[0] is not None:
            channel[array2d < limits[0]] = highlights[0][c]
        if highlights[1] is not None:
            channel[array2d > limits[1]] = highlights[1][c]

        if invalid_mask is not None:
            channel[invalid_mask] = highlights[2][c]

    return result


def apply_gamma(array: Any, gamma: float) -> Any:
    """Apply a gamma curve to an array already scaled 0-1.

    Args:
        array: A 2-D or 3-D numpy array.
        gamma: Gamma factor. ``> 1`` brightens midtones; ``< 1`` darkens.

    Returns:
        The rescaled array.
    """
    if gamma != 1.0:
        array = array**gamma
    return array


__all__ = [
    'HISTOGRAM_BINS',
    '_percentile_lookup',
    'apply_colormap',
    'apply_gamma',
    'fill_zebra_stripes',
    'get_limits',
]
