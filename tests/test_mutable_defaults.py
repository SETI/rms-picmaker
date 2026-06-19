"""Mutable-default guards for picmaker's public API.

:class:`~picmaker.options.PicmakerOptions` uses ``field(default_factory=list)``
for ``strip`` and ``pointer`` so each instance gets its own empty list.
:func:`~picmaker.io.get_outfile` still defaults ``strip`` to ``None``.
"""

import inspect
from collections.abc import Callable
from typing import Any

from picmaker import get_outfile
from picmaker.options import PicmakerOptions


def _default(func: Callable[..., Any], name: str) -> Any:
    sig = inspect.signature(func)
    return sig.parameters[name].default


def test_picmaker_options_strip_default_is_empty_list() -> None:
    a, b = PicmakerOptions(), PicmakerOptions()
    assert a.strip == []
    assert a.strip is not b.strip


def test_picmaker_options_pointer_default_is_empty_list() -> None:
    a, b = PicmakerOptions(), PicmakerOptions()
    assert a.pointer == []
    assert a.pointer is not b.pointer


def test_get_outfile_strip_default_is_not_mutable() -> None:
    assert _default(get_outfile, 'strip') is None
