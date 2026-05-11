"""File I/O helpers — read raw image arrays, write output, and label parsing.

This module is **named** ``io`` but it is NOT the stdlib :mod:`io`
module. To avoid the shadowing trap, always use absolute imports
(``from picmaker.io import X``) and never write ``import io`` inside the
``picmaker`` package. The stdlib ``io`` module is reachable from any
non-``picmaker`` file unchanged.
"""

import os
import pickle
import warnings
from pathlib import Path
from typing import Any

import astropy.io.fits as pyfits
import numpy as np
import pdsparser
from PIL import Image
from vicar import VicarError, VicarImage

from picmaker import instruments
from picmaker.pil_utils import array_to_pil, pil_to_array
from picmaker.tiff16 import ReadTiff16


def read_image_array(
    filename: Any,
    labelfile: Any,
    obj: Any = None,
    hst: bool = False,
) -> tuple[Any, bool, Any]:
    """Read one or more image files and return a stacked 3-D array.

    Args:
        filename: An input file name, or a list of file names whose
            arrays should be stacked together. Files can be in VICAR,
            FITS, TIFF, ``.npy``, or pickle format.
        labelfile: Optional path to a PDS3 label file.
        obj: Index or name of the object to load when the file contains
            multiple image objects. If a list/tuple, multiple objects
            are stacked.
        hst: True to mosaic an HST image involving multiple CCDs.

    Returns:
        ``(array3d, display_upward, filter_info)``:

        * ``array3d`` — 3-D numpy array.
        * ``display_upward`` — True if the default display orientation
          is upward.
        * ``filter_info`` — Optional ``(inst_host, inst_id, filter)``
          tuple.
    """
    if isinstance(filename, str):
        return read_one_image_array(filename, labelfile, obj, hst)

    results = []
    for k in range(len(filename)):
        results.append(read_one_image_array(filename[k], labelfile, None, hst))

    arrays = [r[0] for r in results]
    for k in range(len(arrays)):
        array = arrays[k]
        if len(array.shape) < 3:
            arrays[k] = np.reshape(array, (1,) + array.shape)

    array = np.vstack(arrays)
    return (array,) + results[0][1:]


def read_one_image_array(
    filename: str | os.PathLike[str],
    labelfile: Any,
    obj: Any = None,
    hst: bool = False,
) -> tuple[Any, bool, Any]:
    """Read a single image array, trying each known format in turn.

    The try-cascade is: pickle → numpy ``.npy`` → VICAR → FITS → PIL
    (or 16-bit TIFF) → PDS3 label. Each format is attempted in order
    and the first one that succeeds wins.

    Args:
        filename: Path to the input file.
        labelfile: Optional path to a sibling PDS3 label file.
        obj: Object index/name for multi-image files.
        hst: True to mosaic an HST image involving multiple CCDs.

    Returns:
        ``(array3d, display_upward, filter_info)``. ``filter_info`` is
        ``None`` if no instrument is detected.

    Raises:
        OSError: If none of the format readers succeed.
    """
    filename_str = str(filename)

    # ---- Pickle attempt ----
    try:
        with open(filename_str, 'rb') as f:
            array3d = pickle.load(f)
        if len(array3d.shape) == 2:
            array3d = array3d.reshape((1,) + array3d.shape)
        return (array3d, False, None)
    except Exception:
        # Not a pickle file (or unreadable as one) — fall through. The
        # original picmaker.py:1543-1544 had a `raise e` on IOError that
        # would propagate "file not found" early; PR 3 removes that so
        # the final failure message ("Unrecognized image file format")
        # is consistent across all unreadable-file cases.
        pass

    # ---- numpy .npy attempt ----
    try:
        array3d = np.load(filename_str)
        if len(array3d.shape) == 2:
            array3d = array3d.reshape((1,) + array3d.shape)
        return (array3d, False, None)
    except (OSError, ValueError):
        pass

    # ---- VICAR attempt ----
    # Also catch OSError so a missing-file error propagates through to the
    # final OSError("Unrecognized image file format ...") below rather than
    # surfacing as the rms-vicar FileNotFoundError. The lose-traceback fix
    # in the pickle branch above removed the early `raise e` that previously
    # short-circuited; this keeps the cascade behavior consistent for missing
    # files.
    try:
        vic = VicarImage.from_file(filename_str, extraneous='print')
        array3d = vic.data_3d
        for instrument in instruments.VICAR_INSTRUMENTS:
            filter_info = instrument.detect_vicar(vic)
            if filter_info is not None:
                return (array3d, False, filter_info)
        return (array3d, False, None)
    except (VicarError, OSError):
        pass

    # ---- FITS attempt (preserves the magic-byte sniff at picmaker.py:1602-1605) ----
    try:
        with open(filename_str, 'rb') as f:
            test = f.read(9)
    except OSError:
        test = b''

    if test == b'SIMPLE  =':
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('error')
                hdulist = pyfits.open(filename_str)
                _fitsobj = hdulist[0]  # IndexError if not FITS

                filter_info = None
                for instrument in instruments.FITS_INSTRUMENTS:
                    filter_info = instrument.detect_fits(hdulist)
                    if filter_info is not None:
                        break
                if filter_info is None:
                    inst_id: Any = None
                else:
                    _inst_host, inst_id, _filter_name = filter_info

                array3d = None
                if obj is None:
                    if hst and inst_id == 'ACS/WFC':
                        array = hdulist[1].data
                        try:
                            array2 = hdulist[4].data
                            shape = (2,) + array.shape
                            array3d = np.empty(shape)
                            array3d[0] = array
                            array3d[1] = array2
                        except IndexError:
                            array3d = array

                    elif hst and inst_id == 'WFPC2':
                        array3d_list: list[Any] = []
                        for hdu in hdulist:
                            array = hdu.data
                            if not isinstance(array, np.ndarray):
                                continue
                            if len(array.shape) not in (2, 3):
                                continue
                            array3d_list.append(array)
                        array3d = np.array(array3d_list)

                    else:
                        for hdu in hdulist:
                            array3d = hdu.data
                            if not isinstance(array3d, np.ndarray):
                                continue
                            if len(array3d.shape) in (2, 3):
                                break

                elif isinstance(obj, (list, tuple)):
                    layers = [hdulist[o].data for o in obj]
                    array3d = np.stack(layers)

                else:
                    try:
                        obj = int(obj)
                    except ValueError:
                        pass
                    array3d = hdulist[obj].data.copy()

                if array3d is None:
                    raise OSError('Image array not found in FITS file')

                if len(array3d.shape) == 2:
                    array3d = array3d.reshape((1,) + array3d.shape)

                hdulist.close()
                return (array3d, True, filter_info)

        except (UserWarning, OSError):
            pass

    # ---- PIL / 16-bit TIFF attempt ----
    try:
        array2d = read_array(filename_str, False)
        array3d = array2d.reshape((1,) + array2d.shape)
        return (array3d, False, None)
    except OSError:
        pass

    # ---- PDS3 label attempt ----
    if labelfile:
        result = read_pds_labeled_image_array(labelfile, obj)
        if result is not None:
            return result

    raise OSError(f'Unrecognized image file format: {filename_str}')


def read_pds_labeled_image_array(
    filename: str | os.PathLike[str], obj: Any = None
) -> tuple[Any, bool, tuple[Any, Any, Any]] | None:
    """Read a PDS3-labeled image and return the same triple as :func:`read_one_image_array`.

    Args:
        filename: Path to a ``.LBL`` (or matching) PDS3 label file.
        obj: Optional pointer name or index.

    Returns:
        ``(array3d, False, (inst_host, inst_name, filter_name))`` or
        ``None`` if no parseable label is found.
    """
    filename_str = str(filename)
    label = None
    try:
        label = pdsparser.PdsLabel(filename_str)
    except pdsparser.ParseException:
        (head, ext) = os.path.splitext(filename_str)
        if ext.lower() != '.lbl':
            if os.path.exists(head + '.lbl'):
                try:
                    label = pdsparser.PdsLabel(head + '.lbl')
                except pdsparser.ParseException:
                    pass
            elif os.path.exists(head + '.LBL'):
                try:
                    label = pdsparser.PdsLabel(head + '.LBL')
                except pdsparser.ParseException:
                    pass

    if not label:
        return None

    if isinstance(obj, str):
        pname = '^' + obj
        if pname not in label:
            raise KeyError(f'Object {obj} not found in {filename_str}')

    else:
        pnames = [
            node.name
            for node in label
            if node.name.startswith('^') and node.name.endswith('IMAGE')
        ]
        if not pnames:
            raise KeyError(f'No IMAGE objects found in {filename_str}')

        if obj is None:
            obj = 0

        try:
            pname = pnames[obj]
        except IndexError as e:
            raise IndexError(
                f'Object index {obj} is out of range in {filename_str}'
            ) from e
        except TypeError as e:
            raise TypeError(f'Invalid index type {obj} for {filename_str}') from e

    node = label[pname]
    if isinstance(node, pdsparser.PdsOffsetPointer):
        imagefile = node.value
        offset = node.offset - 1
        if node.unit == 'RECORDS':
            offset *= label['FILE_RECORDS'].value
    else:
        imagefile = node.value
        offset = 0

    imagefile = os.path.join(os.path.split(filename_str)[0], imagefile)

    image = label[pname[1:]]
    lines = image['LINES'].value
    samples = image['LINE_SAMPLES'].value
    bytes_ = image['SAMPLE_BITS'].value // 8
    fmt = image['SAMPLE_TYPE'].value

    try:
        prefix_bytes = image['PREFIX_BYTES'].value
    except KeyError:
        prefix_bytes = 0

    try:
        suffix_bytes = image['SUFFIX_BYTES'].value
    except KeyError:
        suffix_bytes = 0

    prefix_samples = prefix_bytes // bytes_
    if prefix_samples * bytes_ != prefix_bytes:
        raise ValueError(
            f'PREFIX_BYTES and SAMPLE_BITS values are incompatible in {imagefile}'
        )

    suffix_samples = suffix_bytes // bytes_
    if suffix_samples * bytes_ != suffix_bytes:
        raise ValueError(
            f'SUFFIX_BYTES and SAMPLE_BITS values are incompatible in {imagefile}'
        )

    row_samples = prefix_samples + samples + suffix_samples

    offset_samples = offset // bytes_
    if suffix_samples * bytes_ != suffix_bytes:
        raise ValueError(
            f'SAMPLE_BITS and file offset values are incompatible in {imagefile}'
        )

    char1 = '>'
    if 'PC_' in fmt or 'LSB_' in fmt:
        char1 = '<'

    char2 = 'i'
    if 'UNSIGNED' in fmt:
        char2 = 'u'
    if 'REAL' in fmt:
        char2 = 'f'

    dtype = char1 + char2 + str(bytes_)

    data = np.fromfile(imagefile, dtype=dtype)
    data = data[offset_samples:]
    data = data[: lines * row_samples]
    array3d = data.reshape(1, lines, row_samples)
    array3d = array3d[..., prefix_samples : prefix_samples + samples]

    try:
        inst_host = label['INSTRUMENT_NAME'].value
    except KeyError:
        try:
            inst_host = label['SPACECRAFT_NAME'].value
        except KeyError:
            inst_host = ''

    try:
        inst_name = label['INSTRUMENT_HOST_NAME'].value
    except KeyError:
        inst_name = ''

    try:
        filter_name = label['FILTER_NAME'].value
    except KeyError:
        filter_name = ''

    return (array3d, False, (inst_host, inst_name, filter_name))


def read_pil(infile: str | os.PathLike[str]) -> Any:
    """Read a PIL image (or 16-bit TIFF expanded to a PIL image) from a file.

    Args:
        infile: Path to the input file.

    Returns:
        A PIL image or a list of three PIL images (16-bit RGB).
    """
    infile_str = str(infile)
    testfile = infile_str.upper()
    if testfile.endswith('.TIFF') or testfile.endswith('.TIF'):
        try:
            (array, palette) = ReadTiff16(infile_str)  # type: ignore[no-untyped-call]
        except OSError:
            array = None
            palette = None

        if array is not None:
            if palette is not None:
                raise OSError('16-bit palette option is not supported')

            return array_to_pil(array, twobytes=True, rescale=False)

    im = Image.open(infile_str)
    im.load()
    return im


def read_array(infile: str | os.PathLike[str], rescale: bool) -> Any:
    """Read a numpy array from a PIL-readable file (or a 16-bit TIFF).

    Args:
        infile: Path to the input file.
        rescale: True to scale values to the range 0-1.

    Returns:
        A 2-D or 3-D numpy array.
    """
    infile_str = str(infile)
    array = None
    palette = None
    testfile = infile_str.upper()
    if testfile.endswith('.TIFF') or testfile.endswith('.TIF'):
        try:
            (array, palette) = ReadTiff16(infile_str)  # type: ignore[no-untyped-call]
        except OSError:
            array = None
            palette = None

    if array is not None:
        if palette is not None:
            raise OSError('16-bit palette option is not supported')

        if rescale:
            array = array.astype('float') / 65535.0

        return array

    return pil_to_array(Image.open(infile_str), rescale)


def get_outfile(
    infile: str | os.PathLike[str],
    outdir: str | os.PathLike[str] | None = None,
    strip: Any = None,
    suffix: str = '',
    extension: str = 'jpg',
    replace: str = 'all',
) -> str:
    """Derive the output filename for one input.

    Args:
        infile: Name of the input file.
        outdir: Output directory, or ``None`` for the input's directory.
        strip: A string or list of strings to strip from the input
            filename before adding the suffix. ``None`` is equivalent
            to ``['']``.
        suffix: Extra string added before the extension.
        extension: Output file extension (e.g. ``'jpg'``).
        replace: Replacement policy when the output already exists:
            ``'all'`` (silent overwrite), ``'none'`` (skip silently),
            ``'warn'`` (warn and overwrite), or ``'error'``.

    Returns:
        The output file path, or an empty string when ``replace='none'``
        and the file already exists.

    Raises:
        OSError: If ``replace='error'`` and the file already exists.

    Side Effects:
        Creates the output directory tree if it does not exist.
    """
    infile_str = str(infile)
    outdir_str = None if outdir is None else str(outdir)

    if suffix is None:
        suffix = ''
    if strip is None:
        strip = ['']

    outfile = infile_str

    if isinstance(strip, str):
        strip = [strip]
    for substring in strip:
        loc = outfile.rfind(substring)
        if loc >= 0:
            outfile = outfile[:loc] + outfile[loc + len(substring) :]

    if outdir_str is not None:
        outfile = os.path.join(outdir_str, os.path.split(outfile)[1])

    outfile = os.path.splitext(outfile)[0]
    outfile += suffix + '.' + extension

    path = os.path.split(outfile)[0]
    if path != '' and not os.path.exists(path):
        Path(path).mkdir(parents=True, exist_ok=True)

    if os.path.exists(outfile):
        if replace == 'none':
            return ''
        elif replace == 'error':
            raise OSError(f'File already exists: {outfile}')
        elif replace == 'warn':
            warnings.warn(f'File overwritten: {outfile}', UserWarning, stacklevel=2)

    return outfile


__all__ = [
    'get_outfile',
    'read_array',
    'read_image_array',
    'read_one_image_array',
    'read_pds_labeled_image_array',
    'read_pil',
]
