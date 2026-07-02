##########################################################################################
# picmaker/slicing.py
##########################################################################################

import numpy as np


def slice_array(array, *, samples=None, lines=None, bands=None, valid=None, crop=None,
                **kwargs):
    """Return the requested slice of an array.

    Parameters:
        array (array): A 2-D or 3-D image array. It is indexed (lines, samples) if
            2-D, (bands, lines, samples) if 3-D.
        samples (tuple[int, int], optional): Sample limits (s0, s1); None to preserve all
            samples.
        lines (tuple[int, int], optional): Line limits (l0, l1); None to preserve all
            lines.
        bands (tuple[int, int], optional): Band limits (b0, b1) for defining a range of
            bands to coadd; None for all bands.
        valid (tuple[float, float], optional): The value range (vmin, vmax) in the
            array to be considered valid; None treats all values as valid.
        crop (float, optional): Numeric value to crop from the border of the image (e.g.
            0 to crop zero-valued rows and columns). None disables cropping.
        **kwargs: Additional input options, ignored here.

    Returns:
        tuple: `(sliced_array, invalid_mask)`, where

        * `sliced_array` is a 2-D band-averaged array if `bands` were specified.
          Otherwise, the number of dimensions in the original array is preserved. Under
          most circumstances, this matches the dimensionality of the input array (a
          singleton band axis is collapsed, so a 3-D input with one band returns 2-D).
        * `invalid_mask``is the mask array; it may be None if no pixels are masked.
          Values of NaN are always masked. The shape of this mask always matches that of
          `sliced_array`.

    Raises:
        ValueError: If the requested slice has size zero.
    """

    # Apply index ranges
    if samples:
        array = array[..., samples[0]:samples[1]]
    if lines:
        array = array[..., lines[0]:lines[1], :]
    if bands and array.ndim == 3:
        array = array[bands[0]:bands[1], :, :]

    if not array.size:
        raise ValueError('sliced image has size zero')

    # Eliminate the bands axis if it's one
    if array.ndim == 3 and array.shape[0] == 1:
        array = array[0]

    # Define the mask and nan_mask
    mask = None
    nan_mask = None
    if valid:
        mask = (array < valid[0]) | (array > valid[1])
    if array.dtype.kind == 'f':
        nan_mask = np.isnan(array)
        mask = nan_mask if mask is None else (mask | nan_mask)
        if nan_mask.any():
            array = array.copy()        # avoid mutating the caller's array
            array[nan_mask] = 0.

    # Coadd the bands, excluding masked pixels
    if bands and array.ndim == 3:
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
        array, mask = _crop_array(array, crop, mask=mask)

    return (array, mask)


def _crop_array(array, crop=0., *, mask=None):
    """Crop constant-valued borders from a 2-D array.

    Parameters:
        array (array): A 2-D or 3-D image.
        crop (float): A constant pixel value to trim from the border.
        mask (array[bool], optional): Mask array.

    Returns:
        tuple: `(array, mask)`, where `array` is the cropped array and `mask` is the
        cropped mask.
    """

    if mask is not None:
        array[mask] = crop

    other_value = (array != crop)
    if mask is not None:
        other_value &= np.logical_not(mask)

    if array.ndim == 3:
        other_value = np.any(other_value, axis=0)

    rows = np.flatnonzero(np.any(other_value, axis=1))
    cols = np.flatnonzero(np.any(other_value, axis=0))
    if len(rows) != 0:  # not all crop values
        array = array[..., rows[0]:rows[-1]+1, cols[0]:cols[-1]+1]
        if mask is not None:
            mask = mask[..., rows[0]:rows[-1]+1, cols[0]:cols[-1]+1]

    return (array, mask)


__all__ = ['slice_array']

##########################################################################################
