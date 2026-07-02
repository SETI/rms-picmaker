"""Mutable-default guards for picmaker's public API.

Options are now plain dicts produced by
:func:`picmaker.picmaker.validate_options`, not a ``PicmakerOptions`` dataclass.
Two of the surviving helpers still declare list-typed *default arguments*
(:func:`picmaker.control.get_outfile`'s ``strip`` and
:func:`picmaker.control.get_filepaths`'s ``patterns``). These guard against the
classic Python footgun where a shared mutable default is mutated in place and
leaks state across calls.
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


def test_get_outfile_strip_default_not_mutated(tmp_path: Path) -> None:
    """``get_outfile`` must not mutate its shared ``strip`` default list."""
    before = _default(get_outfile, 'strip')
    assert before == []
    infile = tmp_path / 'image.IMG'
    infile.write_bytes(b'')
    get_outfile(str(infile), outdir=str(tmp_path), extension='png')
    after = _default(get_outfile, 'strip')
    assert after == []
    assert after is before


def test_get_filepaths_patterns_default_not_mutated(fixtures_dir: Path) -> None:
    """``get_filepaths`` must not mutate its shared ``patterns`` default list."""
    before = _default(get_filepaths, 'patterns')
    assert before == []
    get_filepaths([str(fixtures_dir / 'cassini_iss.vic')])
    after = _default(get_filepaths, 'patterns')
    assert after == []
    assert after is before


def test_validate_options_returns_independent_dicts() -> None:
    """Each ``validate_options`` call yields its own option dict object."""
    a = validate_options(get_parser().parse_args([]))
    b = validate_options(get_parser().parse_args([]))
    assert a == b
    assert a is not b
    # Mutating one normalized dict does not bleed into a freshly built one.
    a['suffix'] = '_mutated'
    assert b['suffix'] == ''
