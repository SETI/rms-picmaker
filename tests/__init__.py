"""Shared helpers for the per-instrument preview regression tests.

Each preview test drives ``picmaker`` with an instrument's bundled versions
file and compares every generated preview against a committed reference image.
"""

from collections.abc import Sequence
from pathlib import Path

import numpy as np
from PIL import Image

from picmaker.cli import PARSER
from picmaker.picmaker import picmaker

# Maximum tolerated mean absolute difference per pixel between a generated
# preview and its committed reference. Lossless PNGs reproduce to within
# rounding (< 1 DN) and JPEGs add a little encoder noise; a real regression -
# an inverted stretch, a missing tint, a dropped crop or pad - pushes the mean
# difference into the tens or hundreds, far above this bound.
MAX_MEAN_DIFF = 2.0


def generate_previews(input_path: Path, out_dir: Path, versions_path: Path,
                      *, extra_args: Sequence[str] = ()) -> None:
    """Run ``picmaker`` on one input, writing every version into ``out_dir``.

    Parameters:
        input_path: The source data file (a PDS3 label or a VICAR image).
        out_dir: Directory to receive the generated previews.
        versions_path: Versions file listing the per-preview option overrides.
        extra_args: Base command-line options applied to every version (the
            options an instrument's preview script passes outside the versions
            file).
    """
    args = [str(input_path), '--directory', str(out_dir),
            '--versions', str(versions_path), '--proceed', *extra_args]
    options = vars(PARSER.parse_args(args))
    picmaker(**options)  # type: ignore[no-untyped-call]  # untyped public entry point


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
