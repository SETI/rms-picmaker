"""Cover the reader-cascade branches in :mod:`picmaker.io` that the
existing tests don't reach: 2-D-array reshape paths, FITS object
selection, the multi-file ``read_image_array`` stacking path, the HST
mosaic dispatch, and the cascade-end ``Unrecognized image file format``
error.
"""

import pickle
import shutil
from pathlib import Path

import astropy.io.fits as pyfits
import numpy as np
import pdsparser
import pytest
from PIL import Image
from vicar import VicarImage

from picmaker.io import (
    get_outfile,
    read_array,
    read_image_array,
    read_one_image_array,
    read_pds_labeled_image_array,
    read_pil,
)

# ---------------------------------------------------------------------------
# 2-D reshape paths (pickle + numpy)
# ---------------------------------------------------------------------------


def test_pickle_two_dim_reshapes_to_three(tmp_path: Path) -> None:
    """A pickled 2-D array is reshaped to ``(1, lines, samples)``."""
    src = tmp_path / 'flat.pkl'
    with src.open('wb') as f:
        pickle.dump(np.arange(64, dtype='uint8').reshape(8, 8), f)
    arr, default_is_up, filter_info = read_one_image_array(str(src), None)
    assert arr.shape == (1, 8, 8)
    assert default_is_up is False
    assert filter_info is None


def test_pickle_three_dim_passes_through(tmp_path: Path) -> None:
    """A pickled 3-D array is returned as-is."""
    src = tmp_path / 'cube.pkl'
    with src.open('wb') as f:
        pickle.dump(np.zeros((2, 8, 8), dtype='uint8'), f)
    arr, _, _ = read_one_image_array(str(src), None)
    assert arr.shape == (2, 8, 8)


def test_numpy_npy_two_dim_reshapes_to_three(tmp_path: Path) -> None:
    """A 2-D ``.npy`` is reshaped to ``(1, lines, samples)``."""
    src = tmp_path / 'flat.npy'
    np.save(src, np.zeros((8, 8), dtype='uint8'))
    arr, _, _ = read_one_image_array(str(src), None)
    assert arr.shape == (1, 8, 8)


def test_numpy_npy_three_dim_passes_through(tmp_path: Path) -> None:
    """A 3-D ``.npy`` is returned as-is."""
    src = tmp_path / 'cube.npy'
    np.save(src, np.zeros((3, 8, 8), dtype='uint8'))
    arr, _, _ = read_one_image_array(str(src), None)
    assert arr.shape == (3, 8, 8)


# ---------------------------------------------------------------------------
# FITS object selection (lines 196-205 of io.py)
# ---------------------------------------------------------------------------


def test_fits_obj_int(fixtures_dir: Path) -> None:
    """``obj=0`` selects HDU index 0 of a FITS file."""
    arr, default_is_up, filter_info = read_one_image_array(
        str(fixtures_dir / 'nh_mvic.fits'), obj=0
    )
    assert arr.shape == (1, 16, 16)
    assert default_is_up is True
    assert filter_info == ('NEW HORIZONS', 'MVIC', 'BLUE')


def test_fits_obj_tuple_stacks(fixtures_dir: Path) -> None:
    """``obj=(0,)`` stacks the listed HDUs."""
    arr, default_is_up, _ = read_one_image_array(
        str(fixtures_dir / 'nh_mvic.fits'), obj=(0,)
    )
    assert arr.shape == (1, 16, 16)
    assert default_is_up is True


def test_fits_obj_string_int(fixtures_dir: Path) -> None:
    """A numeric ``obj`` passed as a string is converted via ``int()``."""
    arr, _, _ = read_one_image_array(
        str(fixtures_dir / 'nh_mvic.fits'), obj='0'
    )
    assert arr.shape == (1, 16, 16)


def test_fits_hst_acs_wfc_mosaic(fixtures_dir: Path) -> None:
    """``mosaic=True`` on an ACS/WFC fixture stacks the two detector HDUs."""
    arr, default_is_up, filter_info = read_one_image_array(
        str(fixtures_dir / 'hst_acs.fits'), None, mosaic=True
    )
    assert arr.shape == (2, 16, 16)
    assert default_is_up is True
    assert filter_info is not None
    assert filter_info[0] == 'HST'
    assert filter_info[1] == 'ACS/WFC'


def test_fits_hst_wfpc2_mosaic(fixtures_dir: Path) -> None:
    """``mosaic=True`` on a WFPC2 fixture collects every 2-/3-D HDU."""
    arr, default_is_up, filter_info = read_one_image_array(
        str(fixtures_dir / 'hst_wfpc2.fits'), None, mosaic=True
    )
    assert arr.shape == (4, 16, 16)
    assert default_is_up is True
    assert filter_info is not None
    assert filter_info[1] == 'WFPC2'


# ---------------------------------------------------------------------------
# read_image_array: multi-file stacking
# ---------------------------------------------------------------------------


def test_read_image_array_list_stacks_frames(tmp_path: Path) -> None:
    """``read_image_array`` over a list of files stacks the resulting
    arrays into a single 3-D array.
    """
    paths: list[str] = []
    for i in range(3):
        p = tmp_path / f'frame_{i}.npy'
        np.save(p, np.full((8, 8), i, dtype='uint8'))
        paths.append(str(p))

    arr, default_is_up, filter_info = read_image_array(paths, None)
    assert arr.shape == (3, 8, 8)
    assert default_is_up is False
    assert filter_info is None


def test_read_image_array_list_with_three_d_inputs(tmp_path: Path) -> None:
    """``read_image_array`` over a list of 3-D arrays stacks along the
    band axis (no reshape needed).
    """
    paths: list[str] = []
    for i in range(2):
        p = tmp_path / f'cube_{i}.npy'
        np.save(p, np.full((2, 8, 8), i, dtype='uint8'))
        paths.append(str(p))

    arr, _, _ = read_image_array(paths, None)
    assert arr.shape == (4, 8, 8)


# ---------------------------------------------------------------------------
# Unrecognized-format error
# ---------------------------------------------------------------------------


def test_unrecognized_format_raises(tmp_path: Path) -> None:
    """A file no reader recognises produces ``OSError`` with the path."""
    src = tmp_path / 'garbage.bin'
    src.write_bytes(b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x10')
    with pytest.raises(OSError, match='Unrecognized image file format'):
        read_one_image_array(str(src), None)


def test_unrecognized_missing_file_raises(tmp_path: Path) -> None:
    """A missing path also surfaces as the cascade-end error."""
    with pytest.raises(OSError, match='Unrecognized image file format'):
        read_one_image_array(str(tmp_path / 'does_not_exist.bin'), None)


def test_cascade_falls_through_to_pil(fixtures_dir: Path) -> None:
    """A PNG file flows through the cascade to the PIL/read_array branch."""
    arr, default_is_up, filter_info = read_one_image_array(
        str(fixtures_dir / 'small_grayscale.png'), None
    )
    assert arr.ndim == 3
    assert default_is_up is False
    assert filter_info is None


def test_cascade_falls_through_to_pds3(fixtures_dir: Path) -> None:
    """A self-labeled ``.IMG`` file falls through to the PDS3 auto-detection branch."""
    arr, _, _ = read_one_image_array(
        str(fixtures_dir / 'pds3_sample.IMG'),
    )
    assert arr.shape == (1, 8, 8)


def test_get_outfile_creates_nested_output_dir(tmp_path: Path) -> None:
    """``get_outfile`` creates the parent directory tree when it's missing."""
    src = tmp_path / 'in.IMG'
    src.write_bytes(b'')
    out_dir = tmp_path / 'a' / 'b' / 'c'
    result = get_outfile(str(src), outdir=str(out_dir), replace='all')
    assert out_dir.is_dir()
    assert result == str(out_dir / 'in.jpg')


def test_get_outfile_none_suffix_normalizes_to_empty(tmp_path: Path) -> None:
    """``suffix=None`` is normalised to ``''`` before the join."""
    src = tmp_path / 'in.IMG'
    result = get_outfile(
        str(src),
        outdir=str(tmp_path),
        suffix=None,
        extension='png',
    )
    assert result == str(tmp_path / 'in.png')


def test_read_array_tiff_with_bogus_content_falls_through_to_pil(
    tmp_path: Path,
) -> None:
    """A file with ``.tiff`` extension that is not a 16-bit TIFF falls
    through to the PIL path inside :func:`read_array`.
    """
    fake = tmp_path / 'fake.tiff'
    Image.new('L', (4, 4), color=128).save(str(fake), format='TIFF')
    arr = read_array(str(fake), rescale=False)
    assert arr.shape == (4, 4)


def test_read_pil_tiff_with_bogus_content_falls_through_to_pil(
    tmp_path: Path,
) -> None:
    """Same fall-through behaviour for :func:`read_pil`."""
    fake = tmp_path / 'fake.tiff'
    Image.new('L', (4, 4), color=128).save(str(fake), format='TIFF')
    img = read_pil(str(fake))
    assert isinstance(img, Image.Image)
    assert img.size == (4, 4)


# ---------------------------------------------------------------------------
# Pds3Label passed directly (bypasses the str/PathLike branch)
# ---------------------------------------------------------------------------


def test_pds_label_passed_directly_to_read_one_image_array(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """Passing a Pds3Label object directly skips the path-string branch in
    read_one_image_array and dispatches straight to the PDS3 label cascade."""
    shutil.copy(fixtures_dir / 'cassini_iss.vic', tmp_path / 'cassini_iss.vic')
    lbl_path = tmp_path / 'cassini.LBL'
    lbl_path.write_text(
        'PDS_VERSION_ID = PDS3\n'
        'INSTRUMENT_HOST_NAME = "CASSINI ORBITER"\n'
        'INSTRUMENT_ID = "ISSNA"\n'
        'FILTER_NAME = ("CL1", "GRN")\n'
        '^IMAGE = "cassini_iss.vic"\n'
        'END\n'
    )
    label = pdsparser.Pds3Label(str(lbl_path))
    arr, default_is_up, filter_info = read_one_image_array(label)
    assert arr.ndim == 3
    assert filter_info == ('CASSINI', 'ISS', 'CL1+GRN')


# ---------------------------------------------------------------------------
# Generic VICAR / FITS fallbacks for unrecognized instruments
# ---------------------------------------------------------------------------


def test_generic_vicar_fallback_for_unrecognized_instrument(tmp_path: Path) -> None:
    """A VICAR file not claimed by any instrument is read by the generic
    VICAR fallback in read_one_image_array."""
    vic = VicarImage.from_array(np.zeros((8, 8), dtype=np.int16))
    vicpath = str(tmp_path / 'unknown.vic')
    vic.write_file(vicpath)
    arr, default_is_up, filter_info = read_one_image_array(vicpath)
    assert arr.ndim == 3
    assert default_is_up is False
    assert filter_info is None


def test_generic_fits_fallback_for_unrecognized_instrument(tmp_path: Path) -> None:
    """A FITS file with no instrument-specific headers is read by the
    generic FITS fallback in read_one_image_array."""
    fits_path = str(tmp_path / 'unknown.fits')
    hdu = pyfits.PrimaryHDU(data=np.zeros((8, 8), dtype=np.float32))
    pyfits.HDUList([hdu]).writeto(fits_path, overwrite=True)
    arr, default_is_up, filter_info = read_one_image_array(fits_path)
    assert arr.ndim == 3
    assert default_is_up is True
    assert filter_info is None


# ---------------------------------------------------------------------------
# Sibling .lbl / .LBL detection in read_pds_labeled_image_array
# ---------------------------------------------------------------------------

_MINIMAL_LABEL = (
    'PDS_VERSION_ID = PDS3\r\n'
    '^IMAGE = "{name}"\r\n'
    'OBJECT = IMAGE\r\n'
    '  LINES = 8\r\n'
    '  LINE_SAMPLES = 8\r\n'
    '  SAMPLE_BITS = 8\r\n'
    '  SAMPLE_TYPE = UNSIGNED_INTEGER\r\n'
    'END_OBJECT = IMAGE\r\n'
    'END\r\n'
)


def test_sibling_lbl_lowercase_detected(tmp_path: Path) -> None:
    """When the primary data file is missing, io.py finds a lowercase .lbl sibling.

    pdsparser raises FileNotFoundError (an OSError) for missing files without
    looking for siblings; io.py's except block then searches for the sibling.
    """
    data = tmp_path / 'image.dat'
    # Write the actual image bytes under a separate name referenced by ^IMAGE
    raw = tmp_path / 'image_raw.dat'
    raw.write_bytes(np.zeros(64, dtype='uint8').tobytes())
    (tmp_path / 'image.lbl').write_text(_MINIMAL_LABEL.format(name='image_raw.dat'))
    # 'image.dat' itself does not exist — pdsparser raises OSError, io.py
    # then finds and parses the sibling 'image.lbl'.
    result = read_pds_labeled_image_array(str(data))
    assert result is not None
    assert result[0].shape == (1, 8, 8)


def test_sibling_LBL_uppercase_detected(tmp_path: Path) -> None:
    """When the primary data file is missing, io.py finds an uppercase .LBL sibling.

    No lowercase .lbl exists, so the elif branch for .LBL is taken.
    """
    data = tmp_path / 'image2.dat'
    raw = tmp_path / 'image2_raw.dat'
    raw.write_bytes(np.zeros(64, dtype='uint8').tobytes())
    (tmp_path / 'image2.LBL').write_text(_MINIMAL_LABEL.format(name='image2_raw.dat'))
    result = read_pds_labeled_image_array(str(data))
    assert result is not None
    assert result[0].shape == (1, 8, 8)


def test_sibling_search_skipped_for_lbl_extension(tmp_path: Path) -> None:
    """A .lbl file that fails to parse returns None without checking siblings."""
    bad = tmp_path / 'bad.lbl'
    bad.write_bytes(b'not a pds3 label')
    assert read_pds_labeled_image_array(str(bad)) is None


# ---------------------------------------------------------------------------
# get_outfile: missing branches
# ---------------------------------------------------------------------------


def test_get_outfile_no_outdir_writes_next_to_input(tmp_path: Path) -> None:
    """outdir=None places the output file beside the input file."""
    src = tmp_path / 'image.IMG'
    src.write_bytes(b'')
    result = get_outfile(str(src), outdir=None)
    assert result == str(tmp_path / 'image.jpg')


def test_get_outfile_strip_not_found_leaves_name_unchanged(tmp_path: Path) -> None:
    """A strip substring absent from the filename is silently ignored."""
    src = tmp_path / 'image.IMG'
    src.write_bytes(b'')
    result = get_outfile(str(src), strip='NOTPRESENT')
    assert result.endswith('image.jpg')
