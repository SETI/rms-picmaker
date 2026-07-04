"""Regenerate hst_acs.fits — HST ACS/WFC FITS fixture (5 HDUs).

Exercises the ACS/WFC stacking branch (hdulist[4] access).
Detection: ('HST', 'ACS/WFC', ('CL1', 'F606W')).

Run from this directory:
    python hst_acs_recipe.py
"""
from pathlib import Path

import numpy as np
from astropy.io import fits

OUT = Path(__file__).parent.parent / 'fixtures' / 'hst_acs.fits'


def main() -> None:
    """Generate hst_acs.fits with 5 HDUs and expected detection tuple.

    Creates a FITS file with a PrimaryHDU containing HST/ACS/WFC header
    keywords, followed by four ImageHDUs. The expected detection result is
    ('HST', 'ACS/WFC', ('CL1', 'F606W')).

    Args:
        None

    Returns:
        None

    Side Effects:
        Writes hst_acs.fits to the fixtures directory.
    """
    primary = fits.PrimaryHDU()
    primary.header['TELESCOP'] = 'HST'
    primary.header['INSTRUME'] = 'ACS'
    primary.header['DETECTOR'] = 'WFC'
    primary.header['FILTER1'] = 'CL1'
    primary.header['FILTER2'] = 'F606W'
    sci1 = fits.ImageHDU(np.zeros((16, 16), dtype=np.float32), name='SCI')
    err = fits.ImageHDU(np.zeros((16, 16), dtype=np.float32), name='ERR')
    dq = fits.ImageHDU(np.zeros((16, 16), dtype=np.int16), name='DQ')
    sci2 = fits.ImageHDU(np.zeros((16, 16), dtype=np.float32), name='SCI')
    fits.HDUList([primary, sci1, err, dq, sci2]).writeto(OUT, overwrite=True)


if __name__ == '__main__':
    main()
