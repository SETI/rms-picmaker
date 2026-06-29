"""New Horizons MVIC detection and tint.

MVIC is the color imager; its FITS products carry a ``FILTER`` keyword
that drives the per-filter tint in :func:`tint_for`. LORRI (the
panchromatic camera) lives in :mod:`picmaker.instruments.nh_lorri`.
"""

import os
import warnings
from typing import Any

import astropy.io.fits as pyfits
import pdsparser

from picmaker._types import ObjectSelector, ReadResult
from picmaker.instruments import _shared

FILTER_DICT: dict[str, tuple[int, int, int]] = {
    'BLUE': (110, 110, 210),
    'RED': (190, 100, 100),
    'NIR': (210, 65, 45),
    'CH4': (230, 35, 35),
}


def _detect_fits(hdulist: Any) -> tuple[str, str, Any] | None:
    """Extract New Horizons MVIC metadata from an open ``astropy.io.fits`` HDU list.

    The ``HOSTNAME`` keyword identifies the host and ``INSTRU`` the
    instrument; the filter name comes from ``FILTER`` when present. Only
    MVIC (``INSTRU`` of ``'MVIC'`` / ``'MVI'``) is claimed here — other
    New Horizons instruments are left for their own readers.

    Parameters:
        hdulist: An ``astropy.io.fits`` HDU list.

    Returns:
        ``(inst_host, inst_id, filter_name)`` if the file is an NH MVIC
        FITS image, ``None`` otherwise. ``filter_name`` may be ``None`` if
        no ``FILTER`` keyword is present.
    """
    try:
        inst_host = hdulist[0].header['HOSTNAME']
    except KeyError:
        return None
    try:
        inst_id = hdulist[0].header['INSTRU'].upper().strip()
    except KeyError:
        return None
    if inst_id not in ('MVIC', 'MVI'):
        return None

    filter_name: Any
    try:
        filter_name = hdulist[0].header['FILTER'].upper().strip()
    except KeyError:
        filter_name = None
    return (inst_host, inst_id, filter_name)


def read_file(
    filename: str | os.PathLike[str] | pdsparser.Pds3Label,
    obj: ObjectSelector = None,
    **kwargs: Any,
) -> ReadResult | None:
    """Try to detect and read a New Horizons MVIC FITS image.

    Parameters:
        filename: Path to the candidate file. A parsed
            :class:`pdsparser.Pds3Label` is not an MVIC product and yields
            ``None``.
        obj: HDU index, name, or list/tuple of indices to stack.
        **kwargs: Accepted but ignored; MVIC files need no
            instrument-specific options.

    Returns:
        :class:`~picmaker._types.ReadResult` on success, ``None`` if the
        file is not recognized as a New Horizons MVIC FITS image.
    """
    if isinstance(filename, pdsparser.Pds3Label):
        return None
    if not _shared.is_fits_file(filename):
        return None
    try:
        # Set the error filter BEFORE entering pyfits.open() so warnings
        # emitted while parsing the FITS headers (during __enter__) are also
        # promoted to exceptions, not just those raised during HDU access.
        with warnings.catch_warnings():
            warnings.filterwarnings('error')
            with pyfits.open(str(filename)) as hdulist:
                _fitsobj = hdulist[0]  # IndexError / KeyError if not valid FITS
                filter_info = _detect_fits(hdulist)
                if filter_info is None:
                    return None
                array3d = _shared.extract_fits_array(hdulist, obj)
                return ReadResult(array3d, True, filter_info)
    except (UserWarning, OSError):
        return None


def matches(inst_host: str, inst_id: str) -> bool:
    """Predicate identifying the New Horizons MVIC camera, the instrument this module tints.

    Both the host and the instrument id must agree: a New Horizons host
    alone is not enough. The ``inst_id`` test mirrors the MVIC gate in
    :func:`tint_for`.

    Parameters:
        inst_host: Instrument host string.
        inst_id: Instrument id (``'MVIC'`` / ``'MVI'``).

    Returns:
        ``True`` for a New Horizons host whose ``inst_id`` names the MVIC
        camera.
    """
    return inst_host in ('NEW HORIZONS', 'NH') and inst_id in ('MVIC', 'MVI')


def tint_for(inst_id: str, filter_name: Any) -> list[tuple[int, int, int]] | None:
    """Return the full ``[black, tint, white]`` colormap for an MVIC filter.

    Parameters:
        inst_id: Instrument id (``'MVIC'`` / ``'MVI'``).
        filter_name: A key into :data:`picmaker.instruments.nh_mvic.FILTER_DICT`.

    Returns:
        ``[(0, 0, 0), tint, (255, 255, 255)]`` for an MVIC filter, or
        ``[(0, 0, 0), (255, 255, 255)]`` when ``inst_id`` is not MVIC.

    Raises:
        KeyError: If ``filter_name`` is not in
            :data:`picmaker.instruments.nh_mvic.FILTER_DICT` and ``inst_id``
            selects the MVIC path.
    """
    if inst_id not in ('MVIC', 'MVI'):
        return [(0, 0, 0), (255, 255, 255)]
    return [(0, 0, 0), FILTER_DICT[filter_name], (255, 255, 255)]


__all__ = ['FILTER_DICT', 'matches', 'read_file', 'tint_for']
