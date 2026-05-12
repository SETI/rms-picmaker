"""Instrument-specific detection and tint logic.

Each instrument module exposes a uniform 4-method protocol:

* ``detect_vicar(vic) -> tuple[str, str, str] | None`` — returns
  ``(inst_host, inst_id, filter_name)`` for a VICAR file or ``None`` if
  the instrument does not own this label.
* ``detect_fits(hdulist) -> tuple[str, str, str] | None`` — same for
  FITS.
* ``matches(inst_host, inst_id) -> bool`` — host-level predicate.
* ``tint_for(inst_id, filter_name) -> list[tuple[int, int, int]] | None``
  — returns the full colormap (NOT just the tint), or ``None`` for the
  HST unknown-wavelength case.
"""

from types import ModuleType
from typing import Any

from picmaker.instruments import cassini, galileo, hst, nh, voyager

#: Instrument modules whose ``detect_vicar`` may match a VICAR input.
VICAR_INSTRUMENTS: list[ModuleType] = [cassini, galileo, voyager]
#: Instrument modules whose ``detect_fits`` may match a FITS input.
FITS_INSTRUMENTS: list[ModuleType] = [hst, nh]
#: Every registered instrument module.
ALL_INSTRUMENTS: list[ModuleType] = [cassini, voyager, galileo, hst, nh]


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


__all__ = ['ALL_INSTRUMENTS', 'FITS_INSTRUMENTS', 'VICAR_INSTRUMENTS', 'lookup']
