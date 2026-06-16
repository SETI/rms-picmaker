"""Shared format-level utilities for instrument reader modules.

These helpers are imported by individual instrument modules in
:mod:`picmaker.instruments`; they live here (rather than in
:mod:`picmaker.io`) to avoid a circular import between
:mod:`picmaker.io` (which imports :mod:`picmaker.instruments`) and
the instrument sub-modules.
"""

import os
from typing import Any

import numpy as np
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
    be ``b'SIMPLE  ='``. Returns ``False`` on any :exc:`OSError`.

    Parameters:
        filename: Path to the candidate file.
    """
    try:
        with open(filename, 'rb') as f:
            return f.read(9) == b'SIMPLE  ='
    except OSError:
        return False


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


__all__ = ['extract_fits_array', 'is_fits_file', 'try_open_vicar']
