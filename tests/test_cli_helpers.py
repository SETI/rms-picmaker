"""Direct unit tests for the module-private CLI helpers introduced by
the issue-#12 refactor.

The end-to-end coverage in :file:`test_cli.py` and :file:`test_cli_unit.py`
exercises :func:`picmaker.cli.main` through ``argparse`` / subprocess
entry points. These tests reach into the two new private helpers
(:func:`!_collect_option_dicts`, :func:`!_process_directory`) so each
phase of CLI processing has its own focused failure locator.
"""

import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from picmaker.cli import _build_parser, _collect_option_dicts, _process_directory

# ---------------------------------------------------------------------------
# _collect_option_dicts
# ---------------------------------------------------------------------------


def test_collect_option_dicts_no_versions_returns_single_dict() -> None:
    """Without ``--versions``, a single normalized option dict is returned."""
    parser = _build_parser()
    ns = parser.parse_args(['--gamma', '1.5'])

    out = _collect_option_dicts(parser, ns, replace='all', proceed=False)

    assert len(out) == 1
    assert out[0]['gamma'] == 1.5
    assert out[0]['replace'] == 'all'
    assert out[0]['proceed'] is False


def test_collect_option_dicts_versions_lines_each_produce_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each non-blank versions-file line produces one normalized dict.

    A blank line is skipped; the main CLI's ``--replace`` / ``--proceed``
    always override per-line values.
    """
    vfile = tmp_path / 'versions.txt'
    vfile.write_text(
        '--suffix=_v1 --extension=jpg\n'
        '\n'  # blank line, skipped
        '--suffix=_v2 --extension=tif --replace=none\n'
    )
    # The versions-file re-parse appends to sys.argv[1:], so simulate the
    # command-line shape the CLI uses when --versions is set.
    monkeypatch.setattr(sys, 'argv', ['picmaker', '--versions', str(vfile)])
    parser = _build_parser()
    ns = parser.parse_args(['--versions', str(vfile)])

    out = _collect_option_dicts(parser, ns, replace='all', proceed=True)

    assert len(out) == 2
    assert out[0]['suffix'] == '_v1'
    assert out[0]['extension'] == 'jpg'
    assert out[1]['suffix'] == '_v2'
    assert out[1]['extension'] == 'tif'
    # Main CLI's --replace overrides the per-line --replace=none.
    assert all(d['replace'] == 'all' for d in out)
    # Main CLI's --proceed propagates to every line.
    assert all(d['proceed'] is True for d in out)


def test_collect_option_dicts_versions_blank_file_returns_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A versions file with only blank lines returns an empty list."""
    vfile = tmp_path / 'versions.txt'
    vfile.write_text('\n\n   \n')
    monkeypatch.setattr(sys, 'argv', ['picmaker', '--versions', str(vfile)])
    parser = _build_parser()
    ns = parser.parse_args(['--versions', str(vfile)])

    out = _collect_option_dicts(parser, ns, replace='all', proceed=False)

    assert out == []


# ---------------------------------------------------------------------------
# _process_directory
# ---------------------------------------------------------------------------


def test_process_directory_non_recursive_writes_outputs(
    fixtures_dir: Path, tmp_path: Path, basic_option_dict: dict[str, Any],
) -> None:
    """Non-recursive mode processes the top-level directory only."""
    src = tmp_path / 'src'
    src.mkdir()
    shutil.copy(fixtures_dir / 'cassini_iss.vic', src / 'cassini_iss.vic')

    out_dir = tmp_path / 'out'
    # main() computes lcommon = len(common_prefix), which for a single
    # directory equals len(str(src)) — so dirpath[lcommon + 1:] is empty
    # and outputs go directly under directory.
    _process_directory(
        str(src),
        recursive=False,
        pattern='*.vic',
        directory=str(out_dir),
        lcommon=len(str(src)),
        movie=False,
        option_dicts=[basic_option_dict],
        verbose=0,
    )
    found = list(out_dir.rglob('cassini_iss.jpg'))
    assert found, f'expected cassini_iss.jpg under {out_dir}'


def test_process_directory_recursive_walks_subdirs(
    fixtures_dir: Path, tmp_path: Path, basic_option_dict: dict[str, Any],
) -> None:
    """Recursive mode walks subdirectories and mirrors the source tree
    under the output directory using ``lcommon``."""
    src_root = tmp_path / 'src'
    nested = src_root / 'nested'
    nested.mkdir(parents=True)
    shutil.copy(fixtures_dir / 'cassini_iss.vic', nested / 'cassini_iss.vic')

    out_dir = tmp_path / 'out'
    _process_directory(
        str(src_root),
        recursive=True,
        pattern='*.vic',
        directory=str(out_dir),
        # main() sets lcommon to len(common_prefix), which for one
        # directory equals len(str(src_root)). Then this_dir[lcommon+1:]
        # produces the per-subdir tail ('' for src_root, 'nested' for
        # src_root/nested).
        lcommon=len(str(src_root)),
        movie=False,
        option_dicts=[basic_option_dict],
        verbose=0,
    )
    # The mirrored output path keeps the 'nested' subdir under out_dir.
    assert (out_dir / 'nested' / 'cassini_iss.jpg').exists()


def test_process_directory_pattern_filters(
    fixtures_dir: Path, tmp_path: Path, basic_option_dict: dict[str, Any],
) -> None:
    """A narrow pattern skips non-matching files."""
    src = tmp_path / 'src'
    src.mkdir()
    shutil.copy(fixtures_dir / 'cassini_iss.vic', src / 'cassini_iss.vic')
    (src / 'README.txt').write_text('not an image')

    out_dir = tmp_path / 'out'
    _process_directory(
        str(src),
        recursive=False,
        pattern='*.vic',
        directory=str(out_dir),
        lcommon=len(str(src)),
        movie=False,
        option_dicts=[basic_option_dict],
        verbose=0,
    )
    # README.txt should not produce any output.
    assert not list(out_dir.rglob('*.txt'))
    assert list(out_dir.rglob('cassini_iss.jpg'))


def test_process_directory_no_match_is_noop(
    tmp_path: Path, basic_option_dict: dict[str, Any],
) -> None:
    """A directory with no matching files writes nothing (no crash)."""
    src = tmp_path / 'src'
    src.mkdir()
    (src / 'other.txt').write_text('x')

    out_dir = tmp_path / 'out'
    _process_directory(
        str(src),
        recursive=False,
        pattern='*.vic',
        directory=str(out_dir),
        lcommon=len(str(src)),
        movie=False,
        option_dicts=[basic_option_dict],
        verbose=0,
    )
    # No output directory needed; nothing got written.
    assert not out_dir.exists() or not any(out_dir.iterdir())


def test_process_directory_verbose_logs(
    fixtures_dir: Path, tmp_path: Path,
    basic_option_dict: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``verbose=1`` logs each visited directory through ``picmaker.cli``."""
    import logging

    src = tmp_path / 'src'
    src.mkdir()
    shutil.copy(fixtures_dir / 'cassini_iss.vic', src / 'cassini_iss.vic')

    out_dir = tmp_path / 'out'
    with caplog.at_level(logging.INFO, logger='picmaker.cli'):
        _process_directory(
            str(src),
            recursive=False,
            pattern='*.vic',
            directory=str(out_dir),
            lcommon=len(str(src)),
            movie=False,
            option_dicts=[basic_option_dict],
            verbose=1,
        )
    assert str(src) in caplog.text
