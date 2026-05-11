"""WriteTiff16 / ReadTiff16 round-trip tests.

Ports the four legacy driver functions in `tiff16.py` (the `test`, `gray_test`,
`rgb_test`, `palette_test` block at the bottom of the pre-cleanup file) into
proper pytest functions. The driver block has been deleted in the same commit
that introduced this file.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from picmaker.tiff16 import ReadTiff16, WriteTiff16


def test_grayscale_round_trip(tmp_path: Path) -> None:
    arr = (np.arange(64, dtype=np.uint16) * 1000).reshape(8, 8)
    outfile = str(tmp_path / 'gray.tiff')
    WriteTiff16(outfile, arr)

    new_arr, palette = ReadTiff16(outfile)
    assert palette is None
    np.testing.assert_array_equal(new_arr.squeeze(), arr)


def test_rgb_round_trip(tmp_path: Path) -> None:
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        'Pre-PR3: WriteTiff16 checks `palette != None` which returns a numpy '
        'array (not a bool) for non-None palettes — modern numpy raises '
        'ValueError. PR 3 will switch to `palette is not None`.'
    ),
)
def test_palette_round_trip_translate_true(tmp_path: Path) -> None:
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        'Pre-PR3: same `palette != None` ambiguity as the translate-true case.'
    ),
)
def test_palette_round_trip_translate_false(tmp_path: Path) -> None:
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
    # `up=True` flips line ordering on write; ReadTiff16 with `up=True`
    # should produce the original array.
    arr = (np.arange(16, dtype=np.uint16) * 1000).reshape(4, 4)
    outfile = str(tmp_path / 'gray_up.tiff')
    WriteTiff16(outfile, arr, up=True)

    new_arr, _ = ReadTiff16(outfile, up=True)
    np.testing.assert_array_equal(new_arr.squeeze(), arr)


def test_invalid_file_raises(tmp_path: Path) -> None:
    bad = tmp_path / 'bad.tiff'
    bad.write_bytes(b'\x00' * 64)
    with pytest.raises(IOError):
        ReadTiff16(str(bad))
