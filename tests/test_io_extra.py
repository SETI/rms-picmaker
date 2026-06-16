"""Cover the leaf I/O helpers that aren't exercised by the main cascade test."""

from pathlib import Path

import numpy as np
from PIL import Image

from picmaker import (
    read_array,
    read_pds_labeled_image_array,
    read_pil,
    write_pil,
)


class TestReadArray:
    def test_grayscale_png(self, fixtures_dir: Path) -> None:
        arr = read_array(str(fixtures_dir / 'small_grayscale.png'), rescale=False)
        assert arr.shape == (8, 8)
        assert arr.dtype == np.uint8

    def test_rgb_png(self, fixtures_dir: Path) -> None:
        arr = read_array(str(fixtures_dir / 'small_rgb.png'), rescale=False)
        # 3-band image stacks to a 3-D array
        assert arr.shape == (8, 8, 3)

    def test_sixteen_bit_tiff(self, fixtures_dir: Path) -> None:
        # read_tiff16 branch: rescale=False returns the raw uint16 array.
        arr = read_array(str(fixtures_dir / 'small_tiff16.tiff'), rescale=False)
        # small_tiff16.tiff is a grayscale 8x8 written by write_tiff16, so
        # read_tiff16 returns the 2-D shape directly.
        assert arr.shape == (8, 8)

    def test_sixteen_bit_tiff_rescale(self, fixtures_dir: Path) -> None:
        arr = read_array(str(fixtures_dir / 'small_tiff16.tiff'), rescale=True)
        # Rescale=True normalizes to 0-1 float.
        assert arr.max() <= 1.0 + 1e-9


class TestReadPil:
    def test_png_returns_pil_image(self, fixtures_dir: Path) -> None:
        img = read_pil(str(fixtures_dir / 'small_grayscale.png'))
        assert isinstance(img, Image.Image)
        assert img.size == (8, 8)
        assert img.mode == 'L'

    def test_sixteen_bit_tiff(self, fixtures_dir: Path) -> None:
        img = read_pil(str(fixtures_dir / 'small_tiff16.tiff'))
        assert isinstance(img, Image.Image)
        assert img.size == (8, 8)


class TestWritePil:
    def test_round_trip_quality_setting(self, fixtures_dir: Path, tmp_path: Path) -> None:
        img = read_pil(str(fixtures_dir / 'small_grayscale.png'))
        out = tmp_path / 'out.jpg'
        write_pil(img, str(out), quality=50)
        assert out.exists()
        # Higher-quality re-encoding produces a bigger file.
        out2 = tmp_path / 'out_hq.jpg'
        write_pil(img, str(out2), quality=95)
        # Quality 95 is at least as big as quality 50 for the same source.
        assert out2.stat().st_size >= out.stat().st_size


class TestReadPdsLabeledImageArray:
    def test_minimal_pds3_sample(self, fixtures_dir: Path) -> None:
        # read_pds_labeled_image_array returns (array3d, default_is_up,
        # filter_info) or None — matches the read_one_image_array contract.
        result = read_pds_labeled_image_array(
            str(fixtures_dir / 'pds3_sample.IMG'), 'IMAGE'
        )
        assert result is not None
        arr, default_is_up, filter_info = result
        assert arr.shape == (1, 8, 8)
        assert default_is_up is False
        assert filter_info == ('', '', '')
