"""Voyager ISS detection and tint."""

import os
from typing import Any

import pdsparser
from vicar import VicarError

from picmaker._types import ObjectSelector, ReadResult
from picmaker.instruments import _shared

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


def _detect_vicar(vic: Any) -> tuple[str, str, str] | None:
    """Extract Voyager ISS metadata from an open :class:`vicar.VicarImage`.

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


def _detect_pds3(label: pdsparser.Pds3Label) -> tuple[str, str, str] | None:
    """Extract Voyager ISS metadata from a PDS3 label.

    Parameters:
        label: A parsed :class:`pdsparser.Pds3Label`.

    Returns:
        ``('VOYAGER', 'ISS', filter_name)`` if the label identifies a
        Voyager ISS image, ``None`` otherwise.
    """
    try:
        d = label.as_dict()
        host = d.get('INSTRUMENT_HOST_NAME', '') or d.get('INSTRUMENT_HOST_ID', '')
        if not (str(host).startswith('VOYAGER') or str(host).startswith('VG')):
            return None
        if not str(d.get('INSTRUMENT_ID', '')).startswith('ISS'):
            return None
        filter_name = str(d.get('FILTER_NAME', '')).upper().strip()
        return ('VOYAGER', 'ISS', filter_name)
    except TypeError:
        return None


def read_file(
    filename: str | os.PathLike[str] | pdsparser.Pds3Label,
    obj: ObjectSelector = None,
    **kwargs: Any,
) -> ReadResult | None:
    """Try to detect and read a Voyager ISS image.

    Accepts either a file path (VICAR format) or a pre-parsed
    :class:`pdsparser.Pds3Label`.  Returns ``None`` if the file is not
    recognized as a Voyager ISS image.

    Parameters:
        filename: Path to the candidate file, or a parsed PDS3 label.
        obj: Ignored (VICAR files contain a single array).
        **kwargs: Accepted but ignored; Voyager files need no
            instrument-specific options.

    Returns:
        :class:`~picmaker._types.ReadResult` on success, ``None`` if
        the file is not recognized as a Voyager ISS image.
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
    """Predicate identifying the Voyager ISS camera, the instrument this module tints.

    Both the host and the instrument id must agree: a Voyager host alone
    is not enough, since other Voyager instruments (PPS, ...) must not be
    picked up for ISS tinting. The ``inst_id`` test mirrors the ISS gate
    in :func:`tint_for`.

    Parameters:
        inst_host: Instrument host string.
        inst_id: Instrument id (e.g. ``'ISS'``).

    Returns:
        ``True`` for a Voyager host whose ``inst_id`` names the ISS camera.
    """
    return inst_host.startswith('VOYAGER') and inst_id.startswith('ISS')


def tint_for(inst_id: str, filter_name: Any) -> list[tuple[int, int, int]] | None:
    """Return the full ``[black, tint, white]`` colormap for a Voyager filter.

    Non-ISS Voyager instruments fall through to the 2-element
    ``[black, white]`` colormap. Unknown filter names raise
    :class:`KeyError` (the caller is expected to surface that as a
    "no colormap" condition).

    Parameters:
        inst_id: Instrument id (typically ``'ISS'``).
        filter_name: A key into :data:`picmaker.instruments.voyager_iss.FILTER_DICT`.

    Returns:
        ``[(0, 0, 0), tint, (255, 255, 255)]`` for an ISS filter or
        ``[(0, 0, 0), (255, 255, 255)]`` otherwise.

    Raises:
        KeyError: If ``filter_name`` is not in
            :data:`picmaker.instruments.voyager_iss.FILTER_DICT` and
            ``inst_id`` is an ISS instrument.
    """
    if not inst_id.startswith('ISS'):
        return [(0, 0, 0), (255, 255, 255)]
    return [(0, 0, 0), FILTER_DICT[filter_name], (255, 255, 255)]


__all__ = ['FILTER_DICT', 'matches', 'read_file', 'tint_for']
