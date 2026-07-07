"""Shared helpers for the per-instrument preview regression tests.

Each preview test drives ``picmaker`` with an instrument's bundled versions
file and compares every generated preview against a committed reference image.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from picmaker.instruments import read_pds3_image_array
from picmaker.options import get_parser
from picmaker.picmaker import picmaker


def read_pds3_array(label: Any, *args: Any, **kwargs: Any) -> Any:
    """Call ``read_pds3_image_array`` supplying the label's own file path.

    ``read_pds3_image_array`` now takes the label's path explicitly (it no longer
    reaches into the private ``Pds3Label._filepath``); the tests pull it from the
    parsed label, which still exposes it. Shared so the ~25 unit-test call sites
    don't each re-derive the path.
    """
    return read_pds3_image_array(label, getattr(label, '_filepath', ''),
                                 *args, **kwargs)

# Maximum tolerated mean absolute difference per pixel between a generated
# preview and its committed reference. Lossless PNGs reproduce to within
# rounding (< 1 DN) and JPEGs add a little encoder noise; a real regression -
# an inverted stretch, a missing tint, a dropped crop or pad - pushes the mean
# difference into the tens or hundreds, far above this bound.
MAX_MEAN_DIFF = 2.0


def generate_previews(input_path: Path, out_dir: Path,
                      versions_path: Path | None = None, *,
                      extra_args: Sequence[str] = ()) -> None:
    """Run ``picmaker`` on one input, writing every version into ``out_dir``.

    Parameters:
        input_path: The source data file (a PDS3 label or a VICAR/FITS image).
        out_dir: Directory to receive the generated previews.
        versions_path: Versions file listing the per-preview option overrides,
            or ``None`` for a single conversion driven only by ``extra_args``.
        extra_args: Base command-line options applied to the conversion (the
            options an instrument's preview script passes outside the versions
            file).
    """
    args = [str(input_path), '--directory', str(out_dir), '--proceed', *extra_args]
    if versions_path is not None:
        args += ['--versions', str(versions_path)]
    options = vars(get_parser().parse_args(args))
    picmaker(**options)


def render_snapshot(input_path: Path, out_dir: Path, slug: str,
                    option_overrides: Mapping[str, Any], extension: str) -> None:
    """Render one snapshot combo into ``out_dir`` as ``<stem>--<slug>.<ext>``.

    A full default option dict is built from the parser, then ``suffix`` /
    ``extension`` and the combo's option keys are overridden and ``picmaker`` is
    run. Both :file:`fixture_recipes/generate_snapshots.py` and
    :file:`test_snapshots.py` call this, so their pipeline invocations are
    byte-for-byte identical -- the property the snapshot test relies on.
    """
    options = vars(
        get_parser().parse_args([str(input_path), '--directory', str(out_dir)]))
    options['suffix'] = f'--{slug}'
    options['extension'] = extension
    options.update(option_overrides)
    picmaker(**options)


def assert_preview_matches(produced_path: Path, reference_path: Path) -> None:
    """Assert a generated preview matches its committed reference image.

    The shapes must be equal and the mean absolute per-pixel difference must
    stay below :data:`MAX_MEAN_DIFF`.

    Parameters:
        produced_path: The freshly generated preview file.
        reference_path: The committed reference image of the same name.
    """
    produced = np.asarray(Image.open(produced_path)).astype(int)
    expected = np.asarray(Image.open(reference_path)).astype(int)

    assert produced.shape == expected.shape, (
        f'{produced_path.name}: shape {produced.shape} != '
        f'reference {expected.shape}')

    mean_diff = float(np.abs(produced - expected).mean())
    assert mean_diff < MAX_MEAN_DIFF, (
        f'{produced_path.name}: mean absolute difference {mean_diff:.3f} '
        f'exceeds {MAX_MEAN_DIFF}')


# Snapshot comparison tolerances. Both metrics come from the per-pixel difference
# of the two decoded images: the largest absolute difference (worst single pixel)
# and the RMS difference (overall magnitude, which weights larger deviations more).
# Lossless formats (PNG, TIFF) must match exactly (thresholds 0). The JPEG thresholds
# are deliberately tight: they tolerate only minimal lossy-encoder drift, so most
# real changes trip them. When a JPEG snapshot fails, the message reports both
# measured metrics against their thresholds so a tester can judge whether it is
# benign encoder/library drift (small, diffuse -> regenerate or raise the threshold)
# or a genuine pipeline regression (large or spatially structured).
LOSSLESS_SNAPSHOT_EXTS = ('png', 'tif', 'tiff')
SNAPSHOT_JPEG_MAX_TOL = 5       # max absolute per-pixel difference, 0-255 DN
SNAPSHOT_JPEG_RMS_TOL = 0.5     # RMS per-pixel difference, 0-255 DN


def assert_snapshot_matches(produced_path: Path, expected_path: Path, ext: str) -> None:
    """Compare a rendered snapshot to its committed reference by *decoded pixels*.

    The per-pixel difference of the two decoded images is reduced to its largest
    absolute value and its RMS; the snapshot fails if either exceeds its threshold.
    PNG/TIFF are lossless and must match exactly (thresholds 0); JPEG is lossy and
    must match within a small tolerance. This replaces byte-for-byte file
    comparison, which was fragile to encoder/library version changes.

    Parameters:
        produced_path: The freshly rendered snapshot file.
        expected_path: The committed reference snapshot of the same name.
        ext: The file extension (selects exact vs. tolerant thresholds).
    """
    produced = np.asarray(Image.open(produced_path)).astype(float)
    expected = np.asarray(Image.open(expected_path)).astype(float)

    assert produced.shape == expected.shape, (
        f'{produced_path.name}: shape {produced.shape} != '
        f'reference {expected.shape}')

    lossless = ext.lower() in LOSSLESS_SNAPSHOT_EXTS
    max_tol: float = 0.0 if lossless else SNAPSHOT_JPEG_MAX_TOL
    rms_tol: float = 0.0 if lossless else SNAPSHOT_JPEG_RMS_TOL

    diff = produced - expected
    max_abs = float(np.abs(diff).max())
    rms = float(np.sqrt(np.mean(np.square(diff))))

    if lossless:
        guidance = (
            'Lossless PNG/TIFF snapshots must match exactly, so any nonzero '
            'difference is a real change: regenerate via '
            'tests/fixture_recipes/generate_snapshots.py if it is intentional, '
            'otherwise it is a pipeline regression.')
    else:
        guidance = (
            'A small, diffuse difference (a few DN, low RMS) is most likely JPEG '
            'encoder / libjpeg version drift rather than a bug -- regenerate the '
            'snapshots via tests/fixture_recipes/generate_snapshots.py, and if the '
            'new encoder output looks correct, raise SNAPSHOT_JPEG_MAX_TOL / '
            'SNAPSHOT_JPEG_RMS_TOL in tests/__init__.py. A large max, a high RMS, '
            'or a spatially structured difference indicates a real pipeline '
            'regression -- inspect the two images before regenerating.')

    within_tol = max_abs <= max_tol and rms <= rms_tol
    assert within_tol, (
        f'{produced_path.name}: rendered snapshot differs from its committed '
        f'reference.\n'
        f'  max absolute difference = {max_abs:.3f} DN  (threshold {max_tol})\n'
        f'  RMS difference          = {rms:.3f} DN  (threshold {rms_tol})\n'
        f'{guidance}')
