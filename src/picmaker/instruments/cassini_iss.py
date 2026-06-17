"""Cassini ISS detection and tint."""

import os
from typing import Any

from vicar import VicarError

from picmaker._types import ObjectSelector, ReadResult
from picmaker.instruments import _shared


def _iss_tint(filter_name: str) -> tuple[int, int, int]:
    """Map a Cassini ISS filter name to an ``(R, G, B)`` tint.

    The match is a substring test, in declaration order; the first
    branch whose substring appears in ``filter_name`` wins. Unknown
    filter names fall back to neutral gray ``(127, 127, 127)``.

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


def _detect_vicar(vic: Any) -> tuple[str, str, str] | None:
    """Extract Cassini ISS metadata from an open :class:`vicar.VicarImage`.

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


def read_file(
    filename: str | os.PathLike[str],
    obj: ObjectSelector = None,
    hst: bool = False,
    *,
    pds3_label_method: str = 'strict',
) -> ReadResult | None:
    """Try to detect and read a Cassini ISS VICAR image.

    Opens *filename* as VICAR, checks the instrument label, and returns
    the data array with filter metadata.  Returns ``None`` if the file
    is not a Cassini ISS VICAR image.

    Parameters:
        filename: Path to the candidate file.
        obj: Ignored (VICAR files contain a single array).
        hst: Ignored (Cassini is not HST).
        pds3_label_method: Ignored (Cassini files are not PDS3-labeled).

    Returns:
        :class:`~picmaker._types.ReadResult` on success, ``None`` if
        the file is not recognized as a Cassini ISS image.
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
        filter_name: The Cassini filter string from :func:`_detect_vicar`.

    Returns:
        ``[(0, 0, 0), tint, (255, 255, 255)]`` for an ISS filter or
        ``[(0, 0, 0), (255, 255, 255)]`` otherwise.
    """
    if not inst_id.startswith('ISS'):
        return [(0, 0, 0), (255, 255, 255)]
    return [(0, 0, 0), _iss_tint(filter_name), (255, 255, 255)]


__all__ = ['matches', 'read_file', 'tint_for']
