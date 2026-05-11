"""Voyager ISS detection and tint.

Source: picmaker.py (pre-PR-3) lines 1589-1593 (VICAR detect),
2245-2256 (filter dict), 2370-2374 (tint).
"""

from typing import Any

from vicar import VicarError

# Extracted verbatim from picmaker.py:2245-2256.
FILTER_DICT: dict[str, tuple[int, int, int]] = {
    'UV': (200, 60, 255),
    'VIOLET': (200, 120, 255),
    'BLUE': (110, 110, 255),
    'GREEN': (110, 255, 110),
    'ORANGE': (255, 170, 100),
    'NAD': (110, 255, 110),
    'SODIUM': (110, 255, 110),
    'CH4_U': (255, 60, 60),
    'CH4/U': (255, 60, 60),
    'CH4_JS': (255, 60, 60),
    'CH4/JS': (255, 60, 60),
}


def detect_vicar(vic: Any) -> tuple[str, str, str] | None:
    """Detect a Voyager ISS VICAR image.

    Returns:
        ``('VOYAGER', 'ISS', filter_name)`` if the label identifies a
        Voyager ISS image, ``None`` otherwise.
    """
    try:
        if vic['LAB02'][:3] == 'VGR':
            return ('VOYAGER', 'ISS', vic['LAB03'][37:43].rstrip())
    except (VicarError, IndexError, KeyError):
        pass
    return None


def detect_fits(hdulist: Any) -> tuple[str, str, str] | None:
    """Voyager ISS is not delivered as FITS — always returns ``None``."""
    return None


def matches(inst_host: str, inst_id: str) -> bool:
    """Host-level predicate. picmaker.py:2370 also accepts ``'VG'`` but
    no current detection path produces such a host; preserve only the
    ``'VOYAGER'`` prefix.
    """
    return inst_host.startswith('VOYAGER')


def tint_for(inst_id: str, filter_name: Any) -> list[tuple[int, int, int]] | None:
    """Return the full ``[black, tint, white]`` colormap.

    Non-ISS Voyager instruments fall through to the 2-element white
    colormap (matches picmaker.py:2374).

    Unknown filter names propagate ``KeyError`` to the caller — this
    matches the original picmaker.py:2372 behavior.
    """
    if not inst_id.startswith('ISS'):
        return [(0, 0, 0), (255, 255, 255)]
    return [(0, 0, 0), FILTER_DICT[filter_name], (255, 255, 255)]


__all__ = ['FILTER_DICT', 'detect_fits', 'detect_vicar', 'matches', 'tint_for']
