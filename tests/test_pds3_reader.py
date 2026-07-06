"""Tests for :func:`picmaker.instruments.read_pds3_image_array`.

The PDS3 reader resolves the pointer (attached integer, detached string,
detached tuple-with-record) and the on-disk sample layout. It now takes an
already-parsed :class:`pdsparser.Pds3Label` and returns the bare pixel array
(2-D for a single-band IMAGE); the old path-string / ``None`` / sibling-.LBL /
``image_info`` behaviors moved out of this function and their tests are dropped.

Dropped relative to the old ``picmaker.io.read_pds_labeled_image_array`` tests:
  * object lookup by name (``obj='IMAGE'`` / ``obj='MISSING'``) -- ``obj`` is
    now an integer index only.
  * unparseable-file -> ``None`` and the sibling-.LBL fallback -- parsing now
    happens in the reader cascade, not here.
  * ``image_info`` (INSTRUMENT/SPACECRAFT/FILTER) extraction -- this function
    returns only the array now.
"""

from pathlib import Path

import numpy as np
import pdsparser
import pytest

from tests import read_pds3_array as _read


def _write_pds3_attached(tmp_path: Path) -> Path:
    """Build a tiny attached PDS3 IMG with the label in record 1 and 8x8
    UNSIGNED_INTEGER pixels in record 2.
    """
    record_bytes = 512
    label_text = (
        "PDS_VERSION_ID = PDS3\r\n"
        "RECORD_TYPE = FIXED_LENGTH\r\n"
        f"RECORD_BYTES = {record_bytes}\r\n"
        "FILE_RECORDS = 2\r\n"
        "LABEL_RECORDS = 1\r\n"
        "^IMAGE = 2\r\n"
        "OBJECT = IMAGE\r\n"
        "  LINES = 8\r\n"
        "  LINE_SAMPLES = 8\r\n"
        "  SAMPLE_BITS = 8\r\n"
        "  SAMPLE_TYPE = UNSIGNED_INTEGER\r\n"
        "END_OBJECT = IMAGE\r\n"
        "END\r\n"
    )
    label_bytes = label_text.encode('ascii')
    label_bytes += b' ' * (record_bytes - len(label_bytes))
    pixels = np.arange(64, dtype='uint8').tobytes()
    pixels += b'\x00' * (record_bytes - len(pixels))
    p = tmp_path / 'attached.IMG'
    p.write_bytes(label_bytes + pixels)
    return p


def test_attached_integer_pointer(tmp_path: Path) -> None:
    """Attached image: ``^IMAGE = 2`` resolves to record 2 of this file."""
    label = pdsparser.Pds3Label(str(_write_pds3_attached(tmp_path)))
    arr = _read(label)
    assert arr.shape == (8, 8)
    # The pixels we wrote were 0..63.
    np.testing.assert_array_equal(arr.reshape(-1), np.arange(64, dtype='uint8'))


def test_attached_obj_index_zero(tmp_path: Path) -> None:
    """The explicit first-image index (``obj=0``) matches the default."""
    label = pdsparser.Pds3Label(str(_write_pds3_attached(tmp_path)))
    np.testing.assert_array_equal(
        _read(label, 0), _read(label)
    )


def test_attached_obj_out_of_range(tmp_path: Path) -> None:
    """``obj=99`` raises ``IndexError`` for a single-image label."""
    label = pdsparser.Pds3Label(str(_write_pds3_attached(tmp_path)))
    with pytest.raises(IndexError, match='out of range'):
        _read(label, 99)


def test_attached_obj_bad_type(tmp_path: Path) -> None:
    """A non-int ``obj`` fails the range comparison with ``TypeError``."""
    label = pdsparser.Pds3Label(str(_write_pds3_attached(tmp_path)))
    with pytest.raises(TypeError, match='not supported between instances'):
        _read(label, [1, 2])


def test_no_image_objects_raises(tmp_path: Path) -> None:
    """A label without any IMAGE object raises ``ValueError``."""
    lbl = tmp_path / 'empty.LBL'
    lbl.write_text(
        "PDS_VERSION_ID = PDS3\r\n"
        "RECORD_BYTES = 0\r\n"
        "END\r\n"
    )
    with pytest.raises(ValueError, match='does not describe an IMAGE'):
        _read(pdsparser.Pds3Label(str(lbl)))


def test_detached_string_pointer(tmp_path: Path) -> None:
    """Detached image: ``^IMAGE = "data.dat"`` reads the named file."""
    img_file = tmp_path / 'data.dat'
    img_file.write_bytes(np.arange(64, dtype='uint8').tobytes())

    lbl = tmp_path / 'detached.LBL'
    lbl.write_text(
        "PDS_VERSION_ID = PDS3\r\n"
        "RECORD_BYTES = 64\r\n"
        '^IMAGE = "data.dat"\r\n'
        "OBJECT = IMAGE\r\n"
        "  LINES = 8\r\n"
        "  LINE_SAMPLES = 8\r\n"
        "  SAMPLE_BITS = 8\r\n"
        "  SAMPLE_TYPE = UNSIGNED_INTEGER\r\n"
        "END_OBJECT = IMAGE\r\n"
        "END\r\n"
    )
    arr = _read(pdsparser.Pds3Label(str(lbl)))
    assert arr.shape == (8, 8)
    np.testing.assert_array_equal(arr.reshape(-1), np.arange(64, dtype='uint8'))


def test_detached_tuple_pointer_with_record(tmp_path: Path) -> None:
    """Detached image: ``^IMAGE = ("data.dat", 2)`` skips one record."""
    record_bytes = 64
    pad = np.zeros(record_bytes, dtype='uint8')
    pixels = np.arange(64, dtype='uint8')
    (tmp_path / 'data.dat').write_bytes(pad.tobytes() + pixels.tobytes())

    lbl = tmp_path / 'detached.LBL'
    lbl.write_text(
        "PDS_VERSION_ID = PDS3\r\n"
        f"RECORD_BYTES = {record_bytes}\r\n"
        '^IMAGE = ("data.dat", 2)\r\n'
        "OBJECT = IMAGE\r\n"
        "  LINES = 8\r\n"
        "  LINE_SAMPLES = 8\r\n"
        "  SAMPLE_BITS = 8\r\n"
        "  SAMPLE_TYPE = UNSIGNED_INTEGER\r\n"
        "END_OBJECT = IMAGE\r\n"
        "END\r\n"
    )
    arr = _read(pdsparser.Pds3Label(str(lbl)))
    np.testing.assert_array_equal(arr.reshape(-1), pixels)


def test_pds3_msb_signed_two_byte(tmp_path: Path) -> None:
    """An MSB_INTEGER 2-byte image decodes to native-endian signed int16."""
    pixels = np.arange(64, dtype='>i2')
    (tmp_path / 'data.dat').write_bytes(pixels.tobytes())

    lbl = tmp_path / 'two_byte.LBL'
    lbl.write_text(
        "PDS_VERSION_ID = PDS3\r\n"
        '^IMAGE = "data.dat"\r\n'
        "OBJECT = IMAGE\r\n"
        "  LINES = 8\r\n"
        "  LINE_SAMPLES = 8\r\n"
        "  SAMPLE_BITS = 16\r\n"
        "  SAMPLE_TYPE = MSB_INTEGER\r\n"
        "END_OBJECT = IMAGE\r\n"
        "END\r\n"
    )
    arr = _read(pdsparser.Pds3Label(str(lbl)))
    # The reader converts to native byte order, so the dtype is plain int16.
    assert arr.dtype == np.dtype('int16')
    np.testing.assert_array_equal(arr.reshape(-1), pixels.astype('int16'))


def test_pds3_lsb_real_four_byte(tmp_path: Path) -> None:
    """A PC_REAL 4-byte image decodes to native-endian float32."""
    pixels = np.arange(64, dtype='<f4') * 1.5
    (tmp_path / 'data.dat').write_bytes(pixels.tobytes())

    lbl = tmp_path / 'real.LBL'
    lbl.write_text(
        "PDS_VERSION_ID = PDS3\r\n"
        '^IMAGE = "data.dat"\r\n'
        "OBJECT = IMAGE\r\n"
        "  LINES = 8\r\n"
        "  LINE_SAMPLES = 8\r\n"
        "  SAMPLE_BITS = 32\r\n"
        "  SAMPLE_TYPE = PC_REAL\r\n"
        "END_OBJECT = IMAGE\r\n"
        "END\r\n"
    )
    arr = _read(pdsparser.Pds3Label(str(lbl)))
    assert arr.dtype == np.dtype('float32')
    np.testing.assert_array_equal(arr.reshape(-1), pixels.astype('float32'))


def test_pds3_prefix_suffix_samples_stripped(tmp_path: Path) -> None:
    """LINE_PREFIX_BYTES / LINE_SUFFIX_BYTES bytes are stripped from each row."""
    pixels = np.empty((4, 6), dtype='uint8')
    pixels[:] = 0
    # Real samples are columns 1..5 (4 wide); cols 0 and 5 are pre/suffix.
    real = np.arange(16, dtype='uint8').reshape(4, 4)
    pixels[:, 1:5] = real
    (tmp_path / 'data.dat').write_bytes(pixels.tobytes())

    lbl = tmp_path / 'pad.LBL'
    lbl.write_text(
        "PDS_VERSION_ID = PDS3\r\n"
        '^IMAGE = "data.dat"\r\n'
        "OBJECT = IMAGE\r\n"
        "  LINES = 4\r\n"
        "  LINE_SAMPLES = 4\r\n"
        "  SAMPLE_BITS = 8\r\n"
        "  SAMPLE_TYPE = UNSIGNED_INTEGER\r\n"
        "  LINE_PREFIX_BYTES = 1\r\n"
        "  LINE_SUFFIX_BYTES = 1\r\n"
        "END_OBJECT = IMAGE\r\n"
        "END\r\n"
    )
    arr = _read(pdsparser.Pds3Label(str(lbl)))
    assert arr.shape == (4, 4)
    np.testing.assert_array_equal(arr, real)
