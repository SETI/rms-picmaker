"""Unit tests for :func:`picmaker.options.get_versions`.

``get_versions`` reads a ``--versions`` file and expands it into a list of
fully-normalized, deconflicted option dicts (one per non-blank line). Note:
lines are tokenized with ``str.split`` (not ``shlex``), and per-line
``--replace`` / ``--proceed`` values are preserved rather than overridden by a
top-level value.
"""

from pathlib import Path
from typing import Any

from picmaker.options import (
    deconflict_options,
    get_parser,
    get_versions,
    validate_options,
)


def _base(*args: str) -> dict[str, Any]:
    options: dict[str, Any] = validate_options(get_parser().parse_args(list(args)))
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
    # Per-line --replace is preserved, not overridden by the base value.
    assert out[0]['replace'] == 'all'
    assert out[1]['replace'] == 'none'


def test_versions_blank_file_falls_back_to_base(tmp_path: Path) -> None:
    """A versions file with only blank lines falls back to a single run with
    the base options (the ``versions`` key is consumed, not passed through)."""
    vfile = tmp_path / 'versions.txt'
    vfile.write_text('\n\n   \n')
    base = _base('in.vic')
    out = get_versions(**{**base, 'versions': str(vfile)})
    # One fallback run: the base options, deconflicted, with the consumed
    # 'versions' key removed.
    expected = deconflict_options({k: v for k, v in base.items() if k != 'versions'})
    assert out == [expected]
