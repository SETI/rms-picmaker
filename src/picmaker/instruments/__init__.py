"""Instrument-specific detection, file reading, and tint logic.

Each instrument module exposes a uniform protocol:

**Required methods:**

* ``read_file(filename, obj=None, **kwargs) -> ReadResult | None``
  — tries to detect and read *filename*; returns a
  :class:`~picmaker._types.ReadResult` on success or ``None`` if the
  file is not owned by this instrument. Instrument-specific options
  (the fields named in :data:`~picmaker.options.READ_FILE_KWARGS`,
  currently ``mosaic`` and ``pds3_label_method``) arrive via
  ``**kwargs``; any a given instrument does not use are ignored.
* ``matches(inst_host, inst_id) -> bool`` — predicate used by
  :func:`lookup` to find the instrument for tinting. It checks both the
  host and the instrument id, so a module is selected only for the
  specific camera(s) it handles (e.g. New Horizons MVIC and LORRI live in
  separate modules). HST is the exception: it serves every Hubble
  detector and so constrains the host only.
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

from picmaker.instruments import cassini_iss, galileo_ssi, hst, nh_lorri, nh_mvic, voyager_iss

#: Every registered instrument module, in cascade priority order.
#: :func:`read_one_image_array <picmaker.io.read_one_image_array>` tries
#: each instrument's ``read_file()`` in this order; the first to return
#: a non-``None`` result wins.
ALL_INSTRUMENTS: list[ModuleType] = [
    cassini_iss, voyager_iss, galileo_ssi, hst, nh_lorri, nh_mvic
]


def lookup(inst_host: str | None, inst_id: str | None) -> Any | None:
    """Return the first instrument whose ``matches()`` returns True, else None.

    Each instrument's ``matches()`` weighs both ``inst_host`` and
    ``inst_id``, so a host match alone is not enough: a recognized host
    paired with a sub-instrument the module does not handle (e.g. Cassini
    VIMS) returns ``None`` here rather than a mismatched module.

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
