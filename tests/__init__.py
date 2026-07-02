"""Shared helpers for the per-instrument preview regression tests.

Each preview test drives ``picmaker`` with an instrument's bundled versions
file and compares every generated preview against a committed reference image.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from picmaker.parser import get_parser
from picmaker.picmaker import picmaker

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
    picmaker(**options)  # type: ignore[no-untyped-call]  # untyped public entry point


def render_snapshot(input_path: Path, out_dir: Path, slug: str,
                    option_overrides: Mapping[str, Any], extension: str) -> None:
    """Render one snapshot combo into ``out_dir`` as ``<stem>--<slug>.<ext>``.

    A full default option dict is built from the parser, then ``suffix`` /
    ``extension`` and the combo's option keys are overridden and ``picmaker`` is
    run. Both :file:`fixture_recipes/generate_snapshots.py` and
    :file:`test_snapshots.py` call this, so their pipeline invocations are
    byte-for-byte identical -- the property the snapshot test relies on.
    """
    options = vars(get_parser().parse_args([str(input_path), '--directory', str(out_dir)]))
    options['suffix'] = f'--{slug}'
    options['extension'] = extension
    options.update(option_overrides)
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
