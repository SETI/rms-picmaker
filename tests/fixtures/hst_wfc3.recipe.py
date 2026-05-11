"""Regenerate hst_wfc3.fits — single-HDU HST WFC3/UVIS FITS fixture.

Detection: inst_host=TELESCOP='HST', inst_id='WFC3/UVIS' (INSTRUME+'/'+DETECTOR),
filter_name='F606W'. read_one_image_array → ('HST', 'WFC3/UVIS', 'F606W').

Run from this directory:
    python hst_wfc3.recipe.py
"""
from pathlib import Path

import numpy as np
from astropy.io import fits

OUT = Path(__file__).parent / 'hst_wfc3.fits'


def main() -> None:
    hdu = fits.PrimaryHDU(np.zeros((16, 16), dtype=np.float32))
    hdu.header['TELESCOP'] = 'HST'
    hdu.header['INSTRUME'] = 'WFC3'
    hdu.header['DETECTOR'] = 'UVIS'
    hdu.header['FILTER'] = 'F606W'
    fits.HDUList([hdu]).writeto(OUT, overwrite=True)


if __name__ == '__main__':
    main()
