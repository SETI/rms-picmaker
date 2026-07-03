"""Cover the pipeline branches that the snapshot / smoke tests miss:
the frame/size mutex, extension defaulting, the 16-bit guard, ``--zebra``,
movie mode, the ``--versions`` reuse path, wrap/pad, the unreadable-file
error path, a detached PDS3 label, and the display-orientation overrides.

Options are built the CLI way: parse argv through ``get_parser()`` and run it
through ``validate_options`` so the dict has every key ``picmaker`` expects.
"""

import shutil
from pathlib import Path

import numpy as np
import pytest

from picmaker.options import get_parser
from picmaker.picmaker import picmaker, validate_options


def _run(infiles: list[str], tmp_path: Path, *extra: str) -> None:
    """Build a complete options dict the CLI way and run the pipeline."""
    options = validate_options(get_parser().parse_args(
        [*infiles, '--directory', str(tmp_path), *extra]
    ))
    picmaker(**options)


# ---------------------------------------------------------------------------
# Mutex / value-validity checks inside validate_options
# ---------------------------------------------------------------------------


def test_frame_size_incompatible(fixtures_dir: Path, tmp_path: Path) -> None:
    """``--frame`` plus ``--size`` is rejected before any I/O."""
    with pytest.raises(ValueError, match='frame and --size'):
        _run(
            [str(fixtures_dir / 'cassini_iss.vic')], tmp_path,
            '--frame', '50', '50', '--size', '20', '20',
        )


def test_twobytes_requires_tiff_extension(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``--16`` with an explicit non-TIFF extension is rejected; only tiffs may
    be written in 16-bit mode. (``--16`` alone defaults the extension to tiff.)
    """
    with pytest.raises(ValueError, match='only tiffs can be written'):
        _run([str(fixtures_dir / 'cassini_iss.vic')], tmp_path,
             '--16', '--extension', 'jpg')


# ---------------------------------------------------------------------------
# extension default selection
# ---------------------------------------------------------------------------


def test_extension_default_jpg(fixtures_dir: Path, tmp_path: Path) -> None:
    """No ``--extension`` defaults to ``'jpg'`` when not in 16-bit mode."""
    _run([str(fixtures_dir / 'cassini_iss.vic')], tmp_path)
    assert (tmp_path / 'cassini_iss.jpg').exists()


# ---------------------------------------------------------------------------
# zebra fill
# ---------------------------------------------------------------------------


def test_zebra_path(fixtures_dir: Path, tmp_path: Path) -> None:
    """``--zebra`` runs ``fill_zebra_stripes`` without crashing."""
    _run([str(fixtures_dir / 'cassini_iss.vic')], tmp_path, '--zebra')
    assert (tmp_path / 'cassini_iss.jpg').exists()


# ---------------------------------------------------------------------------
# unreadable-file error path
# ---------------------------------------------------------------------------


def test_unreadable_file_raises(tmp_path: Path) -> None:
    """An unrecognized input file raises ``OSError``."""
    bogus = tmp_path / 'bogus.bin'
    bogus.write_bytes(b'not-an-image')
    with pytest.raises(OSError, match='unrecognized file format'):
        _run([str(bogus)], tmp_path)


# ---------------------------------------------------------------------------
# output-directory creation
# ---------------------------------------------------------------------------


def test_creates_output_directory(fixtures_dir: Path, tmp_path: Path) -> None:
    """``picmaker`` creates the output directory tree if it is missing."""
    out_dir = tmp_path / 'fresh' / 'subdir'
    _run([str(fixtures_dir / 'cassini_iss.vic')], out_dir)
    assert out_dir.is_dir()
    assert (out_dir / 'cassini_iss.jpg').exists()


# ---------------------------------------------------------------------------
# movie mode
# ---------------------------------------------------------------------------


def test_movie_mode_writes_every_frame(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """Movie mode scans all frames for a shared stretch, then writes each."""
    src1 = tmp_path / 'frame_001.vic'
    src2 = tmp_path / 'frame_002.vic'
    shutil.copy(fixtures_dir / 'cassini_iss.vic', src1)
    shutil.copy(fixtures_dir / 'cassini_iss.vic', src2)

    out_dir = tmp_path / 'out'
    _run([str(src1), str(src2)], out_dir, '--movie')
    assert (out_dir / 'frame_001.jpg').exists()
    assert (out_dir / 'frame_002.jpg').exists()


def test_movie_mode_unreadable_raises(tmp_path: Path) -> None:
    """Movie mode propagates ``OSError`` when a frame cannot be read."""
    bogus = tmp_path / 'b.bin'
    bogus.write_bytes(b'garbage')
    with pytest.raises(OSError, match='unrecognized file format'):
        _run([str(bogus)], tmp_path / 'out', '--movie')


# ---------------------------------------------------------------------------
# --versions reuse path
# ---------------------------------------------------------------------------


def test_versions_writes_each_variant(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """A ``--versions`` file layers per-line overrides onto the base options,
    reusing the single read of the input for every variant it writes.
    """
    versions = tmp_path / 'versions.txt'
    versions.write_text('--suffix _v1\n--suffix _v2 --gamma 2.0\n')
    _run(
        [str(fixtures_dir / 'cassini_iss.vic')], tmp_path,
        '--versions', str(versions),
    )
    assert (tmp_path / 'cassini_iss_v1.jpg').exists()
    assert (tmp_path / 'cassini_iss_v2.jpg').exists()


# ---------------------------------------------------------------------------
# wrap / pad branches
# ---------------------------------------------------------------------------


def test_wrap_branch_when_image_elongated(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``--wrap`` plus an elongated ``--size`` triggers ``wrap_pil_image``."""
    _run(
        [str(fixtures_dir / 'cassini_iss.vic')], tmp_path,
        '--wrap', '--size', '120', '16',
    )
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_pad_branch_runs(fixtures_dir: Path, tmp_path: Path) -> None:
    """``--frame`` plus ``--pad`` writes a padded output."""
    _run(
        [str(fixtures_dir / 'cassini_iss.vic')], tmp_path,
        '--frame', '64', '64', '--pad',
    )
    assert (tmp_path / 'cassini_iss.jpg').exists()


# ---------------------------------------------------------------------------
# PDS3 detached-label redirect
# ---------------------------------------------------------------------------


_LBL_TEMPLATE = """PDS_VERSION_ID = PDS3
INSTRUMENT_HOST_ID = 'CASSINI'
INSTRUMENT_ID = 'ISS'
DETECTOR_ID = 'NAC'
FILTER_NAME = ('CL1', 'GRN')
^IMAGE = "{image_filename}"
OBJECT = IMAGE
  LINES = 16
  LINE_SAMPLES = 16
  SAMPLE_BITS = 8
  SAMPLE_TYPE = UNSIGNED_INTEGER
END_OBJECT = IMAGE
END
"""


def test_pds3_label_redirects_to_vicar(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """A ``.LBL`` whose ``^IMAGE`` points at a VICAR file is parsed for its
    label metadata while the VICAR reader handles the actual pixels.
    """
    shutil.copy(fixtures_dir / 'cassini_iss.vic', tmp_path / 'cassini_iss.vic')
    lbl = tmp_path / 'sample.LBL'
    lbl.write_text(_LBL_TEMPLATE.format(image_filename='cassini_iss.vic'))
    out_dir = tmp_path / 'out'
    _run([str(lbl)], out_dir)
    assert (out_dir / 'sample.jpg').exists()


# ---------------------------------------------------------------------------
# empty input
# ---------------------------------------------------------------------------


def test_no_input_files_raises(tmp_path: Path) -> None:
    """When no input files resolve, ``picmaker`` raises ``ValueError``."""
    with pytest.raises(ValueError, match='no input files identified'):
        _run([], tmp_path)


# ---------------------------------------------------------------------------
# display orientation overrides
# ---------------------------------------------------------------------------


def test_display_upward_override(fixtures_dir: Path, tmp_path: Path) -> None:
    """``--up`` overrides the per-instrument default orientation."""
    _run([str(fixtures_dir / 'cassini_iss.vic')], tmp_path, '--up')
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_display_downward_override(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``--down`` overrides the per-instrument default orientation."""
    _run([str(fixtures_dir / 'cassini_iss.vic')], tmp_path, '--down')
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_tint_with_no_image_info_skips_override(tmp_path: Path) -> None:
    """``--tint`` on an image with no ``image_info`` leaves the requested
    colormap in place (the tint override path is a no-op).
    """
    # A plain numpy array carries no instrument metadata for the tint to use.
    src = tmp_path / 'plain.npy'
    np.save(src, (np.arange(64).reshape(8, 8) * 4).astype('uint8'))
    _run([str(src)], tmp_path, '--tint')
    assert (tmp_path / 'plain.jpg').exists()
