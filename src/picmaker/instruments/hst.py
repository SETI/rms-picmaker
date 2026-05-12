"""HST detection and wavelength-based tint."""

import logging
from typing import Any

from picmaker._rgb import BFUNC, GFUNC, RFUNC, RGB_BY_NM

logger = logging.getLogger(__name__)


def detect_vicar(vic: Any) -> tuple[str, str, str] | None:
    """HST is not delivered as VICAR — always returns ``None``.

    Parameters:
        vic: A :class:`vicar.VicarImage` instance (unused).

    Returns:
        Always ``None``.
    """
    return None


def detect_fits(hdulist: Any) -> tuple[str, str, Any] | None:
    """Detect an HST FITS image.

    The ``TELESCOP`` keyword identifies the host, ``INSTRUME`` (with an
    optional ``DETECTOR`` suffix) identifies the instrument, and the
    filter name comes from one of ``FILTER``, ``FILTER1``/``FILTER2``
    (HST/ACS), or ``FILTNAM1``/``FILTNAM2`` (HST/WFPC2).

    Parameters:
        hdulist: An ``astropy.io.fits`` HDU list.

    Returns:
        ``(inst_host, inst_id, filter_name)`` where ``filter_name`` may
        be a string or a 2-tuple of strings, or ``None`` if the file is
        not an HST FITS image.
    """
    try:
        inst_host = hdulist[0].header['TELESCOP']
    except KeyError:
        return None
    try:
        inst_id = hdulist[0].header['INSTRUME']
        if 'DETECTOR' in hdulist[0].header:
            inst_id += '/' + hdulist[0].header['DETECTOR']
    except KeyError:
        return None

    filter_name: Any = None
    try:
        filter_name = hdulist[0].header['FILTER'].upper().strip()
    except KeyError:
        pass
    try:
        filter_name = (hdulist[0].header['FILTER1'], hdulist[0].header['FILTER2'])
    except KeyError:
        pass
    try:
        filter_name = (hdulist[0].header['FILTNAM1'], hdulist[0].header['FILTNAM2'])
    except KeyError:
        pass

    return (inst_host, inst_id, filter_name)


def matches(inst_host: str, inst_id: str) -> bool:
    """Host-level predicate: accept any host that mentions HUBBLE or HST.

    Parameters:
        inst_host: Instrument host string (e.g. ``'HST'`` or ``'HUBBLE
            SPACE TELESCOPE'``).
        inst_id: Instrument id.

    Returns:
        ``True`` if either substring appears in ``inst_host``.
    """
    return 'HUBBLE' in inst_host or 'HST' in inst_host


def tint_for(inst_id: str, filter_name: Any) -> list[tuple[int, int, int]] | None:
    """Return the full ``[black, tint, white]`` colormap for an HST filter.

    The tint color comes from inferring a wavelength out of the numeric
    characters in ``filter_name`` (e.g. ``'F606W'`` → 606 nm) and looking
    that wavelength up in :data:`picmaker._rgb.RGB_BY_NM` via the
    :data:`picmaker._rgb.RFUNC` / :data:`picmaker._rgb.GFUNC` /
    :data:`picmaker._rgb.BFUNC` splines. Each detector family has its
    own correction:

    * NICMOS scales the inferred number by 3.5 (its filter names encode
      tens of nm rather than nm).
    * WFC3/IR and ACS/SBC also scale by 3.5 when the inferred number is
      below 200.
    * WFPC2 quad-filters ``FQUV*`` and ``FQCH4*`` are pinned to 300 nm
      and 900 nm respectively.
    * NICMOS polarisers ``POL0S`` / ``POL0L`` are pinned to 110 nm and
      220 nm before the NICMOS x3.5 scaling.

    Broadband filters ``F350LP``, ``F606W``, and ``LONG_PASS`` short-
    circuit to a plain ``[black, white]`` colormap.

    Parameters:
        inst_id: Instrument id, possibly with detector suffix (e.g.
            ``'WFC3/IR'``).
        filter_name: HST filter name; passed through as-is from
            :func:`detect_fits`.

    Returns:
        ``[(0, 0, 0), (r, g, b), (255, 255, 255)]`` for a successfully
        inferred wavelength, ``[(0, 0, 0), (255, 255, 255)]`` for the
        broadband short-circuits, or ``None`` when no wavelength can be
        inferred (a WARNING is logged).
    """
    if filter_name in ('F350LP', 'F606W', 'LONG_PASS'):
        return [(0, 0, 0), (255, 255, 255)]

    wavelength: float = 0
    for c in filter_name:
        if '0' <= c <= '9' and wavelength < 1600:
            wavelength = 10 * wavelength + int(c)

    # Detector-specific wavelength scaling. The elif chain is kept as
    # three separate branches (rather than `or`-combined) so future
    # per-detector adjustments don't change the others' precedence.
    if 'NIC' in inst_id:  # noqa: SIM114
        wavelength *= 3.5
    elif ('WFC3' in inst_id or 'IR' in inst_id) and wavelength < 200:  # noqa: SIM114
        wavelength *= 3.5
    elif ('ACS' in inst_id or 'SBC' in inst_id) and wavelength < 200:
        wavelength *= 3.5
    elif filter_name.startswith('FQUV'):
        wavelength = 300
    elif filter_name.startswith('FQCH4'):
        wavelength = 900
    elif filter_name == 'POL0S':
        wavelength = 110 * 3.5
    elif filter_name == 'POL0L':
        wavelength = 220 * 3.5

    if wavelength == 0:
        logger.warning('Unknown HST filter: %s %s', inst_id, filter_name)
        return None

    wavelength = max(wavelength, RGB_BY_NM[0, 0])
    wavelength = min(wavelength, RGB_BY_NM[-1, 0])

    r = int(RFUNC(wavelength))
    g = int(GFUNC(wavelength))
    b = int(BFUNC(wavelength))
    return [(0, 0, 0), (r, g, b), (255, 255, 255)]


__all__ = ['detect_fits', 'detect_vicar', 'matches', 'tint_for']
