"""End-to-end check of the bundled New Horizons LORRI sample.

Drive ``picmaker`` with the sample versions file and the base options that the
``NHxxLO_previews.sh`` script applies, then compare each generated preview
against the committed reference image, reading the source data both from the
PDS3 label (``.lbl``) and from the FITS image (``.fit``) directly.
"""

from pathlib import Path

import pytest

from tests import assert_preview_matches, generate_previews

DATA_DIR = Path(__file__).parent.parent / 'test_files' / 'nh_lorri'
VERSIONS_FILE = DATA_DIR / 'NHxxLO_previews.txt'
LABEL = DATA_DIR / 'lor_0299140073_0x630_sci.lbl'
IMAGE = DATA_DIR / 'lor_0299140073_0x630_sci.fit'

# Base options the NHxxLO_previews.sh script applies to every version (the
# versions file itself lists only the per-preview overrides).
BASE_ARGS = ('--up', '--extension=jpg', '--percentiles', '0.01', '99.9',
             '--trim-zeros', '--footprint=5')

# Every preview the versions file produces for this image, each with a
# committed reference image of the same name.
PREVIEWS = (
    'lor_0299140073_0x630_sci_full.jpg',
    'lor_0299140073_0x630_sci_med.jpg',
    'lor_0299140073_0x630_sci_small.jpg',
    'lor_0299140073_0x630_sci_thumb.jpg',
)


@pytest.mark.parametrize('reader', ['label', 'fits'])
def test_nh_lorri_previews_match_references(reader: str, tmp_path: Path) -> None:
    """Each generated preview reproduces its reference image, whether the
    source is read from the PDS3 label or from the FITS image."""
    input_path = LABEL if reader == 'label' else IMAGE
    generate_previews(input_path, tmp_path, VERSIONS_FILE, extra_args=BASE_ARGS)

    for name in PREVIEWS:
        produced_path = tmp_path / name
        assert produced_path.exists(), f'{name} was not generated'
        assert_preview_matches(produced_path, DATA_DIR / name)
