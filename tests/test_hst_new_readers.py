"""Read and detection tests for the HST COS, FOC, and STIS readers.

Each reader recognizes its instrument from the FITS headers and reads the
science image:

* COS uses a broadband NUV mirror (MIRRORA / MIRRORB) for imaging, so there is
  no wavelength filter and no default tint.
* STIS imaging filters are named descriptively ("Clear", "OIII", ...) with no
  embedded wavelength, so they carry no default tint.
* FOC predates the modern HST FITS convention (image in the primary HDU, no
  TELESCOP keyword) and encodes its filter wavelength in FILTNAM1 / FILTNAM2,
  like WFPC2, so it does derive a tint.

The samples live under test_files/, matching how HST WFPC2 is tested against
real data — the synthetic single-plane fixtures cannot represent these
multi-extension / primary-HDU structures.
"""

import shutil
from pathlib import Path

import astropy.io.fits as pyfits
import numpy as np
import pytest

from picmaker.instruments import read_image_array, tint_by_nm
from picmaker.instruments.hst_acs import HST_ACS
from picmaker.instruments.hst_cos import HST_COS
from picmaker.instruments.hst_foc import HST_FOC
from picmaker.instruments.hst_stis import HST_STIS

DATA = Path(__file__).parent.parent / 'test_files'
COS = DATA / 'hst_cos' / 'ldaw09p5q_rawacq_small.fits'  # NUV imaging (MIRRORB), shrunk
FOC = DATA / 'hst_foc' / 'x2490106t_d0f.fits'       # FILTNAM1=F220W, FILTNAM2=CLEAR2
FOC_WHEEL4 = DATA / 'hst_foc' / 'x1305601t_d0f.fits'  # CLEAR1/2/3, F278M on wheel 4
STIS = DATA / 'hst_stis' / 'o43v17scq_raw.fits'     # CCD, APERTURE=F28X50LP


class _HDU:
    """Minimal stand-in for a single FITS HDU exposing a ``.header`` mapping."""

    def __init__(self, header: dict[str, str]) -> None:
        self.header = header


# --- reading real files --------------------------------------------------------------

def test_cos_reads_nuv_image_without_tint() -> None:
    """A COS NUV image is recognized and read; broadband mirror imaging carries
    no filter-derived tint."""
    data = read_image_array(COS)
    assert isinstance(data, HST_COS)
    assert np.asarray(data.array).ndim == 2
    assert data.default_upward is True
    assert data.default_tint is None


def test_foc_reads_with_filter_tint() -> None:
    """An FOC image is read and carries the tint derived from its FILTNAM
    filter (F220W, in the UV)."""
    data = read_image_array(FOC)
    assert isinstance(data, HST_FOC)
    assert np.asarray(data.array).ndim == 2
    assert data.default_upward is True
    assert tuple(data.default_tint) == tuple(tint_by_nm(220))


def test_foc_reads_all_four_filter_wheels() -> None:
    """FOC has four filter wheels and the diagnostic filter may sit on any of
    them. This file is clear on wheels 1-3 and carries F278M on wheel 4, so its
    tint is derived from that fourth wheel."""
    data = read_image_array(FOC_WHEEL4)
    assert isinstance(data, HST_FOC)
    assert tuple(data.default_tint) == tuple(tint_by_nm(278))


def test_stis_ccd_image_has_aperture_tint() -> None:
    """A STIS CCD image is read and tinted from its imaging aperture's pivot
    wavelength (F28X50LP -> 722.9 nm, unscaled on the CCD)."""
    data = read_image_array(STIS)
    assert isinstance(data, HST_STIS)
    assert np.asarray(data.array).ndim == 2
    assert data.default_upward is True
    assert tuple(data.default_tint) == tuple(tint_by_nm(722.9))


# --- detection rejects non-matching products -----------------------------------------

def test_cos_rejects_foreign_fits() -> None:
    """A non-HST or non-COS FITS is not a COS product."""
    assert HST_COS.detect_in_fits([_HDU({'TELESCOP': 'NOT-HST'})], 'x') is None
    assert HST_COS.detect_in_fits(
        [_HDU({'TELESCOP': 'HST', 'INSTRUME': 'ACS'})], 'x') is None


def test_stis_rejects_foreign_fits() -> None:
    """A non-HST or non-STIS FITS is not a STIS product."""
    assert HST_STIS.detect_in_fits([_HDU({'TELESCOP': 'NOT-HST'})], 'x') is None
    assert HST_STIS.detect_in_fits(
        [_HDU({'TELESCOP': 'HST', 'INSTRUME': 'ACS'})], 'x') is None


def test_foc_rejects_foreign_fits() -> None:
    """FOC has no TELESCOP keyword, so it matches on INSTRUME alone; a different
    instrument (or a header with no INSTRUME) is rejected."""
    assert HST_FOC.detect_in_fits([_HDU({'INSTRUME': 'WFPC2'})], 'x') is None
    assert HST_FOC.detect_in_fits([_HDU({})], 'x') is None


# --- no-tint branches, via synthetic in-memory HDULists ------------------------------

def _stis_hdulist(aperture: str, detector: str = 'CCD') -> pyfits.HDUList:
    """A minimal STIS HDUList: primary header plus a small SCI image."""
    primary = pyfits.PrimaryHDU()
    primary.header['TELESCOP'] = 'HST'
    primary.header['INSTRUME'] = 'STIS'
    primary.header['DETECTOR'] = detector
    primary.header['APERTURE'] = aperture
    sci = pyfits.ImageHDU(np.zeros((4, 4), dtype='float32'), name='SCI')
    return pyfits.HDUList([primary, sci])


def _foc_hdulist(**filtnam: str) -> pyfits.HDUList:
    """A minimal FOC HDUList: a small primary-HDU image with the given filters."""
    primary = pyfits.PrimaryHDU(np.zeros((4, 4), dtype='float32'))
    primary.header['INSTRUME'] = 'FOC'
    for key, value in filtnam.items():
        primary.header[key] = value
    return pyfits.HDUList([primary])


def test_stis_unknown_aperture_has_no_tint() -> None:
    """A STIS aperture that is not in the wavelength table yields no tint."""
    data = HST_STIS.detect_in_fits(_stis_hdulist('25MAMA', 'FUV-MAMA'), 'x')
    assert data.default_tint is None


def test_stis_non_science_hdu_has_no_tint() -> None:
    """When the selected HDU is not a science ('SCI') extension, no tint applies."""
    primary = pyfits.PrimaryHDU(np.zeros((4, 4), dtype='float32'))
    primary.header['TELESCOP'] = 'HST'
    primary.header['INSTRUME'] = 'STIS'
    data = HST_STIS.detect_in_fits(pyfits.HDUList([primary]), 'x')
    assert data.default_tint is None


def test_foc_non_science_file_has_no_tint() -> None:
    """FOC tints only its _c0f / _d0f science files; a _c1f data-quality file
    carries no tint even with a diagnostic filter."""
    data = HST_FOC.detect_in_fits(_foc_hdulist(FILTNAM1='F175W'), 'x2ip0201t_c1f.fits')
    assert data.default_tint is None


def test_foc_all_clear_filters_have_no_tint() -> None:
    """An FOC science file with every wheel clear has no diagnostic wavelength."""
    hdulist = _foc_hdulist(FILTNAM1='CLEAR1', FILTNAM2='CLEAR2',
                           FILTNAM3='CLEAR3', FILTNAM4='CLEAR4')
    data = HST_FOC.detect_in_fits(hdulist, 'foo_d0f.fits')
    assert data.default_tint is None


# --- FOC multi-extension layout and data quality masks --------------------------------

def _raw_foc() -> np.ndarray:
    """The bundled FOC sample's PRIMARY image."""
    with pyfits.open(FOC) as hdulist:
        return np.array(hdulist[0].data)


def test_foc_mef_reads_like_the_waiver_layout() -> None:
    """A _d0m file (empty PRIMARY, one SCI extension) reads the same image and tint
    as the equivalent _d0f file."""
    image = np.arange(16, dtype='float32').reshape(4, 4)
    d0f = _foc_hdulist(FILTNAM1='F220W')
    d0f[0].data = image

    primary = pyfits.PrimaryHDU()
    primary.header['INSTRUME'] = 'FOC'
    primary.header['FILTNAM1'] = 'F220W'
    d0m = pyfits.HDUList([primary, pyfits.ImageHDU(image, name='SCI')])

    data_f = HST_FOC.detect_in_fits(d0f, 'x_d0f.fits')
    data_m = HST_FOC.detect_in_fits(d0m, 'x_d0m.fits')
    np.testing.assert_array_equal(data_f.array, image)
    np.testing.assert_array_equal(data_m.array, image)
    assert data_f.default_tint == data_m.default_tint == tint_by_nm(220)
    assert data_m.hmask is None
    assert data_m.imask is None


def _foc_image(image: np.ndarray) -> pyfits.HDUList:
    """A minimal FOC HDUList holding `image` in its PRIMARY HDU."""
    primary = pyfits.PrimaryHDU(image)
    primary.header['INSTRUME'] = 'FOC'
    return pyfits.HDUList([primary])


def _write_foc_q0f(directory: Path) -> np.ndarray:
    """Write a _q0f data quality file for the bundled FOC sample into `directory`,
    with the sample's geometry and a few flagged pixels; return the expected mask."""
    dq = np.zeros(_raw_foc().shape, dtype='float32')
    dq[0, :] = 1.
    dq[10, 20] = 4.
    primary = pyfits.PrimaryHDU(dq)
    primary.header['INSTRUME'] = 'FOC'
    primary.writeto(directory / 'x2490106t_q0f.fits')
    return np.asarray(dq != 0, dtype=bool)


def test_foc_d0f_reads_its_q0f_mask(tmp_path: Path) -> None:
    """A _q0f beside the _d0f file is found by default; with ``hst_dq`` it is read
    from that directory instead. Nonzero pixels are set in both masks."""
    shutil.copy(FOC, tmp_path / FOC.name)
    expected = _write_foc_q0f(tmp_path)
    data = read_image_array(tmp_path / FOC.name)
    np.testing.assert_array_equal(data.hmask, expected)
    np.testing.assert_array_equal(data.imask, expected)
    assert data.hmask is not data.imask

    dq_dir = tmp_path / 'q0f'
    dq_dir.mkdir()
    expected = _write_foc_q0f(dq_dir)
    data = read_image_array(FOC, hst_dq=str(dq_dir))
    np.testing.assert_array_equal(data.hmask, expected)


@pytest.mark.parametrize('code', ['c0f', 'c1f', 'c0m'])
def test_foc_calibrated_products_have_no_mask(tmp_path: Path, code: str) -> None:
    """Calibrated FOC files are never masked, even with the raw _q0 data quality file
    and a _c1 file beside them."""
    image = np.ones((4, 4), dtype='float32')
    dq = np.ones((4, 4), dtype='float32')
    layout = code[-1]
    _foc_image(image).writeto(tmp_path / f'x_{code}.fits')
    _foc_image(image).writeto(tmp_path / f'x_c1{layout}.fits', overwrite=True)
    _foc_image(dq).writeto(tmp_path / f'x_q0{layout}.fits')

    data = read_image_array(tmp_path / f'x_{code}.fits')
    assert data.hmask is None
    assert data.imask is None


def test_foc_bundled_samples_have_no_dq_mask() -> None:
    """The bundled FOC samples have no _q0f files beside them."""
    for path in (FOC, FOC_WHEEL4):
        data = read_image_array(path)
        assert data.hmask is None
        assert data.imask is None


# --- DQ extension masks (ACS, COS, NICMOS, STIS, WFC3) --------------------------------

ACS_FLT = DATA / 'hst_acs' / 'j96o01ipq_flt_small.fits'
WFC3_FLT = DATA / 'hst_wfc3' / 'iepl0jltq_flt_small.fits'


def _dq_nonzero(path: Path, extver: int = 1) -> np.ndarray:
    """The DQ extension with the given EXTVER as a boolean mask of flagged pixels. For
    ACS and WFC3, a value of 64 (warm pixel) alone is not flagged."""
    ignore = 64 if path.parent.name in ('hst_acs', 'hst_wfc3') else 0
    with pyfits.open(path) as hdulist:
        dq = np.asarray(hdulist['DQ', extver].data, dtype=np.int64)
    return np.asarray((dq & ~ignore) != 0, dtype=bool)


@pytest.mark.parametrize('path', [
    ACS_FLT,
    WFC3_FLT,
    DATA / 'hst_nicmos' / 'nb06030a0_mos.fits',
    COS,
])
def test_sci_image_uses_its_dq_extension(path: Path) -> None:
    """An image read from a SCI HDU takes its masks from the DQ extension of the same
    EXTVER: every nonzero value is set in both, as separate arrays."""
    data = read_image_array(path)
    expected = _dq_nonzero(path)
    np.testing.assert_array_equal(data.hmask, expected)
    np.testing.assert_array_equal(data.imask, expected)
    assert data.hmask is not data.imask


@pytest.mark.parametrize('path', [ACS_FLT, WFC3_FLT])
def test_two_chip_mosaic_places_each_dq_mask_with_its_chip(path: Path) -> None:
    """In an ACS/WFC or WFC3/UVIS mosaic, each chip's DQ mask lands in the same plane
    as its data (the first SCI HDU is chip 2, so it goes to plane 1)."""
    data = read_image_array(path, mosaic=True)
    assert data.hmask.shape == np.shape(data.array) == (2, *_dq_nonzero(path).shape)
    np.testing.assert_array_equal(data.hmask[1], _dq_nonzero(path, 1))
    np.testing.assert_array_equal(data.hmask[0], _dq_nonzero(path, 2))
    np.testing.assert_array_equal(data.imask, data.hmask)


@pytest.mark.parametrize('path', [
    DATA / 'hst_acs' / 'j96o01ipq_raw_small.fits',
    DATA / 'hst_wfc3' / 'iepl0jltq_raw_small.fits',
    STIS,
])
def test_constant_zero_dq_extension_gives_an_empty_mask(path: Path) -> None:
    """A raw file's DQ extension holds no array, only PIXVALUE = 0, which yields an
    all-False mask of the image's shape."""
    data = read_image_array(path)
    assert data.hmask.shape == np.shape(data.array)
    assert not data.hmask.any()
    assert not data.imask.any()


@pytest.mark.parametrize('path', [
    DATA / 'hst_acs' / 'j96o01010_drz_small.fits',     # drizzled: no DQ extension
    DATA / 'hst_wfc3' / 'iepl0j020_drz_small.fits',
])
def test_no_dq_extension_gives_no_mask(path: Path) -> None:
    """A drizzled product with no DQ extension reads without masks."""
    data = read_image_array(path)
    assert data.hmask is None
    assert data.imask is None


def test_non_science_hdu_gets_no_dq_mask() -> None:
    """Selecting a non-SCI HDU (here the ERR extension) uses no DQ mask."""
    data = read_image_array(ACS_FLT, obj=1)
    assert data.hmask is None
    assert data.imask is None


def test_get_sci_dq_mask_matches_extver_and_pixvalue() -> None:
    """The DQ extension is matched by EXTVER; a constant DQ uses PIXVALUE; a DQ of the
    wrong shape is rejected."""
    from picmaker.instruments._hst_support import get_sci_dq_mask

    sci1 = pyfits.ImageHDU(np.zeros((2, 3), dtype='float32'), name='SCI', ver=1)
    sci2 = pyfits.ImageHDU(np.zeros((2, 3), dtype='float32'), name='SCI', ver=2)
    dq2 = pyfits.ImageHDU(np.array([[0, 4, 0], [0, 0, 1]], dtype='int16'), name='DQ',
                          ver=2)
    dq1 = pyfits.ImageHDU(name='DQ', ver=1)
    dq1.header['PIXVALUE'] = 8
    hdulist = pyfits.HDUList([pyfits.PrimaryHDU(), sci1, sci2, dq2, dq1])

    np.testing.assert_array_equal(get_sci_dq_mask(hdulist, sci2),
                                  [[False, True, False], [False, False, True]])
    np.testing.assert_array_equal(get_sci_dq_mask(hdulist, sci1), np.ones((2, 3)))
    assert get_sci_dq_mask(hdulist, dq2) is None                  # not a SCI HDU
    assert get_sci_dq_mask(pyfits.HDUList([sci1]), sci1) is None   # no DQ at all

    bad = pyfits.HDUList([sci1, pyfits.ImageHDU(np.zeros((3, 3)), name='DQ', ver=1)])
    with pytest.raises(ValueError, match='DQ extension'):
        get_sci_dq_mask(bad, sci1)


def _acs_hdulist(detector: str, dqs: list[np.ndarray],
                 instrument: str = 'ACS') -> pyfits.HDUList:
    """A minimal ACS (or WFC3) HDUList with one SCI/ERR/DQ triple per DQ array; the
    chips are numbered 2, 1 as in two-chip files."""
    primary = pyfits.PrimaryHDU()
    primary.header['TELESCOP'] = 'HST'
    primary.header['INSTRUME'] = instrument
    primary.header['DETECTOR'] = detector
    hdus: list[pyfits.PrimaryHDU | pyfits.ImageHDU] = [primary]
    for ver, dq in enumerate(dqs, start=1):
        sci = pyfits.ImageHDU(np.ones(dq.shape, dtype='float32'), name='SCI', ver=ver)
        sci.header['CCDCHIP'] = 3 - ver
        err = pyfits.ImageHDU(np.zeros(dq.shape, dtype='float32'), name='ERR', ver=ver)
        hdus += [sci, err, pyfits.ImageHDU(dq, name='DQ', ver=ver)]
    return pyfits.HDUList(hdus)


@pytest.mark.parametrize(('instrument', 'detector'), [
    ('ACS', 'HRC'), ('ACS', 'WFC'), ('WFC3', 'UVIS'), ('WFC3', 'IR'),
])
def test_acs_and_wfc3_do_not_mask_warm_pixels_alone(instrument: str,
                                                    detector: str) -> None:
    """ACS and WFC3 leave pixels whose DQ value is exactly 64 (warm pixel) unmasked;
    64 combined with another flag is still masked. Two-chip mosaics (ACS/WFC,
    WFC3/UVIS) follow the same rule on each chip."""
    from picmaker.instruments.hst_wfc3 import HST_WFC3

    reader = HST_ACS if instrument == 'ACS' else HST_WFC3
    dq = np.array([[0, 64, 64 + 16, 16]], dtype='int16')
    expected = [[False, False, True, True]]

    data = reader.detect_in_fits(_acs_hdulist(detector, [dq], instrument), 'x_flt.fits')
    np.testing.assert_array_equal(data.hmask, expected)
    np.testing.assert_array_equal(data.imask, expected)

    if detector in ('WFC', 'UVIS'):
        dq2 = np.array([[64, 64, 1, 0]], dtype='int16')
        hdulist = _acs_hdulist(detector, [dq, dq2], instrument)
        data = reader.detect_in_fits(hdulist, 'x_flt.fits', mosaic=True)
        np.testing.assert_array_equal(data.hmask[1], expected)      # chip 2
        np.testing.assert_array_equal(data.hmask[0], [[False, False, True, False]])


def test_other_instruments_mask_warm_pixel_value() -> None:
    """Instruments other than ACS and WFC3 mask every nonzero DQ value, including 64."""
    from picmaker.instruments.hst_nicmos import HST_NICMOS

    dq = np.array([[0, 64, 64 + 16, 16]], dtype='int16')
    hdulist = _acs_hdulist('NIC2', [dq], instrument='NICMOS')
    hdulist[0].header['FILTER'] = 'F110W'
    data = HST_NICMOS.detect_in_fits(hdulist, 'n_cal.fits')
    np.testing.assert_array_equal(data.hmask, [[False, True, True, True]])


@pytest.mark.parametrize('dtype', ['int16', 'uint16', 'int32'])
def test_get_sci_dq_mask_ignore_bits(dtype: str) -> None:
    """``ignore`` drops the given flag bits, for array and constant DQ extensions and
    for signed or unsigned DQ data."""
    from picmaker.instruments._hst_support import get_sci_dq_mask

    sci = pyfits.ImageHDU(np.zeros((1, 4), dtype='float32'), name='SCI', ver=1)
    dq = pyfits.ImageHDU(np.array([[0, 64, 65, 128]], dtype=dtype), name='DQ', ver=1)
    hdulist = pyfits.HDUList([pyfits.PrimaryHDU(), sci, dq])
    np.testing.assert_array_equal(get_sci_dq_mask(hdulist, sci, ignore=64),
                                  [[False, False, True, True]])
    np.testing.assert_array_equal(get_sci_dq_mask(hdulist, sci),
                                  [[False, True, True, True]])

    const = pyfits.ImageHDU(name='DQ', ver=1)
    const.header['PIXVALUE'] = 64
    hdulist = pyfits.HDUList([pyfits.PrimaryHDU(), sci, const])
    assert not get_sci_dq_mask(hdulist, sci, ignore=64).any()
    assert get_sci_dq_mask(hdulist, sci).all()
