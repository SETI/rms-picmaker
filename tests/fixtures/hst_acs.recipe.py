"""Regenerate hst_acs.fits — HST ACS/WFC FITS fixture (5 HDUs).

Exercises the ACS/WFC stacking branch at picmaker.py:1656-1664 (hdulist[4] access).
Detection: ('HST', 'ACS/WFC', ('CL1', 'F606W')).

Run from this directory:
    python hst_acs.recipe.py
"""
from pathlib import Path

import numpy as np
from astropy.io import fits

OUT = Path(__file__).parent / 'hst_acs.fits'


def main() -> None:
    primary = fits.PrimaryHDU()
    primary.header['TELESCOP'] = 'HST'
    primary.header['INSTRUME'] = 'ACS'
    primary.header['DETECTOR'] = 'WFC'
    primary.header['FILTER1'] = 'CL1'
    primary.header['FILTER2'] = 'F606W'
    sci1 = fits.ImageHDU(np.zeros((16, 16), dtype=np.float32))
    err = fits.ImageHDU(np.zeros((16, 16), dtype=np.float32))
    dq = fits.ImageHDU(np.zeros((16, 16), dtype=np.int16))
    sci2 = fits.ImageHDU(np.zeros((16, 16), dtype=np.float32))
    fits.HDUList([primary, sci1, err, dq, sci2]).writeto(OUT, overwrite=True)


if __name__ == '__main__':
    main()
