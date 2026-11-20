##########################################################################################
# picmaker/slicing.py
##########################################################################################

import copy

import numpy as np


def slice_array(image_data, *, samples=None, lines=None, bands=None, valid=None,
                mask_ranges=None, crop=None, desnow=False, **kwargs):
    """Return a copy of an ImageData object, sliced and masked as requested.

    Parameters:
        image_data (ImageData): The image to slice. Its `array` is a 2-D or 3-D image
            array, indexed (lines, samples) if 2-D, (bands, lines, samples) if 3-D. Its
            `hmask` and `imask` attributes are each None or a boolean array with the
            same shape as `array`.
        samples (tuple[int, int], optional): Sample limits (s0, s1); None to preserve all
            samples.
        lines (tuple[int, int], optional): Line limits (l0, l1); None to preserve all
            lines.
        bands (tuple[int, int], optional): Band limits (b0, b1) for defining a range of
            bands to coadd; None for all bands.
        valid (tuple[float, float], optional): The value range (vmin, vmax) in the
            array to be considered valid; None treats all values as valid.
        mask_ranges (list[tuple[float, float]], optional): Value ranges (vmin, vmax),
            inclusive, of pixels to treat as invalid, e.g., [(0, 0)] to mask zero-valued
            pixels. None masks no additional values.
        crop (float, optional): Numeric value to crop from the border of the image (e.g.
            0 to crop zero-valued rows and columns). None disables cropping.
        desnow (bool, optional): True to keep the `imask` of `image_data`, so that its
            pixels (e.g., an instrument's data quality flags) are drawn in the invalid
            color; False to discard it, so those pixels are drawn normally. Either way,
            `hmask` is kept, so they are still excluded from the stretch.
        **kwargs: Additional input options, ignored here.

    Returns:
        ImageData: A shallow copy of `image_data`, of the same subclass, in which:

        * `array` is the sliced array: band-averaged and 2-D if `bands` were specified;
          otherwise, the number of dimensions in the original array is preserved, except
          that a singleton band axis is collapsed, so a 3-D input with one band returns
          2-D. NaNs are replaced by zero.
        * `hmask` and `imask` have been sliced in the same way as `array` and then
          combined by logical "or" with the invalid-pixel mask, i.e., pixels outside the
          `valid` range, inside any of the `mask_ranges`, or NaN. Where an attribute was
          None, it is replaced by a copy of the invalid-pixel mask. Either one is
          still None if it was None and no pixels are invalid. If `desnow` is False, the
          input `imask` is treated as None, so `imask` holds only invalid pixels.

        The input `image_data` object is not modified.

    Raises:
        ValueError: If the requested slice has size zero.
    """

    array = image_data.array
    masks = [image_data.hmask, image_data.imask if desnow else None]

    def _apply(func):
        """Apply a shape operation to the array and to each existing mask."""
        nonlocal array
        array = func(array)
        masks[:] = [None if m is None else func(m) for m in masks]

    # Apply index ranges
    if samples:
        _apply(lambda a: a[..., samples[0]:samples[1]])
    if lines:
        _apply(lambda a: a[..., lines[0]:lines[1], :])
    if bands and array.ndim == 3:
        _apply(lambda a: a[bands[0]:bands[1], :, :])

    if not array.size:
        raise ValueError('Sliced image has size zero')

    # Eliminate the bands axis if it's one
    if array.ndim == 3 and array.shape[0] == 1:
        _apply(lambda a: a[0])

    # Define the mask and nan_mask
    mask = None
    nan_mask = None
    if valid:
        mask = (array < valid[0]) | (array > valid[1])
    for (vmin, vmax) in (mask_ranges or []):
        in_range = (array >= vmin) & (array <= vmax)
        mask = in_range if mask is None else (mask | in_range)
    if array.dtype.kind == 'f':
        nan_mask = np.isnan(array)
        mask = nan_mask if mask is None else (mask | nan_mask)
        if nan_mask.any():
            array = array.copy()        # avoid mutating the caller's array
            array[nan_mask] = 0.

    # Coadd the bands, excluding masked pixels. An existing mask is collapsed so a pixel
    # stays masked only if it is masked in every band, matching the invalid-pixel mask.
    if bands and array.ndim == 3:
        masks[:] = [None if m is None else np.all(m, axis=0) for m in masks]
        if mask is None:
            array = np.mean(array, axis=0)
        else:
            weights = 1 - mask
            sum1 = np.sum(array * weights, axis=0)
            sum0 = np.sum(weights, axis=0)
            mask = sum0 == 0
            sum0 = np.maximum(sum0, 1)
            array = sum1 / sum0

    # Apply crop if any
    if crop is not None:
        region = _crop_region(array, crop, mask=mask)
        if region is not None:
            _apply(lambda a: a[region])
            if mask is not None:
                mask = mask[region]

    # Merge the invalid-pixel mask into hmask and imask, each getting its own array
    if mask is not None and mask.any():
        masks[:] = [mask.copy() if m is None else (m | mask) for m in masks]

    result = copy.copy(image_data)
    result.array = array
    (result.hmask, result.imask) = masks
    return result


def _crop_region(array, crop=0., *, mask=None):
    """The index region that crops constant-valued borders from an array.

    Parameters:
        array (array): A 2-D or 3-D image.
        crop (float): A constant pixel value to trim from the border.
        mask (array[bool], optional): Mask array; masked pixels count as border.

    Returns:
        tuple or None: An index tuple selecting the cropped region of `array` (or of an
        array of the same shape), or None if every pixel equals `crop` or is masked.
    """

    other_value = (array != crop)
    if mask is not None:
        other_value &= np.logical_not(mask)

    if array.ndim == 3:
        other_value = np.any(other_value, axis=0)

    rows = np.flatnonzero(np.any(other_value, axis=1))
    cols = np.flatnonzero(np.any(other_value, axis=0))
    if len(rows) == 0:  # all crop values
        return None

    return (Ellipsis, slice(rows[0], rows[-1]+1), slice(cols[0], cols[-1]+1))


__all__ = ['slice_array']

##########################################################################################
