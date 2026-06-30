"""Cover the remaining instrument/PDS3 read helpers and the .LBL dispatch path.

Dropped relative to the old ``test_io_extra``:
  * ``TestReadArray`` / ``TestReadPil`` -- ``picmaker.io.read_array`` and
    ``read_pil`` were removed in the refactor and have no replacement.

The PDS3 dispatch tests are rebuilt around proper PDS3 IMAGE objects: the
per-instrument ``detect_in_pds3`` hooks now read pixels via
``read_pds3_image_array``, which requires a real ``OBJECT = IMAGE`` definition
(the old VICAR-pointed stub labels no longer suffice). Each test now asserts
``default_upward`` / ``default_tint`` instead of the removed ``image_info``
triple.
"""

from pathlib import Path

import numpy as np
import pdsparser
from PIL import Image

from picmaker import write_pil
from picmaker.instruments import read_image_array, read_pds3_image_array

# A reusable PDS3 IMAGE object describing 8x8 UNSIGNED_INTEGER pixels stored in
# a detached "data.dat" file alongside the label.
_IMAGE_OBJECT = (
    'OBJECT = IMAGE\r\n'
    '  LINES = 8\r\n'
    '  LINE_SAMPLES = 8\r\n'
    '  SAMPLE_BITS = 8\r\n'
    '  SAMPLE_TYPE = UNSIGNED_INTEGER\r\n'
    'END_OBJECT = IMAGE\r\n'
)


def _write_pds3_pair(tmp_path: Path, name: str, header: str) -> Path:
    """Write a detached PDS3 label (with image-identifying ``header`` keywords)
    next to an 8x8 uint8 ``data.dat`` file, and return the label path.
    """
    (tmp_path / 'data.dat').write_bytes(np.arange(64, dtype='uint8').tobytes())
    lbl = tmp_path / name
    lbl.write_text(
        'PDS_VERSION_ID = PDS3\r\n'
        f'{header}'
        '^IMAGE = "data.dat"\r\n'
        f'{_IMAGE_OBJECT}'
        'END\r\n'
    )
    return lbl


class TestWritePil:
    def test_round_trip_quality_setting(self, fixtures_dir: Path, tmp_path: Path) -> None:
        img = Image.open(str(fixtures_dir / 'small_grayscale.png'))
        out = tmp_path / 'out.jpg'
        write_pil(img, str(out), quality=50)
        assert out.exists()
        out2 = tmp_path / 'out_hq.jpg'
        write_pil(img, str(out2), quality=95)
        # Quality 95 is at least as big as quality 50 for the same source.
        assert out2.stat().st_size >= out.stat().st_size


class TestReadPds3ImageArray:
    def test_minimal_pds3_sample(self, fixtures_dir: Path) -> None:
        """``read_pds3_image_array`` returns the bare pixel array (2-D for a
        single-band IMAGE) given a parsed label.
        """
        label = pdsparser.Pds3Label(str(fixtures_dir / 'pds3_sample.IMG'))
        arr = read_pds3_image_array(label, 0)
        assert arr.shape == (8, 8)


class TestPds3LabelDispatch:
    """``read_image_array`` dispatches ``.LBL`` paths to per-instrument readers."""

    def test_cassini_lbl_dispatches_to_cassini_iss(self, tmp_path: Path) -> None:
        """A Cassini ISS label resolves the ``CL1+RED`` tint."""
        lbl = _write_pds3_pair(
            tmp_path, 'cassini.LBL',
            'INSTRUMENT_HOST_NAME = "CASSINI ORBITER"\r\n'
            'INSTRUMENT_ID = "ISSNA"\r\n'
            'FILTER_NAME = ("CL1", "RED")\r\n',
        )
        data = read_image_array(str(lbl))
        assert data.array.shape == (8, 8)
        assert data.default_upward is False
        assert data.default_tint == (190, 110, 100)

    def test_voyager_lbl_dispatches_to_voyager_iss(self, tmp_path: Path) -> None:
        """A Voyager ISS label resolves the GREEN-filter tint."""
        lbl = _write_pds3_pair(
            tmp_path, 'voyager.LBL',
            'INSTRUMENT_HOST_NAME = "VOYAGER 2"\r\n'
            'INSTRUMENT_ID = "ISSNA"\r\n'
            'FILTER_NAME = "GREEN"\r\n',
        )
        data = read_image_array(str(lbl))
        assert data.array.shape == (8, 8)
        assert data.default_upward is False
        assert data.default_tint == (110, 255, 110)

    def test_galileo_lbl_dispatches_to_galileo_ssi(self, tmp_path: Path) -> None:
        """A Galileo SSI label (SPACECRAFT_NAME + INSTRUMENT_NAME) dispatches to
        galileo_ssi and resolves the GREEN tint.
        """
        lbl = _write_pds3_pair(
            tmp_path, 'galileo.LBL',
            'SPACECRAFT_NAME = "GALILEO ORBITER"\r\n'
            'INSTRUMENT_NAME = "SOLID STATE IMAGING SYSTEM"\r\n'
            'FILTER_NAME = "GREEN"\r\n',
        )
        data = read_image_array(str(lbl))
        assert data.array.shape == (8, 8)
        assert data.default_upward is False
        assert data.default_tint == (110, 190, 110)

    def test_nh_lorri_lbl_dispatches_to_nh_lorri(self, tmp_path: Path) -> None:
        """A New Horizons LORRI label dispatches to nh_lorri (upward, no tint)."""
        lbl = _write_pds3_pair(
            tmp_path, 'lorri.LBL',
            'INSTRUMENT_HOST_ID = "NH"\r\n'
            'INSTRUMENT_ID = "LORRI"\r\n',
        )
        data = read_image_array(str(lbl))
        assert data.array.shape == (8, 8)
        assert data.default_upward is True
        assert data.default_tint is None

    def test_unrecognized_lbl_falls_back_to_generic_reader(self, tmp_path: Path) -> None:
        """A label that no instrument recognises falls through to the generic
        PDS3 reader (downward default, no tint).
        """
        lbl = _write_pds3_pair(tmp_path, 'unknown.LBL', '')
        data = read_image_array(str(lbl))
        assert data.array.shape == (8, 8)
        assert data.default_upward is False
        assert data.default_tint is None
