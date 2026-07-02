"""Mutable-default guards for picmaker's public API.

Options are now plain dicts produced by
:func:`picmaker.picmaker.validate_options`, not a ``PicmakerOptions`` dataclass.
Two of the surviving helpers take list-typed parameters
(:func:`picmaker.control.get_outfile`'s ``strip`` and
:func:`picmaker.control.get_filepaths`'s ``patterns``); both default to the
immutable ``None`` sentinel rather than a shared ``[]``, sidestepping the classic
Python footgun where a mutable default is mutated in place and leaks across calls.
"""

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

from picmaker.control import get_filepaths, get_outfile
from picmaker.parser import get_parser
from picmaker.picmaker import validate_options


def _default(func: Callable[..., Any], name: str) -> Any:
    sig = inspect.signature(func)
    return sig.parameters[name].default


def test_get_outfile_strip_default_is_none_sentinel(tmp_path: Path) -> None:
    """``get_outfile`` uses an immutable ``None`` default for ``strip`` (not a
    shared ``[]``), and still writes an output path when called with it."""
    assert _default(get_outfile, 'strip') is None
    infile = tmp_path / 'image.IMG'
    infile.write_bytes(b'')
    assert get_outfile(str(infile), outdir=str(tmp_path), extension='png')
    assert _default(get_outfile, 'strip') is None


def test_get_filepaths_patterns_default_is_none_sentinel(fixtures_dir: Path) -> None:
    """``get_filepaths`` uses an immutable ``None`` default for ``patterns`` (not
    a shared ``[]``), and still resolves inputs when called with it."""
    assert _default(get_filepaths, 'patterns') is None
    assert get_filepaths([str(fixtures_dir / 'cassini_iss.vic')])
    assert _default(get_filepaths, 'patterns') is None


def test_validate_options_returns_independent_dicts() -> None:
    """Each ``validate_options`` call yields its own option dict object."""
    a = validate_options(get_parser().parse_args([]))
    b = validate_options(get_parser().parse_args([]))
    assert a == b
    assert a is not b
    # Mutating one normalized dict does not bleed into a freshly built one.
    a['suffix'] = '_mutated'
    assert b['suffix'] == ''
