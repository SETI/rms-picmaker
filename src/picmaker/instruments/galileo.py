"""Galileo SSI detection and tint.

Source: picmaker.py (pre-PR-3) lines 1571-1586 (VICAR detect),
2266-2277 (filter dict + names), 2399-2403 (tint).
"""

from typing import Any

from vicar import VicarError

FILTER_NAMES: list[str] = [
    'CLEAR',
    'GREEN',
    'RED',
    'VIOLET',
    'IR-7560',
    'IR-9680',
    'IR-7270',
    'IR-8890',
]

FILTER_DICT: dict[str, tuple[int, int, int]] = {
    'CLEAR': (128, 128, 128),
    'RED': (190, 130, 100),
    'GREEN': (110, 190, 110),
    'VIOLET': (160, 100, 200),
    'IR-7270': (200, 100, 100),
    'IR-7560': (210, 80, 80),
    'IR-8890': (220, 60, 60),
    'IR-9680': (230, 40, 40),
}


def detect_vicar(vic: Any) -> tuple[str, str, str] | None:
    """Detect a Galileo SSI VICAR image.

    Tries the ``MISSION`` keyword first (picmaker.py:1573-1577), then
    falls back to parsing ``LAB01`` / ``LAB03`` (picmaker.py:1581-1586).

    Returns:
        ``('GALILEO', 'SSI', filter_name)`` if the label identifies a
        Galileo SSI image, ``None`` otherwise.
    """
    try:
        if vic['MISSION'] == 'GALILEO':
            filtno = vic['FILTER']
            return ('GALILEO', 'SSI', FILTER_NAMES[filtno])
    except (VicarError, KeyError):
        pass
    try:
        if vic['LAB01'][:7] == 'GLL/SSI':
            filtno = int(vic['LAB03'].partition('FILTER=')[2][0])
            return ('GALILEO', 'SSI', FILTER_NAMES[filtno])
    except (VicarError, KeyError):
        pass
    return None


def detect_fits(hdulist: Any) -> tuple[str, str, str] | None:
    """Galileo SSI is not delivered as FITS — always returns ``None``."""
    return None


def matches(inst_host: str, inst_id: str) -> bool:
    """Host-level predicate; sub-instrument dispatch happens in :func:`tint_for`."""
    return inst_host.startswith('GALILEO')


def tint_for(inst_id: str, filter_name: Any) -> list[tuple[int, int, int]] | None:
    """Return the full ``[black, tint, white]`` colormap.

    Non-SSI Galileo instruments fall through to the 2-element white
    colormap (matches picmaker.py:2403).
    """
    if not (inst_id == 'SSI' or inst_id.startswith('SOLID')):
        return [(0, 0, 0), (255, 255, 255)]
    return [(0, 0, 0), FILTER_DICT[filter_name], (255, 255, 255)]


__all__ = [
    'FILTER_DICT',
    'FILTER_NAMES',
    'detect_fits',
    'detect_vicar',
    'matches',
    'tint_for',
]
