"""Spec tests for :mod:`picmaker.tiff16`, derived from the docstrings.

``write_tiff16`` / ``read_tiff16`` document a round trip for grayscale, RGB, and
palette 16-bit TIFFs, a ``ValueError`` for a bad ``byteorder``, and an
``OSError`` when reading a file that was not written by ``write_tiff16``.
"""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from picmaker import read_tiff16, write_tiff16


def test_grayscale_round_trip(tmp_path: Path) -> None:
    """A 2-D uint16 array survives a write/read round trip; palette is None."""
    arr = np.arange(100, dtype='uint16').reshape(10, 10)
    path = tmp_path / 'gray.tif'
    write_tiff16(path, arr)
    out, palette = read_tiff16(path)
    assert palette is None
    assert out.dtype == np.uint16
    assert np.array_equal(np.asarray(out).reshape(10, 10), arr)


def test_rgb_round_trip(tmp_path: Path) -> None:
    """A 3-D (line, sample, band) uint16 RGB array round-trips."""
    arr = np.arange(300, dtype='uint16').reshape(10, 10, 3)
    path = tmp_path / 'rgb.tif'
    write_tiff16(path, arr)
    out, palette = read_tiff16(path)
    assert palette is None
    assert out.shape == (10, 10, 3)
    assert np.array_equal(out, arr)


def test_up_orientation_round_trips(tmp_path: Path) -> None:
    """Writing and reading with ``up=True`` recovers the original array."""
    arr = np.arange(100, dtype='uint16').reshape(10, 10)
    path = tmp_path / 'up.tif'
    write_tiff16(path, arr, up=True)
    out, _palette = read_tiff16(path, up=True)
    assert np.array_equal(np.asarray(out).reshape(10, 10), arr)


@pytest.mark.parametrize('transpose', [
    Image.Transpose.FLIP_LEFT_RIGHT,
    Image.Transpose.FLIP_TOP_BOTTOM,
    Image.Transpose.ROTATE_90,
    Image.Transpose.ROTATE_180,
    Image.Transpose.ROTATE_270,
])
def test_transpose_round_trips(tmp_path: Path, transpose: Image.Transpose) -> None:
    """A transpose applied on write is undone with the same transpose on read."""
    arr = np.arange(100, dtype='uint16').reshape(10, 10)
    path = tmp_path / 'rot.tif'
    write_tiff16(path, arr, transpose=transpose)
    out, _palette = read_tiff16(path, transpose=transpose)
    assert np.array_equal(np.asarray(out).reshape(10, 10), arr)


def test_palette_round_trip(tmp_path: Path) -> None:
    """A palette image written untranslated round-trips index and palette."""
    palette = np.zeros((65536, 3), dtype='uint16')
    palette[:256] = np.stack([np.arange(256)] * 3, axis=1)
    arr = np.arange(100, dtype='uint16').reshape(10, 10)
    path = tmp_path / 'pal.tif'
    write_tiff16(path, arr, palette=palette, translate=False)
    out, out_palette = read_tiff16(path)
    assert out_palette is not None
    assert out_palette.shape == (65536, 3)
    assert np.array_equal(np.asarray(out).reshape(10, 10), arr)


def test_bad_byteorder_raises_valueerror(tmp_path: Path) -> None:
    """An unrecognized ``byteorder`` is rejected."""
    arr = np.arange(100, dtype='uint16').reshape(10, 10)
    with pytest.raises(ValueError):
        write_tiff16(tmp_path / 'x.tif', arr, byteorder='sideways')


def test_read_non_tiff16_raises_oserror(tmp_path: Path) -> None:
    """Reading an ordinary 8-bit TIFF raises OSError."""
    path = tmp_path / 'plain.tif'
    Image.new('L', (4, 4)).save(path, 'TIFF')
    with pytest.raises(OSError):
        read_tiff16(path)
