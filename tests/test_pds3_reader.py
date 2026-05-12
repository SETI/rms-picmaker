"""Tests for :func:`picmaker.io.read_pds_labeled_image_array`.

The PDS3 reader has four pointer-resolution branches (attached integer,
detached string, detached tuple-with-filename, attached tuple-with-unit)
plus the sibling-label fallback (``foo.LBL`` next to ``foo.IMG``) and
several error paths. Each test covers one branch.
"""

from pathlib import Path

import numpy as np
import pytest

from picmaker.io import read_pds_labeled_image_array


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
    img = _write_pds3_attached(tmp_path)
    result = read_pds_labeled_image_array(str(img))
    assert result is not None
    arr, _, _ = result
    assert arr.shape == (1, 8, 8)
    # The pixels we wrote were 0..63.
    np.testing.assert_array_equal(arr[0].reshape(-1), np.arange(64, dtype='uint8'))


def test_attached_obj_name(tmp_path: Path) -> None:
    """Looking up by explicit object name (``obj='IMAGE'``) works."""
    img = _write_pds3_attached(tmp_path)
    result = read_pds_labeled_image_array(str(img), obj='IMAGE')
    assert result is not None


def test_attached_obj_unknown_name_raises(tmp_path: Path) -> None:
    """A name not in the label raises ``KeyError``."""
    img = _write_pds3_attached(tmp_path)
    with pytest.raises(KeyError, match='Object MISSING not found'):
        read_pds_labeled_image_array(str(img), obj='MISSING')


def test_attached_obj_out_of_range(tmp_path: Path) -> None:
    """``obj=99`` raises ``IndexError`` with the source file in the message."""
    img = _write_pds3_attached(tmp_path)
    with pytest.raises(IndexError, match='out of range'):
        read_pds_labeled_image_array(str(img), obj=99)


def test_attached_obj_bad_type(tmp_path: Path) -> None:
    """A non-int/non-str ``obj`` raises ``TypeError``."""
    img = _write_pds3_attached(tmp_path)
    with pytest.raises(TypeError, match='Invalid index type'):
        read_pds_labeled_image_array(str(img), obj=[1, 2])


def test_no_image_objects_raises(tmp_path: Path) -> None:
    """A label without any ``^.*IMAGE`` pointer raises ``KeyError``."""
    lbl = tmp_path / 'empty.LBL'
    lbl.write_text(
        "PDS_VERSION_ID = PDS3\r\n"
        "RECORD_BYTES = 0\r\n"
        "END\r\n"
    )
    with pytest.raises(KeyError, match='No IMAGE objects found'):
        read_pds_labeled_image_array(str(lbl))


def test_unparseable_file_returns_none(tmp_path: Path) -> None:
    """An unparseable file with no sibling ``.LBL`` returns ``None``."""
    bin_path = tmp_path / 'garbage.IMG'
    bin_path.write_bytes(b'\x00\x01\x02not a label\x03\x04')
    assert read_pds_labeled_image_array(str(bin_path)) is None


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
    result = read_pds_labeled_image_array(str(lbl))
    assert result is not None
    arr, _, _ = result
    assert arr.shape == (1, 8, 8)
    np.testing.assert_array_equal(arr[0].reshape(-1), np.arange(64, dtype='uint8'))


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
    result = read_pds_labeled_image_array(str(lbl))
    assert result is not None
    arr, _, _ = result
    np.testing.assert_array_equal(arr[0].reshape(-1), pixels)


def test_pds3_msb_signed_two_byte(tmp_path: Path) -> None:
    """An MSB_INTEGER 2-byte image decodes with the right dtype."""
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
    result = read_pds_labeled_image_array(str(lbl))
    assert result is not None
    arr, _, _ = result
    assert arr.dtype == np.dtype('>i2')
    np.testing.assert_array_equal(arr[0].reshape(-1), pixels.astype('>i2'))


def test_pds3_lsb_real_four_byte(tmp_path: Path) -> None:
    """A PC_REAL 4-byte image decodes as little-endian float."""
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
    result = read_pds_labeled_image_array(str(lbl))
    assert result is not None
    arr, _, _ = result
    assert arr.dtype == np.dtype('<f4')


def test_pds3_prefix_suffix_samples_stripped(tmp_path: Path) -> None:
    """PREFIX_BYTES / SUFFIX_BYTES bytes are stripped from each row."""
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
        "  PREFIX_BYTES = 1\r\n"
        "  SUFFIX_BYTES = 1\r\n"
        "END_OBJECT = IMAGE\r\n"
        "END\r\n"
    )
    result = read_pds_labeled_image_array(str(lbl))
    assert result is not None
    arr, _, _ = result
    assert arr.shape == (1, 4, 4)
    np.testing.assert_array_equal(arr[0], real)


def test_pds3_label_picks_up_metadata(tmp_path: Path) -> None:
    """INSTRUMENT_NAME / INSTRUMENT_HOST_NAME / FILTER_NAME flow into
    the returned ``filter_info`` triple.
    """
    (tmp_path / 'data.dat').write_bytes(np.arange(64, dtype='uint8').tobytes())
    lbl = tmp_path / 'meta.LBL'
    lbl.write_text(
        "PDS_VERSION_ID = PDS3\r\n"
        'INSTRUMENT_NAME = "ISS"\r\n'
        'INSTRUMENT_HOST_NAME = "CASSINI"\r\n'
        'FILTER_NAME = "RED"\r\n'
        '^IMAGE = "data.dat"\r\n'
        "OBJECT = IMAGE\r\n"
        "  LINES = 8\r\n"
        "  LINE_SAMPLES = 8\r\n"
        "  SAMPLE_BITS = 8\r\n"
        "  SAMPLE_TYPE = UNSIGNED_INTEGER\r\n"
        "END_OBJECT = IMAGE\r\n"
        "END\r\n"
    )
    result = read_pds_labeled_image_array(str(lbl))
    assert result is not None
    _, _, filter_info = result
    assert filter_info == ('ISS', 'CASSINI', 'RED')


def test_pds3_falls_back_to_spacecraft_name(tmp_path: Path) -> None:
    """Without INSTRUMENT_NAME, SPACECRAFT_NAME populates ``inst_host``."""
    (tmp_path / 'data.dat').write_bytes(np.arange(64, dtype='uint8').tobytes())
    lbl = tmp_path / 'sc.LBL'
    lbl.write_text(
        "PDS_VERSION_ID = PDS3\r\n"
        'SPACECRAFT_NAME = "VOYAGER 1"\r\n'
        '^IMAGE = "data.dat"\r\n'
        "OBJECT = IMAGE\r\n"
        "  LINES = 8\r\n"
        "  LINE_SAMPLES = 8\r\n"
        "  SAMPLE_BITS = 8\r\n"
        "  SAMPLE_TYPE = UNSIGNED_INTEGER\r\n"
        "END_OBJECT = IMAGE\r\n"
        "END\r\n"
    )
    result = read_pds_labeled_image_array(str(lbl))
    assert result is not None
    _, _, filter_info = result
    assert filter_info is not None
    assert filter_info[0] == 'VOYAGER 1'


def test_pds3_sibling_label_fallback(tmp_path: Path) -> None:
    """An unparseable ``.IMG`` plus a sibling ``.LBL`` triggers the
    fallback constructor on the .LBL.
    """
    img = tmp_path / 'sample.IMG'
    img.write_bytes(np.arange(64, dtype='uint8').tobytes())
    lbl = tmp_path / 'sample.LBL'
    lbl.write_text(
        "PDS_VERSION_ID = PDS3\r\n"
        '^IMAGE = "sample.IMG"\r\n'
        "OBJECT = IMAGE\r\n"
        "  LINES = 8\r\n"
        "  LINE_SAMPLES = 8\r\n"
        "  SAMPLE_BITS = 8\r\n"
        "  SAMPLE_TYPE = UNSIGNED_INTEGER\r\n"
        "END_OBJECT = IMAGE\r\n"
        "END\r\n"
    )
    # Pass the IMG path (unparseable) — the reader should switch to the .LBL.
    result = read_pds_labeled_image_array(str(img))
    assert result is not None
    arr, _, _ = result
    assert arr.shape == (1, 8, 8)
