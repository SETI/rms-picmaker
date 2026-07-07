"""Read, tint, and mosaic-assembly checks for HST WFC3.

The bundled WFC3/UVIS sample files are downsampled 5x in each direction by pixel
averaging (from the real archived products, so they keep the same HDU structure
and headers, only NAXIS1/NAXIS2 shrink) to stay small and committable. UVIS
stores its two CCDs as separate SCI HDUs, with per-chip ERR HDUs before
drizzling; after drizzling the chips are combined into one array (and the ERR
HDUs are gone), so no mosaic can be built. IR is single-detector.
"""

from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from picmaker.instruments import read_image_array, tint_by_nm
from picmaker.instruments.hst_wfc3 import HST_WFC3

DATA_DIR = Path(__file__).parent.parent / 'test_files' / 'hst_wfc3'
DRZ = DATA_DIR / 'iepl0j020_drz_small.fits'   # drizzled UVIS: single SCI, no ERR HDUs
FLT = DATA_DIR / 'iepl0jltq_flt_small.fits'   # calibrated UVIS: two SCI chips + ERR/DQ
RAW = DATA_DIR / 'iepl0jltq_raw_small.fits'   # raw UVIS: two SCI chips, ERR/DQ HDUs empty

# All three samples were taken through F606W (606 nm); UVIS tints at that
# wavelength unscaled (retint defaults to 1).
F606W_TINT = tint_by_nm(606)


# --- mosaic assembly (no data files) -------------------------------------------------

def test_apply_mosaic_stacks_two_uvis_chips() -> None:
    """``apply_mosaic`` stacks UVIS's two CCDs into ``(2H, W, C)``: UVIS2
    (``arrays_rgb[1]``) on top, UVIS1 (``arrays_rgb[0]``) on the bottom."""
    uvis1 = np.full((5, 4, 3), 1.0)   # arrays_rgb[0]
    uvis2 = np.full((5, 4, 3), 2.0)   # arrays_rgb[1]
    mosaic = HST_WFC3.apply_mosaic([uvis1, uvis2])
    assert mosaic.shape == (10, 4, 3)
    assert int(mosaic[0, 0, 0]) == 2     # top    = UVIS2
    assert int(mosaic[-1, 0, 0]) == 1    # bottom = UVIS1


def test_apply_mosaic_single_chip_passthrough() -> None:
    """A single detector (IR, or a one-chip UVIS) is returned unchanged."""
    chip = np.full((5, 4, 3), 9.0)
    result = HST_WFC3.apply_mosaic([chip])
    assert result.shape == (5, 4, 3)
    np.testing.assert_array_equal(result, chip)


# --- reading real (downsampled) WFC3/UVIS files --------------------------------------

def test_drz_drizzled_reads_single_tinted_array() -> None:
    """A drizzled _drz product has no per-chip ERR HDUs, so even ``mosaic=True``
    yields the single combined SCI array, tinted from FILTER=F606W (UVIS tints
    at the filter wavelength unscaled)."""
    data = read_image_array(DRZ, mosaic=True)
    assert np.asarray(data.array).shape == (878, 825)
    assert data.default_upward is True
    assert tuple(data.default_tint) == tuple(F606W_TINT)


def test_flt_default_reads_first_science_chip() -> None:
    """Without ``--mosaic`` a two-chip UVIS read returns the first science chip."""
    data = read_image_array(FLT)
    assert np.asarray(data.array).shape == (410, 819)
    assert tuple(data.default_tint) == tuple(F606W_TINT)


def test_flt_mosaic_returns_two_chip_cube() -> None:
    """``mosaic=True`` on a two-chip UVIS _flt (with real ERR HDUs) returns a
    ``(2, 410, 819)`` cube."""
    data = read_image_array(FLT, mosaic=True)
    assert np.asarray(data.array).shape == (2, 410, 819)


def test_raw_mosaic_works_with_empty_err_hdus() -> None:
    """A raw file carries ERR/DQ HDUs that hold no data; their mere presence
    still enables the two-chip mosaic (``'ERR' in hdulist``)."""
    data = read_image_array(RAW, mosaic=True)
    assert np.asarray(data.array).shape == (2, 414, 841)


# --- detector detection and tint logic (driven directly through detect_in_fits) ------

def test_detect_returns_none_for_non_hst() -> None:
    """A non-HST telescope is not claimed by the WFC3 reader."""
    with fits.open(FLT) as hdulist:
        hdulist[0].header['TELESCOP'] = 'JWST'
        assert HST_WFC3.detect_in_fits(hdulist, str(FLT)) is None


def test_detect_returns_none_for_non_wfc3_instrument() -> None:
    """An HST product from another instrument is not claimed by the WFC3 reader."""
    with fits.open(FLT) as hdulist:
        hdulist[0].header['INSTRUME'] = 'ACS'
        assert HST_WFC3.detect_in_fits(hdulist, str(FLT)) is None


@pytest.mark.parametrize('filter_name', ['F200LP', 'F350LP'])
def test_undiagnostic_filter_has_no_tint(filter_name: str) -> None:
    """The broad long-pass filters carry no useful color, so no tint is set."""
    with fits.open(FLT) as hdulist:
        hdulist[0].header['FILTER'] = filter_name
        result = HST_WFC3.detect_in_fits(hdulist, str(FLT))
    assert result is not None
    assert result.default_tint is None


def test_uvis_tint_scales_with_retint() -> None:
    """``retint`` multiplies the UVIS filter wavelength before tinting; a factor
    of 2 pushes F606W (606 nm) past the red end of the table."""
    with fits.open(FLT) as hdulist:
        result = HST_WFC3.detect_in_fits(hdulist, str(FLT), retint=2)
    assert result is not None
    assert tuple(result.default_tint) == tuple(tint_by_nm(606 * 2))


def test_ir_detector_uses_ir_retint_scaling() -> None:
    """IR filter names encode wavelength/10 (F160W -> 1600 nm), so the IR path
    tints at ``digits * 10 * 0.4`` (the 0.4 default retint) -- matching NICMOS
    and distinct from the UVIS path (``digits * 1``). Exercised on a UVIS sample
    with FILTER and DETECTOR forced to an IR configuration."""
    with fits.open(FLT) as hdulist:
        hdulist[0].header['DETECTOR'] = 'IR'
        hdulist[0].header['FILTER'] = 'F160W'
        result = HST_WFC3.detect_in_fits(hdulist, str(FLT))
    assert result is not None
    assert tuple(result.default_tint) == tuple(tint_by_nm(160 * 10.0 * 0.4))


# --- chip ordering and error handling ------------------------------------------------

def test_flt_mosaic_orders_chips_by_ccdchip() -> None:
    """The two-chip cube is ordered by CCDCHIP: the first SCI HDU (CCDCHIP 2)
    lands at cube index 1, which is exactly what a default (non-mosaic) read
    returns. The two chips carry different pixels."""
    single = np.asarray(read_image_array(FLT).array)
    cube = np.asarray(read_image_array(FLT, mosaic=True).array)
    assert cube.shape == (2, 410, 819)
    np.testing.assert_array_equal(cube[1], single)   # CCDCHIP 2 = first SCI HDU
    assert not np.array_equal(cube[0], cube[1])


def test_mosaic_raises_without_ccdchip_headers() -> None:
    """If a mosaic is requested but no extension carries CCDCHIP, the chip order
    is unknowable and the reader rejects the file."""
    with fits.open(FLT) as hdulist:
        for hdu in hdulist:
            hdu.header.remove('CCDCHIP', ignore_missing=True, remove_all=True)
        with pytest.raises(ValueError, match='Unrecognized WFC3 image file structure'):
            HST_WFC3.detect_in_fits(hdulist, str(FLT), mosaic=True)


def test_mosaic_raises_when_selected_hdu_not_image(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Defensive guard on the mosaic path: a selected non-IMAGE HDU is rejected.
    Normal input can't reach this (``get_fits_image_hdu`` validates the HDU
    first), so it is forced by making ``get_fits_image_hdus`` yield a table."""
    import picmaker.instruments.hst_wfc3 as mod
    with fits.open(FLT) as hdulist:
        table_hdu = hdulist['WCSCORR']
        monkeypatch.setattr(mod, 'get_fits_image_hdus', lambda *a, **k: [table_hdu])
        with pytest.raises(ValueError, match='not an IMAGE'):
            HST_WFC3.detect_in_fits(hdulist, str(FLT), mosaic=True)
