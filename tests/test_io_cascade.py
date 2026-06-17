"""Cover the reader-cascade branches in :mod:`picmaker.io` that the
existing tests don't reach: 2-D-array reshape paths, FITS object
selection, the multi-file ``read_image_array`` stacking path, the HST
mosaic dispatch, and the cascade-end ``Unrecognized image file format``
error.
"""

import pickle
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from picmaker.io import get_outfile, read_array, read_image_array, read_one_image_array, read_pil

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
