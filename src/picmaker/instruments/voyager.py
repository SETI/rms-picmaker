"""Voyager ISS detection and tint."""

from typing import Any

from vicar import VicarError

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

    Voyager VICAR labels carry their identifying string in ``LAB02`` (a
    ``VGR`` prefix) and the filter name in characters 37..43 of
    ``LAB03``; trailing spaces are stripped.

    Parameters:
        vic: A :class:`vicar.VicarImage` instance.

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
    """Voyager ISS is not delivered as FITS — always returns ``None``.

    Parameters:
        hdulist: An ``astropy.io.fits`` HDU list (unused).

    Returns:
        Always ``None``.
    """
    return None


def matches(inst_host: str, inst_id: str) -> bool:
    """Host-level predicate; sub-instrument dispatch happens in :func:`tint_for`.

    Parameters:
        inst_host: Instrument host string.
        inst_id: Instrument id (e.g. ``'ISS'``).

    Returns:
        ``True`` for any host whose name starts with ``'VOYAGER'``.
    """
    return inst_host.startswith('VOYAGER')


def tint_for(inst_id: str, filter_name: Any) -> list[tuple[int, int, int]] | None:
    """Return the full ``[black, tint, white]`` colormap for a Voyager filter.

    Non-ISS Voyager instruments fall through to the 2-element
    ``[black, white]`` colormap. Unknown filter names raise
    :class:`KeyError` (the caller is expected to surface that as a
    "no colormap" condition).

    Parameters:
        inst_id: Instrument id (typically ``'ISS'``).
        filter_name: A key into :data:`picmaker.instruments.voyager.FILTER_DICT`.

    Returns:
        ``[(0, 0, 0), tint, (255, 255, 255)]`` for an ISS filter or
        ``[(0, 0, 0), (255, 255, 255)]`` otherwise.

    Raises:
        KeyError: If ``filter_name`` is not in :data:`picmaker.instruments.voyager.FILTER_DICT` and
            ``inst_id`` is an ISS instrument.
    """
    if not inst_id.startswith('ISS'):
        return [(0, 0, 0), (255, 255, 255)]
    return [(0, 0, 0), FILTER_DICT[filter_name], (255, 255, 255)]


__all__ = ['FILTER_DICT', 'detect_fits', 'detect_vicar', 'matches', 'tint_for']
