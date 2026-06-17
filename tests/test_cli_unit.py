"""In-process unit tests for ``picmaker.cli`` internals.

The subprocess-based tests in :mod:`tests.test_cli` cover the
end-to-end CLI contract (exit codes, ``--help`` baseline, ``--versions``).
These tests exercise the private helpers directly so the coverage tool
counts them and so each validation rule has a focused assertion that
fails with a clear locator.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import pytest

from picmaker.cli import (
    _build_parser,
    _normalize_and_validate,
    _separate_files_and_dirs,
    main,
)

# ---------------------------------------------------------------------------
# _build_parser
# ---------------------------------------------------------------------------


def test_build_parser_returns_argument_parser() -> None:
    """``_build_parser`` returns an :class:`argparse.ArgumentParser`."""
    parser = _build_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_build_parser_parses_empty_args() -> None:
    """The parser succeeds on an empty argv (no positionals required)."""
    parser = _build_parser()
    ns = parser.parse_args([])
    assert ns.files == []
    assert ns.directory is None
    assert ns.recursive is False
    assert ns.pattern == '*'
    assert ns.replace == 'all'
    assert ns.gamma == 1.0
    assert ns.extension is None
    assert ns.percentiles == (0.0, 100.0)


def test_build_parser_parses_typical_args() -> None:
    """A typical invocation binds every documented dest."""
    parser = _build_parser()
    ns = parser.parse_args([
        '--directory', '/tmp/out',
        '--pattern', '*.IMG',
        '--quality', '90',
        '--gamma', '2.0',
        '--rotate', 'rot90',
        '--filter', 'sharpen',
        '--tint',
        'in.vic',
    ])
    assert ns.directory == '/tmp/out'
    assert ns.pattern == '*.IMG'
    assert ns.quality == 90
    assert ns.gamma == 2.0
    assert ns.rotate == 'rot90'
    assert ns.filter_name == 'sharpen'
    assert ns.tint is True
    assert ns.files == ['in.vic']


def test_build_parser_underscore_aliases() -> None:
    """``--alt_strip`` / ``--alt_pointer`` / ``--frame_max`` / ``--gapsize``
    underscore aliases bind to the same dests as the hyphenated forms.
    """
    parser = _build_parser()
    ns = parser.parse_args([
        '--alt_strip', '.IMG',
        '--alt_pointer', 'IMAGE_2',
        '--frame_max', '50',
        '--gapsize', '3',
        '--gapcolor', 'red',
        '--trimzeros',
    ])
    assert ns.alt_strip == '.IMG'
    assert ns.alt_pointer == 'IMAGE_2'
    assert ns.frame_max == 50
    assert ns.gap_size == 3
    assert ns.gap_color == 'red'
    assert ns.trim_zeros is True


def test_build_parser_rejects_bad_choice() -> None:
    """An unknown ``--rotate`` value triggers argparse's ``SystemExit``."""
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(['--rotate', 'tumble'])


# ---------------------------------------------------------------------------
# _separate_files_and_dirs
# ---------------------------------------------------------------------------


def test_separate_files_and_dirs_splits_paths(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """Existing files go into the file list; everything else goes into
    the directory list (trailing slashes stripped).
    """
    existing_file = str(fixtures_dir / 'cassini_iss.vic')
    nonexistent = str(tmp_path / 'missing')
    dir_with_slash = str(tmp_path) + '/'

    files, dirs = _separate_files_and_dirs(
        [existing_file, nonexistent, dir_with_slash]
    )
    assert files == [existing_file]
    assert dirs == [nonexistent, str(tmp_path)]


def test_separate_files_and_dirs_empty() -> None:
    """An empty input yields two empty lists."""
    files, dirs = _separate_files_and_dirs([])
    assert files == []
    assert dirs == []


# ---------------------------------------------------------------------------
# _normalize_and_validate — mutex checks
# ---------------------------------------------------------------------------


def _parse(*args: str) -> argparse.Namespace:
    return _build_parser().parse_args(list(args))


def test_normalize_mosaic_band_incompatible() -> None:
    """``--mosaic`` rejects ``--band``."""
    ns = _parse('--mosaic', '--band', '0')
    with pytest.raises(ValueError, match='mosaic and band'):
        _normalize_and_validate(ns, 'all', False)


def test_normalize_mosaic_bands_incompatible() -> None:
    """``--mosaic`` rejects ``--bands``."""
    ns = _parse('--mosaic', '--bands', '0', '1')
    with pytest.raises(ValueError, match='mosaic and band'):
        _normalize_and_validate(ns, 'all', False)


def test_normalize_band_bands_mismatch_rejected() -> None:
    """``--band`` and ``--bands`` with mismatched endpoints conflict."""
    ns = _parse('--band', '2', '--bands', '0', '1')
    with pytest.raises(ValueError, match='band and bands'):
        _normalize_and_validate(ns, 'all', False)


def test_normalize_band_bands_aligned_ok() -> None:
    """``--band B`` plus ``--bands B B`` is accepted."""
    ns = _parse('--band', '3', '--bands', '3', '3')
    out = _normalize_and_validate(ns, 'all', False)
    # argparse nargs=2 produces a list; the check passes when the
    # endpoints match.
    assert list(out['bands']) == [3, 3]


def test_normalize_mosaic_movie_incompatible() -> None:
    """``--mosaic`` rejects ``--movie``."""
    ns = _parse('--mosaic', '--movie')
    with pytest.raises(ValueError, match='mosaic and movie'):
        _normalize_and_validate(ns, 'all', False)


def test_normalize_scale_wscale_incompatible() -> None:
    """``--scale`` and ``--wscale`` conflict."""
    ns = _parse('--scale', '50', '--wscale', '75')
    with pytest.raises(ValueError, match='scale and wscale'):
        _normalize_and_validate(ns, 'all', False)


def test_normalize_scale_hscale_incompatible() -> None:
    """``--scale`` and ``--hscale`` conflict."""
    ns = _parse('--scale', '50', '--hscale', '75')
    with pytest.raises(ValueError, match='scale and hscale'):
        _normalize_and_validate(ns, 'all', False)


def test_normalize_frame_size_incompatible() -> None:
    """``--frame`` and ``--size`` conflict."""
    ns = _parse('--frame', '100', '100', '--size', '50', '50')
    with pytest.raises(ValueError, match='frame and size'):
        _normalize_and_validate(ns, 'all', False)


def test_normalize_overlap_overlaps_incompatible() -> None:
    """``--overlap`` and ``--overlaps`` conflict."""
    ns = _parse('--overlap', '5', '--overlaps', '5', '10')
    with pytest.raises(ValueError, match='overlap and overlaps'):
        _normalize_and_validate(ns, 'all', False)


def test_normalize_up_down_incompatible() -> None:
    """``--up`` and ``--down`` conflict."""
    ns = _parse('--up', '--down')
    with pytest.raises(ValueError, match='--up and --down'):
        _normalize_and_validate(ns, 'all', False)


def test_normalize_twobytes_non_tiff_rejected() -> None:
    """``--16`` plus a non-TIFF extension is rejected."""
    ns = _parse('--16', '--extension', 'jpg')
    with pytest.raises(ValueError, match='16-bit mode'):
        _normalize_and_validate(ns, 'all', False)


def test_normalize_twobytes_filter_rejected() -> None:
    """``--16`` plus ``--filter`` is rejected."""
    ns = _parse('--16', '--extension', 'tiff', '--filter', 'sharpen')
    with pytest.raises(ValueError, match='16-bit filter'):
        _normalize_and_validate(ns, 'all', False)


def test_normalize_twobytes_with_tiff_ok() -> None:
    """``--16 --extension tif`` is accepted (tif prefix matches)."""
    ns = _parse('--16', '--extension', 'tif')
    out = _normalize_and_validate(ns, 'all', False)
    assert out['twobytes'] is True


# ---------------------------------------------------------------------------
# _normalize_and_validate — shape/value normalization
# ---------------------------------------------------------------------------


def test_normalize_rectangle_converts_to_slices() -> None:
    """``--rectangle s1 l1 s2 l2`` becomes sorted half-open
    ``samples`` / ``lines`` pairs.
    """
    ns = _parse('--rectangle', '10', '20', '5', '25')
    out = _normalize_and_validate(ns, 'all', False)
    # rectangle = (s1=10, l1=20, s2=5, l2=25)
    # samples: sorted([s1-1, s2]) = sorted([9, 5]) = [5, 9]
    # lines:   sorted([l1-1, l2]) = sorted([19, 25]) = [19, 25]
    assert out['samples'] == [5, 9]
    assert out['lines'] == [19, 25]


def test_normalize_scale_defaults_propagate() -> None:
    """When ``--scale`` is given, ``--wscale`` / ``--hscale`` default to it."""
    ns = _parse('--scale', '75')
    out = _normalize_and_validate(ns, 'all', False)
    assert out['scale'] == (75.0, 75.0)


def test_normalize_wscale_only() -> None:
    """``--wscale`` alone leaves the height scale at 100."""
    ns = _parse('--wscale', '50')
    out = _normalize_and_validate(ns, 'all', False)
    assert out['scale'] == (50.0, 100.0)


def test_normalize_percentiles_sorted() -> None:
    """``--percentiles`` is sorted ascending."""
    ns = _parse('--percentiles', '95', '5')
    out = _normalize_and_validate(ns, 'all', False)
    assert out['percentiles'] == (5.0, 95.0)


def test_normalize_limits_sorted() -> None:
    """``--limits`` is sorted ascending."""
    ns = _parse('--limits', '200', '50')
    out = _normalize_and_validate(ns, 'all', False)
    assert out['limits'] == (50.0, 200.0)


def test_normalize_valid_sorted() -> None:
    """``--valid`` is sorted ascending."""
    ns = _parse('--valid', '999', '1')
    out = _normalize_and_validate(ns, 'all', False)
    assert out['valid'] == (1.0, 999.0)


def test_normalize_alt_pointer_becomes_list() -> None:
    """``--alt-pointer`` produces a 2-element pointer list."""
    ns = _parse('--pointer', 'IMAGE', '--alt-pointer', 'IMAGE_2')
    out = _normalize_and_validate(ns, 'all', False)
    assert out['pointer'] == ['IMAGE', 'IMAGE_2']


def test_normalize_alt_strip_becomes_list() -> None:
    """``--alt-strip`` produces a 2-element strip list."""
    ns = _parse('--strip', '.IMG', '--alt-strip', '.LBL')
    out = _normalize_and_validate(ns, 'all', False)
    assert out['strip'] == ['.IMG', '.LBL']


def test_normalize_overlap_to_overlaps() -> None:
    """A single ``--overlap N`` is mirrored into the overlaps pair."""
    ns = _parse('--overlap', '7')
    out = _normalize_and_validate(ns, 'all', False)
    assert out['overlap'] == (7.0, 7.0)


def test_normalize_overlap_default_zero() -> None:
    """No overlap option means ``(0, 0)``."""
    ns = _parse()
    out = _normalize_and_validate(ns, 'all', False)
    assert out['overlap'] == (0.0, 0.0)


def test_normalize_mosaic_skips_band_default() -> None:
    """``--mosaic`` mode leaves the band fields untouched (``None``)."""
    ns = _parse('--mosaic')
    out = _normalize_and_validate(ns, 'all', False)
    assert out['bands'] is None


def test_normalize_filter_and_rotate_lowercased() -> None:
    """``--filter`` and ``--rotate`` are normalised to lowercase."""
    ns = _parse('--filter', 'SHARPEN', '--rotate', 'ROT90')
    out = _normalize_and_validate(ns, 'all', False)
    assert out['filter_name'] == 'sharpen'
    assert out['rotate'] == 'rot90'


def test_normalize_pds3_label_method_default_is_strict() -> None:
    """``--pds3-label-method`` defaults to ``'strict'``."""
    ns = _parse()
    out = _normalize_and_validate(ns, 'all', False)
    assert out['pds3_label_method'] == 'strict'


@pytest.mark.parametrize('method', ['strict', 'loose', 'compound', 'fast'])
def test_normalize_pds3_label_method_accepts_each_choice(method: str) -> None:
    """Each documented ``--pds3-label-method`` value passes through to
    the option dict."""
    ns = _parse('--pds3-label-method', method)
    out = _normalize_and_validate(ns, 'all', False)
    assert out['pds3_label_method'] == method


def test_normalize_pds3_label_method_rejects_unknown() -> None:
    """An unknown ``--pds3-label-method`` value is rejected by argparse
    before normalization runs."""
    with pytest.raises(SystemExit):
        _parse('--pds3-label-method', 'turbo')


# ---------------------------------------------------------------------------
# main() — orchestration paths
# ---------------------------------------------------------------------------


def test_main_no_args_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """``picmaker`` with no positionals is a no-op (no exception)."""
    monkeypatch.setattr(sys, 'argv', ['picmaker'])
    # main() returns None on success; no SystemExit when there's nothing to do.
    main()


def test_main_movie_versions_mutex(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--movie`` + ``--versions`` is rejected with exit code 1."""
    monkeypatch.setattr(sys, 'argv', ['picmaker', '--movie', '--versions', 'x'])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1


def test_main_bad_verbose_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--verbose 5`` is rejected."""
    monkeypatch.setattr(sys, 'argv', ['picmaker', '--verbose', '5'])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1


def test_main_bad_replace_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--replace garbage`` is rejected."""
    monkeypatch.setattr(sys, 'argv', ['picmaker', '--replace', 'garbage'])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1


def test_main_processes_single_file(
    monkeypatch: pytest.MonkeyPatch, fixtures_dir: Path, tmp_path: Path
) -> None:
    """A single VICAR fixture passes through main() and produces a JPEG."""
    monkeypatch.setattr(sys, 'argv', [
        'picmaker',
        '--directory', str(tmp_path),
        '--replace', 'all',
        str(fixtures_dir / 'cassini_iss.vic'),
    ])
    main()
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_main_directory_pattern(
    monkeypatch: pytest.MonkeyPatch, fixtures_dir: Path, tmp_path: Path
) -> None:
    """A directory plus a narrow ``--pattern`` processes the match."""
    # Use a sub-directory with a narrow pattern so we don't trip on the
    # corrupt_vicar.vic fixture used by the read-failure tests.
    src = tmp_path / 'src'
    src.mkdir()
    import shutil
    shutil.copy(fixtures_dir / 'cassini_iss.vic', src / 'cassini_iss.vic')

    out_dir = tmp_path / 'out'
    monkeypatch.setattr(sys, 'argv', [
        'picmaker',
        '--directory', str(out_dir),
        '--pattern', '*.vic',
        '--replace', 'all',
        str(src),
    ])
    main()
    found = list(out_dir.rglob('cassini_iss.jpg'))
    assert found, f'expected cassini_iss.jpg under {out_dir}'


def test_main_recursive_directory(
    monkeypatch: pytest.MonkeyPatch, fixtures_dir: Path, tmp_path: Path
) -> None:
    """``-r`` plus a parent directory walks subdirs."""
    src = tmp_path / 'src' / 'nested'
    src.mkdir(parents=True)
    import shutil
    shutil.copy(fixtures_dir / 'cassini_iss.vic', src / 'cassini_iss.vic')

    out_dir = tmp_path / 'out'
    monkeypatch.setattr(sys, 'argv', [
        'picmaker',
        '--directory', str(out_dir),
        '--recursive',
        '--pattern', '*.vic',
        '--replace', 'all',
        str(tmp_path / 'src'),
    ])
    main()
    found = list(out_dir.rglob('cassini_iss.jpg'))
    assert found, f'expected cassini_iss.jpg under {out_dir}'


def test_main_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    """``KeyboardInterrupt`` from the parser surfaces as ``sys.exit(2)``."""

    def kb(*_a: Any, **_kw: Any) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(sys, 'argv', ['picmaker'])
    monkeypatch.setattr('picmaker.cli._build_parser', kb)
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2
