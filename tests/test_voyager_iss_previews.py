"""End-to-end check of the bundled Voyager ISS sample.

The ``VGISS_previews.sh`` script runs picmaker twice: the medium / small /
thumbnail previews come from the CLEANED image via the versions file, while
the full-size preview comes from the RAW image with ``--suffix=_full``. Both
runs use ``--strip`` to drop the ``_CLEANED`` / ``_RAW`` marker from the output
name. Each preview is compared against its committed reference, reading the
source both from the PDS3 label (``.LBL``) and the VICAR image (``.IMG``).
"""

from pathlib import Path

import pytest

from tests import assert_preview_matches, generate_previews

DATA_DIR = Path(__file__).parent.parent / 'test_files' / 'voyager_iss'
VERSIONS_FILE = DATA_DIR / 'VGISS_versions.txt'

# Base options the VGISS_previews.sh script applies to both runs.
BASE_ARGS = ('--down', '--extension=jpg', '--percentiles', '0.1', '99.9', '--trim=5')

# Previews built from the CLEANED image via the versions file, and the single
# full-size preview built from the RAW image. Each has a committed reference of
# the same name.
CLEANED_PREVIEWS = (
    'C1124748_med.jpg',
    'C1124748_small.jpg',
    'C1124748_thumb.jpg',
)
FULL_PREVIEW = 'C1124748_full.jpg'


@pytest.mark.parametrize('reader', ['label', 'img'])
def test_voyager_previews_match_references(reader: str, tmp_path: Path) -> None:
    """Each generated preview reproduces its reference image, whether the
    source is read from the PDS3 label or from the VICAR image."""
    ext = '.LBL' if reader == 'label' else '.IMG'

    # medium / small / thumbnail come from the CLEANED image and the versions file
    generate_previews(DATA_DIR / f'C1124748_CLEANED{ext}', tmp_path, VERSIONS_FILE,
                      extra_args=(*BASE_ARGS, '--strip', '_CLEANED'))
    # the full-size preview comes from the RAW image
    generate_previews(DATA_DIR / f'C1124748_RAW{ext}', tmp_path,
                      extra_args=(*BASE_ARGS, '--strip', '_RAW', '--suffix=_full'))

    for name in (FULL_PREVIEW, *CLEANED_PREVIEWS):
        produced_path = tmp_path / name
        assert produced_path.exists(), f'{name} was not generated'
        assert_preview_matches(produced_path, DATA_DIR / name)
