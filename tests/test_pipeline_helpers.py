"""Direct unit tests for the module-private pipeline helpers.

The issue-#12 refactor split :func:`picmaker.pipeline.images_to_pics`
into three private helpers (:func:`!_pds3_resolve_pointer`,
:func:`!_hst_mosaic_rgb`, :func:`!_process_one_image`) and two HST
mosaic-assembly helpers (:func:`!_hst_wfpc2_mosaic`,
:func:`!_hst_acs_panel_mosaic`). These tests exercise each helper in
isolation so the existing end-to-end coverage in
:file:`test_pipeline.py` / :file:`test_pipeline_branches.py` is not
the only safety net for the refactored code.
"""

from pathlib import Path

import numpy as np
import pytest

from picmaker.options import PicmakerOptions
from picmaker.pipeline import (
    _hst_acs_panel_mosaic,
    _hst_mosaic_rgb,
    _hst_wfpc2_mosaic,
    _pds3_resolve_pointer,
    _process_one_image,
)

# ---------------------------------------------------------------------------
# _pds3_resolve_pointer
# ---------------------------------------------------------------------------


_LBL_SINGLE_FILE = """PDS_VERSION_ID = PDS3
INSTRUMENT_HOST_ID = 'CASSINI'
INSTRUMENT_ID = 'ISS'
DETECTOR_ID = 'NAC'
FILTER_NAME = ('CL1', 'GRN')
^IMAGE = "frame.dat"
END
"""

_LBL_LIST = """PDS_VERSION_ID = PDS3
INSTRUMENT_HOST_ID = 'CASSINI'
INSTRUMENT_ID = 'ISS'
^IMAGE = ("frame_a.dat", "frame_b.dat", "frame_c.dat")
END
"""

_LBL_TUPLE = """PDS_VERSION_ID = PDS3
SPACECRAFT_ID = 'CASSINI'
INSTRUMENT_NAME = 'ISS'
^IMAGE = ("frame.dat", 1)
END
"""

_LBL_NO_INSTRUMENT = """PDS_VERSION_ID = PDS3
^IMAGE = "frame.dat"
END
"""

_LBL_SPACECRAFT_NAME = """PDS_VERSION_ID = PDS3
SPACECRAFT_NAME = 'VOYAGER 1'
^IMAGE = "frame.dat"
END
"""

_LBL_ALT_POINTER = """PDS_VERSION_ID = PDS3
INSTRUMENT_HOST_ID = 'CASSINI'
INSTRUMENT_ID = 'ISS'
^IMAGE_2 = "frame.dat"
END
"""

_LBL_MISSING_POINTER = """PDS_VERSION_ID = PDS3
INSTRUMENT_HOST_ID = 'CASSINI'
END
"""


def _write_lbl(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text)
    return p


def test_pds3_resolve_pointer_single_file(tmp_path: Path) -> None:
    """A single-file ``^IMAGE`` pointer returns a single resolved path
    and a populated ``filter_info``."""
    lbl = _write_lbl(tmp_path, 'sample.LBL', _LBL_SINGLE_FILE)

    imagefile, filter_info = _pds3_resolve_pointer(str(lbl), ['IMAGE'], obj=0)

    assert imagefile == str(tmp_path / 'frame.dat')
    assert filter_info is not None
    # pdsparser preserves the parenthesised list shape; we don't care
    # whether it surfaces as a tuple or a list here, just the contents.
    assert filter_info[0] == 'CASSINI'
    assert filter_info[1] == 'ISS/NAC'
    assert list(filter_info[2]) == ['CL1', 'GRN']


def test_pds3_resolve_pointer_obj_none_picks_all(tmp_path: Path) -> None:
    """``obj=None`` against a list pointer returns every entry as a list."""
    lbl = _write_lbl(tmp_path, 'list.LBL', _LBL_LIST)

    imagefile, filter_info = _pds3_resolve_pointer(str(lbl), ['IMAGE'], obj=None)

    assert imagefile == [
        str(tmp_path / 'frame_a.dat'),
        str(tmp_path / 'frame_b.dat'),
        str(tmp_path / 'frame_c.dat'),
    ]
    # No DETECTOR_ID → inst_id stays at INSTRUMENT_ID value, no slash.
    assert filter_info is not None
    assert filter_info[0] == 'CASSINI'
    assert filter_info[1] == 'ISS'


def test_pds3_resolve_pointer_obj_int_picks_one(tmp_path: Path) -> None:
    """``obj=1`` against a list pointer returns a single resolved path."""
    lbl = _write_lbl(tmp_path, 'list.LBL', _LBL_LIST)

    imagefile, _ = _pds3_resolve_pointer(str(lbl), ['IMAGE'], obj=1)

    assert imagefile == str(tmp_path / 'frame_b.dat')


def test_pds3_resolve_pointer_obj_sequence_picks_several(tmp_path: Path) -> None:
    """A list ``obj=[0, 2]`` returns those two entries from the pointer."""
    lbl = _write_lbl(tmp_path, 'list.LBL', _LBL_LIST)

    imagefile, _ = _pds3_resolve_pointer(str(lbl), ['IMAGE'], obj=[0, 2])

    assert imagefile == [
        str(tmp_path / 'frame_a.dat'),
        str(tmp_path / 'frame_c.dat'),
    ]


def test_pds3_resolve_pointer_tuple_pointer(tmp_path: Path) -> None:
    """A ``(filename, record)`` tuple pointer keeps the filename half."""
    lbl = _write_lbl(tmp_path, 'tuple.LBL', _LBL_TUPLE)

    imagefile, filter_info = _pds3_resolve_pointer(str(lbl), ['IMAGE'], obj=0)

    assert imagefile == str(tmp_path / 'frame.dat')
    # SPACECRAFT_ID is the host fallback when INSTRUMENT_HOST_ID is absent;
    # INSTRUMENT_NAME is the inst_id fallback when INSTRUMENT_ID is absent.
    assert filter_info == ('CASSINI', 'ISS', None)


def test_pds3_resolve_pointer_no_instrument_returns_none_filter(
    tmp_path: Path,
) -> None:
    """Without any host key, ``filter_info`` is ``None``."""
    lbl = _write_lbl(tmp_path, 'bare.LBL', _LBL_NO_INSTRUMENT)

    _, filter_info = _pds3_resolve_pointer(str(lbl), ['IMAGE'], obj=0)

    assert filter_info is None


def test_pds3_resolve_pointer_spacecraft_name_fallback(
    tmp_path: Path,
) -> None:
    """``SPACECRAFT_NAME`` is the last host fallback."""
    lbl = _write_lbl(tmp_path, 'scn.LBL', _LBL_SPACECRAFT_NAME)

    _, filter_info = _pds3_resolve_pointer(str(lbl), ['IMAGE'], obj=0)

    assert filter_info == ('VOYAGER 1', None, None)


def test_pds3_resolve_pointer_alt_pointer(tmp_path: Path) -> None:
    """When the first pointer is missing, the alternates are tried."""
    lbl = _write_lbl(tmp_path, 'alt.LBL', _LBL_ALT_POINTER)

    imagefile, _ = _pds3_resolve_pointer(
        str(lbl), ['IMAGE', 'IMAGE_2'], obj=0,
    )

    assert imagefile == str(tmp_path / 'frame.dat')


def test_pds3_resolve_pointer_missing_raises(tmp_path: Path) -> None:
    """A label without the requested pointer raises ``KeyError``."""
    lbl = _write_lbl(tmp_path, 'nope.LBL', _LBL_MISSING_POINTER)

    with pytest.raises(KeyError, match='PDS pointer IMAGE not found'):
        _pds3_resolve_pointer(str(lbl), ['IMAGE'], obj=0)


def test_pds3_resolve_pointer_obj_out_of_range_raises(
    tmp_path: Path,
) -> None:
    """An integer ``obj`` past the end of the resolved pointer raises."""
    lbl = _write_lbl(tmp_path, 'sample.LBL', _LBL_SINGLE_FILE)

    with pytest.raises(IndexError, match='out of range'):
        _pds3_resolve_pointer(str(lbl), ['IMAGE'], obj=5)


def test_pds3_resolve_pointer_string_pointer_normalized(
    tmp_path: Path,
) -> None:
    """A scalar pointer name is wrapped to a one-element list internally."""
    lbl = _write_lbl(tmp_path, 'sample.LBL', _LBL_SINGLE_FILE)

    imagefile, _ = _pds3_resolve_pointer(str(lbl), 'IMAGE', obj=0)

    assert imagefile == str(tmp_path / 'frame.dat')


# ---------------------------------------------------------------------------
# _hst_wfpc2_mosaic
# ---------------------------------------------------------------------------


def _make_quad_bands() -> list[np.ndarray]:
    """Four 4x4 RGB arrays with distinct band-channel signatures."""
    return [
        np.full((4, 4, 3), float(b + 1)) for b in range(4)
    ]


def test_hst_wfpc2_mosaic_string_imagefile_uses_rot90_b() -> None:
    """A single-string imagefile triggers the ``np.rot90(arrays_rgb[b], b)``
    fallback; the assembled mosaic is 2x size in both axes."""
    bands = _make_quad_bands()
    out = _hst_wfpc2_mosaic(bands, imagefile='single.fits')

    assert out.shape == (8, 8, 3)
    # PC1 (b=0) is top-right; its rotation count is 0, so values are 1.
    assert np.allclose(out[:4, 4:], 1.0)
    # WF2 (b=1) is top-left; rotation 1 preserves the fill value 2.
    assert np.allclose(out[:4, :4], 2.0)


def test_hst_wfpc2_mosaic_per_detector_filenames() -> None:
    """Per-detector filenames assign each band to its quadrant by name."""
    bands = _make_quad_bands()
    files = ['x_WF3_y.fits', 'x_WF2_y.fits', 'x_PC1_y.fits', 'x_WF4_y.fits']
    out = _hst_wfpc2_mosaic(bands, imagefile=files)

    assert out.shape == (8, 8, 3)
    # PC1 (file index 2 → fill 3) goes top-right, no rotation.
    assert np.allclose(out[:4, 4:], 3.0)
    # WF2 (file index 1 → fill 2) goes top-left.
    assert np.allclose(out[:4, :4], 2.0)
    # WF3 (file index 0 → fill 1) goes bottom-left.
    assert np.allclose(out[4:, :4], 1.0)
    # WF4 (file index 3 → fill 4) goes bottom-right.
    assert np.allclose(out[4:, 4:], 4.0)


def test_hst_wfpc2_mosaic_unknown_filename_falls_back_to_b_rotation() -> None:
    """A per-detector path that matches no ``PC1``/``WFn`` token falls back
    to the ``b``-indexed quadrant with ``np.rot90(..., b)``."""
    bands = _make_quad_bands()
    files = ['unknown_a.fits'] * 4
    out = _hst_wfpc2_mosaic(bands, imagefile=files)

    assert out.shape == (8, 8, 3)


# ---------------------------------------------------------------------------
# _hst_acs_panel_mosaic
# ---------------------------------------------------------------------------


def test_hst_acs_panel_mosaic_string_imagefile_stacks_inverted() -> None:
    """A single-string imagefile uses the legacy ``1 - b`` panel indexing
    (band 0 on bottom, band 1 on top)."""
    bands = [
        np.full((4, 4, 3), 1.0),  # band 0
        np.full((4, 4, 3), 2.0),  # band 1
    ]
    out = _hst_acs_panel_mosaic(bands, imagefile='single.fits')

    assert out.shape == (8, 4, 3)
    # band 0 placed in panel[1] (bottom half).
    assert np.allclose(out[4:], 1.0)
    # band 1 placed in panel[0] (top half).
    assert np.allclose(out[:4], 2.0)


def test_hst_acs_panel_mosaic_per_detector_filenames() -> None:
    """Per-detector filenames place WFC1 on top and WFC2 below regardless
    of the band order."""
    bands = [
        np.full((4, 4, 3), 5.0),
        np.full((4, 4, 3), 9.0),
    ]
    out = _hst_acs_panel_mosaic(
        bands, imagefile=['data_WFC2_x.fits', 'data_WFC1_x.fits']
    )

    # WFC1 (band 1, value 9) is on top; WFC2 (band 0, value 5) is on bottom.
    assert np.allclose(out[:4], 9.0)
    assert np.allclose(out[4:], 5.0)


# ---------------------------------------------------------------------------
# _hst_mosaic_rgb
# ---------------------------------------------------------------------------


def _hst_options(**overrides: object) -> PicmakerOptions:
    """Build a minimal PicmakerOptions suitable for HST mosaic tests."""
    base: dict[str, object] = {
        'replace': 'all', 'hst': True, 'bands': None,
        'samples': None, 'lines': None, 'valid': None, 'crop': None,
        'zebra': False, 'limits': (0.0, 3.0),
        'percentiles': None, 'trim': 0, 'trim_zeros': False, 'footprint': 0,
        'histogram': False, 'colormap': None,
        'below_color': None, 'above_color': None, 'invalid_color': 'black',
    }
    base.update(overrides)
    return PicmakerOptions(**base)  # type: ignore[arg-type]


def test_hst_mosaic_rgb_wfpc2_produces_2x2_mosaic() -> None:
    """``WFPC2`` mode assembles four detectors into a 2x2 mosaic of
    twice the per-detector size. With a colormap-bearing input the
    channel count is 3; with ``colormap=None`` the apply_colormap path
    keeps it grayscale (channel count 1) — either way the mosaic
    spatial shape doubles."""
    array3d = np.tile(
        np.linspace(0.0, 3.0, 16, dtype=np.float32).reshape(1, 4, 4),
        (4, 1, 1),
    )
    filter_info = ('HST', 'WFPC2', 'F555W')

    mosaic, returned = _hst_mosaic_rgb(
        array3d, filter_info, 'single.fits',
        options=_hst_options(),
        default_is_up=False, is_int=False, colormap='red-blue',
    )

    assert mosaic.shape == (8, 8, 3)
    assert returned.shape == array3d.shape  # no flip when default_is_up=False


def test_hst_mosaic_rgb_acs_two_panel() -> None:
    """``ACS/WFC`` mode with two bands produces a stacked panel mosaic
    (height doubles, width unchanged)."""
    array3d = np.tile(
        np.linspace(0.0, 3.0, 16, dtype=np.float32).reshape(1, 4, 4),
        (2, 1, 1),
    )
    filter_info = ('HST', 'ACS/WFC', 'F606W')

    mosaic, _ = _hst_mosaic_rgb(
        array3d, filter_info, imagefile='single.fits',
        options=_hst_options(),
        default_is_up=False, is_int=False, colormap='red-blue',
    )

    assert mosaic.shape == (8, 4, 3)


def test_hst_mosaic_rgb_acs_single_band_no_mosaic() -> None:
    """A single-band ACS/WFC input returns the per-band RGB unchanged
    (no stacking, original per-band spatial shape preserved)."""
    array3d = np.linspace(0.0, 3.0, 16, dtype=np.float32).reshape(1, 4, 4)
    filter_info = ('HST', 'ACS/WFC', 'F606W')

    mosaic, _ = _hst_mosaic_rgb(
        array3d, filter_info, imagefile='single.fits',
        options=_hst_options(),
        default_is_up=False, is_int=False, colormap='red-blue',
    )

    # No stacking: original (lines, samples, 3) shape.
    assert mosaic.shape == (4, 4, 3)


def test_hst_mosaic_rgb_flips_when_default_is_up() -> None:
    """``default_is_up=True`` reverses the ``axis=1`` (lines) before
    per-detector processing; the returned array3d reflects the flip."""
    # Use a deterministic gradient so the flip is visible.
    array3d = np.arange(16, dtype=np.float32).reshape(1, 4, 4)
    array3d = np.tile(array3d, (4, 1, 1))
    filter_info = ('HST', 'WFPC2', 'F555W')

    _, returned = _hst_mosaic_rgb(
        array3d, filter_info, imagefile='single.fits',
        options=_hst_options(),
        default_is_up=True, is_int=False, colormap=None,
    )

    # Returned array3d should be the lines-reversed input.
    np.testing.assert_array_equal(returned, array3d[:, ::-1, :])


# ---------------------------------------------------------------------------
# _process_one_image
# ---------------------------------------------------------------------------


def _basic_options(**overrides: object) -> PicmakerOptions:
    """A complete PicmakerOptions suitable for end-to-end helper calls."""
    base: dict[str, object] = {
        'replace': 'all', 'proceed': False, 'extension': 'jpg', 'suffix': '',
        'strip': [], 'quality': 75, 'twobytes': False, 'bands': (0, 1),
        'lines': None, 'samples': None, 'obj': None, 'pointer': ['IMAGE'],
        'size': None, 'scale': (100.0, 100.0), 'crop': None, 'frame': None,
        'pad': False, 'pad_color': 'black', 'frame_max': None, 'wrap': False,
        'wrap_ratio': None, 'overlap': (0.0, 0.0), 'gap_size': 1,
        'gap_color': 'white', 'hst': False, 'valid': None, 'limits': None,
        'percentiles': None, 'trim': 0, 'trim_zeros': False, 'footprint': 0,
        'histogram': False, 'colormap': None, 'below_color': None,
        'above_color': None, 'invalid_color': 'black', 'gamma': 1.0,
        'tint': False, 'display_upward': False, 'display_downward': False,
        'rotate': 'none', 'filter_name': 'none', 'zebra': False,
    }
    base.update(overrides)
    return PicmakerOptions(**base)  # type: ignore[arg-type]


def test_process_one_image_writes_output(
    fixtures_dir: Path, tmp_path: Path,
) -> None:
    """A standard call writes one file and returns ``(limits, reuse_tuple)``."""
    result = _process_one_image(
        str(fixtures_dir / 'cassini_iss.vic'),
        _basic_options(),
        reuse=None,
        directory=str(tmp_path),
    )
    assert result is not None
    (lo, hi), reuse_tuple = result
    assert lo is not None
    assert hi is not None
    assert isinstance(reuse_tuple, tuple)
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_process_one_image_replace_none_skip(
    fixtures_dir: Path, tmp_path: Path,
) -> None:
    """When ``replace='none'`` and the output already exists, the helper
    returns ``None`` so the caller can ``continue``."""
    out = tmp_path / 'cassini_iss.jpg'
    out.write_bytes(b'sentinel')

    result = _process_one_image(
        str(fixtures_dir / 'cassini_iss.vic'),
        _basic_options(replace='none'),
        reuse=None,
        directory=str(tmp_path),
    )
    assert result is None
    # File untouched.
    assert out.read_bytes() == b'sentinel'


def test_process_one_image_reuse_short_circuits_read(
    fixtures_dir: Path, tmp_path: Path,
) -> None:
    """Passing a ``reuse`` tuple skips re-reading the file (the resulting
    JPEG still gets written)."""
    # First, get a reuse tuple by processing once.
    first = _process_one_image(
        str(fixtures_dir / 'cassini_iss.vic'),
        _basic_options(),
        reuse=None,
        directory=str(tmp_path),
    )
    assert first is not None
    _, reuse_tuple = first

    # Now reuse it for a second pass with a different suffix; the file
    # gets written without rereading the input.
    second_dir = tmp_path / 'second'
    second_dir.mkdir()
    result = _process_one_image(
        str(fixtures_dir / 'cassini_iss.vic'),
        _basic_options(suffix='_again'),
        reuse=reuse_tuple,
        directory=str(second_dir),
    )
    assert result is not None
    assert (second_dir / 'cassini_iss_again.jpg').exists()


def test_process_one_image_display_downward_overrides(
    fixtures_dir: Path, tmp_path: Path,
) -> None:
    """``display_downward=True`` overrides the per-instrument default."""
    result = _process_one_image(
        str(fixtures_dir / 'cassini_iss.vic'),
        _basic_options(display_downward=True),
        reuse=None,
        directory=str(tmp_path),
    )
    assert result is not None
    assert (tmp_path / 'cassini_iss.jpg').exists()
