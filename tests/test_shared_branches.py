"""Branch coverage for picmaker.instruments._shared helper functions."""

from pathlib import Path
from typing import Any

import astropy.io.fits as pyfits
import numpy as np
import pytest

from picmaker.instruments._shared import (
    extract_fits_array,
    is_fits_file,
    read_pds3_image_array,
)


class _FakeLabel:
    """Minimal stand-in for pdsparser.Pds3Label used to unit-test _shared internals."""

    def __init__(self, filepath: str, d: dict[str, Any]) -> None:
        self._filepath = filepath
        # read_pds3_image_array reads the parsed plain dict via ``.dict``
        # (matching real pdsparser.Pds3Label); ``as_dict()`` is kept for
        # callers that exercise the conversion form.
        self.dict = d
        self._d = d

    def as_dict(self) -> dict[str, Any]:
        return self._d


def test_is_fits_file_type_error_returns_false() -> None:
    """Passing a non-path-like value (None) returns False without raising."""
    assert is_fits_file(None) is False  # type: ignore[arg-type]


class TestExtractFitsArray:
    def test_string_obj_not_parseable_as_int_uses_hdu_name(self) -> None:
        """A string obj that int() cannot parse is used directly as an HDU name key."""
        arr = np.zeros((8, 8), dtype=np.int16)
        hdu_named = pyfits.ImageHDU(data=arr, name='SCI')
        hdulist = pyfits.HDUList([pyfits.PrimaryHDU(), hdu_named])
        result = extract_fits_array(hdulist, 'SCI')
        assert result.shape == (1, 8, 8)

    def test_obj_none_no_valid_hdu_raises_oserror(self) -> None:
        """obj=None with no 2-D/3-D HDU raises OSError."""
        hdulist = pyfits.HDUList([pyfits.PrimaryHDU()])  # data is None
        with pytest.raises(OSError, match='Image array not found'):
            extract_fits_array(hdulist, None)

    def test_list_obj_with_3d_layer_raises(self) -> None:
        """A list obj selecting a 3-D HDU raises instead of returning a 4-D array."""
        cube = pyfits.ImageHDU(data=np.zeros((2, 4, 4), dtype=np.int16), name='CUBE')
        hdulist = pyfits.HDUList([pyfits.PrimaryHDU(), cube])
        with pytest.raises(OSError, match='must each be 2-D'):
            extract_fits_array(hdulist, [1])

    def test_list_obj_of_2d_layers_stacks_into_bands(self) -> None:
        """A list obj of 2-D HDUs stacks one band per HDU."""
        a = pyfits.ImageHDU(data=np.zeros((4, 4), dtype=np.int16), name='A')
        b = pyfits.ImageHDU(data=np.ones((4, 4), dtype=np.int16), name='B')
        hdulist = pyfits.HDUList([pyfits.PrimaryHDU(), a, b])
        result = extract_fits_array(hdulist, [1, 2])
        assert result.shape == (2, 4, 4)


class TestReadPds3ImageArray:
    def test_no_image_pointer_raises(self, tmp_path: Path) -> None:
        """A label dict with no ^*IMAGE key raises OSError immediately."""
        fake = _FakeLabel(str(tmp_path / 'test.LBL'), {})
        with pytest.raises(OSError, match='No \\^\\*IMAGE pointer'):
            read_pds3_image_array(fake, None)

    def test_int_pointer_uses_label_basename_as_data_file(self, tmp_path: Path) -> None:
        """An integer ^IMAGE pointer sets data_filename to the label's own basename."""
        lbl = tmp_path / 'test.LBL'
        lbl.write_bytes(b'not vicar not fits')
        fake = _FakeLabel(str(lbl), {'^IMAGE': 1})
        # data_file resolves to the label file itself, which is neither VICAR
        # nor FITS, so the final OSError fires.
        with pytest.raises(OSError, match='Cannot read PDS3 data file'):
            read_pds3_image_array(fake, None)

    def test_int_pointer_record_offset_above_one_raises(self, tmp_path: Path) -> None:
        """An integer ^IMAGE record number > 1 (a real byte offset this reader
        cannot seek to) raises rather than silently reading from byte 0."""
        lbl = tmp_path / 'test.LBL'
        lbl.write_bytes(b'not vicar not fits')
        fake = _FakeLabel(str(lbl), {'^IMAGE': 5})
        with pytest.raises(OSError, match='record offset 5 is not supported'):
            read_pds3_image_array(fake, None)

    def test_unexpected_pointer_type_raises(self, tmp_path: Path) -> None:
        """A pointer value of unrecognized type (float) raises OSError."""
        fake = _FakeLabel(str(tmp_path / 'test.LBL'), {'^IMAGE': 3.14})
        with pytest.raises(OSError, match='Unexpected \\^IMAGE pointer value'):
            read_pds3_image_array(fake, None)

    def test_fits_data_file_reads_via_fits_branch(self, tmp_path: Path) -> None:
        """A string ^IMAGE pointer to a clean FITS file reads via the FITS branch."""
        arr = np.zeros((8, 8), dtype=np.float32)
        fits_path = tmp_path / 'data.fits'
        pyfits.HDUList([pyfits.PrimaryHDU(data=arr)]).writeto(
            str(fits_path), overwrite=True
        )
        fake = _FakeLabel(str(tmp_path / 'test.LBL'), {'^IMAGE': 'data.fits'})
        result = read_pds3_image_array(fake, None)
        assert result.ndim == 3

    def test_unreadable_data_file_raises(self, tmp_path: Path) -> None:
        """A pointer to a file that is neither VICAR nor FITS raises OSError."""
        (tmp_path / 'junk.dat').write_bytes(b'not vicar not fits data here')
        fake = _FakeLabel(str(tmp_path / 'test.LBL'), {'^IMAGE': 'junk.dat'})
        with pytest.raises(OSError, match='Cannot read PDS3 data file'):
            read_pds3_image_array(fake, None)
