"""End-to-end read_one_image_array tests for all instrument fixtures + the
malformed cascade."""

from __future__ import annotations

from pathlib import Path

import pytest

from picmaker.picmaker import read_one_image_array

# (fixture_name, expected detect tuple, expected is_color flag)
INSTRUMENT_FIXTURES = [
    ('cassini_iss.vic', ('CASSINI', 'ISS', 'CL1+GRN'), False),
    ('voyager_iss.vic', ('VOYAGER', 'ISS', 'GREEN'), False),
    ('galileo_ssi_a.vic', ('GALILEO', 'SSI', 'GREEN'), False),
    ('galileo_ssi_b.vic', ('GALILEO', 'SSI', 'GREEN'), False),
    ('hst_wfc3.fits', ('HST', 'WFC3/UVIS', 'F606W'), True),
    ('hst_acs.fits', ('HST', 'ACS/WFC', ('CL1', 'F606W')), True),
    ('hst_wfpc2.fits', ('HST', 'WFPC2', ('F555W', 'CLEAR2')), True),
    ('nh_mvic.fits', ('NEW HORIZONS', 'MVIC', 'BLUE'), True),
]


@pytest.mark.parametrize(('fixture', 'expected', 'is_color'), INSTRUMENT_FIXTURES)
def test_instrument_detection(
    fixture: str, expected: tuple, is_color: bool, fixtures_dir: Path
) -> None:
    array, color, detect = read_one_image_array(str(fixtures_dir / fixture), None)
    assert detect == expected
    assert color is is_color
    assert array.ndim == 3  # always 3-D after reshape


@pytest.mark.parametrize('fixture', [
    'malformed_pickle.bin',
    'malformed_numpy.bin',
    'corrupt_vicar.vic',
    'corrupt_fits.fits',
])
def test_malformed_falls_through_cascade(fixture: str, fixtures_dir: Path) -> None:
    with pytest.raises(IOError, match=r'Unrecognized image file format'):
        read_one_image_array(str(fixtures_dir / fixture), None)
