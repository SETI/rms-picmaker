"""Shared format-level utilities for instrument reader modules.

These helpers are imported by individual instrument modules in
:mod:`picmaker.instruments`; they live here (rather than in
:mod:`picmaker.io`) to avoid a circular import between
:mod:`picmaker.io` (which imports :mod:`picmaker.instruments`) and
the instrument sub-modules.
"""

import os
import warnings
from typing import Any

import astropy.io.fits as pyfits
import numpy as np
import pdsparser
from numpy.typing import NDArray
from vicar import VicarError, VicarImage

from picmaker._types import ObjectSelector


def try_open_vicar(filename: str | os.PathLike[str]) -> VicarImage | None:
    """Try to parse *filename* as a VICAR image.

    Parameters:
        filename: Path to the candidate file.

    Returns:
        A :class:`vicar.VicarImage` instance on success, or ``None`` if
        the file cannot be opened or parsed as VICAR (including on
        :exc:`OSError` for missing or unreadable files).
    """
    try:
        return VicarImage.from_file(str(filename), extraneous='print', strict=False)
    except (VicarError, OSError):
        return None


def is_fits_file(filename: str | os.PathLike[str]) -> bool:
    """Return ``True`` iff *filename* starts with the FITS magic bytes.

    The FITS standard requires the first 9 bytes of a valid FITS file to
    be ``b'SIMPLE  ='``. Returns ``False`` on any :exc:`OSError` or
    :exc:`TypeError` (e.g. when *filename* is not a path-like object).

    Parameters:
        filename: Path to the candidate file.
    """
    try:
        with open(filename, 'rb') as f:
            return f.read(9) == b'SIMPLE  ='
    except (OSError, TypeError):
        return False


def read_pds3_image_array(
    label: pdsparser.PdsLabel,
    obj: ObjectSelector,
) -> NDArray[Any]:
    """Read the image array pointed to by a PDS3 label's ``^IMAGE`` pointer.

    Resolves the first ``^*IMAGE`` pointer in the label to a data file
    (relative to the label's own directory), then reads the data via the
    VICAR parser if the file is a VICAR image, or via the FITS reader if
    the file starts with the FITS magic bytes.

    Parameters:
        label: A parsed :class:`pdsparser.PdsLabel` with at least one
            ``^IMAGE`` (or ``^*IMAGE``) pointer.
        obj: Forwarded to :func:`extract_fits_array` when the data file
            is a FITS image; ignored for VICAR images.

    Returns:
        3-D ``(bands, lines, samples)`` numpy array.

    Raises:
        OSError: If no ``^*IMAGE`` pointer is found, or if the data file
            cannot be read as VICAR or FITS.
    """
    label_dict = label.as_dict()
    label_filepath: str = str(label._filepath)
    label_dir = os.path.dirname(label_filepath)

    pnames = [k for k in label_dict if k.startswith('^') and k.endswith('IMAGE')]
    if not pnames:
        raise OSError('No ^*IMAGE pointer found in PDS3 label')
    pname = pnames[0]
    node = label_dict[pname]

    if isinstance(node, (list, tuple)):
        data_filename = str(node[0])
    elif isinstance(node, str):
        data_filename = node
    elif isinstance(node, int):
        data_filename = os.path.basename(label_filepath)
    else:
        raise OSError(f'Unexpected ^IMAGE pointer value: {node!r}')

    data_file = os.path.join(label_dir, data_filename)

    vic = try_open_vicar(data_file)
    if vic is not None:
        array3d: NDArray[Any] = vic.data_3d
        if array3d.ndim == 2:
            array3d = array3d.reshape((1, *array3d.shape))
        return array3d

    if is_fits_file(data_file):
        try:
            with warnings.catch_warnings(), pyfits.open(data_file) as hdulist:
                warnings.filterwarnings('error')
                return extract_fits_array(hdulist, obj)
        except (UserWarning, OSError):
            pass

    raise OSError(f'Cannot read PDS3 data file: {data_file}')


def extract_fits_array(hdulist: Any, obj: ObjectSelector) -> NDArray[Any]:
    """Extract the image array from an open FITS HDU list.

    Handles ``obj=None`` (auto-detect the first valid 2-D or 3-D HDU),
    a list or tuple ``obj`` (stack the listed HDUs along the band axis),
    or a scalar ``obj`` (direct HDU index or name).  Always returns a
    3-D ``(bands, lines, samples)`` array.

    Parameters:
        hdulist: An open ``astropy.io.fits`` HDU list.
        obj: Object selector controlling which HDU(s) to read.

    Returns:
        3-D numpy array.

    Raises:
        OSError: If ``obj`` is ``None`` and no valid image array is
            found in the HDU list.
    """
    array3d: NDArray[Any] | None = None

    if obj is None:
        for hdu in hdulist:
            candidate: Any = hdu.data
            if isinstance(candidate, np.ndarray) and candidate.ndim in (2, 3):
                array3d = candidate
                break
    elif isinstance(obj, (list, tuple)):
        layers = [hdulist[o].data for o in obj]
        array3d = np.stack(layers)
    else:
        obj_key: Any = obj
        try:
            obj_key = int(obj_key)
        except (ValueError, TypeError):
            pass
        array3d = hdulist[obj_key].data.copy()

    if array3d is None:
        raise OSError('Image array not found in FITS file')
    if array3d.ndim == 2:
        array3d = array3d.reshape((1, *array3d.shape))
    return array3d


__all__ = ['extract_fits_array', 'is_fits_file', 'read_pds3_image_array', 'try_open_vicar']
