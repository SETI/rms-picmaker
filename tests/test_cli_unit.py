"""In-process unit tests for the picmaker CLI internals.

The subprocess-based tests in :mod:`tests.test_cli` cover the
end-to-end CLI contract (exit codes, ``--help`` baseline, ``--versions``).
These tests exercise the ``get_parser()`` factory (:mod:`picmaker.parser`) and
the option-validation and file-discovery helpers directly so the coverage tool
counts them and so each validation rule has a focused assertion that fails with
a clear locator.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import pytest

from picmaker.control import get_filepaths
from picmaker.instruments import DEFAULT_PDS3_METHOD, PDS3_METHODS
from picmaker.main import main
from picmaker.parser import get_parser
from picmaker.picmaker import validate_options

# ---------------------------------------------------------------------------
# get_parser
# ---------------------------------------------------------------------------


def test_parser_is_argument_parser() -> None:
    """``get_parser()`` returns an :class:`argparse.ArgumentParser`."""
    assert isinstance(get_parser(), argparse.ArgumentParser)


def test_parser_parses_empty_args() -> None:
    """The parser succeeds on an empty argv (no positionals required)."""
    ns = get_parser().parse_args([])
    assert ns.files == []
    assert ns.directory is None
    assert ns.recursive is False
    assert ns.patterns == []
    assert ns.replace == 'all'
    assert ns.gamma == 1.0
    assert ns.extension is None
    assert ns.percentiles == (0.0, 100.0)
    assert ns.pds3_method == DEFAULT_PDS3_METHOD


def test_parser_parses_typical_args() -> None:
    """A typical invocation binds every documented dest."""
    ns = get_parser().parse_args([
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
    assert ns.patterns == ['*.IMG']
    assert ns.quality == 90
    assert ns.gamma == 2.0
    assert ns.rotate == 'rot90'
    assert ns.filter == 'sharpen'
    assert ns.tint is True
    assert ns.files == ['in.vic']


def test_parser_pointer_is_list() -> None:
    """``--pointer`` accepts one or more values into a list."""
    ns = get_parser().parse_args(['--pointer', 'IMAGE', 'IMAGE_2'])
    assert ns.pointers == ['IMAGE', 'IMAGE_2']


def test_parser_lines_and_samples() -> None:
    """``--lines`` / ``--samples`` each take a pair of ints."""
    ns = get_parser().parse_args(['--lines', '10', '20', '--samples', '5', '25'])
    assert ns.lines == [10, 20]
    assert ns.samples == [5, 25]


def test_parser_rejects_bad_choice() -> None:
    """An unknown ``--rotate`` value triggers argparse's ``SystemExit``."""
    with pytest.raises(SystemExit):
        get_parser().parse_args(['--rotate', 'tumble'])


# ---------------------------------------------------------------------------
# get_filepaths  (file / directory discovery)
# ---------------------------------------------------------------------------


def test_get_filepaths_single_file(fixtures_dir: Path) -> None:
    """An existing file yields one ``(filepath, output-dir)`` pair whose
    output directory defaults to the file's parent."""
    fx = fixtures_dir / 'cassini_iss.vic'
    result = get_filepaths([str(fx)])
    assert result == [(fx, fx.parent)]


def test_get_filepaths_directory_override(fixtures_dir: Path) -> None:
    """An explicit ``directory`` becomes the output dir for a plain file."""
    fx = fixtures_dir / 'cassini_iss.vic'
    result = get_filepaths([str(fx)], directory='/tmp/out')
    assert result == [(fx, Path('/tmp/out'))]


def test_get_filepaths_missing_raises(tmp_path: Path) -> None:
    """A nonexistent path raises :class:`FileNotFoundError`."""
    with pytest.raises(FileNotFoundError, match='No such file'):
        get_filepaths([str(tmp_path / 'missing.IMG')])


def test_get_filepaths_empty() -> None:
    """An empty input yields an empty list."""
    assert get_filepaths([]) == []


# ---------------------------------------------------------------------------
# validate_options — mutex checks
# ---------------------------------------------------------------------------


def _vo(*args: str) -> dict[str, Any]:
    return validate_options(get_parser().parse_args(list(args)))


def test_validate_band_bands_incompatible() -> None:
    """``--band`` and ``--bands`` with mismatched endpoints conflict."""
    with pytest.raises(ValueError, match='--band and --bands'):
        _vo('--band', '2', '--bands', '0', '1')


def test_validate_scale_wscale_incompatible() -> None:
    """``--scale`` and ``--wscale`` conflict."""
    with pytest.raises(ValueError, match='--scale and --wscale'):
        _vo('--scale', '50', '--wscale', '75')


def test_validate_scale_hscale_incompatible() -> None:
    """``--scale`` and ``--hscale`` conflict."""
    with pytest.raises(ValueError, match='--scale and --hscale'):
        _vo('--scale', '50', '--hscale', '75')


def test_validate_up_down_incompatible() -> None:
    """``--up`` and ``--down`` conflict."""
    with pytest.raises(ValueError, match='--up and --down'):
        _vo('--up', '--down')


def test_validate_frame_size_incompatible() -> None:
    """``--frame`` and ``--size`` conflict."""
    with pytest.raises(ValueError, match='--frame and --size'):
        _vo('--frame', '100', '100', '--size', '50', '50')


def test_validate_overlap_overlaps_incompatible() -> None:
    """``--overlap`` and ``--overlaps`` conflict."""
    with pytest.raises(ValueError, match='--overlap and --overlaps'):
        _vo('--overlap', '5', '--overlaps', '5', '10')


def test_validate_twobytes_non_tiff_rejected() -> None:
    """``--16`` plus a non-TIFF extension is rejected."""
    with pytest.raises(ValueError, match='16-bit mode'):
        _vo('--16', '--extension', 'jpg')


def test_validate_bad_extension_rejected() -> None:
    """An unrecognized ``--extension`` is rejected."""
    # argparse enforces --extension choices, so feed a dict directly to reach
    # the validate_options guard.
    with pytest.raises(ValueError, match='unrecognized --extension'):
        validate_options({'extension': 'xyz'})


# ---------------------------------------------------------------------------
# validate_options — shape / value normalization
# ---------------------------------------------------------------------------


def test_validate_twobytes_with_tiff_ok() -> None:
    """``--16 --extension tif`` is accepted (tif matches)."""
    out = _vo('--16', '--extension', 'tif')
    assert out['twobytes'] is True


def test_validate_band_becomes_bands_pair() -> None:
    """``--band B`` is expanded into a ``(B, B)`` bands pair."""
    out = _vo('--band', '3')
    assert out['bands'] == (3, 3)


def test_validate_scale_defaults_propagate() -> None:
    """When ``--scale`` is given, ``wscale`` / ``hscale`` default to it."""
    out = _vo('--scale', '75')
    assert out['scale'] == (75.0, 75.0)


def test_validate_wscale_only() -> None:
    """``--wscale`` alone leaves the height scale at 100."""
    out = _vo('--wscale', '50')
    assert out['scale'] == (50.0, 100.0)


def test_validate_overlap_to_overlaps() -> None:
    """A single ``--overlap N`` is mirrored into the overlaps pair."""
    out = _vo('--overlap', '7')
    assert out['overlaps'] == (7.0, 7.0)


def test_validate_overlap_default_zero() -> None:
    """No overlap option means ``(0, 0)``."""
    out = _vo()
    assert out['overlaps'] == (0.0, 0.0)


def test_validate_down_sets_display_upward_false() -> None:
    """``--down`` sets ``display_upward`` to ``False``."""
    out = _vo('--down')
    assert out['display_upward'] is False


def test_validate_no_band_leaves_bands_none() -> None:
    """Without ``--band`` / ``--bands`` the bands field stays ``None``."""
    out = _vo()
    assert out['bands'] is None


def test_validate_pds3_method_default_is_fast() -> None:
    """``--pds3-method`` defaults to ``'fast'``."""
    out = _vo()
    assert out['pds3_method'] == DEFAULT_PDS3_METHOD


@pytest.mark.parametrize('method', PDS3_METHODS)
def test_validate_pds3_method_accepts_each_choice(method: str) -> None:
    """Each documented ``--pds3-method`` value passes through."""
    out = _vo('--pds3-method', method)
    assert out['pds3_method'] == method


def test_validate_pds3_method_rejects_unknown() -> None:
    """An unknown ``--pds3-method`` value is rejected by argparse."""
    with pytest.raises(SystemExit):
        _vo('--pds3-method', 'turbo')


def test_validate_movie_versions_incompatible(fixtures_dir: Path) -> None:
    """``--movie`` + ``--versions`` is rejected."""
    versions = str(fixtures_dir / 'two_versions.txt')
    with pytest.raises(ValueError, match='--movie and --versions'):
        _vo('--movie', '--versions', versions)


# ---------------------------------------------------------------------------
# main() — orchestration paths
# ---------------------------------------------------------------------------


def test_main_no_args_exits_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """``picmaker`` with no positionals exits 1 (no input files)."""
    monkeypatch.setattr(sys, 'argv', ['picmaker'])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1


def test_main_movie_versions_mutex(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--movie`` + ``--versions`` raises before the pipeline runs."""
    monkeypatch.setattr(
        sys, 'argv', ['picmaker', '--movie', '--versions', 'x', 'in.vic']
    )
    with pytest.raises(ValueError, match='--movie and --versions'):
        main()


def test_main_bad_replace_exits_two(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--replace garbage`` is rejected by argparse (exit 2)."""
    monkeypatch.setattr(sys, 'argv', ['picmaker', '--replace', 'garbage'])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2


def test_main_bad_logging_exits_two(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--logging 5`` is rejected by argparse (exit 2)."""
    monkeypatch.setattr(sys, 'argv', ['picmaker', '--logging', '5'])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2


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


def test_main_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch, fixtures_dir: Path, tmp_path: Path
) -> None:
    """``KeyboardInterrupt`` from the pipeline surfaces as ``sys.exit(2)``."""

    def kb(*_a: Any, **_kw: Any) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(sys, 'argv', [
        'picmaker',
        '--directory', str(tmp_path),
        str(fixtures_dir / 'cassini_iss.vic'),
    ])
    # main() does ``from picmaker.picmaker import picmaker`` lazily; patch the
    # attribute on the module object (the package re-exports the same name, so
    # a dotted-string target would be ambiguous).
    monkeypatch.setattr(sys.modules['picmaker.picmaker'], 'picmaker', kb)
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2
