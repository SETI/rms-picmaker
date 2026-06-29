"""Behavioural test for the ``--recursive``, ``--pattern`` and ``--movie`` options.

The bundled ``cassini_iss_fmovie`` sample holds Cassini ISS VICAR images split
across two subdirectories. Each frame exists twice: an original
(``N..._1.IMG``) and a brightness-scaled copy (``N..._1_xNN.IMG``) whose pixels
were multiplied by 0.5, 0.6, ... 1.0 and clipped back to bytes. ``subdir1``
holds the 0.5-0.7 copies, ``subdir2`` the 0.8-1.0 copies.

Driving picmaker over the directory tree exercises three options together:

* ``--recursive`` descends into ``subdir1`` and ``subdir2`` to find the images;
* ``--pattern '*_x*.IMG'`` selects only the scaled copies, ignoring the
  unscaled originals;
* ``--movie`` applies one shared stretch across the whole set, so the per-frame
  brightness ramp survives into the previews instead of every frame being
  normalised independently.
"""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tests import generate_previews

DATA_DIR = Path(__file__).parent.parent / 'test_files' / 'cassini_iss_fmovie'

# The scaled previews in ascending brightness order, with the scale factor that
# produced each source frame.
SCALED_FRAMES = (
    ('subdir1/N1881794510_1_x05.jpg', 0.5),
    ('subdir1/N1881794918_1_x06.jpg', 0.6),
    ('subdir1/N1881795326_1_x07.jpg', 0.7),
    ('subdir2/N1881795734_1_x08.jpg', 0.8),
    ('subdir2/N1881796142_1_x09.jpg', 0.9),
    ('subdir2/N1881796550_1_x10.jpg', 1.0),
)

# Options selecting only the scaled frames across the directory tree.
PATTERN_ARGS = ['--recursive', '--pattern', '*_x*.IMG', '--extension', 'jpg']


def _mean_brightness(path: Path) -> float:
    """Mean pixel value of a generated preview."""
    return float(np.asarray(Image.open(path)).mean())


def test_recursive_pattern_selects_only_scaled_frames(tmp_path: Path) -> None:
    """``--recursive`` reaches both subdirectories and ``--pattern`` keeps only
    the scaled copies, leaving the six unscaled originals untouched."""
    generate_previews(DATA_DIR, tmp_path, extra_args=[*PATTERN_ARGS, '--movie'])

    produced = sorted(p.relative_to(tmp_path).as_posix()
                      for p in tmp_path.rglob('*.jpg'))
    assert produced == sorted(name for name, _ in SCALED_FRAMES)


def test_movie_preserves_brightness_ramp(tmp_path: Path) -> None:
    """With ``--movie`` a single shared stretch spans the set, so mean
    brightness rises monotonically from the 0.5x frame to the 1.0x frame."""
    generate_previews(DATA_DIR, tmp_path, extra_args=[*PATTERN_ARGS, '--movie'])

    means = [_mean_brightness(tmp_path / name) for name, _ in SCALED_FRAMES]
    assert all(lo < hi for lo, hi in zip(means, means[1:])), means
    # A genuine ramp, not a few DN of encoder noise.
    assert means[-1] - means[0] > 20


def test_without_movie_each_frame_is_normalised(tmp_path: Path) -> None:
    """Without ``--movie`` every frame is stretched independently, undoing the
    scaling so all frames land at essentially the same brightness - the
    contrast that shows ``--movie`` is what preserves the ramp."""
    generate_previews(DATA_DIR, tmp_path, extra_args=PATTERN_ARGS)

    means = [_mean_brightness(tmp_path / name) for name, _ in SCALED_FRAMES]
    assert max(means) - min(means) < 3, means


def test_pattern_requires_recursive_to_reach_subdirectories(tmp_path: Path) -> None:
    """Without ``--recursive`` the top-level directory holds no matching files,
    so picmaker reports that no inputs were identified."""
    with pytest.raises(ValueError, match='no input files identified'):
        generate_previews(DATA_DIR, tmp_path,
                          extra_args=['--pattern', '*_x*.IMG', '--extension', 'jpg'])
