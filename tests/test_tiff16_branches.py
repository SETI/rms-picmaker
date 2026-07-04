"""Cover the tiff16 branches the existing tests don't reach: RGB write,
3-D grayscale, big-endian byte order, transpose=ROTATE_90, and up=True
vertical flip.
"""

from pathlib import Path

import numpy as np
from PIL import Image

from picmaker.tiff16 import read_tiff16, write_tiff16


def test_tiff16_rgb_write(tmp_path: Path) -> None:
    """A 16-bit RGB array writes successfully."""
    rgb = np.zeros((8, 8, 3), dtype='uint16')
    rgb[..., 0] = 10000
    rgb[..., 1] = 20000
    rgb[..., 2] = 30000
    out = tmp_path / 'rgb.tiff'
    write_tiff16(str(out), rgb)
    array, palette = read_tiff16(str(out))
    assert palette is None
    # RGB shape is preserved.
    assert array.shape == (8, 8, 3)


def test_tiff16_three_d_grayscale(tmp_path: Path) -> None:
    """A 3-D ``(h, w, 1)`` grayscale array round-trips through tiff16."""
    arr = (np.arange(64, dtype='uint16') * 100).reshape(8, 8, 1)
    out = tmp_path / 'gray3d.tiff'
    write_tiff16(str(out), arr)
    array, palette = read_tiff16(str(out))
    assert palette is None
    # Read back as 2-D; reshape the input the same way for comparison.
    assert array.shape == (8, 8)
    np.testing.assert_array_equal(array, arr.reshape(8, 8))


def test_tiff16_big_endian(tmp_path: Path) -> None:
    """``byteorder='big'`` writes a big-endian TIFF that round-trips."""
    arr = (np.arange(64, dtype='uint16') * 100).reshape(8, 8)
    out = tmp_path / 'big.tiff'
    write_tiff16(str(out), arr, byteorder='big')
    array, palette = read_tiff16(str(out))
    array = np.squeeze(array)
    assert array.shape == (8, 8)
    assert palette is None
    np.testing.assert_array_equal(array, arr)


def test_tiff16_transpose_rotate90(tmp_path: Path) -> None:
    """``transpose=Image.Transpose.ROTATE_90`` rotates before writing."""
    arr = (np.arange(64, dtype='uint16') * 100).reshape(8, 8)
    out = tmp_path / 'rot.tiff'
    write_tiff16(str(out), arr, transpose=Image.Transpose.ROTATE_90)
    array, _ = read_tiff16(str(out))
    array = np.squeeze(array)
    # write_tiff16 applies np.rot90(arr, 1) before writing; the round
    # trip should produce the same 90-degree rotated array.
    np.testing.assert_array_equal(array, np.rot90(arr, 1))


def test_tiff16_up_flag_flips_vertically(tmp_path: Path) -> None:
    """``up=True`` flips the image vertically before writing."""
    arr = (np.arange(64, dtype='uint16') * 100).reshape(8, 8)
    out = tmp_path / 'up.tiff'
    write_tiff16(str(out), arr, up=True)
    array, _ = read_tiff16(str(out))
    array = np.squeeze(array)
    assert array.shape == (8, 8)
    # The writer flipped vertically on disk, so the round trip
    # (without ``up=True`` on the read) returns the flipped array.
    np.testing.assert_array_equal(array, np.flipud(arr))
