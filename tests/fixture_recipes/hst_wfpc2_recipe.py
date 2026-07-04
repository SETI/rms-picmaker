"""Regenerate hst_wfpc2.fits — HST WFPC2 FITS fixture.

Mimics real WFPC2 structure: the four detectors (PC1, WF2, WF3, WF4) are stored
as a data cube in the PRIMARY HDU, with a group-parameters table in HDU[1]
carrying the DETECTOR column. Exercises the WFPC2 detector-selection and
stacking branches. Detection: ('HST', 'WFPC2').

Run from this directory:
    python hst_wfpc2_recipe.py
"""
from pathlib import Path

import numpy as np
from astropy.io import fits

OUT = Path(__file__).parent.parent / 'fixtures' / 'hst_wfpc2.fits'


def main() -> None:
    """Create a WFPC2 FITS file: a (4, 16, 16) detector cube in the PRIMARY HDU
    plus a table HDU whose DETECTOR column maps each plane to a detector."""
    # Four 16x16 detector planes, each a distinct ramp so the planes differ.
    cube = np.stack([
        b + np.arange(16, dtype=np.float32)[np.newaxis, :] * np.ones((16, 1), np.float32)
        for b in range(4)
    ])

    primary = fits.PrimaryHDU(cube)
    primary.header['TELESCOP'] = 'HST'
    primary.header['INSTRUME'] = 'WFPC2'
    primary.header['FILTNAM1'] = 'F555W'
    primary.header['FILTNAM2'] = 'CLEAR2'

    detector_col = fits.Column(name='DETECTOR', format='J', array=np.array([1, 2, 3, 4]))
    table = fits.BinTableHDU.from_columns([detector_col])

    fits.HDUList([primary, table]).writeto(OUT, overwrite=True)


if __name__ == '__main__':
    main()
