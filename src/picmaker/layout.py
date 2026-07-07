##########################################################################################
# pipeline/layout.py
##########################################################################################

import numpy as np

from picmaker.colornames import ColorNames
from picmaker.pil_utils import array_to_pil, pil_to_array


def wrap_pil_image(image, wrapped_size, sections, wrap_axis=0, gap_size=1,
                   gap_color='white', **kwargs):
    """Wrap a PIL image into `sections` sub-images separated by gaps.

    Parameters:
        image (PIL.Image): A PIL image.
        wrapped_size (tuple[int, int]): (width, height) of the final wrapped image.
        sections (int): Number of sections to wrap.
        wrap_axis (int, optional): 0 for horizontal wrapping; 1 for vertical.
        gap_size (int, optional): Width of gap in pixels between sections.
        gap_color (str or tuple[int, int, int], optional): Gap color, either as a name or
            as an (R, G, B) triple.
        **kwargs: Additional input arguments ignored here.

    Returns:
        PIL.Image: A new PIL image of the requested size.
    """

    # Get the gap color if necessary
    if gap_size > 0:
        if isinstance(gap_color, str):
            gap_color = ColorNames.lookup(gap_color)
    else:
        gap_color = [0, 0, 0]

    # Get the image array
    array = pil_to_array(image, rescale=False)
    array = np.atleast_3d(array)
    two_bytes = (array.dtype.itemsize == 2)

    # Create an empty buffer (and convert to RGB if necessary)
    if array.shape[2] == 1 and gap_size > 0 and \
       (gap_color[0] != gap_color[1] or gap_color[0] != gap_color[2]):
        buffer = np.empty((wrapped_size[1], wrapped_size[0], 3),
                          dtype=array.dtype)
    else:
        buffer = np.empty((wrapped_size[1], wrapped_size[0], array.shape[2]),
                          dtype=array.dtype)

    # Match the gap color to the byte size
    if two_bytes:
        gap_color = (int(gap_color[0]/255. * 65535.9999),
                     int(gap_color[1]/255. * 65535.9999),
                     int(gap_color[2]/255. * 65535.9999))

    # Pre-fill the buffer with the gap color
    if buffer.shape[2] == 1:
        buffer[:, :, 0] = gap_color[0]
    else:
        buffer[:, :, 0] = gap_color[0]
        buffer[:, :, 1] = gap_color[1]
        buffer[:, :, 2] = gap_color[2]

    # Insert the sections using horizontal wrapping
    if wrap_axis == 0:
        di = wrapped_size[0]
        dj = (wrapped_size[1] + gap_size) // sections
        dl = dj - gap_size
        float_s0 = 0.5
        float_ds = (image.size[0] - wrapped_size[0]) / (sections - 1.)
        j0 = int((wrapped_size[1] - dj * sections - gap_size)/2. + 0.5)
        for _k in range(sections):
            s0 = int(float_s0)
            s1 = s0 + di
            j1 = j0 + dl
            buffer[j0:j1, :] = array[:, s0:s1]
            float_s0 += float_ds
            j0 += dj

    # Otherwise, insert using vertical wrapping
    else:
        di = (wrapped_size[0] + gap_size) // sections
        dj = wrapped_size[1]
        ds = di - gap_size
        float_l0 = 0.5
        float_dl = (image.size[1] - wrapped_size[1]) / (sections - 1.)
        i0 = int((wrapped_size[0] - di * sections - gap_size)/2. + 0.5)
        for _k in range(sections):
            l0 = int(float_l0)
            l1 = l0 + dj
            i1 = i0 + ds
            buffer[:, i0:i1] = array[l0:l1, :]
            float_l0 += float_dl
            i0 += di

    # Convert the new buffer back to a PIL image
    return array_to_pil(buffer, two_bytes, rescale=False)


def pad_pil_image(image, frame=None, pad=False, pad_color='gray', **kwargs):
    """Pad a PIL image to fill a target frame size.

    Parameters:
        image (PIL.Image): A PIL image.
        frame (tuple[int, int], optional): (width, height) for padding, or None to
            skip padding.
        pad (bool, optional): True to pad the image.
        pad_color (str or tuple[int, int, int], optional): Pad fill color (name or
            (R, G, B) triple).
        **kwargs: Additional input arguments ignored here.

    Returns:
        PIL.Image: A padded PIL image of the requested size, or the original if no padding
        is needed.
    """

    # Make sure padding is needed
    if frame is None or not pad:
        return image

    if image.width >= frame[0] and image.height >= frame[1]:
        return image

    # Get the pad color
    if isinstance(pad_color, str):
        pad_color = ColorNames.lookup(pad_color)

    # Get the image array
    array = pil_to_array(image, rescale=False)
    array = np.atleast_3d(array)
    two_bytes = (array.dtype.itemsize == 2)

    # Create an empty buffer (and convert to RGB if necessary)
    width = max(image.width, frame[0])
    height = max(image.height, frame[1])

    if (array.shape[2] == 1
            and (pad_color[0] != pad_color[1] or pad_color[0] != pad_color[2])):
        buffer = np.empty((height, width, 1), dtype=array.dtype)
    else:
        buffer = np.empty((height, width, array.shape[2]), dtype=array.dtype)

    # Match the gap color to the byte size
    if two_bytes:
        pad_color = (int(pad_color[0]/255. * 65535.9999),
                     int(pad_color[1]/255. * 65535.9999),
                     int(pad_color[2]/255. * 65535.9999))

    # Pre-fill the buffer with the gap color
    if buffer.shape[2] == 1:
        buffer[:, :, 0] = pad_color[0]
    else:
        buffer[:, :, 0] = pad_color[0]
        buffer[:, :, 1] = pad_color[1]
        buffer[:, :, 2] = pad_color[2]

    # Insert the image
    l0 = (height - image.height) // 2
    s0 = (width - image.width) // 2
    l1 = l0 + image.height
    s1 = s0 + image.width
    buffer[l0:l1, s0:s1] = array[:, :]

    # Convert the new buffer back to a PIL image
    return array_to_pil(buffer, two_bytes, rescale=False)


__all__ = ['pad_pil_image', 'wrap_pil_image']

##########################################################################################
