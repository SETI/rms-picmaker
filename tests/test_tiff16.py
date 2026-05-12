"""Tests for :func:`WriteTiff16` and :func:`ReadTiff16` round-trip conversion.

Ports the four legacy driver functions in :mod:`tiff16` (the :func:`test`,
gray_test, rgb_test, palette_test block) into proper pytest functions. The
driver block has been deleted in the same commit that introduced this file.
"""

from pathlib import Path

import numpy as np
import pytest

from picmaker.tiff16 import ReadTiff16, WriteTiff16


def test_grayscale_round_trip(tmp_path: Path) -> None:
    """Test that a grayscale uint16 array writes and reads back unchanged.

    Creates an 8x8 array, writes it with WriteTiff16, reads it back with
    ReadTiff16, and verifies the data matches.
    """
    arr = (np.arange(64, dtype=np.uint16) * 1000).reshape(8, 8)
    outfile = str(tmp_path / 'gray.tiff')
    WriteTiff16(outfile, arr)

    new_arr, palette = ReadTiff16(outfile)
    assert palette is None
    np.testing.assert_array_equal(new_arr.squeeze(), arr)


def test_rgb_round_trip(tmp_path: Path) -> None:
    """Test that an RGB uint16 array writes and reads back unchanged.

    Creates an 8x8x3 array with varying channel values, writes it with
    WriteTiff16, reads it back with ReadTiff16, and verifies the data matches.
    """
    # Construct (h, w, 3) array.
    arr = np.zeros((8, 8, 3), dtype=np.uint16)
    arr[..., 0] = (np.arange(64) * 100).reshape(8, 8)
    arr[..., 1] = 32000
    arr[..., 2] = (np.arange(64) * 50).reshape(8, 8)
    outfile = str(tmp_path / 'rgb.tiff')
    WriteTiff16(outfile, arr)

    new_arr, palette = ReadTiff16(outfile)
    assert palette is None
    np.testing.assert_array_equal(new_arr, arr)


def test_palette_round_trip_translate_true(tmp_path: Path) -> None:
    """Test palette TIFF with translate=True converts to RGB on write."""
    arr = np.arange(64, dtype=np.int32).reshape(8, 8)
    palette = np.zeros((65536, 3), dtype=np.int32)
    for dn in range(64):
        palette[dn, 0] = dn * 1024
        palette[dn, 1] = dn * 512
        palette[dn, 2] = dn * 256
    outfile = str(tmp_path / 'palette.tiff')
    WriteTiff16(outfile, arr, palette=palette, translate=True)
    new_arr, new_palette = ReadTiff16(outfile)
    assert new_palette is None
    assert new_arr.shape == (8, 8, 3)


def test_palette_round_trip_translate_false(tmp_path: Path) -> None:
    """Test palette TIFF with translate=False preserves palette format."""
    arr = np.arange(64, dtype=np.int32).reshape(8, 8)
    palette = np.zeros((65536, 3), dtype=np.int32)
    for dn in range(64):
        palette[dn, 0] = dn * 1024
        palette[dn, 1] = dn * 512
        palette[dn, 2] = dn * 256
    outfile = str(tmp_path / 'palette_native.tiff')
    WriteTiff16(outfile, arr, palette=palette, translate=False)
    new_arr, new_palette = ReadTiff16(outfile)
    assert new_palette is not None
    assert new_arr.shape in ((8, 8), (8, 8, 1))


def test_up_flag_flips_grayscale(tmp_path: Path) -> None:
    """Test that up=True flag correctly inverts vertical orientation.

    WriteTiff16 with up=True flips line ordering on write; ReadTiff16 with
    up=True should reverse the flip and produce the original array.
    """
    # `up=True` flips line ordering on write; ReadTiff16 with `up=True`
    # should produce the original array.
    arr = (np.arange(16, dtype=np.uint16) * 1000).reshape(4, 4)
    outfile = str(tmp_path / 'gray_up.tiff')
    WriteTiff16(outfile, arr, up=True)

    new_arr, _ = ReadTiff16(outfile, up=True)
    np.testing.assert_array_equal(new_arr.squeeze(), arr)


def test_invalid_file_raises(tmp_path: Path) -> None:
    """Test that ReadTiff16 raises IOError for corrupt TIFF files.

    Creates a file with invalid content and verifies that ReadTiff16 raises
    IOError with appropriate message.
    """
    bad = tmp_path / 'bad.tiff'
    bad.write_bytes(b'\x00' * 64)
    with pytest.raises(IOError) as excinfo:
        ReadTiff16(str(bad))
    assert 'File format is not TIFF' in str(excinfo.value)


def test_wrong_tiff_version_raises(tmp_path: Path) -> None:
    """A file with valid byte-order magic but a non-42 TIFF version field is rejected.

    Regression: ReadTiff16 built an OSError for this case but did not raise it,
    silently accepting the file and proceeding with corrupt IFD parsing.
    """
    bad = tmp_path / 'bad_version.tiff'
    # Little-endian 'II' magic, version=43 (not 42), IFD offset=8.
    bad.write_bytes(b'II' + (43).to_bytes(2, 'little') + (8).to_bytes(4, 'little'))
    with pytest.raises(OSError, match='File format is not TIFF'):
        ReadTiff16(str(bad))
