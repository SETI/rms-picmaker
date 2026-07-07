##########################################################################################
# picmaker/pil_utils.py
##########################################################################################
"""PIL image read/write support.

These functions wrap PIL.Image so callers can move between numpy arrays and PIL images and
write JPEG/TIFF/16-bit TIFF without owning the mode-specific details themselves.
"""

import pathlib

import numpy as np
from PIL import Image

from picmaker.tiff16 import write_tiff16

PIL_EXTENSIONS = ['bmp', 'dib', 'gif', 'jpg', 'jpeg', 'png', 'tif', 'tiff']


def array_to_pil(array, twobytes=False, rescale=True):
    """Convert an array to a PIL image.

    For the special case of a 16-bit RGB image, the result is a list of three PIL images
    (one per channel).

    Parameters:
        array (array): Image array containing one band of grayscale or three bands
            if RGB.
        twobytes (bool, optional): True for 16-bit images, False for 8-bit.
        rescale (bool, optional): True to scale values from unity; False to leave them
            alone.

    Returns:
        (PIL.Image or list of three): A PIL image or, for 16-bit RGB, a list of three PIL
        images.
    """

    # Get the array size in image ordering
    array = np.atleast_3d(array)
    old_size = (array.shape[1], array.shape[0])

    # Determine the number of channels
    channels = array.shape[2]

    # Use PIL 32-bit mode for two-byte images
    if twobytes:

        # Re-scale from unity if necessary
        if rescale:
            array = array * 65535.9999

        array = array.astype('int32')

        # Return a list if there are RGB channels
        if channels >= 3:
            result = []
            for c in range(3):
                im = Image.new(mode='I', size=old_size)
                im.putdata(array[:, :, c].flatten())
                result.append(im)

        # Otherwise, return a single PIL image
        else:
            result = Image.new(mode='I', size=old_size)
            result.putdata(array[:, :, 0].flatten())

    # Use a PIL "L" or "RGB" image for one-byte images
    else:

        # Re-scale from unity
        if rescale:
            array = array * 255.99999

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


def pil_to_array(image, rescale=True):
    """Convert a PIL image (or list of RGB images) to a Numpy array.

    The shape of the returned array is (height, width, channel) for an RGB image or
    (height, width) for a grayscale image.

    Parameters:
        image (PIL.Image or list of three): A PIL image or a list of three for 16-bit RGB.
        rescale (bool, optional): True to scale values to the range 0-1; False to leave
            them alone.

    Returns:
        (array): 2-D or 3-D image array.

    Raises:
        OSError: If a PIL image has an unsupported mode (not "I", "L", or RGB).
    """

    # Determine if it's a triple
    if isinstance(image, (list, tuple)):
        bands = []
        for im in image:
            bands.append(_one_pil_to_array(im, rescale=rescale))

        return np.dstack((bands[0], bands[1], bands[2]))

    # Deal with an RGB image in three bands
    if image.mode.startswith('RGB'):
        (r, g, b) = image.split()[:3]

        r = _one_pil_to_array(r, rescale=rescale)
        g = _one_pil_to_array(g, rescale=rescale)
        b = _one_pil_to_array(b, rescale=rescale)

        array = np.dstack((r, g, b))
        return array

    # Otherwise it's a simple case
    return _one_pil_to_array(image, rescale=rescale)


def _one_pil_to_array(image, rescale):

    # 32-bit case...
    if image.mode == 'I':
        array = np.array(image.getdata(), dtype='uint32')
        array = array.reshape((image.size[1], image.size[0]))

        if rescale:
            array = array.astype('float') / 65535.
        else:
            array = array.astype('uint16')

        return array

    # 8-bit grayscale case...
    if image.mode == 'L':
        array = np.array(image.getdata(), dtype='uint8')
        array = array.reshape((image.size[1], image.size[0]))

        if rescale:
            array = array.astype('float') / 255.

        return array

    raise OSError('Unsupported PIL image format')


def write_pil(image, outfile, quality=75):
    """Write a PIL image (or list of RGB images) to a file.

    Parameters:
        image (PIL.Image or list of three): A PIL image or a list of three for 16-bit RGB.
        outfile (str or Path): The output file to write.
        quality (float): Quality factor 0-100 to use for JPEG output.

    Raises:
        OSError: If a single PIL image has an unsupported mode for the chosen output.
    """

    # Create the parent directory if necessary
    outfile = pathlib.Path(outfile)
    outfile.parent.mkdir(parents=True, exist_ok=True)

    # If it's a list, write a RGB 16-bit Tiff
    if isinstance(image, (list, tuple)):

        # Convert images back to a numpy arrays
        newarrays = []
        for c in range(3):
            newarrays.append(np.array(image[c].getdata(), dtype='int32'))

        array = np.dstack((newarrays[0], newarrays[1], newarrays[2]))

        # Reshape, clip and convert back to two bytes
        array = array.reshape((image[0].size[1], image[0].size[0], 3))
        array = array.clip(0, 65535).astype('uint16')

        # Write file
        write_tiff16(outfile, array)

    # If it's a single 32-bit image, write a grayscale Tiff
    elif image.mode == 'I':
        array = np.array(image.getdata(), dtype='int32')
        array = array.reshape((image.size[1], image.size[0], 1))
        array = array.clip(0, 65535).astype('uint16')

        # Write file
        write_tiff16(outfile, array)

    # Otherwise use the standard PIL output mechanism
    else:
        image.save(outfile, quality=quality)


__all__ = ['PIL_EXTENSIONS', 'array_to_pil', 'pil_to_array', 'write_pil']

##########################################################################################
