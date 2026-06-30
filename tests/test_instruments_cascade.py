"""Cover the reader-cascade branches in :mod:`picmaker.instruments` that the
main detection test doesn't reach: single-file pickle/numpy reads, FITS object
selection, the multi-file ``read_image_array`` stacking path, the generic
VICAR/FITS fallbacks, and the cascade-end ``unrecognized file format`` error.

Post-refactor notes:
  * ``read_image_array`` returns an :class:`ImageData` (``.array``,
    ``.default_upward``, ``.default_tint``); it no longer returns a triple.
  * A single-file read is no longer reshaped to ``(1, lines, samples)`` -- a
    2-D pickle/numpy/PNG comes back 2-D. Only the multi-file stacking path adds
    a band axis.
  * ``read_array``/``read_pil``, the ``mosaic`` option, FITS ``obj`` parsed
    from a string/tuple, passing a ``Pds3Label`` directly, and the sibling-.LBL
    fallback are all gone; those tests are dropped.
"""

import pickle
from pathlib import Path

import astropy.io.fits as pyfits
import numpy as np
import pytest
from vicar import VicarImage

from picmaker import get_outfile
from picmaker.instruments import read_image_array

# ---------------------------------------------------------------------------
# Single-file pickle / numpy reads (no reshape to 3-D anymore)
# ---------------------------------------------------------------------------


def test_pickle_two_dim_stays_two_dim(tmp_path: Path) -> None:
    """A pickled 2-D array is returned as 2-D (no band axis added)."""
    src = tmp_path / 'flat.pkl'
    with src.open('wb') as f:
        pickle.dump(np.arange(64, dtype='uint8').reshape(8, 8), f)
    data = read_image_array(str(src))
    assert data.array.shape == (8, 8)
    assert data.default_upward is False
    assert data.default_tint is None


def test_pickle_three_dim_passes_through(tmp_path: Path) -> None:
    """A pickled 3-D array is returned as-is."""
    src = tmp_path / 'cube.pkl'
    with src.open('wb') as f:
        pickle.dump(np.zeros((2, 8, 8), dtype='uint8'), f)
    assert read_image_array(str(src)).array.shape == (2, 8, 8)


def test_numpy_npy_two_dim_stays_two_dim(tmp_path: Path) -> None:
    """A 2-D ``.npy`` is returned as 2-D."""
    src = tmp_path / 'flat.npy'
    np.save(src, np.zeros((8, 8), dtype='uint8'))
    assert read_image_array(str(src)).array.shape == (8, 8)


def test_numpy_npy_three_dim_passes_through(tmp_path: Path) -> None:
    """A 3-D ``.npy`` is returned as-is."""
    src = tmp_path / 'cube.npy'
    np.save(src, np.zeros((3, 8, 8), dtype='uint8'))
    assert read_image_array(str(src)).array.shape == (3, 8, 8)


# ---------------------------------------------------------------------------
# FITS object selection
# ---------------------------------------------------------------------------


def test_fits_obj_int(fixtures_dir: Path) -> None:
    """``obj=0`` selects HDU index 0 of a FITS file."""
    data = read_image_array(str(fixtures_dir / 'nh_mvic.fits'), obj=0)
    assert data.array.shape == (16, 16)
    assert data.default_upward is True
    assert data.default_tint is None


# ---------------------------------------------------------------------------
# read_image_array: multi-file stacking
# ---------------------------------------------------------------------------


def test_read_image_array_list_stacks_frames(tmp_path: Path) -> None:
    """``read_image_array`` over a list of 2-D files stacks the arrays into a
    single 3-D array along a new leading band axis.
    """
    paths: list[str] = []
    for i in range(3):
        p = tmp_path / f'frame_{i}.npy'
        np.save(p, np.full((8, 8), i, dtype='uint8'))
        paths.append(str(p))

    data = read_image_array(paths)
    assert data.array.shape == (3, 8, 8)
    assert data.default_upward is False
    assert data.default_tint is None


def test_read_image_array_list_with_three_d_inputs(tmp_path: Path) -> None:
    """``read_image_array`` over a list of 3-D arrays stacks along the band
    axis (no reshape needed).
    """
    paths: list[str] = []
    for i in range(2):
        p = tmp_path / f'cube_{i}.npy'
        np.save(p, np.full((2, 8, 8), i, dtype='uint8'))
        paths.append(str(p))

    assert read_image_array(paths).array.shape == (4, 8, 8)


# ---------------------------------------------------------------------------
# Unrecognized-format error
# ---------------------------------------------------------------------------


def test_unrecognized_format_raises(tmp_path: Path) -> None:
    """A file no reader recognises produces ``OSError``."""
    src = tmp_path / 'garbage.bin'
    src.write_bytes(b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x10')
    with pytest.raises(OSError, match='unrecognized file format'):
        read_image_array(str(src))


def test_cascade_falls_through_to_pil(fixtures_dir: Path) -> None:
    """A PNG file flows through the cascade to the generic PIL branch and is
    returned 2-D (single-band grayscale, no band axis added).
    """
    data = read_image_array(str(fixtures_dir / 'small_grayscale.png'))
    assert data.array.shape == (8, 8)
    assert data.default_upward is False
    assert data.default_tint is None


def test_cascade_falls_through_to_pds3(fixtures_dir: Path) -> None:
    """A self-labeled ``.IMG`` file falls through to the PDS3 signature branch."""
    data = read_image_array(str(fixtures_dir / 'pds3_sample.IMG'))
    assert data.array.shape == (8, 8)
    assert data.default_upward is False


# ---------------------------------------------------------------------------
# Generic VICAR / FITS fallbacks for unrecognized instruments
# ---------------------------------------------------------------------------


def test_generic_vicar_fallback_for_unrecognized_instrument(tmp_path: Path) -> None:
    """A VICAR file not claimed by any instrument is read by the generic VICAR
    fallback. vicar preserves a leading band axis, so the result is 3-D.
    """
    vic = VicarImage.from_array(np.zeros((8, 8), dtype=np.int16))
    vicpath = str(tmp_path / 'unknown.vic')
    vic.write_file(vicpath)
    data = read_image_array(vicpath)
    assert data.array.shape == (1, 8, 8)
    assert data.default_upward is False
    assert data.default_tint is None


def test_generic_fits_fallback_for_unrecognized_instrument(tmp_path: Path) -> None:
    """A FITS file with no instrument-specific headers is read by the generic
    FITS fallback (``default_upward`` is True for FITS).
    """
    fits_path = str(tmp_path / 'unknown.fits')
    hdu = pyfits.PrimaryHDU(data=np.zeros((8, 8), dtype=np.float32))
    pyfits.HDUList([hdu]).writeto(fits_path, overwrite=True)
    data = read_image_array(fits_path)
    assert data.array.shape == (8, 8)
    assert data.default_upward is True
    assert data.default_tint is None


# ---------------------------------------------------------------------------
# get_outfile (picmaker.control) -- still present; returns a pathlib.Path
# ---------------------------------------------------------------------------


def test_get_outfile_creates_nested_output_dir(tmp_path: Path) -> None:
    """``get_outfile`` creates the parent directory tree when it's missing."""
    src = tmp_path / 'in.IMG'
    src.write_bytes(b'')
    out_dir = tmp_path / 'a' / 'b' / 'c'
    result = get_outfile(str(src), outdir=str(out_dir), replace='all')
    assert out_dir.is_dir()
    assert Path(result) == out_dir / 'in.jpg'


def test_get_outfile_none_suffix_normalizes_to_empty(tmp_path: Path) -> None:
    """``suffix=None`` is treated as empty before the join."""
    src = tmp_path / 'in.IMG'
    result = get_outfile(str(src), outdir=str(tmp_path), suffix=None, extension='png')
    assert Path(result) == tmp_path / 'in.png'


def test_get_outfile_no_outdir_writes_next_to_input(tmp_path: Path) -> None:
    """outdir=None places the output file beside the input file."""
    src = tmp_path / 'image.IMG'
    src.write_bytes(b'')
    result = get_outfile(str(src), outdir=None)
    assert Path(result) == tmp_path / 'image.jpg'


def test_get_outfile_strip_not_found_leaves_name_unchanged(tmp_path: Path) -> None:
    """A strip substring absent from the filename is silently ignored."""
    src = tmp_path / 'image.IMG'
    src.write_bytes(b'')
    result = get_outfile(str(src), strip='NOTPRESENT')
    assert str(result).endswith('image.jpg')
