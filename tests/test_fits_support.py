"""Unit tests for picmaker.instruments._fits_support HDU-selection helpers.

These replace the FITS-side coverage that the removed test_shared_branches.py
gave, driven directly against the current `_fits_support` API.
"""

import numpy as np
import pytest
from astropy.io import fits

from picmaker.instruments._fits_support import (
    get_fits_array,
    get_fits_image_hdu,
    get_fits_image_hdus,
    hdu_is_image,
)


def _hdulist() -> fits.HDUList:
    """A dataless primary + two named IMAGE extensions + a BINTABLE."""
    primary = fits.PrimaryHDU()
    sci = fits.ImageHDU(np.arange(16, dtype=np.float32).reshape(4, 4), name='SCI')
    dq = fits.ImageHDU(np.zeros((4, 4), dtype=np.int16), name='DQ')
    table = fits.BinTableHDU.from_columns(
        [fits.Column(name='x', format='I', array=np.arange(3))], name='TAB')
    return fits.HDUList([primary, sci, dq, table])


def test_hdu_is_image_true_for_image_extension() -> None:
    assert hdu_is_image(_hdulist()['SCI']) is True


def test_hdu_is_image_false_for_bintable() -> None:
    assert hdu_is_image(_hdulist()['TAB']) is False


def test_hdu_is_image_false_for_dataless_primary() -> None:
    """No XTENSION card and NAXIS < 2 -> not an image."""
    assert hdu_is_image(fits.PrimaryHDU()) is False


def test_hdu_is_image_false_for_table_without_xtension() -> None:
    """NAXIS >= 2 but TFIELDS present (a table-like HDU) -> not an image."""
    primary = fits.PrimaryHDU(np.zeros((4, 4), dtype=np.float32))
    primary.header['TFIELDS'] = 3
    assert hdu_is_image(primary) is False


def test_get_fits_image_hdus_returns_all_images_by_default() -> None:
    assert [h.name for h in get_fits_image_hdus(_hdulist())] == ['SCI', 'DQ']


def test_get_fits_image_hdus_pointer_string_selects_by_extname() -> None:
    """A bare string pointer is accepted, and the EXTNAME-less primary HDU is
    skipped rather than raising (regression guard for the `.get` fix)."""
    assert [h.name for h in get_fits_image_hdus(_hdulist(), pointers='DQ')] == ['DQ']


def test_get_fits_image_hdus_unknown_pointer_raises_keyerror() -> None:
    with pytest.raises(KeyError, match='NOPE'):
        get_fits_image_hdus(_hdulist(), pointers=['NOPE'])


def test_get_fits_image_hdus_no_image_raises_valueerror() -> None:
    table = _hdulist()['TAB']
    with pytest.raises(ValueError, match='No IMAGE HDU'):
        get_fits_image_hdus(fits.HDUList([fits.PrimaryHDU(), table]))


def test_get_fits_image_hdu_obj_index_selects_nth_image() -> None:
    assert get_fits_image_hdu(_hdulist(), obj=1).name == 'DQ'
    assert get_fits_image_hdu(_hdulist(), obj=-1).name == 'DQ'


def test_get_fits_image_hdu_obj_out_of_range_raises_indexerror() -> None:
    with pytest.raises(IndexError, match='out of range'):
        get_fits_image_hdu(_hdulist(), obj=9)


def test_get_fits_image_hdu_non_image_pointer_raises_valueerror() -> None:
    with pytest.raises(ValueError, match='not an IMAGE'):
        get_fits_image_hdu(_hdulist(), pointers=['TAB'])


def test_get_fits_array_returns_selected_image_data() -> None:
    arr = get_fits_array(_hdulist(), pointers=['SCI'])
    assert arr.shape == (4, 4)
    assert arr[0, 0] == 0
    assert arr[-1, -1] == 15
