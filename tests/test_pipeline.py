"""End-to-end pipeline tests via ``picmaker(**options)`` on every fixture.

The byte-identical snapshot tests live in test_snapshots.py — this file just
asserts that the pipeline produces an output file with sensible properties for
each option combination. Options are built the way the CLI builds them, by
parsing argv through ``get_parser()`` and running it through
``validate_options`` so the resulting dict has every key ``picmaker`` expects.
"""

from pathlib import Path

import pytest
from PIL import Image

from picmaker.options import get_parser
from picmaker.picmaker import picmaker

# hst_acs.fits and hst_wfpc2.fits are omitted from the end-to-end pipeline
# fixtures here; their readers are covered by the instrument reading tests.
ALL_FIXTURES = [
    'cassini_iss.vic',
    'voyager_iss.vic',
    'galileo_ssi_a.vic',
    'galileo_ssi_b.vic',
    'hst_wfc3.fits',
    'nh_mvic.fits',
]


def _run(infile: Path, tmp_path: Path, *extra: str) -> None:
    """Build a complete options dict the CLI way and run the pipeline."""
    options = vars(get_parser().parse_args(
        [str(infile), '--directory', str(tmp_path), *extra]
    ))
    picmaker(**options)


@pytest.mark.parametrize('fixture', ALL_FIXTURES)
def test_default_options_writes_jpeg(
    fixture: str, fixtures_dir: Path, tmp_path: Path
) -> None:
    _run(fixtures_dir / fixture, tmp_path)
    expected = tmp_path / (Path(fixture).stem + '.jpg')
    assert expected.exists()
    with Image.open(expected) as img:
        # Every instrument fixture is a 16x16 synthetic frame and the
        # default pipeline preserves that size (no --frame / --scale).
        assert img.size == (16, 16)


@pytest.mark.parametrize('fixture', ALL_FIXTURES)
def test_gamma_two(fixture: str, fixtures_dir: Path, tmp_path: Path) -> None:
    _run(fixtures_dir / fixture, tmp_path, '--gamma', '2.0')
    assert (tmp_path / (Path(fixture).stem + '.jpg')).exists()


@pytest.mark.parametrize('fixture', ALL_FIXTURES)
def test_percentile_stretch(
    fixture: str, fixtures_dir: Path, tmp_path: Path
) -> None:
    _run(fixtures_dir / fixture, tmp_path, '--percentiles', '5', '95')
    assert (tmp_path / (Path(fixture).stem + '.jpg')).exists()


def test_tint_option(fixtures_dir: Path, tmp_path: Path) -> None:
    _run(fixtures_dir / 'cassini_iss.vic', tmp_path, '--tint')
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_rotate_rot90(fixtures_dir: Path, tmp_path: Path) -> None:
    _run(fixtures_dir / 'cassini_iss.vic', tmp_path, '--rotate', 'rot90')
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_movie_option_writes_outputs(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    # Movie mode runs the pipeline in two passes (limits scan, then write).
    _run(fixtures_dir / 'cassini_iss.vic', tmp_path, '--movie')
    assert (tmp_path / 'cassini_iss.jpg').exists()


@pytest.mark.parametrize('fixture', ALL_FIXTURES)
def test_sixteen_bit_tiff_extension(
    fixture: str, fixtures_dir: Path, tmp_path: Path
) -> None:
    _run(fixtures_dir / fixture, tmp_path, '--16', '--extension', 'tiff')
    assert (tmp_path / (Path(fixture).stem + '.tiff')).exists()


def test_replace_none_skips_existing_output(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``--replace none`` leaves an existing output file untouched.

    Regression: ``get_outfile`` returns ``''`` to signal a skip, but
    ``picmaker`` forwarded that empty path to ``write_pil`` and crashed with
    ``ValueError: unknown file extension`` instead of skipping.
    """
    _run(fixtures_dir / 'cassini_iss.vic', tmp_path)
    out = tmp_path / 'cassini_iss.jpg'
    assert out.exists()
    # Overwrite with a sentinel; a second run with --replace none must not
    # touch the file (and must not raise).
    out.write_bytes(b'SENTINEL')
    _run(fixtures_dir / 'cassini_iss.vic', tmp_path, '--replace', 'none')
    assert out.read_bytes() == b'SENTINEL'


def test_proceed_continues_past_unreadable_file(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``--proceed`` skips an unreadable input and still processes later files.

    Regression: ``--proceed`` was a parsed CLI flag that ``picmaker`` never
    acted on, so the first bad file aborted the whole run.
    """
    src = tmp_path / 'src'
    src.mkdir()
    bad = src / 'bad.vic'
    bad.write_bytes(b'not a vicar file')
    out = tmp_path / 'out'
    # Both input files must precede the options for argparse to collect them.
    options = vars(get_parser().parse_args([
        str(bad), str(fixtures_dir / 'cassini_iss.vic'),
        '--directory', str(out), '--proceed',
    ]))
    picmaker(**options)
    # The unreadable file is skipped; the good file still produces output.
    assert (out / 'cassini_iss.jpg').exists()


def test_movie_proceed_continues_past_unreadable_file(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``--movie --proceed`` skips an unreadable file during the limits scan
    and still writes the readable frames."""
    src = tmp_path / 'src'
    src.mkdir()
    bad = src / 'bad.vic'
    bad.write_bytes(b'not a vicar file')
    out = tmp_path / 'out'
    options = vars(get_parser().parse_args([
        str(bad), str(fixtures_dir / 'cassini_iss.vic'),
        '--directory', str(out), '--movie', '--proceed',
    ]))
    picmaker(**options)
    assert (out / 'cassini_iss.jpg').exists()
