"""Regenerate nh_mvic.fits — New Horizons MVIC FITS fixture.

Detection: inst_host=HOSTNAME='NEW HORIZONS', inst_id=INSTRU='MVIC', filter='BLUE'.
read_one_image_array → ('NEW HORIZONS', 'MVIC', 'BLUE').

Run from this directory:
    python nh_mvic.recipe.py
"""
from pathlib import Path

import numpy as np
from astropy.io import fits

OUT = Path(__file__).parent / 'nh_mvic.fits'


def main() -> None:
    hdu = fits.PrimaryHDU(np.zeros((16, 16), dtype=np.float32))
    hdu.header['HOSTNAME'] = 'NEW HORIZONS'
    hdu.header['INSTRU'] = 'MVIC'
    hdu.header['FILTER'] = 'BLUE'
    fits.HDUList([hdu]).writeto(OUT, overwrite=True)


if __name__ == '__main__':
    main()
