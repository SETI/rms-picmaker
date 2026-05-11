"""warning-to-error elevation in the FITS branch (picmaker.py:1604-1605).

Inside `read_one_image_array`'s FITS branch, the code wraps the
`pyfits.open(...)` call in `warnings.catch_warnings(): filterwarnings('error')`.
This is what makes an `AstropyUserWarning`/`VerifyWarning` cause the FITS
parser to be rejected and let the cascade continue.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from picmaker.picmaker import read_one_image_array


def test_corrupt_fits_falls_through_via_warning_elevation(
    fixtures_dir: Path,
) -> None:
    # corrupt_fits.fits starts with the SIMPLE  = magic so the FITS branch
    # gets entered; the body is garbage so astropy raises a warning that the
    # filterwarnings('error') block elevates → caught by `except (UserWarning,
    # OSError)` → cascade continues → PIL also fails → final IOError.
    with pytest.raises(IOError, match=r'Unrecognized image file format'):
        read_one_image_array(str(fixtures_dir / 'corrupt_fits.fits'), None)
