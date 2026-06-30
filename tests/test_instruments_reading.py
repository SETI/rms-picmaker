"""End-to-end :func:`picmaker.instruments.read_image_array` tests for the
instrument fixtures plus the malformed/unrecognized cascade.

The post-refactor reader no longer returns a ``(array, color, detect)`` triple;
it returns an :class:`picmaker.instruments.ImageData` with ``.array``,
``.default_upward``, and ``.default_tint`` attributes. The old per-frame
instrument-detection metadata (the ``('CASSINI', 'ISS', ...)`` tuples and the
``is_color`` flag) no longer exists, so those assertions are dropped.
"""

from pathlib import Path

import pytest

from picmaker.instruments import read_image_array

# (fixture_name, expected_shape, default_upward, default_tint)
# VICAR fixtures come back 3-D (band axis preserved by vicar); the FITS
# fixtures come back 2-D. Synthetic fixtures carry no FILTER_NAME, so the
# default tint is None. hst_acs.fits / hst_wfpc2.fits are xfailed: their
# instrument modules (hst_acs, hst_wfpc2) are work-in-progress and raise
# AttributeError inside detect_in_fits.
INSTRUMENT_FIXTURES = [
    ('cassini_iss.vic', (1, 16, 16), False, None),
    ('voyager_iss.vic', (1, 16, 16), False, None),
    ('galileo_ssi_a.vic', (1, 16, 16), False, None),
    ('galileo_ssi_b.vic', (1, 16, 16), False, None),
    ('hst_wfc3.fits', (16, 16), True, None),
    ('nh_mvic.fits', (16, 16), True, None),
    pytest.param(
        'hst_acs.fits', (16, 16), True, None,
        marks=pytest.mark.xfail(
            reason='hst_acs instrument module is WIP and raises in detect_in_fits',
            strict=False,
        ),
    ),
    pytest.param(
        'hst_wfpc2.fits', (16, 16), True, None,
        marks=pytest.mark.xfail(
            reason='hst_wfpc2 instrument module is WIP and raises in detect_in_fits',
            strict=False,
        ),
    ),
]


@pytest.mark.parametrize(('fixture', 'shape', 'upward', 'tint'), INSTRUMENT_FIXTURES)
def test_instrument_detection(
    fixture: str,
    shape: tuple[int, ...],
    upward: bool,
    tint: tuple[int, int, int] | None,
    fixtures_dir: Path,
) -> None:
    data = read_image_array(str(fixtures_dir / fixture))
    assert data.array.shape == shape
    assert data.default_upward is upward
    assert data.default_tint == tint


@pytest.mark.parametrize('fixture', [
    'malformed_pickle.bin',
    'malformed_numpy.bin',
    'corrupt_vicar.vic',
    'corrupt_fits.fits',
])
def test_malformed_falls_through_cascade(fixture: str, fixtures_dir: Path) -> None:
    with pytest.raises(OSError, match=r'unrecognized file format'):
        read_image_array(str(fixtures_dir / fixture))
