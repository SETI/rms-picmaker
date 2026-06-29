"""New Horizons LORRI detection.

LORRI is a panchromatic framing camera with no filters, so it requires
no color tinting: :func:`tint_for` always returns the plain
``[black, white]`` colormap. LORRI products are read from their PDS3
labels; the color imager MVIC lives in
:mod:`picmaker.instruments.nh_mvic`.
"""

import os
from typing import Any

import pdsparser

from picmaker._types import ObjectSelector, ReadResult
from picmaker.instruments import _shared


def _detect_pds3(label: pdsparser.Pds3Label) -> tuple[str, str, None] | None:
    """Extract New Horizons LORRI metadata from a PDS3 label.

    Parameters:
        label: A parsed :class:`pdsparser.Pds3Label`.

    Returns:
        ``('NEW HORIZONS', 'LORRI', None)`` if the label identifies a New
        Horizons LORRI image, ``None`` otherwise.
    """
    try:
        d = label.as_dict()
        if d.get('INSTRUMENT_HOST_NAME') != 'NEW HORIZONS':
            return None
        if d.get('INSTRUMENT_ID') != 'LORRI':
            return None
        return ('NEW HORIZONS', 'LORRI', None)
    except (KeyError, TypeError):
        return None


def read_file(
    filename: str | os.PathLike[str] | pdsparser.Pds3Label,
    obj: ObjectSelector = None,
    **kwargs: Any,
) -> ReadResult | None:
    """Try to detect and read a New Horizons LORRI image from its PDS3 label.

    Parameters:
        filename: A parsed :class:`pdsparser.Pds3Label`. A bare file path
            is not a LORRI product here and yields ``None``.
        obj: Object selector forwarded to the PDS3 array reader.
        **kwargs: Accepted but ignored; LORRI files need no
            instrument-specific options.

    Returns:
        :class:`~picmaker._types.ReadResult` on success, ``None`` if the
        file is not recognized as a New Horizons LORRI image.
    """
    if not isinstance(filename, pdsparser.Pds3Label):
        return None
    filter_info = _detect_pds3(filename)
    if filter_info is None:
        return None
    array3d = _shared.read_pds3_image_array(filename, obj)
    return ReadResult(array3d, True, filter_info)


def matches(inst_host: str, inst_id: str) -> bool:
    """Predicate identifying the New Horizons LORRI camera.

    Both the host and the instrument id must agree.

    Parameters:
        inst_host: Instrument host string.
        inst_id: Instrument id (``'LORRI'``).

    Returns:
        ``True`` for a New Horizons host whose ``inst_id`` names the LORRI
        camera.
    """
    return inst_host in ('NEW HORIZONS', 'NH') and inst_id == 'LORRI'


def tint_for(inst_id: str, filter_name: Any) -> list[tuple[int, int, int]] | None:
    """Return the plain ``[black, white]`` colormap.

    LORRI is panchromatic and carries no filters, so there is nothing to
    tint: the colormap is always ``[(0, 0, 0), (255, 255, 255)]``,
    independent of ``inst_id`` and ``filter_name``.
    """
    return [(0, 0, 0), (255, 255, 255)]


__all__ = ['matches', 'read_file', 'tint_for']
