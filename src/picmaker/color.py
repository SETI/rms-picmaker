"""Mission-agnostic colormap dispatch.

:func:`tinted_colormap` takes a ``(host, instrument, filter)`` triple
from the I/O cascade and returns a per-filter colormap (or ``None``).
The mission-specific logic lives in :mod:`picmaker.instruments`; this
module's only job is to normalize the filter description and forward
to :func:`picmaker.instruments.lookup`.

The wavelength → RGB constants ``RGB_BY_NM``, ``RFUNC``, ``GFUNC``, and
``BFUNC`` are surfaced here as well as on :mod:`picmaker._rgb`, so that
``from picmaker.color import RGB_BY_NM`` is a single short import.
"""


from typing import Any

from picmaker import instruments
from picmaker._rgb import BFUNC, GFUNC, RFUNC, RGB_BY_NM


def tinted_colormap(filter_info: Any) -> list[tuple[int, int, int]] | None:
    """Return a colormap based on filter info.

    Parameters:
        filter_info: A tuple ``(instrument_host, instrument_id, filter)``,
            where ``filter`` may be a single name or a 2-tuple of names
            (e.g. HST/ACS).

    Returns:
        A colormap as a list of ``(R, G, B)`` tuples (typically
        ``[black, tint, white]``), or ``None`` if no colormap can be
        derived.
    """
    if filter_info is None:
        return None

    (inst_host, inst_id, filter_name) = filter_info
    if filter_name is None:
        return None

    # CL1/CL2/CLEAR*/N/A normalization for two-tuple filters (HST/ACS,
    # WFPC2): if either side is a "clear" marker, drop it; if both are
    # clear, the colormap is plain black-white.
    if isinstance(filter_name, tuple):
        (filter1, filter2) = filter_name
        if filter1.startswith('CLEAR') or filter1 == 'CL1' or filter1 == 'N/A':
            filter1 = 'CLEAR'
        if filter2.startswith('CLEAR') or filter2 == 'CL2' or filter2 == 'N/A':
            filter2 = 'CLEAR'
        if filter1 == 'CLEAR':
            filter_name = filter2
        elif filter2 == 'CLEAR':
            filter_name = filter1
        else:
            filter_name = filter1 + '+' + filter2

    if filter_name == 'CLEAR':
        return [(0, 0, 0), (255, 255, 255)]

    if inst_host is None:
        return None

    instrument = instruments.lookup(inst_host, inst_id)
    if instrument is None:
        return None

    result: list[tuple[int, int, int]] | None = instrument.tint_for(
        inst_id or '', filter_name
    )
    return result


__all__ = ['BFUNC', 'GFUNC', 'RFUNC', 'RGB_BY_NM', 'tinted_colormap']
