"""PIL image conversion + I/O helpers.

These wrap ``PIL.Image`` so callers can move between numpy arrays and
PIL images and write JPEG / TIFF / 16-bit TIFF without owning the
mode-specific details themselves.
"""

import os
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from picmaker.tiff16 import WriteTiff16


def array_to_pil(array: Any, twobytes: bool = False, rescale: bool = True) -> Any:
    """Convert an array to a PIL image.

    For the special case of a 16-bit RGB image, the result is a list of
    three PIL images (one per channel).

    Parameters:
        array: Image array containing one band of grayscale or three bands
            if RGB.
        twobytes: True for 16-bit images, False for 8-bit.
        rescale: True to scale values from unit; False to leave them alone.

    Returns:
        A PIL image, or a list of three PIL images for 16-bit RGB.
    """
    array = np.atleast_3d(array)
    old_size = (array.shape[1], array.shape[0])
    channels = array.shape[2]

    if twobytes:
        if rescale:
            array *= 65535.9999

        array = array.astype('int32')

        if channels >= 3:
            result: Any = []
            for c in range(3):
                im = Image.new(mode='I', size=old_size)
                im.putdata(array[:, :, c].flatten())
                result.append(im)
        else:
            result = Image.new(mode='I', size=old_size)
            result.putdata(array[:, :, 0].flatten())

    else:
        if rescale:
            array *= 255.99999

        array = array.astype('uint8')

        imlist = []
        for c in range(channels):
            imlist.append(Image.new(mode='L', size=old_size))
            imlist[c].putdata(array[:, :, c].flatten())

        if channels >= 3:
            result = Image.merge('RGB', imlist[0:3])
        else:
            result = imlist[0]

    return result


def pil_to_array(image: Any, rescale: bool = True) -> Any:
    """Convert a PIL image (or list of RGB images) to a numpy array.

    The shape of the returned array is ``(lines, samples, bands)`` for an
    RGB image or ``(lines, samples)`` for a grayscale image.

    Parameters:
        image: A PIL image or list/tuple of three.
        rescale: True to scale values to the range 0-1; False to leave
            them alone.

    Returns:
        A numpy array.
    """
    if isinstance(image, (list, tuple)):
        bands = []
        for i in image:
            bands.append(_one_pil_to_array(i, rescale))
        return np.dstack((bands[0], bands[1], bands[2]))

    if image.mode.startswith('RGB'):
        (r, g, b) = image.split()[:3]
        r = _one_pil_to_array(r, rescale)
        g = _one_pil_to_array(g, rescale)
        b = _one_pil_to_array(b, rescale)
        return np.dstack((r, g, b))

    return _one_pil_to_array(image, rescale)


def _one_pil_to_array(image: Any, rescale: bool) -> Any:
    """Convert a single-band PIL image to a 2-D numpy array."""
    # 32-bit case
    if image.mode == 'I':
        array = np.array(image.getdata(), dtype='uint32')
        array = array.reshape((image.size[1], image.size[0]))
        if rescale:
            array = array.astype('float') / 65535.0
        else:
            array = array.astype('uint16')
        return array

    # 8-bit grayscale case. ``rescale=True`` returns a float in [0, 1]
    # (matching the documented contract and the ``'I'``-mode branch
    # above); ``rescale=False`` returns the raw uint8 0..255 array that
    # downstream consumers (filter, write) expect.
    if image.mode == 'L':
        array = np.array(image.getdata(), dtype='uint8')
        array = array.reshape((image.size[1], image.size[0]))
        if rescale:
            return array.astype('float') / 255.0
        return array

    raise OSError('Unsupported PIL image format')


def write_pil(image: Any, outfile: str | os.PathLike[str], quality: int = 75) -> None:
    """Write a PIL image (or list of RGB images) to a file.

    Parameters:
        image: A PIL image or a list of three images.
        outfile: The output file to write.
        quality: Quality factor 0-100 to use for JPEG output.
    """
    outfile_path = Path(outfile)
    parent = outfile_path.parent
    if str(parent) and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

    if isinstance(image, (list, tuple)):
        newarrays = []
        for c in range(3):
            newarrays.append(np.array(image[c].getdata(), dtype='int32'))

        array = np.dstack((newarrays[0], newarrays[1], newarrays[2]))
        array = array.reshape((image[c].size[1], image[c].size[0], 3))
        array = array.clip(0, 65535).astype('uint16')

        WriteTiff16(str(outfile_path), array)

    elif image.mode == 'I':
        array = np.array(image.getdata(), dtype='int32')
        array = array.reshape((image.size[1], image.size[0], 1))
        array = array.clip(0, 65535).astype('uint16')

        WriteTiff16(str(outfile_path), array)

    else:
        image.save(str(outfile_path), quality=quality)


__all__ = ['_one_pil_to_array', 'array_to_pil', 'pil_to_array', 'write_pil']
