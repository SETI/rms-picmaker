"""New Horizons MVIC detection and tint."""

from typing import Any

FILTER_DICT: dict[str, tuple[int, int, int]] = {
    'BLUE': (110, 110, 210),
    'RED': (190, 100, 100),
    'NIR': (210, 65, 45),
    'CH4': (230, 35, 35),
}


def detect_vicar(vic: Any) -> tuple[str, str, str] | None:
    """NH is not delivered as VICAR — always returns ``None``.

    Parameters:
        vic: A :class:`vicar.VicarImage` instance (unused).

    Returns:
        Always ``None``.
    """
    return None


def detect_fits(hdulist: Any) -> tuple[str, str, Any] | None:
    """Detect a New Horizons FITS image.

    The ``HOSTNAME`` keyword identifies the host and ``INSTRU``
    identifies the instrument; the filter name comes from ``FILTER``
    when present.

    Parameters:
        hdulist: An ``astropy.io.fits`` HDU list.

    Returns:
        ``(inst_host, inst_id, filter_name)`` if the file is an NH FITS
        image, ``None`` otherwise. ``filter_name`` may be ``None`` if no
        ``FILTER`` keyword is present.
    """
    try:
        inst_host = hdulist[0].header['HOSTNAME']
    except KeyError:
        return None
    try:
        inst_id = hdulist[0].header['INSTRU'].upper().strip()
    except KeyError:
        return None

    filter_name: Any
    try:
        filter_name = hdulist[0].header['FILTER'].upper().strip()
    except KeyError:
        filter_name = None
    return (inst_host, inst_id, filter_name)


def matches(inst_host: str, inst_id: str) -> bool:
    """Host-level predicate; sub-instrument dispatch happens in :func:`tint_for`.

    Parameters:
        inst_host: Instrument host string.
        inst_id: Instrument id.

    Returns:
        ``True`` if ``inst_host`` is ``'NEW HORIZONS'`` or ``'NH'``.
    """
    return inst_host in ('NEW HORIZONS', 'NH')


def tint_for(inst_id: str, filter_name: Any) -> list[tuple[int, int, int]] | None:
    """Return the full ``[black, tint, white]`` colormap for an NH filter.

    Only the MVIC camera gets a colored tint; every other New Horizons
    instrument falls through to the 2-element ``[black, white]``
    colormap.

    Parameters:
        inst_id: Instrument id (``'MVIC'`` / ``'MVI'`` for the color
            path).
        filter_name: A key into :data:`picmaker.instruments.nh.FILTER_DICT`.

    Returns:
        ``[(0, 0, 0), tint, (255, 255, 255)]`` for an MVIC filter or
        ``[(0, 0, 0), (255, 255, 255)]`` otherwise.

    Raises:
        KeyError: If ``filter_name`` is not in
            :data:`picmaker.instruments.nh.FILTER_DICT` and
            ``inst_id`` selects the MVIC path.
    """
    if inst_id not in ('MVIC', 'MVI'):
        return [(0, 0, 0), (255, 255, 255)]
    return [(0, 0, 0), FILTER_DICT[filter_name], (255, 255, 255)]


__all__ = ['FILTER_DICT', 'detect_fits', 'detect_vicar', 'matches', 'tint_for']
