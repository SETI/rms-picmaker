"""PREFIX_BYTES / SUFFIX_BYTES misalignment edge cases for the PDS3
reader, plus pointer-format variants.
Companion to :mod:`tests.test_pds3_reader` (the happy paths).
"""

from pathlib import Path

import numpy as np
import pytest

from picmaker.io import read_pds_labeled_image_array


def test_pds3_prefix_bytes_misaligned_raises(tmp_path: Path) -> None:
    """``PREFIX_BYTES`` not divisible by ``SAMPLE_BITS / 8`` raises ValueError."""
    (tmp_path / 'data.dat').write_bytes(np.zeros(64, dtype='uint8').tobytes())
    lbl = tmp_path / 'bad.LBL'
    lbl.write_text(
        "PDS_VERSION_ID = PDS3\r\n"
        '^IMAGE = "data.dat"\r\n'
        "OBJECT = IMAGE\r\n"
        "  LINES = 8\r\n"
        "  LINE_SAMPLES = 8\r\n"
        "  SAMPLE_BITS = 16\r\n"
        "  SAMPLE_TYPE = UNSIGNED_INTEGER\r\n"
        "  PREFIX_BYTES = 1\r\n"
        "END_OBJECT = IMAGE\r\n"
        "END\r\n"
    )
    with pytest.raises(ValueError, match='PREFIX_BYTES'):
        read_pds_labeled_image_array(str(lbl))


def test_pds3_list_pointer_with_filename_and_record_offset(tmp_path: Path) -> None:
    """``^IMAGE = ("file.dat", n)`` list pointer resolves filename and offset."""
    (tmp_path / 'data.dat').write_bytes(np.zeros(64, dtype='uint8').tobytes())
    lbl = tmp_path / 'list_ptr.LBL'
    lbl.write_text(
        'PDS_VERSION_ID = PDS3\r\n'
        '^IMAGE = ("data.dat", 1)\r\n'
        'OBJECT = IMAGE\r\n'
        '  LINES = 8\r\n'
        '  LINE_SAMPLES = 8\r\n'
        '  SAMPLE_BITS = 8\r\n'
        '  SAMPLE_TYPE = UNSIGNED_INTEGER\r\n'
        'END_OBJECT = IMAGE\r\n'
        'END\r\n'
    )
    result = read_pds_labeled_image_array(str(lbl))
    assert result is not None
    assert result[0].shape == (1, 8, 8)


def test_pds3_suffix_bytes_misaligned_raises(tmp_path: Path) -> None:
    """``SUFFIX_BYTES`` not divisible by ``SAMPLE_BITS / 8`` raises ValueError."""
    (tmp_path / 'data.dat').write_bytes(np.zeros(64, dtype='uint8').tobytes())
    lbl = tmp_path / 'bad.LBL'
    lbl.write_text(
        "PDS_VERSION_ID = PDS3\r\n"
        '^IMAGE = "data.dat"\r\n'
        "OBJECT = IMAGE\r\n"
        "  LINES = 8\r\n"
        "  LINE_SAMPLES = 8\r\n"
        "  SAMPLE_BITS = 16\r\n"
        "  SAMPLE_TYPE = UNSIGNED_INTEGER\r\n"
        "  SUFFIX_BYTES = 1\r\n"
        "END_OBJECT = IMAGE\r\n"
        "END\r\n"
    )
    with pytest.raises(ValueError, match='SUFFIX_BYTES'):
        read_pds_labeled_image_array(str(lbl))
