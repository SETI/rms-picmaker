"""Galileo SSI detection and tint."""

import os
from typing import Any

import pdsparser
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
    :data:`picmaker.instruments.galileo_ssi.FILTER_NAMES`, then a
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
    except (VicarError, KeyError, IndexError, ValueError):
        pass
    return None


def _detect_pds3(label: pdsparser.Pds3Label) -> tuple[str, str, str] | None:
    """Extract Galileo SSI metadata from a PDS3 label.

    Parameters:
        label: A parsed :class:`pdsparser.Pds3Label`.

    Returns:
        ``('GALILEO', 'SSI', filter_name)`` if the label identifies a
        Galileo SSI image, ``None`` otherwise.
    """
    try:
        d = label.as_dict()
        if d.get('SPACECRAFT_NAME') != 'GALILEO ORBITER':
            return None
        if not str(d.get('INSTRUMENT_ID', '')).startswith('SSI'):
            return None
        if 'FILTER_NAME' in d:
            filter_name = str(d['FILTER_NAME'])
        elif 'FILTER_NUMBER' in d:
            filter_name = FILTER_NAMES[int(d['FILTER_NUMBER'])]
        else:
            filter_name = ''
        return ('GALILEO', 'SSI', filter_name)
    except (KeyError, TypeError, IndexError):
        return None


def read_file(
    filename: str | os.PathLike[str] | pdsparser.Pds3Label,
    obj: ObjectSelector = None,
    **kwargs: Any,
) -> ReadResult | None:
    """Try to detect and read a Galileo SSI image.

    Accepts either a file path (VICAR format) or a pre-parsed
    :class:`pdsparser.Pds3Label`.  Returns ``None`` if the file is not
    recognized as a Galileo SSI image.

    Parameters:
        filename: Path to the candidate file, or a parsed PDS3 label.
        obj: Ignored (VICAR files contain a single array).
        **kwargs: Accepted but ignored; Galileo files need no
            instrument-specific options.

    Returns:
        :class:`~picmaker._types.ReadResult` on success, ``None`` if
        the file is not recognized as a Galileo SSI image.
    """
    if isinstance(filename, pdsparser.Pds3Label):
        filter_info = _detect_pds3(filename)
        if filter_info is None:
            return None
        array3d = _shared.read_pds3_image_array(filename, obj)
        return ReadResult(array3d, False, filter_info)

    vic = _shared.try_open_vicar(filename)
    if vic is None:
        return None
    filter_info = _detect_vicar(vic)
    if filter_info is None:
        return None
    return ReadResult(_shared.ensure_3d(vic.data_3d), False, filter_info)


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

    Only the SSI camera and the ``SOLID``-prefixed variants get a colored tint; every
    other Galileo instrument falls through to the 2-element ``[black, white]`` colormap.

    Parameters:
        inst_id: Instrument id.
        filter_name: A key into :data:`picmaker.instruments.galileo_ssi.FILTER_DICT`.

    Returns:
        ``[(0, 0, 0), tint, (255, 255, 255)]`` for an SSI filter or
        ``[(0, 0, 0), (255, 255, 255)]`` otherwise.

    Raises:
        KeyError: If ``filter_name`` is not in
            :data:`picmaker.instruments.galileo_ssi.FILTER_DICT` and
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
