"""Read, mosaic-assembly, and mosaic-pipeline checks for HST WF/PC (WFPC1).

Like WFPC2, a WFPC1 science product stores its detectors as a cube in the
PRIMARY HDU with a group-parameters table in the second HDU. Two shrunk samples
are bundled: a four-detector ``_c0f`` file (Wide Field chips 1-4, filter F718M)
and a single-detector ``_c0f`` file (chip 6, filter F284W). Their single-plane
geometry cannot be represented by the synthetic fixtures, so WFPC1 is tested
against real data.
"""

from pathlib import Path

import astropy.io.fits as pyfits
import numpy as np
import pytest
from PIL import Image

from picmaker.instruments import read_image_array, tint_by_nm
from picmaker.instruments.hst_wfpc import HST_WFPC
from picmaker.options import get_parser, validate_options
from picmaker.picmaker import picmaker

DATA_DIR = Path(__file__).parent.parent / 'test_files' / 'hst_wfpc'
MOSAIC = DATA_DIR / 'w0ck0103t_c0f_small.fits'   # four detectors, FILTNAM1=F718M
SINGLE = DATA_DIR / 'w0nq0108t_c0f_small.fits'   # one detector, FILTNAM1=F284W


class _HDU:
    """Minimal stand-in for a single FITS HDU exposing a ``.header`` mapping."""

    def __init__(self, header: dict[str, str]) -> None:
        self.header = header


def _raw_cube(path: Path) -> np.ndarray:
    """The raw PRIMARY detector cube, read directly with astropy.

    Only the PRIMARY HDU is touched, so the malformed group-table keyword (which
    trips a VerifyWarning) is never read here.
    """
    with pyfits.open(path) as hdulist:
        return np.array(hdulist[0].data)


# --- reading -------------------------------------------------------------------------

def test_reads_first_detector_with_filter_tint() -> None:
    """A default read returns the first detector plane, tinted from F718M."""
    data = read_image_array(MOSAIC)
    assert np.asarray(data.array).shape == (160, 160)
    assert data.default_upward is True
    assert tuple(data.default_tint) == tuple(tint_by_nm(718))


def test_single_detector_file_reads_and_tints() -> None:
    """A single-detector file reads its one plane and tints from F284W."""
    data = read_image_array(SINGLE)
    assert np.asarray(data.array).shape == (160, 160)
    assert tuple(data.default_tint) == tuple(tint_by_nm(284))


def test_default_and_obj_read_the_matching_detector_planes() -> None:
    """A default read returns detector plane 0; ``obj=N`` returns the Nth plane,
    byte-for-byte with the raw PRIMARY cube."""
    raw = _raw_cube(MOSAIC)
    np.testing.assert_array_equal(np.asarray(read_image_array(MOSAIC).array), raw[0])
    np.testing.assert_array_equal(
        np.asarray(read_image_array(MOSAIC, obj=2).array), raw[2])


def test_mosaic_returns_the_four_detector_cube() -> None:
    """``mosaic=True`` returns all four detector planes, matching the raw cube."""
    np.testing.assert_array_equal(
        np.asarray(read_image_array(MOSAIC, mosaic=True).array), _raw_cube(MOSAIC))


# --- mosaic assembly -----------------------------------------------------------------

def test_apply_mosaic_assembles_four_quadrants() -> None:
    """``apply_mosaic`` tiles the four detectors into a ``(2H, 2W, C)`` image,
    in pre-inversion orientation: chip 1 lower-right, 2 lower-left, 3 upper-left,
    4 upper-right."""
    planes = [np.full((8, 8, 3), v, dtype=float) for v in (1, 2, 3, 4)]
    inst = HST_WFPC(np.zeros((4, 8, 8, 3)), True, None)
    mosaic = inst.apply_mosaic(planes)

    assert mosaic.shape == (16, 16, 3)

    def q(row: int, col: int) -> int:
        return int(mosaic[row, col, 0])

    assert q(2, 2) == 3      # chip 3 upper-left
    assert q(2, 12) == 4     # chip 4 upper-right
    assert q(12, 2) == 2     # chip 2 lower-left
    assert q(12, 12) == 1    # chip 1 lower-right


# --- mosaic pipeline -----------------------------------------------------------------

def test_mosaic_pipeline_renders_2x2(tmp_path: Path) -> None:
    """``--mosaic`` renders a full 2x2 detector mosaic, twice the single-chip
    size (160 -> 320)."""
    options = validate_options(get_parser().parse_args([
        str(MOSAIC), '--directory', str(tmp_path),
        '--mosaic', '--percentiles', '1', '99',
    ]))
    picmaker(**options)

    out = tmp_path / 'w0ck0103t_c0f_small.jpg'
    assert out.exists()
    with Image.open(out) as img:
        assert img.size == (320, 320)


# --- detection -----------------------------------------------------------------------

def test_rejects_foreign_fits() -> None:
    """A non-WFPC FITS (WFPC1 matches on INSTRUME alone) is rejected."""
    assert HST_WFPC.detect_in_fits([_HDU({'INSTRUME': 'WFPC2'})], 'x') is None
    assert HST_WFPC.detect_in_fits([_HDU({})], 'x') is None


def test_obj_out_of_range_raises() -> None:
    """A plane index beyond the detector cube raises IndexError."""
    with pytest.raises(IndexError):
        read_image_array(MOSAIC, obj=99)


# --- no-tint and partial-mosaic branches, via synthetic in-memory HDULists ------------

def _wfpc_hdulist(array: np.ndarray, detectors: list[int] | None = None,
                  **header: str) -> pyfits.HDUList:
    """A minimal WFPC HDUList: a primary-HDU image plus an optional
    group-parameters table carrying a DETECTOR column."""
    primary = pyfits.PrimaryHDU(array.astype('float32'))
    primary.header['INSTRUME'] = 'WFPC'
    for key, value in header.items():
        primary.header[key] = value
    hdus = [primary]
    if detectors is not None:
        col = pyfits.Column(name='DETECTOR', format='J', array=np.array(detectors))
        hdus.append(pyfits.BinTableHDU.from_columns([col]))
    return pyfits.HDUList(hdus)


def test_non_science_file_has_no_tint() -> None:
    """WFPC tints only its _c0f / _d0f science files; a _c1f file has no tint
    even with a diagnostic filter."""
    data = HST_WFPC.detect_in_fits(
        _wfpc_hdulist(np.zeros((4, 4)), FILTNAM1='F718M'), 'w_c1f.fits')
    assert data.default_tint is None


def test_all_undiagnostic_filters_have_no_tint() -> None:
    """A science file whose filters are all undiagnostic (e.g. a polarizer) has
    no diagnostic wavelength."""
    data = HST_WFPC.detect_in_fits(
        _wfpc_hdulist(np.zeros((4, 4)), FILTNAM1='POL0', FILTNAM2=''), 'w_c0f.fits')
    assert data.default_tint is None


def test_mosaic_fills_missing_detectors_from_the_table() -> None:
    """A file with fewer than four planes is expanded to a four-plane cube using
    the group table's DETECTOR column."""
    array = np.stack([np.full((4, 4), 1.0), np.full((4, 4), 2.0)])  # 2 planes
    hdulist = _wfpc_hdulist(array, detectors=[1, 3], FILTNAM1='F718M')
    cube = np.asarray(HST_WFPC.detect_in_fits(hdulist, 'w_c0f.fits', mosaic=True).array)

    assert cube.shape == (4, 4, 4)
    assert cube[0, 0, 0] == 1.0     # detector 1 -> plane 0
    assert cube[2, 0, 0] == 2.0     # detector 3 -> plane 2
    assert cube[1].sum() == 0.0     # unfilled planes stay zero
