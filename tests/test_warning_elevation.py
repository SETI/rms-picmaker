"""A corrupt FITS file is rejected by the FITS reader and falls through the
:func:`picmaker.instruments.read_image_array` cascade.

``corrupt_fits.fits`` begins with the ``SIMPLE = `` magic so the FITS branch is
entered, but its body is garbage. The FITS reader fails (or its
detect_in_fits hook does), the cascade continues, every other reader also
fails, and the cascade ends with ``OSError('unrecognized file format ...')``.
"""

from pathlib import Path

import pytest

from picmaker.instruments import read_image_array


def test_corrupt_fits_falls_through_to_unrecognized(fixtures_dir: Path) -> None:
    with pytest.raises(OSError, match=r'unrecognized file format'):
        read_image_array(str(fixtures_dir / 'corrupt_fits.fits'))
