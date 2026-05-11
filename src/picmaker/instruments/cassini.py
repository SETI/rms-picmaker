"""Cassini ISS detection and tint.

Source: picmaker.py (pre-PR-3) lines 1562-1568 (VICAR detect) and
2376-2397 (per-filter tint chain).
"""

from typing import Any

from vicar import VicarError


def _iss_tint(filter_name: str) -> tuple[int, int, int]:
    """Map a Cassini ISS filter name to an (R, G, B) tint.

    Falls back to grey ``(127, 127, 127)`` for unknown filters; preserves
    the if/elif chain at picmaker.py:2378-2393 byte for byte.
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
    """Cassini ISS is not delivered as FITS — always returns ``None``."""
    return None


def matches(inst_host: str, inst_id: str) -> bool:
    """Host-level predicate; sub-instrument dispatch happens in :func:`tint_for`."""
    return inst_host.startswith('CASSINI')


def tint_for(inst_id: str, filter_name: Any) -> list[tuple[int, int, int]] | None:
    """Return the full ``[black, tint, white]`` colormap.

    Non-ISS Cassini instruments fall through to the 2-element white
    colormap (matches picmaker.py:2397).
    """
    if not inst_id.startswith('ISS'):
        return [(0, 0, 0), (255, 255, 255)]
    return [(0, 0, 0), _iss_tint(filter_name), (255, 255, 255)]


__all__ = ['detect_fits', 'detect_vicar', 'matches', 'tint_for']
