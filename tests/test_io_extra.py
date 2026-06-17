"""Cover the leaf I/O helpers that aren't exercised by the main cascade test."""

import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from picmaker import (
    read_array,
    read_one_image_array,
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


def _write_lbl(tmp_path: Path, name: str, text: str, data_src: Path) -> Path:
    """Write a minimal PDS3 label next to a copy of a data fixture."""
    shutil.copy(data_src, tmp_path / data_src.name)
    lbl = tmp_path / name
    lbl.write_text(text)
    return lbl


class TestPds3LabelDispatch:
    """read_one_image_array dispatches .LBL paths to per-instrument readers."""

    def test_cassini_lbl_dispatches_to_cassini_iss(
        self, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """A .LBL with INSTRUMENT_HOST_NAME='CASSINI ORBITER' is dispatched to
        cassini_iss and returns the correct filter_info with '+'-joined filters."""
        lbl = _write_lbl(
            tmp_path,
            'cassini.LBL',
            'PDS_VERSION_ID = PDS3\n'
            'INSTRUMENT_HOST_NAME = "CASSINI ORBITER"\n'
            'FILTER_NAME = ("CL1", "RED")\n'
            '^IMAGE = "cassini_iss.vic"\n'
            'END\n',
            fixtures_dir / 'cassini_iss.vic',
        )
        arr, default_is_up, filter_info = read_one_image_array(str(lbl))
        assert arr.ndim == 3
        assert default_is_up is False
        assert filter_info == ('CASSINI', 'ISS', 'CL1+RED')

    def test_voyager_lbl_dispatches_to_voyager_iss(
        self, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """A .LBL with INSTRUMENT_HOST_NAME starting with 'VOYAGER' dispatches
        to voyager_iss."""
        lbl = _write_lbl(
            tmp_path,
            'voyager.LBL',
            'PDS_VERSION_ID = PDS3\n'
            'INSTRUMENT_HOST_NAME = "VOYAGER 2"\n'
            'FILTER_NAME = "CLEAR"\n'
            '^IMAGE = "voyager_iss.vic"\n'
            'END\n',
            fixtures_dir / 'voyager_iss.vic',
        )
        arr, default_is_up, filter_info = read_one_image_array(str(lbl))
        assert arr.ndim == 3
        assert default_is_up is False
        assert filter_info == ('VOYAGER', 'ISS', 'CLEAR')

    def test_galileo_lbl_dispatches_to_galileo_ssi(
        self, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """A .LBL with SPACECRAFT_NAME='GALILEO ORBITER' dispatches to
        galileo_ssi and returns the correct filter_info."""
        lbl = _write_lbl(
            tmp_path,
            'galileo.LBL',
            'PDS_VERSION_ID = PDS3\n'
            'SPACECRAFT_NAME = "GALILEO ORBITER"\n'
            'FILTER_NAME = "CLEAR"\n'
            '^IMAGE = "galileo_ssi_a.vic"\n'
            'END\n',
            fixtures_dir / 'galileo_ssi_a.vic',
        )
        arr, default_is_up, filter_info = read_one_image_array(str(lbl))
        assert arr.ndim == 3
        assert default_is_up is False
        assert filter_info == ('GALILEO', 'SSI', 'CLEAR')

    def test_nh_lorri_lbl_dispatches_to_nh_lorri(
        self, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """A .LBL with INSTRUMENT_HOST_NAME='NEW HORIZONS' and
        INSTRUMENT_ID='LORRI' dispatches to nh_lorri."""
        lbl = _write_lbl(
            tmp_path,
            'lorri.LBL',
            'PDS_VERSION_ID = PDS3\n'
            'INSTRUMENT_HOST_NAME = "NEW HORIZONS"\n'
            'INSTRUMENT_ID = "LORRI"\n'
            '^IMAGE = "nh_mvic.fits"\n'
            'END\n',
            fixtures_dir / 'nh_mvic.fits',
        )
        arr, default_is_up, filter_info = read_one_image_array(str(lbl))
        assert arr.ndim == 3
        assert default_is_up is True
        assert filter_info == ('NEW HORIZONS', 'LORRI', None)

    def test_unrecognized_lbl_falls_back_to_generic_reader(
        self, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """A .LBL that no instrument recognises falls through to the generic
        read_pds3_image_array path."""
        lbl = _write_lbl(
            tmp_path,
            'unknown.LBL',
            'PDS_VERSION_ID = PDS3\n'
            '^IMAGE = "cassini_iss.vic"\n'
            'END\n',
            fixtures_dir / 'cassini_iss.vic',
        )
        arr, default_is_up, filter_info = read_one_image_array(str(lbl))
        assert arr.ndim == 3
        assert default_is_up is False
        assert filter_info is None
