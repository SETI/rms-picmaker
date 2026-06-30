##########################################################################################
# picmaker/orientation.py
##########################################################################################
"""Support for picmaker orientation options."""

import numpy as np

ROTATE_CHOICES = ['none', 'fliplr', 'fliptb', 'rot90', 'rot180', 'rot270']


def rotate_rgb_array(array_rgb, *, default_upward, display_upward=None, rotation=None,
                     **kwargs):
    """Apply an new orientation to an array.

    Parameters:
        array_rgb (np.ndarray): A 2-D or 3-D array. The index order is ``(lines,
            samples)`` or ``(lines, samples, channels)``.
        default_upward (bool): True to display the image with lines increasing upward;
            False to display with the lines increasing downward. This default is used only
            if it is not overridden by ``display_upward``.
        display_upward (bool, optional): True to display the image with lines increasing
            upward; False to display with the lines increasing downward.
        rotation (str, optional): Name of the rotation to be applied. Choices are
            ``"NONE"``, ``"FLIPLR"``, ``"FLIPTB"``,  ``"ROT90"``, ``"ROT180"``,
            ``"ROT270"``. Values are case-insensitive. Rotation is counterclockwise.
        **kwargs: Additional input parameters, ignored here.

    Returns:
        The rotated array.

    Raises:
        KeyError: If ``rotation_name`` is not one of the recognized choices.
    """

    # Resolve the desired vertical orientation, falling back to the instrument default.
    if display_upward is None:
        display_upward = default_upward

    # Image data is stored top-down; flip vertically to make lines increase upward.
    if display_upward:
        array_rgb = np.flipud(array_rgb)

    if not rotation:
        return array_rgb

    rotation = rotation.lower()
    if rotation == 'none':
        return array_rgb
    if rotation == 'fliplr':
        return np.fliplr(array_rgb)
    if rotation == 'fliptb':
        return np.flipud(array_rgb)
    if rotation == 'rot90':
        return np.rot90(array_rgb, 1)
    if rotation == 'rot180':
        return np.rot90(array_rgb, 2)
    if rotation == 'rot270':
        return np.rot90(array_rgb, 3)

    raise KeyError(f'unrecognized rotation method: {rotation}')


__all__ = ['ROTATE_CHOICES', 'rotate_rgb_array']

##########################################################################################
