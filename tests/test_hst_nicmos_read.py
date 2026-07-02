"""Read/render check of the bundled HST NICMOS sample.

The committed reference jpgs were produced by the old tool from the PDS3-labeled
``RAW_TIFF_DOCUMENT`` / ``MOS_JPEG_DOCUMENT`` browse products named in
``HSTN_previews.txt``; those source documents are not bundled here (only the
multi-extension FITS is), and the recipe used ``--pointer`` / ``--alt_pointer``
options the current tool no longer has. The references are therefore not
reproducible pixel-for-pixel from this FITS.

This test instead pins the behaviour restored by the NICMOS reader fix: the
science (``SCI``) extension is read even though the PRIMARY HDU carries no data,
the filter-derived tint is attached, and picmaker renders previews whose size
and mode match the committed references.
"""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from picmaker.instruments import read_image_array
from tests import generate_previews

DATA_DIR = Path(__file__).parent.parent / 'test_files' / 'hst_nicmos'
IMAGE = DATA_DIR / 'nb06030a0_mos.fits'

# Base options from HSTN_previews.sh; each version adds its own overrides.
BASE_ARGS = ('--percentiles', '0.02', '99.98', '--gamma', '0.5', '--extension', 'jpg')

# (suffix, per-version args, reference jpg, expected PIL mode). The tinted
# previews are RGB; the unscaled _full has no tint and stays grayscale.
PREVIEWS = (
    ('_full', ('--scale', '200'), 'NB06030A0_full.jpg', 'L'),
    ('_med', ('--frame', '512', '512', '--tint'), 'NB06030A0_med.jpg', 'RGB'),
    ('_small', ('--frame', '256', '256', '--tint'), 'NB06030A0_small.jpg', 'RGB'),
    ('_thumb', ('--frame', '100', '100', '--tint'), 'NB06030A0_thumb.jpg', 'RGB'),
)


def test_nicmos_fits_reads_science_extension() -> None:
    """The multi-extension NICMOS FITS reads from its SCI image (the PRIMARY HDU
    has no data) and carries the tint derived from the F187N filter."""
    data = read_image_array(IMAGE)
    array = np.asarray(data.array)

    assert array.shape == (263, 265)        # the SCI extension, not empty PRIMARY
    assert array.dtype.kind == 'f'          # float science data
    assert data.default_upward is True
    # F187N (1870 nm) scaled by the default retint (0.4) -> 748 nm -> deep red.
    assert tuple(data.default_tint) == (255, 61, 61)


@pytest.mark.parametrize(('suffix', 'version_args', 'reference', 'mode'), PREVIEWS)
def test_nicmos_preview_geometry(suffix: str, version_args: tuple[str, ...],
                                 reference: str, mode: str, tmp_path: Path) -> None:
    """picmaker renders each preview from the FITS at the same size and mode as
    its committed reference (only the geometry is asserted: the reference pixels
    come from other, unbundled source documents)."""
    generate_previews(IMAGE, tmp_path,
                      extra_args=(*BASE_ARGS, *version_args, '--suffix', suffix))

    produced = tmp_path / f'nb06030a0_mos{suffix}.jpg'
    assert produced.exists(), f'{produced.name} was not generated'

    with Image.open(produced) as got, Image.open(DATA_DIR / reference) as ref:
        assert got.size == ref.size
        assert got.mode == mode
