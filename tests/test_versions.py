"""Unit tests for :func:`picmaker.options.get_versions`.

``get_versions`` reads a ``--versions`` file and expands it into a list of
option dicts (one per non-blank line), layering each line's overrides onto the
base options. The returned dicts are *raw* — not validated or deconflicted (that
happens later, per version, inside ``picmaker``) — and the consumed ``versions``
and ``files`` keys are stripped. Lines are tokenized with ``str.split`` (not
``shlex``), and per-line ``--replace`` / ``--proceed`` values are preserved.
"""

from pathlib import Path
from typing import Any

from picmaker.options import (
    get_parser,
    get_versions,
    shift_to_zero_origin,
)


def _base(*args: str) -> dict[str, Any]:
    # Raw parsed options, as picmaker hands them to get_versions (unvalidated).
    options: dict[str, Any] = vars(get_parser().parse_args(list(args)))
    return options


def test_no_versions_returns_single_options_dict() -> None:
    """Without a ``--versions`` file a single option dict is returned."""
    base = _base('--gamma', '1.5')
    out = get_versions(**base)
    assert len(out) == 1
    assert out[0]['gamma'] == 1.5


def test_versions_none_returns_the_kwargs() -> None:
    """``versions=None`` returns a single deconflicted options dict built from
    the base options."""
    base = _base('--suffix', '_x')
    out = get_versions(**base)
    assert len(out) == 1
    assert out[0]['suffix'] == '_x'


def test_versions_lines_each_produce_one_dict(tmp_path: Path) -> None:
    """Each non-blank line yields one normalized dict; blank lines skip."""
    vfile = tmp_path / 'versions.txt'
    vfile.write_text(
        '--suffix=_v1 --extension=jpg\n'
        '\n'  # blank line, skipped
        '--suffix=_v2 --extension=tif --replace=none\n'
    )
    base = _base('in.vic')
    out = get_versions(**{**base, 'versions': str(vfile)})

    assert len(out) == 2
    assert out[0]['suffix'] == '_v1'
    assert out[0]['extension'] == 'jpg'
    assert out[1]['suffix'] == '_v2'
    assert out[1]['extension'] == 'tif'
    # Per-line --replace is preserved; raw dicts carry the parser default (None)
    # where a line does not set it.
    assert out[0]['replace'] is None
    assert out[1]['replace'] == 'none'


def test_versions_index_options_match_cli_origin(tmp_path: Path) -> None:
    """Index options are 1-based in a versions file exactly as on the command line.

    Regression for the origin-shift asymmetry: ``--obj 2`` must resolve to the same
    0-based value whether it is typed on the command line or written in a versions file,
    and a base ``--obj 1`` (0-based 0) inherited by an unrelated version line must survive
    expansion rather than being dropped.
    """
    # Command line: --obj 2 shifts to 0-based 1.
    cli = shift_to_zero_origin(_base('x.fits', '--obj', '2'))
    assert cli['obj'] == 1

    # The same flag in a versions file lands on the same 0-based value.
    vfile = tmp_path / 'versions.txt'
    vfile.write_text('--obj 2 --suffix _b\n')
    base = _base('x.fits', '--versions', str(vfile))
    (from_file,) = [shift_to_zero_origin(o) for o in get_versions(**base)]
    assert from_file['obj'] == cli['obj'] == 1

    # A base --obj 1 (0-based 0) inherited by a version line without --obj is preserved.
    vfile2 = tmp_path / 'versions2.txt'
    vfile2.write_text('--suffix _a\n')
    base2 = _base('x.fits', '--obj', '1', '--versions', str(vfile2))
    (inherited,) = [shift_to_zero_origin(o) for o in get_versions(**base2)]
    assert inherited['obj'] == 0


def test_versions_blank_file_falls_back_to_base(tmp_path: Path) -> None:
    """A versions file with only blank lines falls back to a single run with
    the base options (the ``versions`` key is consumed, not passed through)."""
    vfile = tmp_path / 'versions.txt'
    vfile.write_text('\n\n   \n')
    base = _base('in.vic')
    out = get_versions(**{**base, 'versions': str(vfile)})
    # One fallback run: the raw base options with the consumed 'versions' and
    # 'files' keys stripped (get_versions absorbs both).
    expected = {k: v for k, v in base.items() if k not in ('versions', 'files')}
    assert out == [expected]
