"""Read and mosaic-assembly checks for HST ACS.

The bundled ACS/WFC sample files are downsampled 5x in each direction by pixel
averaging (from the real archived products, so they keep the same HDU structure
and headers, only NAXIS1/NAXIS2 shrink) to stay small and committable. WFC
stores its two CCDs as separate SCI HDUs, with per-chip ERR HDUs before
drizzling; after drizzling the chips are combined into one array (and the ERR
HDUs are gone), so no mosaic can be built.
"""

from pathlib import Path

import numpy as np

from picmaker.instruments import read_image_array, tint_by_nm
from picmaker.instruments.hst_acs import HST_ACS

DATA_DIR = Path(__file__).parent.parent / 'test_files' / 'hst_acs'
DRZ = DATA_DIR / 'j96o01010_drz_small.fits'   # drizzled WFC: single SCI, no ERR HDUs
FLT = DATA_DIR / 'j96o01ipq_flt_small.fits'   # calibrated WFC: two SCI chips + ERR/DQ
RAW = DATA_DIR / 'j96o01ipq_raw_small.fits'   # raw WFC: two SCI chips, ERR/DQ HDUs empty


# --- mosaic assembly (no data files) -------------------------------------------------

def test_apply_mosaic_stacks_two_wfc_chips() -> None:
    """``apply_mosaic`` stacks WFC's two CCDs into ``(2H, W, C)``: WFC2
    (``arrays_rgb[1]``) on top, WFC1 (``arrays_rgb[0]``) on the bottom."""
    wfc1 = np.full((5, 4, 3), 1.0)   # arrays_rgb[0]
    wfc2 = np.full((5, 4, 3), 2.0)   # arrays_rgb[1]
    mosaic = HST_ACS.apply_mosaic([wfc1, wfc2])
    assert mosaic.shape == (10, 4, 3)
    assert int(mosaic[0, 0, 0]) == 2     # top    = WFC2
    assert int(mosaic[-1, 0, 0]) == 1    # bottom = WFC1


def test_apply_mosaic_single_chip_passthrough() -> None:
    """A single detector (HRC/SBC, or a one-chip WFC) is returned unchanged."""
    chip = np.full((5, 4, 3), 9.0)
    result = HST_ACS.apply_mosaic([chip])
    assert result.shape == (5, 4, 3)
    np.testing.assert_array_equal(result, chip)


# --- reading real (downsampled) ACS/WFC files ----------------------------------------

def test_drz_drizzled_reads_single_tinted_array() -> None:
    """A drizzled _drz product has no per-chip ERR HDUs, so even ``mosaic=True``
    yields the single combined SCI array, tinted from FILTER1=F606W (WFC uses
    retint 1)."""
    data = read_image_array(DRZ, mosaic=True)
    assert np.asarray(data.array).shape == (847, 842)
    assert data.default_upward is True
    assert tuple(data.default_tint) == tuple(tint_by_nm(606))


def test_flt_default_reads_first_science_chip() -> None:
    """Without ``--mosaic`` a two-chip WFC read returns the first science chip."""
    data = read_image_array(FLT)
    assert np.asarray(data.array).shape == (409, 819)


def test_flt_mosaic_returns_two_chip_cube() -> None:
    """``mosaic=True`` on a two-chip WFC _flt (with real ERR HDUs) returns a
    ``(2, 409, 819)`` cube."""
    data = read_image_array(FLT, mosaic=True)
    assert np.asarray(data.array).shape == (2, 409, 819)


def test_raw_mosaic_works_with_empty_err_hdus() -> None:
    """A raw file carries ERR/DQ HDUs that hold no data; their mere presence
    still enables the two-chip mosaic (``'ERR' in hdulist``)."""
    data = read_image_array(RAW, mosaic=True)
    assert np.asarray(data.array).shape == (2, 413, 828)
