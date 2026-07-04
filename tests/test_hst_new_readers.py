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

from pathlib import Path

import astropy.io.fits as pyfits
import numpy as np

from picmaker.instruments import read_image_array, tint_by_nm
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
