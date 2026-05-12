"""Cover the tiff16 branches the existing tests don't reach: RGB write,
3-D grayscale, big-endian byte order, transpose=ROTATE_90, and up=True
vertical flip.
"""

from pathlib import Path

import numpy as np
from PIL import Image

from picmaker.tiff16 import ReadTiff16, WriteTiff16


def test_tiff16_rgb_write(tmp_path: Path) -> None:
    """A 16-bit RGB array writes successfully."""
    rgb = np.zeros((8, 8, 3), dtype='uint16')
    rgb[..., 0] = 10000
    rgb[..., 1] = 20000
    rgb[..., 2] = 30000
    out = tmp_path / 'rgb.tiff'
    WriteTiff16(str(out), rgb)
    array, palette = ReadTiff16(str(out))
    assert palette is None
    # RGB shape is preserved.
    assert array.shape == (8, 8, 3)


def test_tiff16_three_d_grayscale(tmp_path: Path) -> None:
    """A 3-D ``(h, w, 1)`` grayscale array is reduced and written."""
    arr = (np.arange(64, dtype='uint16') * 100).reshape(8, 8, 1)
    out = tmp_path / 'gray3d.tiff'
    WriteTiff16(str(out), arr)
    assert out.exists()


def test_tiff16_big_endian(tmp_path: Path) -> None:
    """``byteorder='big'`` writes a big-endian TIFF that round-trips."""
    arr = (np.arange(64, dtype='uint16') * 100).reshape(8, 8)
    out = tmp_path / 'big.tiff'
    WriteTiff16(str(out), arr, byteorder='big')
    array, palette = ReadTiff16(str(out))
    assert array.shape == (8, 8) or array.shape == (8, 8, 1)
    assert palette is None


def test_tiff16_transpose_rotate90(tmp_path: Path) -> None:
    """``transpose=Image.Transpose.ROTATE_90`` rotates before writing."""
    arr = (np.arange(64, dtype='uint16') * 100).reshape(8, 8)
    out = tmp_path / 'rot.tiff'
    WriteTiff16(str(out), arr, transpose=Image.Transpose.ROTATE_90)
    assert out.exists()


def test_tiff16_up_flag_flips_vertically(tmp_path: Path) -> None:
    """``up=True`` flips the image before writing."""
    arr = (np.arange(64, dtype='uint16') * 100).reshape(8, 8)
    out = tmp_path / 'up.tiff'
    WriteTiff16(str(out), arr, up=True)
    assert out.exists()
