"""End-to-end check of the bundled Cassini ISS sample.

Drive ``picmaker`` with the sample versions file and compare each generated
preview against the committed reference image, reading the source data both
from the PDS3 label (``.LBL``) and from the VICAR image (``.IMG``) directly.
"""

from pathlib import Path

import pytest

from tests import assert_preview_matches, generate_previews

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


@pytest.mark.parametrize('reader', ['label', 'img'])
def test_cassini_previews_match_references(reader: str, tmp_path: Path) -> None:
    """Each generated preview reproduces its reference image, whether the
    source is read from the PDS3 label or from the VICAR ``.IMG``."""
    input_path = LABEL if reader == 'label' else IMAGE
    generate_previews(input_path, tmp_path, VERSIONS_FILE)

    for name in PREVIEWS:
        produced_path = tmp_path / name
        assert produced_path.exists(), f'{name} was not generated'
        assert_preview_matches(produced_path, DATA_DIR / name)
