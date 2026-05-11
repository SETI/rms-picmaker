"""Cassini ISS detection and tint."""

from typing import Any

from vicar import VicarError


def _iss_tint(filter_name: str) -> tuple[int, int, int]:
    """Map a Cassini ISS filter name to an ``(R, G, B)`` tint.

    The match is a substring test, in declaration order; the first
    branch whose substring appears in ``filter_name`` wins. Unknown
    filter names fall back to neutral grey ``(127, 127, 127)``.

    Parameters:
        filter_name: A Cassini ISS filter string, typically
            ``'<filter1>+<filter2>'``.

    Returns:
        The ``(R, G, B)`` tint with each channel in ``[0, 255]``.
    """
    if 'IR' in filter_name:
        return (200, 80, 80)
    if 'UV' in filter_name:
        return (160, 80, 220)
    if 'VIO' in filter_name:
        return (160, 120, 200)
    if 'BL' in filter_name:
        return (110, 180, 180) if 'GRN' in filter_name else (110, 110, 180)
    if 'GRN' in filter_name:
        return (190, 190, 110) if 'RED' in filter_name else (110, 190, 110)
    if 'RED' in filter_name:
        return (190, 110, 100)
    if 'MT1' in filter_name:
        return (190, 110, 100)
    if 'CB1' in filter_name:
        return (190, 110, 100)
    if 'HAL' in filter_name:
        return (190, 110, 100)
    if 'MT' in filter_name:
        return (200, 80, 80)
    if 'CB' in filter_name:
        return (200, 80, 80)
    return (127, 127, 127)


def detect_vicar(vic: Any) -> tuple[str, str, str] | None:
    """Detect a Cassini ISS VICAR image.

    Looks at the ``INSTRUMENT_HOST_NAME`` and ``FILTER_NAME`` label
    fields; the filter is delivered as a 2-tuple of names that are
    joined with ``'+'``.

    Parameters:
        vic: A :class:`vicar.VicarImage` instance.

    Returns:
        ``('CASSINI', 'ISS', '<filter1>+<filter2>')`` if the label
        identifies a Cassini ISS image, ``None`` otherwise.
    """
    try:
        if vic['INSTRUMENT_HOST_NAME'] == 'CASSINI ORBITER':
            filter1, filter2 = vic['FILTER_NAME']
            return ('CASSINI', 'ISS', filter1 + '+' + filter2)
    except (VicarError, KeyError):
        pass
    return None


def detect_fits(hdulist: Any) -> tuple[str, str, str] | None:
    """Cassini ISS is not delivered as FITS — always returns ``None``.

    Parameters:
        hdulist: An ``astropy.io.fits`` HDU list (unused).

    Returns:
        Always ``None``.
    """
    return None


def matches(inst_host: str, inst_id: str) -> bool:
    """Host-level predicate; sub-instrument dispatch happens in :func:`tint_for`.

    Parameters:
        inst_host: Instrument host string (e.g. ``'CASSINI ORBITER'``).
        inst_id: Instrument id (e.g. ``'ISS'``).

    Returns:
        ``True`` for any Cassini host.
    """
    return inst_host.startswith('CASSINI')


def tint_for(inst_id: str, filter_name: Any) -> list[tuple[int, int, int]] | None:
    """Return the full ``[black, tint, white]`` colormap for a Cassini filter.

    Non-ISS Cassini instruments fall through to the 2-element
    ``[black, white]`` colormap (no tint).

    Parameters:
        inst_id: Instrument id (typically ``'ISS'``).
        filter_name: The Cassini filter string from :func:`detect_vicar`.

    Returns:
        ``[(0, 0, 0), tint, (255, 255, 255)]`` for an ISS filter or
        ``[(0, 0, 0), (255, 255, 255)]`` otherwise.
    """
    if not inst_id.startswith('ISS'):
        return [(0, 0, 0), (255, 255, 255)]
    return [(0, 0, 0), _iss_tint(filter_name), (255, 255, 255)]


__all__ = ['detect_fits', 'detect_vicar', 'matches', 'tint_for']
