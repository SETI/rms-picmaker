####################################################################################################
# tiff16.py
#
# Simple method write_tiff16() to write a numpy array as a 16-bit uncompressed
# tiff, in grayscale, RGB color or palette color.
#
# Associated method read_tiff16() is not a general implementation of the Tiff
# standard; however, it will successfully read 16-bit Tiffs written by
# write_tiff16().
#
# Note, however, that 16-bit palette color is not widely supported. For this
# reason, a "translate" option is provided, which converts palette color to RGB.
#
# Mark R. Showalter, SETI Institute, July 2009
####################################################################################################

import sys
from struct import pack, unpack
from typing import Any

import numpy as np
from PIL import Image


def write_tiff16(
    filename: str,
    array: Any,
    palette: Any = None,
    up: bool = False,
    byteorder: str = "native",
    translate: bool = True,
    transpose: Any = None,
) -> None:
    """Write a 16-bit TIFF file from a 2-D or 3-D numpy array.

    Three TIFF formats are supported: grayscale, RGB, and palette.

    Parameters:
        filename: The name of the file to write.
        array: A numpy 2-D or 3-D array containing the image pixels.
            Values are converted to unsigned 16-bit if they are not
            already in that format. Indices are
            ``(line, sample, band)``; the third axis is optional. If
            present with size ``>= 3`` and no ``palette`` is provided,
            ``array[:, :, 0:3]`` is interpreted as the ``(R, G, B)``
            values for each pixel.
        palette: Optional ``(65536, 3)`` array. When provided, the 0th
            band of ``array`` indexes into the palette to derive each
            pixel's ``(R, G, B)`` triple.
        up: True for line numbers to increase upward; False (default)
            for downward.
        byteorder: One of ``'native'``, ``'little'``, or ``'big'``.
            Default is ``'native'``.
        translate: True to translate a palette image to RGB on write
            (default; many TIFF readers do not support 16-bit
            palettes). False writes the palette index plus the palette
            table.
        transpose: Optional geometric transformation before writing.
            Choices match ``PIL.Image.Transpose``:
            ``FLIP_LEFT_RIGHT``, ``FLIP_TOP_BOTTOM``, ``ROTATE_90``,
            ``ROTATE_180``, ``ROTATE_270``.
    """

    # Open the output file
    with open(filename, "wb") as f:

        # Flip if line numbers increase upward
        if up:
            array = np.flipud(array)

        # Apply transpose operation if needed
        if transpose == Image.Transpose.FLIP_LEFT_RIGHT:
            array = np.fliplr(array)
        if transpose == Image.Transpose.FLIP_TOP_BOTTOM:
            array = np.flipud(array)
        if transpose == Image.Transpose.ROTATE_90:
            array = np.rot90(array,1)
        if transpose == Image.Transpose.ROTATE_180:
            array = np.rot90(array,2)
        if transpose == Image.Transpose.ROTATE_270:
            array = np.rot90(array,3)

        # Interpret the shape of the image
        if array.ndim == 3:
            (height, width, bands) = array.shape
        else:
            (height, width) = array.shape
            bands = 1
            array = array.reshape((height, width, 1))

        # What type of tiff?
        has_palette = (palette is not None)
        is_rgb = bands >= 3
        if has_palette:
            is_rgb = False  # Palette overrides RGB data

        # Determine how to handle the palette in the output file
        if translate and has_palette:
            has_palette = False
            is_rgb = True
            translate_to_rgb = True
        else:
            translate_to_rgb = False

        # Interpret the byte order. Validate explicitly so an unknown
        # `byteorder` value fails fast rather than silently being
        # treated as big-endian.
        byteorder = byteorder.lower()
        if byteorder == "native":
            byteorder = sys.byteorder
        if byteorder == "little":
            o = "<"
            flag = b"I"
        elif byteorder == "big":
            o = ">"
            flag = b"M"
        else:
            raise ValueError(
                f"byteorder must be 'native', 'little', or 'big'; got {byteorder!r}"
            )

        # Write the Image File Header
        #------- 0 bytes
        f.write(pack("cc", flag, flag))
        f.write(pack(o+"H", 42))                            # TIFF's 42
        f.write(pack(o+"L", 8))                             # IFD begins at offset 8
        #------- 8 bytes

        # Determine the key offsets into the file
        ifd_offset = 8

        if has_palette:
            ifd_entries = 12
            after_bytes = 16 + 65536 * 3 * 2
            pixel_bytes = 2
        elif is_rgb:
            ifd_entries = 12
            after_bytes = 16 + 8
            pixel_bytes = 6
        else:
            ifd_entries = 11
            after_bytes = 16
            pixel_bytes = 2

        ifd_bytes = 2 + 12 * ifd_entries + 4
        after_offset = ifd_offset + ifd_bytes

        data_offset = after_offset + after_bytes

        # Write the Image File Directory
        f.write(pack(o+"H", ifd_entries))                   # number of entries

        f.write(pack(o+"HHLL",  256, 4, 1, width))          # image width
        f.write(pack(o+"HHLL",  257, 4, 1, height))         # image height

        if is_rgb:                                          # bits per sample
            f.write(pack(o+"HHLL", 258, 3, 3, after_offset + 16))
        else:
            f.write(pack(o+"HHLHH", 258, 3, 1, 16, 0))

        f.write(pack(o+"HHLHH", 259, 3, 1, 1, 0))           # no compression

        if has_palette:                                     # photometric model
            f.write(pack(o+"HHLHH", 262, 3, 1, 3, 0))       # palette
        elif is_rgb:
            f.write(pack(o+"HHLHH", 262, 3, 1, 2, 0))       # RGB
        else:
            f.write(pack(o+"HHLHH", 262, 3, 1, 1, 0))       # black is zero

        f.write(pack(o+"HHLL",  273, 4, 1, data_offset))    # where data begins

        if is_rgb:                                          # samples per pixel
            f.write(pack(o+"HHLHH", 277, 3, 1, 3, 0))

        f.write(pack(o+"HHLL",  278, 4, 1, height))         # rows per strip
        f.write(pack(o+"HHLL",  279, 4, 1, width * height * pixel_bytes))
                                                            # bytes per strip
        f.write(pack(o+"HHLL",  282, 5, 1, after_offset))   # x resolution
        f.write(pack(o+"HHLL",  283, 5, 1, after_offset + 8))
                                                            # y resolution

        f.write(pack(o+"HHLHH", 296, 3, 1, 2, 0))           # unit is inches

        if has_palette:                                     # start of table
            f.write(pack(o+"HHLL", 320, 3, 3*65536, after_offset + 16))

        f.write(pack(o+"L", 0))                             # end of IFD

        # "After" values pointed to by every IFD
        f.write(pack(o+"LL", 72, 1))                        # x unit is 72/inch
        f.write(pack(o+"LL", 72, 1))                        # y unit is 72/inch

        # Write the palette here if there is one
        if has_palette:
            palette[0:65536,0:3].astype(o+"u2").transpose().tofile(f,sep="")

        # Otherwise, write the size of each RGB pixel if necessary
        elif is_rgb:                                        # samples per pixel
            f.write(pack(o+"HHHH", 16, 16, 16, 0))

        # Translate colors if necessary
        if translate_to_rgb:
            array = palette[array[:,:,0],0:3]

        # Otherwise just slice off the needed bands
        elif is_rgb:
            array = array[:,:,0:3]

        else:
            array = array[:,:,0]

        # Append data to output file
        array.astype(o+"u2").tofile(f, sep="")

def read_tiff16(
    filename: str,
    up: bool = False,
    transpose: Any = None,
) -> tuple[Any, Any]:
    """Read a 16-bit TIFF file written by :func:`write_tiff16`.

    No other TIFF file formats are supported.

    Parameters:
        filename: The name of the file to read.
        up: True for line numbers to increase upward; False (default)
            for downward.
        transpose: Optional geometric transformation to undo on the
            image before returning. Choices match
            ``PIL.Image.Transpose``: ``FLIP_LEFT_RIGHT``,
            ``FLIP_TOP_BOTTOM``, ``ROTATE_90``, ``ROTATE_180``,
            ``ROTATE_270``.

    Returns:
        ``(array, palette)``:

        * ``array`` — a numpy 2-D or 3-D ``uint16`` array indexed
          ``(line, sample, band)``. The third axis is present only for
          RGB inputs (``size >= 3``).
        * ``palette`` — an optional ``(65536, 3)`` array. When present,
          the 0th band of ``array`` indexes into the palette to derive
          each pixel's ``(R, G, B)`` triple. ``None`` for non-palette
          inputs.
    """

    # Open the output file inside a `with` so the handle is closed
    # promptly if any `raise OSError` / `my_assert` short-circuits the
    # parse (otherwise the file leaks until GC and `pytest -W error`
    # turns the ResourceWarning into a test failure).
    with open(filename, "rb") as f:

        # Read the Image File Header
        #------- 0 bytes
        # f.read(pack("cc", flag, flag))
        # f.read(pack(o+"H", fortytwo))                     # TIFF's 42
        # f.read(pack(o+"L", eight))                        # IFD begins at offset 8
        #------- 8 bytes

        flag1 = f.read(1)
        flag2 = f.read(1)
        if flag1 != flag2:
            raise OSError("File format is not TIFF")

        if   flag1 == b'I':
            o = "<"
        elif flag1 == b"M":
            o = ">"
        else:
            raise OSError("File format is not TIFF")

        t = unpack(o+"H", f.read(2))
        if t[0] != 42:
            raise OSError("File format is not TIFF")

        t = unpack(o+"L", f.read(4))
        my_assert(t[0] == 8)

        # f.write(pack(o+"H", ifd_entries))                 # number of entries
        # f.write(pack(o+"HHLL",  256, 4, 1, width))        # image width
        # f.write(pack(o+"HHLL",  257, 4, 1, height))       # image height

        t = unpack(o+"H", f.read(2))
        ifd_entries = t[0]

        t = unpack(o+"HHLL", f.read(12))
        my_assert((t[0],t[1],t[2]) == (256, 4, 1))
        width = t[3]

        t = unpack(o+"HHLL", f.read(12))
        my_assert((t[0],t[1],t[2]) == (257, 4, 1))
        height = t[3]

        # if is_rgb:                                        # bits per sample
        #     f.write(pack(o+"HHLL", 258, 3, 3, after_offset + 16))
        # else:
        #     f.write(pack(o+"HHLHH", 258, 3, 1, 16, 0))

        t = unpack(o+"HHLHH", f.read(12))
        my_assert((t[0],t[1]) == (258, 3))

        if   t[2] == 3:
            is_rgb = True
        elif t[2] == 1:
            is_rgb = False
        else:
            my_assert(False)

        if is_rgb:
            after_offset = t[3] - 16
        else:
            my_assert((t[3],t[4]) == (16, 0))

        # f.write(pack(o+"HHLHH", 259, 3, 1, 1, 0))         # no compression

        t = unpack(o+"HHLHH", f.read(12))
        my_assert(t == (259, 3, 1, 1, 0))

        # if has_palette:                                   # photometric model
        #    f.write(pack(o+"HHLHH", 262, 3, 1, 3, 0))      # palette
        # elif is_rgb:
        #    f.write(pack(o+"HHLHH", 262, 3, 1, 2, 0))      # RGB
        # else:
        #    f.write(pack(o+"HHLHH", 262, 3, 1, 1, 0))      # black is zero

        t = unpack(o+"HHLHH", f.read(12))
        has_palette = (t == (262, 3, 1, 3, 0))
        test_rgb    = (t == (262, 3, 1, 2, 0))
        is_gray     = (t == (262, 3, 1, 1, 0))

        my_assert(test_rgb == is_rgb)
        my_assert(has_palette or is_rgb or is_gray)

        # Fill in expected sizes now
        ifd_offset = 8

        if has_palette:
            ifd_entries = 12
            after_bytes = 16 + 65536 * 3 * 2
            pixel_bytes = 2
        elif is_rgb:
            ifd_entries = 12
            after_bytes = 16 + 8
            pixel_bytes = 6
        else:
            ifd_entries = 11
            after_bytes = 16
            pixel_bytes = 2

        ifd_bytes = 2 + 12 * ifd_entries + 4
        after_offset = ifd_offset + ifd_bytes

        data_offset = after_offset + after_bytes

        # f.write(pack(o+"HHLL",  273, 4, 1, data_offset))  # where data begins

        t = unpack(o+"HHLL", f.read(12))
        my_assert(t == (273, 4, 1, data_offset))

        # if is_rgb:                                        # samples per pixel
        #    f.write(pack(o+"HHLHH", 277, 3, 1, 3, 0))

        if is_rgb:
            t = unpack(o+"HHLHH", f.read(12))
            my_assert(t == (277, 3, 1, 3, 0))

        # f.write(pack(o+"HHLL",  278, 4, 1, height))       # rows per strip
        # f.write(pack(o+"HHLL",  279, 4, 1, width * height * pixel_bytes))
                                                            # bytes per strip

        t = unpack(o+"HHLL", f.read(12))
        my_assert(t == (278, 4, 1, height))

        if is_rgb:
            pixel_bytes = 6
        else:
            pixel_bytes = 2

        t = unpack(o+"HHLL", f.read(12))
        my_assert(t == (279, 4, 1, width * height * pixel_bytes))

        # f.write(pack(o+"HHLL",  282, 5, 1, after_offset)) # x resolution
        # f.write(pack(o+"HHLL",  283, 5, 1, after_offset + 8))
                                                            # y resolution

        t = unpack(o+"HHLL", f.read(12))
        my_assert(t == (282, 5, 1, after_offset))

        t = unpack(o+"HHLL", f.read(12))
        my_assert(t == (283, 5, 1, after_offset + 8))

        # f.write(pack(o+"HHLHH", 296, 3, 1, 2, 0))         # unit is inches

        t = unpack(o+"HHLHH", f.read(12))
        my_assert(t == (296, 3, 1, 2, 0))

        # if has_palette:                                   # start of table
        #    f.write(pack(o+"HHLL", 320, 3, 3*65536, after_offset + 16))

        if has_palette:
            t = unpack(o+"HHLL", f.read(12))
            my_assert(t == (320, 3, 3*65536, after_offset + 16))

        # f.write(pack(o+"L", 0))                           # end of IFD

        t = unpack(o+"L", f.read(4))
        my_assert(t[0] == 0)

        # "After" values pointed to by every IFD
        # f.write(pack(o+"LL", 72, 1))                      # x unit is 72/inch
        # f.write(pack(o+"LL", 72, 1))                      # y unit is 72/inch

        t = unpack(o+"LL", f.read(8))
        my_assert(t == (72,1))

        t = unpack(o+"LL", f.read(8))
        my_assert(t == (72,1))

        # Read the palette here if there is one
        # if has_palette:
        #    palette[0:65536,0:3].astype(o+"u2").transpose().tofile(f,sep="")

        palette = None
        if has_palette:
            palette = np.fromfile(f, dtype=o+"u2", count=65536*3, sep="")
            palette = palette.reshape((3,65536)).transpose()

        # Otherwise, write the size of each RGB pixel if necessary
        # elif is_rgb:                                      # samples per pixel
        #     f.write(pack(o+"HHHH", 16, 16, 16, 0))

        elif is_rgb:
            t = unpack(o+"HHHH", f.read(8))
            my_assert(t == (16, 16, 16, 0))

        # Append data to output file
        # array.astype(o+"u2").tofile(f, sep="")

        items = width * height
        if is_rgb:
            items *= 3
        array = np.fromfile(f, dtype=o+"u2", count=items, sep="")

    # Interpret the shape of the image
    # if array.ndim == 3:
    #     (height, width, bands) = array.shape
    # else:
    #     (height, width) = array.shape
    #     bands = 1
    #     array = array.reshape((height, width, 1))

    if is_rgb:
        array = array.reshape(height, width, 3)
    else:
        array = array.reshape(height, width)

    # Apply transpose operation if needed
    if transpose == Image.Transpose.FLIP_LEFT_RIGHT:
        array = np.fliplr(array)
    if transpose == Image.Transpose.FLIP_TOP_BOTTOM:
        array = np.flipud(array)
    if transpose == Image.Transpose.ROTATE_90:
        array = np.rot90(array,3)
    if transpose == Image.Transpose.ROTATE_180:
        array = np.rot90(array,2)
    if transpose == Image.Transpose.ROTATE_270:
        array = np.rot90(array,1)

    # Flip if line numbers increase upward
    # if up: array = np.flipud(array)

    if up:
        array = np.flipud(array)

    return(array, palette)

def my_assert(test: bool) -> None:
    if not test:
        raise OSError("Not a recognized TIFF16 file.")

