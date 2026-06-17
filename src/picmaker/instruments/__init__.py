"""Instrument-specific detection, file reading, and tint logic.

Each instrument module exposes a uniform protocol:

**Required methods:**

* ``read_file(filename, obj, *, mosaic, pds3_label_method) -> ReadResult | None``
  — tries to detect and read *filename*; returns a
  :class:`~picmaker._types.ReadResult` on success or ``None`` if the
  file is not owned by this instrument.
* ``matches(inst_host, inst_id) -> bool`` — host-level predicate used
  by :func:`lookup` to find the instrument for tinting.
* ``tint_for(inst_id, filter_name) -> list[tuple[int, int, int]] | None``
  — returns the full colormap (NOT just the tint), or ``None`` for the
  HST unknown-wavelength case.

**Optional methods (checked via** ``hasattr`` **):**

* ``apply_tint(array3d, filter_info, options) -> NDArray | None`` —
  custom colorization; called only under ``--tint``; return a
  ``(H, W, C)`` RGB array to replace the standard colormap pipeline,
  or ``None`` to fall through.
* ``apply_mosaic(array3d, filter_info, options, *, default_is_up, colormap,
  imagefile) -> NDArray | None`` — multi-detector array assembly; called only
  under ``--mosaic``; return the assembled ``(H, W, C)`` array, or ``None``
  to fall through to the standard ``_band_to_rgb`` path.
"""

from types import ModuleType
from typing import Any

from picmaker.instruments import cassini_iss, galileo_ssi, hst, nh_lorri, voyager_iss

#: Every registered instrument module, in cascade priority order.
#: :func:`read_one_image_array <picmaker.io.read_one_image_array>` tries
#: each instrument's ``read_file()`` in this order; the first to return
#: a non-``None`` result wins.
ALL_INSTRUMENTS: list[ModuleType] = [cassini_iss, voyager_iss, galileo_ssi, hst, nh_lorri]


def lookup(inst_host: str | None, inst_id: str | None) -> Any | None:
    """Return the first instrument whose ``matches()`` returns True, else None.

    Parameters:
        inst_host: Instrument host string (e.g. ``'CASSINI ORBITER'``).
        inst_id: Instrument id (e.g. ``'ISS'``). Pass ``None`` if unknown.

    Returns:
        The matching instrument module, or ``None`` if no instrument
        matches.
    """
    if inst_host is None:
        return None
    inst_id_safe = inst_id or ''
    for inst in ALL_INSTRUMENTS:
        if inst.matches(inst_host, inst_id_safe):
            return inst
    return None


__all__ = ['ALL_INSTRUMENTS', 'lookup']
