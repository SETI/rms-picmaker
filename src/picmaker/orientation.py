##########################################################################################
# picmaker/orientation.py
##########################################################################################
"""Support for picmaker orientation options."""

ROTATE_CHOICES = ['none', 'fliplr', 'fliptb', 'rot90', 'rot180', 'rot270']


def rotate_array(array, *, default_upward, display_upward=None, rotation=None, **kwargs):
    """Apply an new orientation to an array.

    Parameters:
        array (np.ndarray): A 2-D or 3-D array.
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

    # Convert to the default orientation
    if display_upward:
        array = array[..., ::-1, :]

    if not rotation:
        return array

    rotation = rotation.upper()
    if rotation == 'NONE':
        return array
    if rotation == 'FLIPLR':
        return array[..., ::-1]
    if rotation == 'FLIPTB':
        return array[..., ::-1, :]
    if rotation == 'ROT180':
        return array[..., ::-1, ::-1]
    if rotation == 'ROT90':
        return array.swapaxes(-2, -1)[..., ::-1, :]
    if rotation == 'ROT270':
        return array.swapaxes(-2, -1)[..., :, ::-1]

    raise KeyError(f'unrecognized rotation method: {rotation}')


__all__ = ['ROTATE_CHOICES', rotate_array]

##########################################################################################
