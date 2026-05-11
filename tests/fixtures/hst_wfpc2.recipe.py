"""Regenerate hst_wfpc2.fits — HST WFPC2 FITS fixture (5 HDUs).

Exercises the WFPC2 stacking branch at picmaker.py:1667.
Detection: ('HST', 'WFPC2', ('F555W', 'CLEAR2')).

Run from this directory:
    python hst_wfpc2.recipe.py
"""
from pathlib import Path

import numpy as np
from astropy.io import fits

OUT = Path(__file__).parent / 'hst_wfpc2.fits'


def main() -> None:
    primary = fits.PrimaryHDU()
    primary.header['TELESCOP'] = 'HST'
    primary.header['INSTRUME'] = 'WFPC2'
    primary.header['FILTNAM1'] = 'F555W'
    primary.header['FILTNAM2'] = 'CLEAR2'
    hdus = [primary] + [
        fits.ImageHDU(np.zeros((16, 16), dtype=np.float32)) for _ in range(4)
    ]
    fits.HDUList(hdus).writeto(OUT, overwrite=True)


if __name__ == '__main__':
    main()
