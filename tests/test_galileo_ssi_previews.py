"""End-to-end check of the bundled Galileo SSI sample.

Drive ``picmaker`` with the sample versions file and the base options that the
``GO_0xxx_previews.sh`` script applies, then compare each generated preview
against the committed reference image, reading the source data both from the
PDS3 label (``.LBL``) and from the VICAR image (``.IMG``) directly.
"""

from pathlib import Path

import pytest

from tests import assert_preview_matches, generate_previews

DATA_DIR = Path(__file__).parent.parent / 'test_files' / 'galileo_ssi'
VERSIONS_FILE = DATA_DIR / 'GO_0xxx_previews.txt'
LABEL = DATA_DIR / 'C0552809300R.LBL'
IMAGE = DATA_DIR / 'C0552809300R.IMG'

# Base options the GO_0xxx_previews.sh script applies to every version (the
# versions file itself lists only the per-preview overrides).
BASE_ARGS = ('--down', '--extension=jpg', '--footprint=5', '--trim-zeros')

# Every preview the versions file produces for this image, each with a
# committed reference image of the same name.
PREVIEWS = (
    'C0552809300R_full.jpg',
    'C0552809300R_med.jpg',
    'C0552809300R_small.jpg',
    'C0552809300R_thumb.jpg',
)


@pytest.mark.parametrize('reader', ['label', 'img'])
def test_galileo_previews_match_references(reader: str, tmp_path: Path) -> None:
    """Each generated preview reproduces its reference image, whether the
    source is read from the PDS3 label or from the VICAR ``.IMG``."""
    input_path = LABEL if reader == 'label' else IMAGE
    generate_previews(input_path, tmp_path, VERSIONS_FILE, extra_args=BASE_ARGS)

    for name in PREVIEWS:
        produced_path = tmp_path / name
        assert produced_path.exists(), f'{name} was not generated'
        assert_preview_matches(produced_path, DATA_DIR / name)
