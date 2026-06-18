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
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import astropy.io.fits as pyfits
import numpy as np
import pdsparser
from numpy.typing import NDArray
from PIL import Image
from vicar import VicarError, VicarImage

from picmaker import instruments
from picmaker._types import FilterInfo, ObjectSelector, ReadResult
from picmaker.instruments._shared import extract_fits_array, is_fits_file, read_pds3_image_array
from picmaker.options import DEFAULT_PDS3_LABEL_METHOD
from picmaker.pil_utils import array_to_pil, pil_to_array
from picmaker.tiff16 import read_tiff16


def read_image_array(
    filename: (
        str | os.PathLike[str] | pdsparser.Pds3Label
        | Sequence[str | os.PathLike[str]]
    ),
    obj: ObjectSelector = None,
    **kwargs: Any,
) -> ReadResult:
    """Read one or more image files and return a stacked 3-D array.

    Parameters:
        filename: An input file path, a :class:`pdsparser.Pds3Label`
            object (pre-parsed PDS3 label), or a list of file paths
            whose arrays should be stacked together. Files can be in
            VICAR, FITS, TIFF, ``.npy``, or pickle format. Paths
            ending in ``.LBL`` or ``.lbl`` are parsed and dispatched
            as PDS3 labels.
        obj: Index or name of the object to load when the file contains
            multiple image objects. If a list/tuple, multiple objects
            are stacked.
        **kwargs: Instrument-specific options forwarded to each
            instrument's :func:`read_file`. See
            :data:`picmaker.options.READ_FILE_KWARGS` for the list of
            options passed from the pipeline.

    Returns:
        ``(array3d, display_upward, filter_info)``:

        * ``array3d`` — 3-D numpy array.
        * ``display_upward`` — True if the default display orientation
          is upward.
        * ``filter_info`` — Optional ``(inst_host, inst_id, filter)``
          tuple.
    """
    if isinstance(filename, (str, os.PathLike, pdsparser.Pds3Label)):
        return read_one_image_array(filename, obj, **kwargs)

    results = []
    for k in range(len(filename)):
        results.append(read_one_image_array(filename[k], None, **kwargs))

    arrays = [r[0] for r in results]
    for k in range(len(arrays)):
        array = arrays[k]
        if len(array.shape) < 3:
            arrays[k] = np.reshape(array, (1, *array.shape))

    array = np.vstack(arrays)
    return ReadResult(array, results[0].default_is_up, results[0].filter_info)


def read_one_image_array(
    filename: str | os.PathLike[str] | pdsparser.Pds3Label,
    obj: ObjectSelector = None,
    **kwargs: Any,
) -> ReadResult:
    """Read a single image array, trying each known format in turn.

    When *filename* is a :class:`pdsparser.Pds3Label` (or a path ending
    in ``.LBL`` / ``.lbl``), the PDS3 label branch runs first: each
    instrument's :func:`read_file` is tried in order, and an unrecognized
    label falls through to :func:`read_pds_labeled_image_array`.

    For all other paths the cascade is: pickle → numpy ``.npy`` →
    per-instrument readers → generic VICAR fallback → generic FITS
    fallback → PIL (or 16-bit TIFF) → PDS3 auto-detection (the file
    itself is tried as a PDS3 label, which also detects sibling ``.LBL``
    files via :func:`read_pds_labeled_image_array`).

    Parameters:
        filename: Path to the input file, or a pre-parsed
            :class:`pdsparser.Pds3Label`. Paths ending in ``.LBL`` or
            ``.lbl`` are parsed automatically.
        obj: Object index/name for multi-image files.
        **kwargs: Instrument-specific options forwarded verbatim to each
            instrument's :func:`read_file`. See
            :data:`picmaker.options.READ_FILE_KWARGS` for the standard
            set.

    Returns:
        ``(array3d, display_upward, filter_info)``. ``filter_info`` is
        ``None`` if no instrument is detected.

    Raises:
        OSError: If none of the format readers succeed. The per-reader
            failure causes are attached via ``__cause__`` as an
            :class:`ExceptionGroup` so callers can inspect what each
            reader rejected.
    """
    # ---- Auto-parse .LBL paths ----
    if isinstance(filename, (str, os.PathLike)):
        path_str = str(filename)
        if path_str.upper().endswith('.LBL'):
            filename = pdsparser.Pds3Label(
                path_str, method=kwargs.get('pds3_label_method', DEFAULT_PDS3_LABEL_METHOD)
            )

    # ---- PDS3 label branch ----
    # Instrument readers are tried first; an unrecognized label falls back
    # to the generic reader which also handles embedded labels and detects
    # sibling .LBL files when given a data-file path.
    if isinstance(filename, pdsparser.Pds3Label):
        for instrument in instruments.ALL_INSTRUMENTS:
            result = instrument.read_file(filename, obj, **kwargs)
            if result is not None:
                return cast('ReadResult', result)
        # Generic fallback: resolve ^IMAGE and read via VICAR/FITS.
        # This handles labels that don't match any known instrument but
        # point to a VICAR or FITS data file.
        array3d = read_pds3_image_array(filename, obj)
        return ReadResult(array3d, False, None)

    # ---- Non-label cascade ----
    filename_str = str(filename)
    cascade_errors: list[Exception] = []

    # ---- Pickle attempt ----
    # The pickle branch is the only one that catches the broad ``Exception``
    # because pickle.load can raise nearly anything (OSError on missing/unreadable
    # files, pickle.UnpicklingError on bad streams, AttributeError/ImportError
    # during object reconstruction, TypeError on .shape access if the unpickled
    # value isn't a numpy array, etc.). The exception is collected for the
    # diagnostic ExceptionGroup at the cascade end.
    try:
        with open(filename_str, 'rb') as f:
            array3d = pickle.load(f)
        if len(array3d.shape) == 2:
            array3d = array3d.reshape((1, *array3d.shape))
        return ReadResult(array3d, False, None)
    except Exception as exc:
        cascade_errors.append(exc)

    # ---- numpy .npy attempt ----
    try:
        array3d = np.load(filename_str)
        if len(array3d.shape) == 2:
            array3d = array3d.reshape((1, *array3d.shape))
        return ReadResult(array3d, False, None)
    except (OSError, ValueError) as exc:
        cascade_errors.append(exc)

    # ---- Per-instrument readers ----
    # Each instrument's read_file() handles its own format detection and
    # array extraction.  Instruments that share a format (VICAR, FITS)
    # call shared utilities from picmaker.instruments._shared internally.
    for instrument in instruments.ALL_INSTRUMENTS:
        result = instrument.read_file(filename, obj, **kwargs)
        if result is not None:
            return cast('ReadResult', result)

    # ---- Generic VICAR fallback (unrecognized or un-labelled VICAR file) ----
    # Also catches OSError so a missing-file error propagates through to the
    # final OSError("Unrecognized image file format ...") below rather than
    # surfacing as the rms-vicar FileNotFoundError.
    try:
        vic = VicarImage.from_file(filename_str, extraneous='print', strict=False)
        array3d = vic.data_3d
        if len(array3d.shape) == 2:
            array3d = array3d.reshape((1, *array3d.shape))
        return ReadResult(array3d, False, None)
    except (VicarError, OSError) as exc:
        cascade_errors.append(exc)

    # ---- Generic FITS fallback (unrecognized FITS file) ----
    if is_fits_file(filename_str):
        try:
            with warnings.catch_warnings(), pyfits.open(filename_str) as hdulist:
                warnings.filterwarnings('error')
                _fitsobj = hdulist[0]  # IndexError if not FITS

                array3d = extract_fits_array(hdulist, obj)
                return ReadResult(array3d, True, None)

        except (UserWarning, OSError) as exc:
            cascade_errors.append(exc)

    # ---- PIL / 16-bit TIFF attempt ----
    try:
        array2d = read_array(filename_str, False)
        array3d = array2d.reshape((1, *array2d.shape))
        return ReadResult(array3d, False, None)
    except OSError as exc:
        cascade_errors.append(exc)

    # ---- PDS3 auto-detection (embedded label or sibling .LBL) ----
    # read_pds_labeled_image_array first tries to parse filename_str itself
    # as a PDS3 label; if that fails and the extension is not .lbl, it also
    # checks for a sibling .lbl / .LBL file next to the data file.
    pds3_result = read_pds_labeled_image_array(
        filename_str, obj,
        pds3_label_method=kwargs.get('pds3_label_method', DEFAULT_PDS3_LABEL_METHOD),
    )
    if pds3_result is not None:
        return pds3_result

    cause: BaseException | None = (
        ExceptionGroup('No reader matched', cascade_errors)
        if cascade_errors
        else None
    )
    raise OSError(
        f'Unrecognized image file format: {filename_str}'
    ) from cause


def read_pds_labeled_image_array(
    filename: str | os.PathLike[str],
    obj: ObjectSelector = None,
    *,
    pds3_label_method: str = DEFAULT_PDS3_LABEL_METHOD,
) -> ReadResult | None:
    """Read a PDS3-labeled image and return the same triple as :func:`read_one_image_array`.

    Parameters:
        filename: Path to a ``.LBL`` (or matching) PDS3 label file.
        obj: Optional pointer name or index.
        pds3_label_method: Forwarded to :class:`pdsparser.Pds3Label` as
            its ``method=`` argument (``'strict'``, ``'loose'``,
            ``'compound'``, or ``'fast'``).

    Returns:
        ``(array3d, False, (inst_host, inst_name, filter_name))`` or
        ``None`` if no parseable label is found.
    """
    filename_str = str(filename)
    label = None
    try:
        label = pdsparser.Pds3Label(filename_str, method=pds3_label_method)
    except (pdsparser.ParseException, SyntaxError, OSError):
        (head, ext) = os.path.splitext(filename_str)
        if ext.lower() != '.lbl':
            if os.path.exists(head + '.lbl'):
                try:
                    label = pdsparser.Pds3Label(head + '.lbl', method=pds3_label_method)
                except (pdsparser.ParseException, SyntaxError, OSError):
                    pass
            elif os.path.exists(head + '.LBL'):
                try:
                    label = pdsparser.Pds3Label(head + '.LBL', method=pds3_label_method)
                except (pdsparser.ParseException, SyntaxError, OSError):
                    pass

    if not label:
        return None

    # pdsparser.Pds3Label proxies every dict operation through to its
    # underlying ``.dict`` attribute, which is a plain dict. Pull it out
    # once and use it directly for the rest of the function.
    label_dict = label.dict

    if isinstance(obj, str):
        pname = '^' + obj
        if pname not in label_dict:
            raise KeyError(f'Object {obj} not found in {filename_str}')

    else:
        pnames = [
            key
            for key in label_dict
            if key.startswith('^') and key.endswith('IMAGE')
        ]
        if not pnames:
            raise KeyError(f'No IMAGE objects found in {filename_str}')

        if obj is None:
            obj = 0
        elif not isinstance(obj, int):
            raise TypeError(f'Invalid index type {obj} for {filename_str}')

        try:
            pname = pnames[obj]
        except IndexError as e:
            raise IndexError(
                f'Object index {obj} is out of range in {filename_str}'
            ) from e

    # Resolve the pointer to ``(imagefile, byte_offset)``. The current
    # pdsparser API stores the pointer value in ``label_dict[pname]`` and
    # the offset and unit in companion keys ``<pname>_offset`` /
    # ``<pname>_unit``. The unit is either ``'<BYTES>'`` or an empty
    # string (RECORDS default).
    node = label_dict[pname]
    record_bytes = label_dict.get('RECORD_BYTES', 0) or 0
    unit = label_dict.get(pname + '_unit', '') or ''

    if isinstance(node, int):
        imagefile = filename_str
        offset_value = node
    elif isinstance(node, str):
        imagefile = os.path.join(os.path.split(filename_str)[0], node)
        offset_value = label_dict.get(pname + '_offset', 1) or 1
    elif isinstance(node, (list, tuple)):
        if isinstance(node[0], str):
            imagefile = os.path.join(os.path.split(filename_str)[0], node[0])
            offset_value = int(node[1]) if len(node) >= 2 else 1
        else:
            imagefile = filename_str
            offset_value = int(node[0])
    else:
        raise TypeError(f'Unsupported pointer value {node!r} in {filename_str}')

    if 'BYTES' in unit:
        offset = max(int(offset_value) - 1, 0)
    else:
        offset = max(int(offset_value) - 1, 0) * record_bytes

    image = label_dict[pname[1:]]
    lines = image['LINES']
    samples = image['LINE_SAMPLES']
    bytes_ = image['SAMPLE_BITS'] // 8
    fmt = image['SAMPLE_TYPE']

    prefix_bytes = image.get('PREFIX_BYTES', 0)
    suffix_bytes = image.get('SUFFIX_BYTES', 0)

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
    if offset_samples * bytes_ != offset:
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

    inst_host = (
        label_dict.get('INSTRUMENT_NAME', '')
        or label_dict.get('SPACECRAFT_NAME', '')
    )
    inst_name = label_dict.get('INSTRUMENT_HOST_NAME', '')
    filter_name = label_dict.get('FILTER_NAME', '')

    return ReadResult(array3d, False, (inst_host, inst_name, filter_name))


def read_pil(infile: str | os.PathLike[str]) -> Image.Image | list[Image.Image]:
    """Read a PIL image (or 16-bit TIFF expanded to a PIL image) from a file.

    Parameters:
        infile: Path to the input file.

    Returns:
        A PIL image or a list of three PIL images (16-bit RGB).
    """
    infile_str = str(infile)
    testfile = infile_str.upper()
    if testfile.endswith('.TIFF') or testfile.endswith('.TIF'):
        try:
            (array, palette) = read_tiff16(infile_str)
        except OSError:
            array = None
            palette = None

        if array is not None:
            if palette is not None:
                raise OSError('16-bit palette option is not supported')

            return cast(
                'Image.Image | list[Image.Image]',
                array_to_pil(array, twobytes=True, rescale=False),
            )

    im = Image.open(infile_str)
    im.load()
    return im


def read_array(infile: str | os.PathLike[str], rescale: bool) -> NDArray[Any]:
    """Read a numpy array from a PIL-readable file (or a 16-bit TIFF).

    Parameters:
        infile: Path to the input file.
        rescale: True to scale values to the range 0-1.

    Returns:
        A 2-D or 3-D numpy array. The dtype depends on the input format
        and on ``rescale``: ``uint8`` for 8-bit PIL inputs without
        rescaling, ``uint16`` for 16-bit TIFF, and ``float64`` whenever
        ``rescale`` is true.
    """
    infile_str = str(infile)
    array = None
    palette = None
    testfile = infile_str.upper()
    if testfile.endswith('.TIFF') or testfile.endswith('.TIF'):
        try:
            (array, palette) = read_tiff16(infile_str)
        except OSError:
            array = None
            palette = None

    if array is not None:
        if palette is not None:
            raise OSError('16-bit palette option is not supported')

        if rescale:
            array = array.astype('float') / 65535.0

        return cast('NDArray[Any]', array)

    return cast('NDArray[Any]', pil_to_array(Image.open(infile_str), rescale))


def get_outfile(
    infile: str | os.PathLike[str],
    outdir: str | os.PathLike[str] | None = None,
    strip: Any = None,
    suffix: str | None = '',
    extension: str = 'jpg',
    replace: str = 'all',
) -> str:
    """Derive the output filename for one input.

    Parameters:
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
    'FilterInfo',
    'ReadResult',
    'get_outfile',
    'read_array',
    'read_image_array',
    'read_one_image_array',
    'read_pds_labeled_image_array',
    'read_pil',
]
