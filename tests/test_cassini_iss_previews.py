"""End-to-end check of the bundled Cassini ISS sample.

Drive ``picmaker`` with the sample versions file and compare each generated
preview against the committed reference image, reading the source data both
from the PDS3 label (``.LBL``) and from the VICAR image (``.IMG``) directly.
"""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from picmaker.cli import PARSER
from picmaker.picmaker import picmaker

DATA_DIR = Path(__file__).parent.parent / 'test_files' / 'cassini_iss'
VERSIONS_FILE = DATA_DIR / 'COISS_previews.txt'
LABEL = DATA_DIR / 'W1746306759_1.LBL'
IMAGE = DATA_DIR / 'W1746306759_1.IMG'

# Every preview the versions file produces for this image, each with a
# committed reference image of the same name.
PREVIEWS = (
    'W1746306759_1_full.png',
    'W1746306759_1_med.jpg',
    'W1746306759_1_small.jpg',
    'W1746306759_1_thumb.jpg',
)

# Maximum tolerated mean absolute difference per pixel. The lossless PNG is
# reproduced to within rounding (< 1 DN); the tinted JPEG adds a little
# encoder noise. A real regression - an inverted stretch or a missing tint -
# pushes the mean difference into the tens or hundreds, far above this bound.
MAX_MEAN_DIFF = 2.0


def _generate_previews(input_path: Path, out_dir: Path) -> None:
    """Run ``picmaker`` on one input, writing every version into ``out_dir``."""
    args = [str(input_path), '--directory', str(out_dir),
            '--versions', str(VERSIONS_FILE), '--proceed']
    options = vars(PARSER.parse_args(args))
    picmaker(**options)  # type: ignore[no-untyped-call]  # untyped public entry point


@pytest.mark.parametrize('reader', ['label', 'img'])
def test_cassini_previews_match_references(reader: str, tmp_path: Path) -> None:
    """Each generated preview reproduces its reference image, whether the
    source is read from the PDS3 label or from the VICAR ``.IMG``."""
    input_path = LABEL if reader == 'label' else IMAGE
    _generate_previews(input_path, tmp_path)

    for name in PREVIEWS:
        produced_path = tmp_path / name
        assert produced_path.exists(), f'{name} was not generated'

        produced = np.asarray(Image.open(produced_path)).astype(int)
        expected = np.asarray(Image.open(DATA_DIR / name)).astype(int)

        assert produced.shape == expected.shape, (
            f'{name}: shape {produced.shape} != reference {expected.shape}')

        mean_diff = float(np.abs(produced - expected).mean())
        assert mean_diff < MAX_MEAN_DIFF, (
            f'{name}: mean absolute difference {mean_diff:.3f} exceeds '
            f'{MAX_MEAN_DIFF}')
