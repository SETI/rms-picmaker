"""Unit tests for picmaker.instruments._pds3_support.

Replaces the PDS3-side coverage from the removed test_shared_branches.py,
driving read_pds3_image_array with a dict-like fake label and tiny hand-built
data files so each pointer/layout/error branch is exercised directly.
"""

from typing import Any

import numpy as np
import pytest

from picmaker.instruments._pds3_support import (
    _resolve_pds3_filename,
    read_pds3_image_array,
)


class FakeLabel(dict):
    """Dict-like stand-in for pdsparser.Pds3Label (adds the ._filepath attr)."""

    def __init__(self, data: dict[str, Any], filepath: str = '') -> None:
        super().__init__(data)
        self._filepath = filepath


def _img(lines: int, samples: int, bits: int = 16,
         stype: str = 'MSB_INTEGER', **extra: Any) -> dict[str, Any]:
    image = {'SAMPLE_TYPE': stype, 'SAMPLE_BITS': bits,
             'LINES': lines, 'LINE_SAMPLES': samples}
    image.update(extra)
    return image


def _label(tmp_path: Any, image: dict[str, Any], file_bytes: bytes, *,
           extra: dict[str, Any] | None = None) -> FakeLabel:
    (tmp_path / 'data.img').write_bytes(file_bytes)
    data: dict[str, Any] = {'IMAGE': image, '^IMAGE': 'data.img'}
    if extra:
        data.update(extra)
    return FakeLabel(data, filepath=str(tmp_path / 'label.lbl'))


# --- happy paths ---------------------------------------------------------------------

def test_reads_2d_msb_integer(tmp_path: Any) -> None:
    arr = np.arange(6, dtype='>i2').reshape(2, 3)
    out = read_pds3_image_array(_label(tmp_path, _img(2, 3), arr.tobytes()))
    assert out.shape == (2, 3)
    assert out.dtype.byteorder in ('=', '<')
    np.testing.assert_array_equal(out, np.arange(6).reshape(2, 3))


def test_pointer_selects_named_image(tmp_path: Any) -> None:
    arr = np.arange(6, dtype='>i2').reshape(2, 3)
    out = read_pds3_image_array(_label(tmp_path, _img(2, 3), arr.tobytes()),
                                pointers=['IMAGE'])
    assert out.shape == (2, 3)


def test_byte_unit_offset(tmp_path: Any) -> None:
    arr = np.arange(6, dtype='>i2').reshape(2, 3)
    label = _label(tmp_path, _img(2, 3), arr.tobytes(),
                   extra={'^IMAGE_unit': '<BYTES>', '^IMAGE_offset': 1})
    assert read_pds3_image_array(label).shape == (2, 3)


def test_complex_sample_type(tmp_path: Any) -> None:
    arr = np.array([[1 + 2j, 3 + 4j], [5 + 6j, 7 + 8j]], dtype='>c8')
    out = read_pds3_image_array(
        _label(tmp_path, _img(2, 2, bits=64, stype='MSB_COMPLEX'), arr.tobytes()))
    assert out.shape == (2, 2)
    assert out.dtype.kind == 'c'


def test_bil_line_interleaved_shape(tmp_path: Any) -> None:
    data = np.arange(12, dtype='>i2').tobytes()
    image = _img(2, 3, BANDS=2, BAND_STORAGE_TYPE='LINE_INTERLEAVED')
    assert read_pds3_image_array(_label(tmp_path, image, data)).shape == (2, 2, 3)


def test_bip_sample_interleaved_shape(tmp_path: Any) -> None:
    data = np.arange(12, dtype='>i2').tobytes()
    image = _img(2, 3, BANDS=2, BAND_STORAGE_TYPE='SAMPLE_INTERLEAVED')
    assert read_pds3_image_array(_label(tmp_path, image, data)).shape == (2, 2, 3)


# --- error branches ------------------------------------------------------------------

def test_unknown_pointer_raises_keyerror(tmp_path: Any) -> None:
    arr = np.arange(6, dtype='>i2').reshape(2, 3)
    with pytest.raises(KeyError, match='not found'):
        read_pds3_image_array(_label(tmp_path, _img(2, 3), arr.tobytes()),
                              pointers=['NOPE'])


def test_no_image_object_raises_valueerror(tmp_path: Any) -> None:
    label = FakeLabel({'HISTOGRAM': {'OBJECT': 'HISTOGRAM'}},
                      filepath=str(tmp_path / 'l.lbl'))
    with pytest.raises(ValueError, match='does not describe an IMAGE'):
        read_pds3_image_array(label)


def test_obj_out_of_range_raises_indexerror(tmp_path: Any) -> None:
    arr = np.arange(6, dtype='>i2').reshape(2, 3)
    with pytest.raises(IndexError, match='out of range'):
        read_pds3_image_array(_label(tmp_path, _img(2, 3), arr.tobytes()), obj=5)


def test_missing_pointer_keyword_raises_valueerror(tmp_path: Any) -> None:
    label = FakeLabel({'IMAGE': _img(2, 3)}, filepath=str(tmp_path / 'l.lbl'))
    with pytest.raises(ValueError, match='no pointer'):
        read_pds3_image_array(label)


def test_attached_pointer_without_file_raises(tmp_path: Any) -> None:
    # Integer pointer (attached) with no backing label file: also drives the
    # base_dir='.' fallback for an empty _filepath.
    label = FakeLabel({'IMAGE': _img(2, 3), '^IMAGE': 3}, filepath='')
    with pytest.raises(ValueError, match='attached pointer'):
        read_pds3_image_array(label)


def test_short_file_raises_valueerror(tmp_path: Any) -> None:
    # Label promises 2x3 samples (12 bytes) but the file holds only 2.
    with pytest.raises(ValueError, match='fewer image records'):
        read_pds3_image_array(_label(tmp_path, _img(2, 3), b'\x00\x00'))


# --- _resolve_pds3_filename ----------------------------------------------------------

def test_resolve_filename_finds_case_variant(tmp_path: Any) -> None:
    (tmp_path / 'DATA.IMG').write_bytes(b'x')
    assert _resolve_pds3_filename(tmp_path, 'data.img').is_file()


def test_resolve_filename_missing_raises(tmp_path: Any) -> None:
    with pytest.raises(FileNotFoundError, match='could not find data file'):
        _resolve_pds3_filename(tmp_path, 'nope.img')
