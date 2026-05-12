"""Galileo SSI detection and tint."""

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

    Two label conventions are tried in order: the ``MISSION`` keyword
    with a numeric ``FILTER`` index into
    :data:`picmaker.instruments.galileo.FILTER_NAMES`, then a
    ``GLL/SSI`` prefix in ``LAB01`` with ``FILTER=<digit>`` somewhere
    in ``LAB03``.

    Parameters:
        vic: A :class:`vicar.VicarImage` instance.

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
    """Galileo SSI is not delivered as FITS — always returns ``None``.

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
        inst_id: Instrument id (e.g. ``'SSI'``).

    Returns:
        ``True`` for any host whose name starts with ``'GALILEO'``.
    """
    return inst_host.startswith('GALILEO')


def tint_for(inst_id: str, filter_name: Any) -> list[tuple[int, int, int]] | None:
    """Return the full ``[black, tint, white]`` colormap for a Galileo filter.

    Only the SSI camera and the ``SOLID``-prefixed variants get a
    colored tint; every other Galileo instrument falls through to the
    2-element ``[black, white]`` colormap.

    Parameters:
        inst_id: Instrument id.
        filter_name: A key into :data:`picmaker.instruments.galileo.FILTER_DICT`.

    Returns:
        ``[(0, 0, 0), tint, (255, 255, 255)]`` for an SSI filter or
        ``[(0, 0, 0), (255, 255, 255)]`` otherwise.

    Raises:
        KeyError: If ``filter_name`` is not in
            :data:`picmaker.instruments.galileo.FILTER_DICT` and
            ``inst_id`` selects the SSI path.
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
