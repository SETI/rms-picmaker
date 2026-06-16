"""Shared type definitions for the reader cascade.

Defined here (rather than in :mod:`picmaker.io`) so that
:mod:`picmaker.instruments` sub-modules can import them without
creating a circular import with :mod:`picmaker.io`.
"""

from typing import Any, NamedTuple

from numpy.typing import NDArray

# Reader-cascade ``filter_info`` element: ``(inst_host, inst_id, filter_name)``
# or ``None``. The inner ``filter_name`` may be a 2-tuple for HST (see
# :mod:`picmaker.instruments.hst`), which keeps the static type as
# ``tuple[str, str, Any] | None`` rather than ``tuple[str, str, str] | None``.
FilterInfo = tuple[str, str, Any] | None

# Selector for multi-image files. FITS and PDS3 both accept an integer index
# or a pointer/HDU name; FITS additionally accepts a list/tuple of such
# selectors when stacking multiple HDUs into one 3-D array. Sequence is
# spelled out as list/tuple (not Sequence[...]) because ``str`` is itself
# a Sequence[str] and the runtime branches use ``isinstance(obj, (list,
# tuple))`` to discriminate.
ObjectSelector = int | str | list[int | str] | tuple[int | str, ...] | None


class ReadResult(NamedTuple):
    """Triple returned by the reader cascade.

    A :class:`typing.NamedTuple` so callers can use either positional
    unpacking (``array, up, info = read_one_image_array(...)``) or
    attribute access (``result.array3d``) interchangeably.
    """

    #: 3-D numpy array indexed ``(bands, lines, samples)``.
    array3d: NDArray[Any]
    #: True if the per-instrument default display orientation is upward
    #: (line numbers increase upward).
    default_is_up: bool
    #: ``(inst_host, inst_id, filter_name)`` or ``None`` if no registered
    #: instrument matched. ``filter_name`` is usually a string but is a
    #: 2-tuple for some HST conventions.
    filter_info: FilterInfo


__all__ = ['FilterInfo', 'ObjectSelector', 'ReadResult']
