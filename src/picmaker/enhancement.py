##########################################################################################
# picmaker/enhancement.py
##########################################################################################
"""Image enhancement options."""

import numpy as np
from scipy.stats import rankdata

from picmaker.colornames import ColorNames


def apply_colormap(array, valid_limits, invalid_mask=None, *, layer=None,
                   default_tint=None, histogram=False, colormap=None, tint=False,
                   below_color=None, above_color=None, invalid_color='black', gamma=1.,
                   **kwargs):
    """Apply a colormap to up to three grayscale images.

    Produces a 3-D array with one channel (grayscale) or three channels (RGB), in axis
    order (line, sample, channel). Values are scaled zero to one.

    Parameters:
        array (array): A 2-D or 3-D numpy array. If 3-D, the axis order is (bands, lines,
            samples).
        valid_limits (tuple[float, float]): The values that correspond to the minimum and
            maximum of the mapping.
        invalid_mask (array[bool], optional): Boolean mask of invalid pixels, including
            all NaNs in `array`.
        layer (int, None): The layer selection of the overall data array, if any.
        default_tint (str, tuple[int, int, int], or list of these, optional): The default
            colormap to use as defined by the instrument. This is used if not overridden
            by `colormap` and if `tint` is True.
        histogram (bool, optional): True to use histogram shading (uniform DN
            distribution).
        colormap (str, tuple[int, int, int], or list, optional): A color or list of
            colors to define the colors for the image. For example, ["black", "blue",
            "white"] defines a mapping in which the darkest pixels are black, the
            brightest pixels are white, and intermediate values contain varying shades of
            blue. If a single color is specified, it is treated as shorthand for ["black",
            <color>, "white"].
        tint (bool, optional): True to apply the instrument's `default_tint` as the
            colormap when no explicit `colormap` is given.
        below_color (str or tuple[int, int, int], optional): Color for pixels below the
            lower limit. The default is the first color of the `colormap`.
        above_color (str or tuple[int, int, int], optional): Color for pixels above the
            upper limit. The default is the last color of the `colormap`.
        invalid_color (str or tuple[int, int, int], optional): Color for invalid pixels.
        gamma (float): Gamma factor. Values > 1 darken midtones; values < 1 brighten
            midtones.
        **kwargs: Other input options, ignored.

    Returns:
        array[float]: A 3-D array in axis order `(line, sample, channel)`` scaled zero to
        one. For a grayscale image, the last axis has length 1; otherwise, it has length
        3.

    Notes:
        All colors are defined by either a color name (e.g., "blue") or by a tuple of
        three (R,G,B) integers in the range 0-255 (e.g., (255,255,0) for yellow). You can
        also specify a color using a string that contains an RGB tuple.
    """

    def _to_rgb(color):
        if isinstance(color, str):
            return ColorNames.lookup(color)
        return color

    def _is_color(color):
        return not (color[0] == color[1] == color[2])

    # Convert the source array to 3-D if necessary for consistent indexing below
    if array.ndim == 2:
        array = array[np.newaxis]
        if invalid_mask is not None:
            invalid_mask = invalid_mask[np.newaxis]
        bands = 1
    else:
        array = array[:3]   # no more than three bands here
        bands = array.shape[0]

    # When --tint is set and no explicit colormap is given, use the instrument's default
    # tint color as the colormap; the block below expands it to black -> tint -> white.
    if tint and not colormap and default_tint is not None:
        colormap = default_tint

    # Interpret colors and masks
    is_color = bands > 1
    if colormap:
        if not isinstance(colormap, list):
            colormap = [colormap]
        colormap = [_to_rgb(c) for c in colormap]
        is_color = is_color or any(_is_color(c) for c in colormap)

        if len(colormap) == 1:
            colormap = [(0, 0, 0), colormap[0], (255, 255, 255)]

    full_mask = np.zeros(array.shape, dtype='bool')
    below_mask = array < valid_limits[0]
    any_below = np.any(below_mask)
    if any_below:
        if below_color is None:
            below_color = colormap[0] if colormap else (0, 0, 0)
        else:
            below_color = _to_rgb(below_color)
        is_color = is_color or _is_color(below_color)
        full_mask |= below_mask

    above_mask = array > valid_limits[1]
    any_above = np.any(above_mask)
    if any_above:
        if above_color is None:
            above_color = colormap[-1] if colormap else (255, 255, 255)
        else:
            above_color = _to_rgb(above_color)
        is_color = is_color or _is_color(above_color)
        full_mask |= above_mask

    any_invalid = invalid_mask is not None and np.any(invalid_mask)
    if any_invalid:
        invalid_color = (0, 0, 0) if invalid_color is None else _to_rgb(invalid_color)
        is_color = is_color or _is_color(invalid_color)
        full_mask |= invalid_mask

    if not (any_below or any_above or any_invalid):
        full_mask = None

    # Determine whether we need one or three channels
    channels = 3 if is_color else 1

    # Apply the histogram scaling if necessary; scale zero to one
    if histogram:
        rankings = []
        for b in range(bands):
            if full_mask is None:
                source = array[b]
                count = source.size
            else:
                source = array[b].astype('float')
                source[full_mask[b]] = np.nan
                count = source.size - np.sum(full_mask[b])
            ranked = rankdata(source, nan_policy='omit').reshape(source.shape)
            # Values are 1 to count now. Each band must be scaled to the same maximum.
            ranked = (ranked - 0.5) / count
            rankings.append(ranked)

        if bands == 1:
            scaled = rankings[0][np.newaxis]
        else:
            scaled = np.array(rankings)

        if full_mask is not None:
            scaled[full_mask] = 0.  # hide the NaNs

    else:
        if array.dtype.kind in {'u', 'i'}:
            # expand valid_limits for int arrays
            valid_limits = (valid_limits[0] - 0.5, valid_limits[1] + 0.5)

        scaled = (array - valid_limits[0]) / (valid_limits[1] - valid_limits[0])
        scaled = np.clip(scaled, 0., 1., out=scaled)    # clip in place

    # Apply gamma
    if gamma != 1.:
        scaled = scaled ** gamma

    # Initialize the RGB array
    if is_color and bands < 3:
        moved = np.moveaxis(scaled, 0, -1)
        rgb_array = np.empty(moved.shape[:-1] + (3,))
        rgb_array[..., :bands] = moved
        rgb_array[..., bands:] = moved[..., -1:]
    else:
        rgb_array = np.moveaxis(scaled, 0, -1)

    # Apply the colormap
    if colormap:
        xbins = np.arange(len(colormap)) / (len(colormap) - 1)
        rgb_maps = [[c[k] / 255. for c in colormap] for k in range(3)]
        for b in range(channels):
            rgb_array[..., b] = np.interp(rgb_array[..., b], xbins, rgb_maps[b])

    # Fill in the highlight colors. The masks are in (band, line, sample) order; collapse
    # each to a 2-D spatial mask matching the (line, sample, channel) RGB array.
    for has_any, color, mask in [(any_below, below_color, below_mask),
                                 (any_above, above_color, above_mask),
                                 (any_invalid, invalid_color, invalid_mask)]:
        if has_any:
            spatial = np.any(mask, axis=0)
            rgb_array[spatial] = [color[b] / 255. for b in range(channels)]

    return rgb_array


__all__ = ['apply_colormap']

##########################################################################################
