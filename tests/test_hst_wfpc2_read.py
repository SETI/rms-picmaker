"""Read, mosaic-assembly, and mosaic-pipeline checks for HST WFPC2.

Real WFPC2 products store the four detectors (PC1, WF2, WF3, WF4) as a data
cube in the PRIMARY HDU, with a group-parameters table in the second HDU
carrying the ``DETECTOR`` column. Two files are bundled: the ``_c0f`` calibrated
science image (float32, filter F675W, so it carries a filter-derived tint) and
the ``_c1f`` data-quality file (int16, no tint). The synthetic single-plane
fixtures cannot represent this structure, so WFPC2 is tested against real data.
"""

from pathlib import Path

import astropy.io.fits as pyfits
import numpy as np
import pytest
from PIL import Image

from picmaker.instruments import read_image_array, tint_by_nm
from picmaker.instruments.hst_wfpc2 import HST_WFPC2
from picmaker.options import get_parser
from picmaker.picmaker import picmaker, validate_options

DATA_DIR = Path(__file__).parent.parent / 'test_files' / 'hst_wfpc2'
SCIENCE = DATA_DIR / 'u2tf0504t_c0f.fits'   # _c0f: calibrated science (float32)
QUALITY = DATA_DIR / 'u2tf0504t_c1f.fits'   # _c1f: data quality (int16)


def _raw_cube(path: Path) -> np.ndarray:
    """The raw PRIMARY ``(4, 400, 400)`` detector cube, read directly with astropy.

    Only the PRIMARY HDU is touched, so the malformed group-table keyword (which
    trips a VerifyWarning) is never read here.
    """
    with pyfits.open(path) as hdulist:
        return np.array(hdulist[0].data)


# --- reading -------------------------------------------------------------------------

def test_c0f_reads_single_detector_with_filter_tint() -> None:
    """The _c0f science file reads one 400x400 detector by default and carries
    the tint derived from its filter."""
    data = read_image_array(SCIENCE)
    assert np.asarray(data.array).shape == (400, 400)
    assert data.default_upward is True
    assert tuple(data.default_tint) == (255, 98, 98)


def test_c1f_reads_without_tint() -> None:
    """The _c1f data-quality file reads the same geometry but carries no tint;
    only _c0f science files derive a filter tint."""
    data = read_image_array(QUALITY)
    assert np.asarray(data.array).shape == (400, 400)
    assert data.default_tint is None


def test_default_and_obj_read_the_matching_raw_detector_planes() -> None:
    """A default read returns the first detector plane; ``obj=N`` returns the Nth
    plane — byte-for-byte with the raw PRIMARY cube."""
    raw = _raw_cube(SCIENCE)
    np.testing.assert_array_equal(np.asarray(read_image_array(SCIENCE).array), raw[0])
    np.testing.assert_array_equal(
        np.asarray(read_image_array(SCIENCE, obj=0).array), raw[0])
    np.testing.assert_array_equal(
        np.asarray(read_image_array(SCIENCE, obj=2).array), raw[2])


def test_mosaic_returns_the_raw_detector_cube() -> None:
    """``mosaic=True`` returns all four detector planes, matching the raw cube."""
    np.testing.assert_array_equal(
        np.asarray(read_image_array(SCIENCE, mosaic=True).array), _raw_cube(SCIENCE))


def test_tint_matches_the_f675w_filter() -> None:
    """The _c0f tint is exactly the one derived from its FILTNAM1=F675W (675 nm)."""
    tint = read_image_array(SCIENCE).default_tint
    assert tuple(tint) == tuple(tint_by_nm(675))


def test_c1f_preserves_integer_dq_dtype() -> None:
    """The _c1f data-quality pixels are read as integers (int16), not floats."""
    assert np.asarray(read_image_array(QUALITY).array).dtype.kind == 'i'


def test_obj_out_of_range_raises() -> None:
    """Selecting a plane index beyond the detector cube raises IndexError."""
    with pytest.raises(IndexError):
        read_image_array(SCIENCE, obj=99)


# --- mosaic assembly -----------------------------------------------------------------

def test_apply_mosaic_assembles_four_quadrants() -> None:
    """``apply_mosaic`` tiles the four detectors into a ``(2H, 2W, C)`` image.

    It assembles in pre-inversion orientation (the pipeline flips the result
    vertically for the upward display): PC1 lower-right, WF2 lower-left, WF3
    upper-left, WF4 upper-right.
    """
    # Tag each detector plane with its 1-based id so it can be located.
    planes = [np.full((8, 8, 3), v, dtype=float) for v in (1, 2, 3, 4)]
    inst = HST_WFPC2(np.zeros((4, 8, 8, 3)), True, None)
    mosaic = inst.apply_mosaic(planes)

    assert mosaic.shape == (16, 16, 3)

    def q(row: int, col: int) -> int:
        return int(mosaic[row, col, 0])

    assert q(2, 2) == 3     # WF3 upper-left
    assert q(2, 12) == 4    # WF4 upper-right
    assert q(12, 2) == 2    # WF2 lower-left
    assert q(12, 12) == 1   # PC1 lower-right


# --- mosaic pipeline -----------------------------------------------------------------

@pytest.mark.parametrize('name', ['u2tf0504t_c0f.fits', 'u2tf0504t_c1f.fits'])
def test_mosaic_pipeline_renders_2x2(name: str, tmp_path: Path) -> None:
    """``--mosaic`` renders a full 2x2 detector mosaic, twice the single-chip
    size. Both files are exercised: the ``_c1f`` file has no masked pixels, which
    once crashed the per-band mosaic loop (invalid_mask was ``None``)."""
    options = validate_options(get_parser().parse_args([
        str(DATA_DIR / name), '--directory', str(tmp_path),
        '--mosaic', '--percentiles', '1', '99',
    ]))
    picmaker(**options)

    out = tmp_path / name.replace('.fits', '.jpg')
    assert out.exists()
    with Image.open(out) as img:
        assert img.size == (800, 800)   # 2 x the 400x400 single detector


# --- partial-mosaic / no-tint branches, via synthetic in-memory HDULists --------------

def _synth_wfpc2(array: np.ndarray, detectors: list[int] | None = None,
                 **header: str) -> pyfits.HDUList:
    """A minimal WFPC2 HDUList: a primary-HDU image plus an optional
    group-parameters table carrying a DETECTOR column."""
    primary = pyfits.PrimaryHDU(array.astype('float32'))
    primary.header['TELESCOP'] = 'HST'
    primary.header['INSTRUME'] = 'WFPC2'
    for key, value in header.items():
        primary.header[key] = value
    hdus = [primary]
    if detectors is not None:
        col = pyfits.Column(name='DETECTOR', format='J', array=np.array(detectors))
        hdus.append(pyfits.BinTableHDU.from_columns([col]))
    return pyfits.HDUList(hdus)


def test_mosaic_fills_missing_detectors_from_table() -> None:
    """A file with fewer than four planes is expanded to a four-plane cube using
    the group table's DETECTOR column."""
    array = np.stack([np.full((4, 4), 1.0), np.full((4, 4), 2.0)])  # PC1 and WF3
    hdulist = _synth_wfpc2(array, detectors=[1, 3], FILTNAM1='F675W')
    cube = np.asarray(HST_WFPC2.detect_in_fits(hdulist, 'u_c0f.fits', mosaic=True).array)

    assert cube.shape == (4, 4, 4)
    assert cube[0, 0, 0] == 1.0     # detector 1 -> plane 0
    assert cube[2, 0, 0] == 2.0     # detector 3 -> plane 2
    assert cube[1].sum() == 0.0     # unfilled planes stay zero


def test_all_undiagnostic_filters_have_no_tint() -> None:
    """A science file whose filters are all undiagnostic (e.g. a polarizer) has
    no diagnostic wavelength."""
    hdulist = _synth_wfpc2(np.zeros((4, 4)), FILTNAM1='POL0', FILTNAM2='')
    data = HST_WFPC2.detect_in_fits(hdulist, 'u_c0f.fits')
    assert data.default_tint is None
