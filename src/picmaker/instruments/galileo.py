"""Galileo SSI detection and tint."""

import os
from typing import Any

from vicar import VicarError

from picmaker._types import ObjectSelector, ReadResult
from picmaker.instruments import _shared

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


def _detect_vicar(vic: Any) -> tuple[str, str, str] | None:
    """Extract Galileo SSI metadata from an open :class:`vicar.VicarImage`.

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


def read_file(
    filename: str | os.PathLike[str],
    obj: ObjectSelector = None,
    hst: bool = False,
    *,
    pds3_label_method: str = 'strict',
) -> ReadResult | None:
    """Try to detect and read a Galileo SSI VICAR image.

    Opens *filename* as VICAR, checks the instrument label, and returns
    the data array with filter metadata.  Returns ``None`` if the file
    is not a Galileo SSI VICAR image.

    Parameters:
        filename: Path to the candidate file.
        obj: Ignored (VICAR files contain a single array).
        hst: Ignored (Galileo is not HST).
        pds3_label_method: Ignored (Galileo files are not PDS3-labeled).

    Returns:
        :class:`~picmaker._types.ReadResult` on success, ``None`` if
        the file is not recognized as a Galileo SSI image.
    """
    vic = _shared.try_open_vicar(filename)
    if vic is None:
        return None
    filter_info = _detect_vicar(vic)
    if filter_info is None:
        return None
    array3d = vic.data_3d
    if array3d.ndim == 2:
        array3d = array3d.reshape((1, *array3d.shape))
    return ReadResult(array3d, False, filter_info)


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
    'matches',
    'read_file',
    'tint_for',
]
