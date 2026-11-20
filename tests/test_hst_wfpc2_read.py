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
from picmaker.options import deconflict_options, get_parser, validate_options
from picmaker.picmaker import picmaker

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
    inst = HST_WFPC2(np.zeros((4, 8, 8, 3)), None, None, True, None)
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
    once crashed the per-band mosaic loop (invalid_mask was ``None``). The output is
    grayscale because each quadrant renders only its own detector."""
    options = vars(get_parser().parse_args([
        str(DATA_DIR / name), '--directory', str(tmp_path),
        '--mosaic', '--percentiles', '1', '99',
    ]))
    picmaker(**options)

    out = tmp_path / name.replace('.fits', '.jpg')
    assert out.exists()
    with Image.open(out) as img:
        assert img.size == (800, 800)   # 2 x the 400x400 single detector
        # Each quadrant is its own detector in grayscale, not an RGB composite of the
        # first three detectors
        assert img.mode == 'L'


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


# --- multi-extension FITS (_c0m) layout -----------------------------------------------

def _synth_wfpc2_mef(planes: list[np.ndarray], detectors: list[int],
                     **header: str) -> pyfits.HDUList:
    """A minimal multi-extension WFPC2 HDUList: an empty PRIMARY HDU followed by one
    SCI image extension per detector, each carrying a DETECTOR keyword."""
    primary = pyfits.PrimaryHDU()
    primary.header['TELESCOP'] = 'HST'
    primary.header['INSTRUME'] = 'WFPC2'
    for key, value in header.items():
        primary.header[key] = value
    hdus: list[pyfits.PrimaryHDU | pyfits.ImageHDU] = [primary]
    for plane, det in zip(planes, detectors, strict=True):
        ext = pyfits.ImageHDU(plane.astype('float32'), name='SCI')
        ext.header['DETECTOR'] = det
        hdus.append(ext)
    return pyfits.HDUList(hdus)


def test_mef_reads_detectors_from_extensions() -> None:
    """A _c0m file (empty PRIMARY, one SCI extension per detector) reads the first
    detector by default, ``obj=N`` selects the Nth, and the filter tint applies."""
    planes = [np.full((4, 4), float(v)) for v in (1, 2, 3, 4)]
    hdulist = _synth_wfpc2_mef(planes, [1, 2, 3, 4], FILTNAM1='F673N')

    data = HST_WFPC2.detect_in_fits(hdulist, 'u_c0m.fits')
    np.testing.assert_array_equal(np.asarray(data.array), planes[0])
    assert tuple(data.default_tint) == tuple(tint_by_nm(673))

    data = HST_WFPC2.detect_in_fits(hdulist, 'u_c0m.fits', obj=2)
    np.testing.assert_array_equal(np.asarray(data.array), planes[2])


def test_mef_mosaic_places_detectors_by_keyword() -> None:
    """A partial _c0m mosaic places each extension by its DETECTOR keyword."""
    planes = [np.full((4, 4), 1.0), np.full((4, 4), 2.0)]
    hdulist = _synth_wfpc2_mef(planes, [2, 4])
    cube = np.asarray(HST_WFPC2.detect_in_fits(hdulist, 'u_c0m.fits', mosaic=True).array)

    assert cube.shape == (4, 4, 4)
    assert cube[1, 0, 0] == 1.0     # detector 2 -> plane 1
    assert cube[3, 0, 0] == 2.0     # detector 4 -> plane 3
    assert cube[0].sum() == 0.0
    assert cube[2].sum() == 0.0


def test_mef_full_mosaic_returns_all_planes() -> None:
    """A complete four-detector _c0m mosaic stacks the extensions in order."""
    planes = [np.full((4, 4), float(v)) for v in (1, 2, 3, 4)]
    hdulist = _synth_wfpc2_mef(planes, [1, 2, 3, 4])
    cube = np.asarray(HST_WFPC2.detect_in_fits(hdulist, 'u_c0m.fits', mosaic=True).array)
    np.testing.assert_array_equal(cube, np.stack(planes))


def test_mef_without_image_data_raises() -> None:
    """A WFPC2 file with neither PRIMARY data nor image extensions is rejected."""
    hdulist = _synth_wfpc2_mef([], [])
    with pytest.raises(ValueError, match='No image data'):
        HST_WFPC2.detect_in_fits(hdulist, 'u_c0m.fits')


@pytest.mark.parametrize('detectors', [[1, 2, 3, 4], [1, 3], [2, 4], [4]])
@pytest.mark.parametrize('options', [{}, {'obj': 0}, {'obj': -1}, {'mosaic': True}])
def test_waiver_and_mef_layouts_are_read_identically(detectors: list[int],
                                                     options: dict[str, object]) -> None:
    """The same detectors stored as a _c0f cube or as _c0m extensions yield the same
    array and tint for every selection mode."""
    planes = [np.full((4, 4), 10.0 * det) for det in detectors]
    c0f = _synth_wfpc2(np.stack(planes), detectors=detectors, FILTNAM1='F555W')
    c0m = _synth_wfpc2_mef(planes, detectors, FILTNAM1='F555W')

    data_f = HST_WFPC2.detect_in_fits(c0f, 'u_c0f.fits', **options)
    data_m = HST_WFPC2.detect_in_fits(c0m, 'u_c0m.fits', **options)

    np.testing.assert_array_equal(np.asarray(data_f.array), np.asarray(data_m.array))
    assert np.asarray(data_f.array).shape == np.asarray(data_m.array).shape
    assert data_f.default_tint == data_m.default_tint


# --- data quality masks (--hst-dq) ----------------------------------------------------

def _raw_dq_mask() -> np.ndarray:
    """The bundled _c1f data quality cube as a boolean "nonzero" mask."""
    return np.asarray(_raw_cube(QUALITY) != 0, dtype=bool)


@pytest.mark.parametrize(('name', 'dq_name'), [
    ('u_c0f.fits', 'u_c1f.fits'),
    ('u_c0m.fits', 'u_c1m.fits'),
    ('u_d0f.fits', 'u_q0f.fits'),
    ('u_d0m.fits', 'u_q0m.fits'),
    ('U_C0F.FITS', 'U_C1F.FITS'),
    ('U_D0M.FITS', 'U_Q0M.FITS'),
    ('u_c1f.fits', None),
    ('u_q0m.fits', None),
    ('u_c0fx.fits', None),
])
def test_dq_path_maps_science_to_quality_names(name: str, dq_name: str | None) -> None:
    """Each science file type maps to its data quality file, in the same directory by
    default or in the ``hst_dq`` directory; other files have no counterpart."""
    from picmaker.instruments._hst_support import get_dq_path

    if dq_name is None:
        assert get_dq_path(Path('data') / name) is None
        return
    assert get_dq_path(Path('data') / name) == Path('data') / dq_name
    assert get_dq_path(Path('data') / name, 'dq') == Path('dq') / dq_name


def test_dq_mask_loaded_from_same_directory_by_default() -> None:
    """The bundled _c0f file picks up its _c1f neighbor: every nonzero data quality
    pixel is set in both masks, as two separate arrays."""
    data = read_image_array(SCIENCE, mosaic=True)
    np.testing.assert_array_equal(data.hmask, _raw_dq_mask())
    np.testing.assert_array_equal(data.imask, _raw_dq_mask())
    assert data.hmask is not data.imask

    data = read_image_array(SCIENCE, obj=2)
    np.testing.assert_array_equal(data.hmask, _raw_dq_mask()[2])


def test_dq_file_itself_and_missing_dq_have_no_mask(tmp_path: Path) -> None:
    """A data quality file gets no mask of its own, and a science file whose data
    quality file is not in the ``hst_dq`` directory reads without masks."""
    data = read_image_array(QUALITY)
    assert data.hmask is None
    assert data.imask is None

    data = read_image_array(SCIENCE, hst_dq=str(tmp_path))
    assert data.hmask is None
    assert data.imask is None


def test_dq_mask_from_separate_directory_mef_partial_mosaic(tmp_path: Path) -> None:
    """A _c0m file with only detectors 2 and 4 reads its _c1m mask from the
    ``hst_dq`` directory; mosaic placement puts the mask planes with the data."""
    data_dir = tmp_path / 'c0m'
    dq_dir = tmp_path / 'c1m'
    data_dir.mkdir()
    dq_dir.mkdir()

    planes = [np.full((4, 4), 1.0), np.full((4, 4), 2.0)]
    _synth_wfpc2_mef(planes, [2, 4]).writeto(data_dir / 'u_c0m.fits')
    dq = [np.zeros((4, 4), dtype='int16'), np.zeros((4, 4), dtype='int16')]
    dq[0][0, 0] = 2
    dq[1][3, 3] = 258
    _synth_wfpc2_mef(dq, [2, 4]).writeto(dq_dir / 'u_c1m.fits')

    data = read_image_array(data_dir / 'u_c0m.fits', mosaic=True, hst_dq=str(dq_dir))
    expected = np.zeros((4, 4, 4), dtype=bool)
    expected[1, 0, 0] = True        # detector 2 -> plane 1
    expected[3, 3, 3] = True        # detector 4 -> plane 3
    np.testing.assert_array_equal(data.hmask, expected)
    np.testing.assert_array_equal(data.imask, expected)

    data = read_image_array(data_dir / 'u_c0m.fits', obj=1, hst_dq=str(dq_dir))
    np.testing.assert_array_equal(data.imask, expected[3])


def test_dq_mask_shape_mismatch_raises(tmp_path: Path) -> None:
    """A data quality file whose cube does not match the science cube is rejected."""
    _synth_wfpc2_mef([np.ones((4, 4))], [1]).writeto(tmp_path / 'u_c0m.fits')
    _synth_wfpc2_mef([np.zeros((5, 5))], [1]).writeto(tmp_path / 'u_c1m.fits')
    with pytest.raises(ValueError, match='Data quality'):
        read_image_array(tmp_path / 'u_c0m.fits')


def test_hst_dq_cli_option(tmp_path: Path) -> None:
    """``--hst-dq`` is parsed into ``hst_dq``, and flagged pixels are drawn in the
    ``--invalid`` color."""
    args = get_parser().parse_args([str(SCIENCE), '--hst-dq', 'some/dir'])
    assert args.hst_dq == 'some/dir'

    def _red_fraction(*extra: str) -> float:
        options = vars(get_parser().parse_args([
            str(SCIENCE), '--directory', str(tmp_path), '--invalid', 'red',
            '--extension', 'png', '--hst-dq', str(DATA_DIR), *extra,
        ]))
        picmaker(**options)
        with Image.open(tmp_path / 'u2tf0504t_c0f.png') as img:
            pixels = np.asarray(img.convert('RGB')).reshape(-1, 3)
        return float(np.all(pixels == (255, 0, 0), axis=1).mean())

    # Flagged pixels are drawn in the --invalid color only with --desnow
    assert _red_fraction('--desnow') == pytest.approx(_raw_dq_mask()[0].mean(), abs=0.01)
    assert _red_fraction() == 0.0


@pytest.mark.parametrize(('name', 'dq_name'), [
    ('x_d0f.fits', 'x_q0f.fits'),
    ('X_D0M.FITS', 'X_Q0M.FITS'),
    ('x_c0f.fits', None),
    ('x_c1f.fits', None),
    ('x_q0f.fits', None),
])
def test_dq_path_custom_codes(name: str, dq_name: str | None) -> None:
    """A custom ``dq_codes`` mapping (FOC's) maps only the listed science file types;
    other codes have no data quality file."""
    from picmaker.instruments._hst_support import get_dq_path

    expected = None if dq_name is None else Path('data') / dq_name
    assert get_dq_path(Path('data') / name, dq_codes={'d0': 'q0'}) == expected


def test_dq_pixels_are_excluded_from_the_stretch_without_desnow(tmp_path: Path) -> None:
    """Without --desnow, flagged pixels are drawn normally but still excluded from the
    stretch: the limits match those of the unflagged pixels alone."""
    from picmaker.picmaker import picmaker1

    options = vars(get_parser().parse_args([str(SCIENCE)]))
    options = validate_options(options)
    deconflict_options(options)
    (_, limits) = picmaker1(SCIENCE, '', options, return_limits=True)

    good = _raw_cube(SCIENCE)[0][~_raw_dq_mask()[0]]
    assert limits == (pytest.approx(float(good.min())), pytest.approx(float(good.max())))
