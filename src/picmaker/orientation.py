##########################################################################################
# picmaker/orientation.py
##########################################################################################
"""Support for picmaker orientation options."""

import numpy as np

ROTATE_CHOICES = ['none', 'fliplr', 'fliptb', 'rot90', 'rot180', 'rot270']


def rotate_rgb_array(array_rgb, *, default_upward, display_upward=None, rotate=None,
                     **kwargs):
    """Apply a new orientation to an array.

    Parameters:
        array_rgb (array): A 2-D or 3-D array. The index order is (lines, samples) or
            (lines, samples, channels).
        default_upward (bool): True to display the image with lines increasing upward;
            False to display with the lines increasing downward. This default is used only
            if it is not overridden by `display_upward`.
        display_upward (bool, optional): True to display the image with lines increasing
            upward; False to display with the lines increasing downward.
        rotate (str, optional): Name of the rotation to be applied. Choices are "none",
            "fliplr", "fliptb",  "rot90", "rot180", "rot270". Values are case-insensitive.
            Rotation is counterclockwise.
        **kwargs: Additional input parameters, ignored here.

    Returns:
        array: The rotated array.

    Raises:
        KeyError: If `rotate` is not one of the recognized choices.
    """

    # Resolve the desired vertical orientation, falling back to the instrument default.
    if display_upward is None:
        display_upward = default_upward

    # Image data is stored top-down; flip vertically to make lines increase upward.
    if display_upward:
        array_rgb = np.flipud(array_rgb)

    if not rotate:
        return array_rgb

    rotate = rotate.lower()
    if rotate == 'none':
        return array_rgb
    if rotate == 'fliplr':
        return np.fliplr(array_rgb)
    if rotate == 'fliptb':
        return np.flipud(array_rgb)
    if rotate == 'rot90':
        return np.rot90(array_rgb, 1)
    if rotate == 'rot180':
        return np.rot90(array_rgb, 2)
    if rotate == 'rot270':
        return np.rot90(array_rgb, 3)

    raise KeyError(f'unrecognized rotate option: {rotate}')


__all__ = ['ROTATE_CHOICES', 'rotate_rgb_array']

##########################################################################################
