"""Read, mosaic-assembly, and mosaic-pipeline checks for HST WF/PC (WFPC1).

Like WFPC2, a WFPC1 science product stores its detectors as a cube in the
PRIMARY HDU with a group-parameters table in the second HDU. Two shrunk samples
are bundled: a four-detector ``_c0f`` file (Wide Field chips 1-4, filter F718M)
and a single-detector ``_c0f`` file (chip 6, filter F284W). Their single-plane
geometry cannot be represented by the synthetic fixtures, so WFPC1 is tested
against real data.
"""

import shutil
import warnings
from pathlib import Path

import astropy.io.fits as pyfits
import numpy as np
import pytest
from astropy.io.fits.verify import VerifyWarning
from PIL import Image

from picmaker.instruments import read_image_array, tint_by_nm
from picmaker.instruments.hst_wfpc import HST_WFPC
from picmaker.options import get_parser
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
    inst = HST_WFPC(np.zeros((4, 8, 8, 3)), None, None, True, None)
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
    options = vars(get_parser().parse_args([
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


# --- multi-extension FITS (_c0m) layout -----------------------------------------------

def _wfpc_mef(planes: list[np.ndarray], detectors: list[int],
              **header: str) -> pyfits.HDUList:
    """A minimal multi-extension WFPC HDUList: an empty PRIMARY HDU followed by one
    SCI image extension per detector, each carrying a DETECTOR keyword."""
    primary = pyfits.PrimaryHDU()
    primary.header['INSTRUME'] = 'WFPC'
    for key, value in header.items():
        primary.header[key] = value
    hdus: list[pyfits.PrimaryHDU | pyfits.ImageHDU] = [primary]
    for plane, det in zip(planes, detectors, strict=True):
        ext = pyfits.ImageHDU(plane, name='SCI')
        ext.header['DETECTOR'] = det
        hdus.append(ext)
    return pyfits.HDUList(hdus)


def test_mef_reads_detectors_and_tints() -> None:
    """A _c0m file reads the first detector by default, ``obj=N`` selects the Nth,
    and a _c0m science file carries its filter tint."""
    planes = [np.full((4, 4), float(v)) for v in (1, 2, 3, 4)]
    hdulist = _wfpc_mef(planes, [5, 6, 7, 8], FILTNAM1='F718M')

    data = HST_WFPC.detect_in_fits(hdulist, 'w_c0m.fits')
    np.testing.assert_array_equal(np.asarray(data.array), planes[0])
    assert tuple(data.default_tint) == tuple(tint_by_nm(718))

    data = HST_WFPC.detect_in_fits(hdulist, 'w_c0m.fits', obj=2)
    np.testing.assert_array_equal(np.asarray(data.array), planes[2])


def test_mosaic_places_pc_detectors_modulo_four() -> None:
    """PC detectors 5-8 fill planes 0-3, the same as WF detectors 1-4."""
    planes = [np.full((4, 4), 1.0), np.full((4, 4), 2.0)]
    hdulist = _wfpc_mef(planes, [6, 8])
    cube = np.asarray(HST_WFPC.detect_in_fits(hdulist, 'w_c0m.fits', mosaic=True).array)

    assert cube.shape == (4, 4, 4)
    assert cube[1, 0, 0] == 1.0     # detector 6 -> plane 1
    assert cube[3, 0, 0] == 2.0     # detector 8 -> plane 3
    assert cube[0].sum() == 0.0
    assert cube[2].sum() == 0.0


@pytest.mark.parametrize('detectors', [[1, 2, 3, 4], [5, 6, 7, 8], [1, 3], [6], [5, 8]])
@pytest.mark.parametrize('options', [{}, {'obj': 0}, {'obj': -1}, {'mosaic': True}])
def test_waiver_and_mef_layouts_are_read_identically(detectors: list[int],
                                                     options: dict[str, object]) -> None:
    """The same detectors stored as a _c0f cube or as _c0m extensions yield the same
    array and tint for every selection mode."""
    planes = [np.full((4, 4), 10.0 * det) for det in detectors]
    c0f = _wfpc_hdulist(np.stack(planes), detectors=detectors, FILTNAM1='F718M')
    c0m = _wfpc_mef([p.astype('float32') for p in planes], detectors, FILTNAM1='F718M')

    data_f = HST_WFPC.detect_in_fits(c0f, 'w_c0f.fits', **options)
    data_m = HST_WFPC.detect_in_fits(c0m, 'w_c0m.fits', **options)

    np.testing.assert_array_equal(np.asarray(data_f.array), np.asarray(data_m.array))
    assert np.asarray(data_f.array).shape == np.asarray(data_m.array).shape
    assert data_f.default_tint == data_m.default_tint


# --- data quality masks (--hst-dq) ----------------------------------------------------

def _write_dq_beside_copy(directory: Path,
                          dq_directory: Path | None = None) -> np.ndarray:
    """Copy the four-detector sample into `directory` and write a matching _c1f data
    quality file (same cube shape and group table) into `dq_directory`, defaulting to
    the same directory. Returns the expected boolean mask."""
    dq_directory = dq_directory or directory
    shutil.copy(MOSAIC, directory / MOSAIC.name)

    dq = np.zeros(_raw_cube(MOSAIC).shape, dtype='int16')
    dq[0, :2, :] = 2
    dq[2, 5, 7] = 8
    dq[3, :, -1] = 258
    with pyfits.open(MOSAIC) as hdulist:
        hdulist[0].data = dq
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', VerifyWarning)
            hdulist.writeto(dq_directory / 'w0ck0103t_c1f_small.fits')
    return np.asarray(dq != 0, dtype=bool)


def test_dq_mask_loaded_from_same_directory(tmp_path: Path) -> None:
    """A _c1f file beside the _c0f file is found by default; its nonzero pixels are
    set in both masks, selected like the data for mosaics and for ``obj``."""
    expected = _write_dq_beside_copy(tmp_path)
    data = read_image_array(tmp_path / MOSAIC.name, mosaic=True)
    np.testing.assert_array_equal(data.hmask, expected)
    np.testing.assert_array_equal(data.imask, expected)
    assert data.hmask is not data.imask

    data = read_image_array(tmp_path / MOSAIC.name, obj=3)
    np.testing.assert_array_equal(data.imask, expected[3])


def test_dq_mask_from_hst_dq_directory(tmp_path: Path) -> None:
    """With ``hst_dq``, the data quality file is read from that directory instead."""
    data_dir = tmp_path / 'c0f'
    dq_dir = tmp_path / 'c1f'
    data_dir.mkdir()
    dq_dir.mkdir()
    expected = _write_dq_beside_copy(data_dir, dq_dir)

    data = read_image_array(data_dir / MOSAIC.name)
    assert data.hmask is None
    assert data.imask is None

    data = read_image_array(data_dir / MOSAIC.name, hst_dq=str(dq_dir))
    np.testing.assert_array_equal(data.hmask, expected[0])


def test_bundled_samples_have_no_dq_mask() -> None:
    """The bundled samples have no data quality files beside them."""
    for path in (MOSAIC, SINGLE):
        data = read_image_array(path)
        assert data.hmask is None
        assert data.imask is None
