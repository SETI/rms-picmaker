"""Pointer-format and multi-band layout branches for
:func:`picmaker.instruments.read_pds3_image_array`.
Companion to :mod:`tests.test_pds3_reader`.

Dropped relative to the old ``picmaker.io`` tests: the PREFIX_BYTES /
SUFFIX_BYTES "misaligned -> ValueError" cases. The reader now reads
LINE_PREFIX_BYTES / LINE_SUFFIX_BYTES as opaque void-byte blocks of any width,
so there is no divisibility check to trigger and no replacement behavior.
"""

from pathlib import Path

import numpy as np
import pdsparser

from picmaker.instruments import read_pds3_image_array


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
    arr = read_pds3_image_array(pdsparser.Pds3Label(str(lbl)))
    assert arr.shape == (8, 8)


def test_pds3_band_sequential_three_dim(tmp_path: Path) -> None:
    """A ``BANDS`` IMAGE in BAND_SEQUENTIAL order returns a 3-D array shaped
    (bands, lines, samples).
    """
    pixels = np.arange(2 * 4 * 4, dtype='uint8')
    (tmp_path / 'data.dat').write_bytes(pixels.tobytes())
    lbl = tmp_path / 'bands.LBL'
    lbl.write_text(
        'PDS_VERSION_ID = PDS3\r\n'
        '^IMAGE = "data.dat"\r\n'
        'OBJECT = IMAGE\r\n'
        '  LINES = 4\r\n'
        '  LINE_SAMPLES = 4\r\n'
        '  BANDS = 2\r\n'
        '  BAND_STORAGE_TYPE = BAND_SEQUENTIAL\r\n'
        '  SAMPLE_BITS = 8\r\n'
        '  SAMPLE_TYPE = UNSIGNED_INTEGER\r\n'
        'END_OBJECT = IMAGE\r\n'
        'END\r\n'
    )
    arr = read_pds3_image_array(pdsparser.Pds3Label(str(lbl)))
    assert arr.shape == (2, 4, 4)
    np.testing.assert_array_equal(arr, pixels.reshape(2, 4, 4))
