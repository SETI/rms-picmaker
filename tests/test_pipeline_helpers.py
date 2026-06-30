"""Direct unit tests for module-private pipeline and instrument helpers.

The pipeline's private helper :func:`!_process_one_image` and the HST
mosaic-assembly helpers (:func:`!_wfpc2_mosaic`, :func:`!_acs_panel_mosaic`,
:func:`picmaker.instruments.hst.apply_mosaic`) are exercised in isolation so the
existing end-to-end coverage in :file:`test_pipeline.py` /
:file:`test_pipeline_branches.py` is not the only safety net.
"""

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from picmaker.instruments.hst import (
    _acs_panel_mosaic,
    _wfpc2_mosaic,
    apply_mosaic,
)
from picmaker.options import PDS3_METHODS, PicmakerOptions
from picmaker.pipeline import _process_one_image

# ---------------------------------------------------------------------------
# PicmakerOptions.validate — pds3_method
# ---------------------------------------------------------------------------


def test_pds3_methods_constant_is_canonical_set() -> None:
    """The exported tuple lists every supported value once, in CLI order."""
    assert PDS3_METHODS == ('strict', 'loose', 'compound', 'fast')


@pytest.mark.parametrize('method', list(PDS3_METHODS))
def test_picmaker_options_accepts_each_pds3_method(method: str) -> None:
    """Every documented value is accepted by ``PicmakerOptions.validate``."""
    PicmakerOptions(pds3_method=method).validate()


def test_picmaker_options_rejects_unknown_pds3_method() -> None:
    """An unknown ``pds3_method`` value raises with a message that
    names the offending value and the accepted set."""
    with pytest.raises(ValueError, match=r"invalid pds3_method 'turbo'"):
        PicmakerOptions(pds3_method='turbo').validate()



# ---------------------------------------------------------------------------
# _wfpc2_mosaic
# ---------------------------------------------------------------------------


def _make_quad_bands() -> list[np.ndarray]:
    """Four 4x4 RGB arrays with distinct band-channel signatures (fills
    1.0, 2.0, 3.0, 4.0 in band-index order)."""
    return [
        np.full((4, 4, 3), float(b + 1)) for b in range(4)
    ]


# Slice keys for each quadrant of an 8x8 mosaic built from 4x4 bands.
_WFPC2_QUADRANTS = {
    'PC1': (slice(None, 4), slice(4, None)),   # top-right
    'WF2': (slice(None, 4), slice(None, 4)),   # top-left
    'WF3': (slice(4, None), slice(None, 4)),   # bottom-left
    'WF4': (slice(4, None), slice(4, None)),   # bottom-right
}


@pytest.mark.parametrize(
    ('imagefile', 'expected_fills'),
    [
        # A single-string imagefile triggers the b-indexed quadrant
        # placement with np.rot90(arrays_rgb[b], b). A rotation by an
        # integer multiple of 90° leaves a constant-fill array
        # unchanged, so each quadrant still shows its source band's
        # fill value.
        (
            'single.fits',
            {'PC1': 1.0, 'WF2': 2.0, 'WF3': 3.0, 'WF4': 4.0},
        ),
        # Per-detector filenames assign each band to its quadrant by
        # name regardless of band order; the PC1/WF2/WF3/WF4 token in
        # the filename wins.
        (
            ['x_WF3_y.fits', 'x_WF2_y.fits', 'x_PC1_y.fits', 'x_WF4_y.fits'],
            {'PC1': 3.0, 'WF2': 2.0, 'WF3': 1.0, 'WF4': 4.0},
        ),
        # A per-detector path that matches no PC1/WFn token falls back
        # to the b-indexed quadrant with np.rot90(..., b) — same final
        # placement as the single-string case.
        (
            ['unknown_a.fits'] * 4,
            {'PC1': 1.0, 'WF2': 2.0, 'WF3': 3.0, 'WF4': 4.0},
        ),
    ],
    ids=['string-imagefile', 'per-detector-filenames', 'unknown-filenames'],
)
def test_wfpc2_mosaic_quadrant_placement(
    imagefile: Any,
    expected_fills: dict[str, float],
) -> None:
    """The WFPC2 mosaic is 8x8 with each quadrant filled per
    ``imagefile``'s dispatch rule."""
    bands = _make_quad_bands()
    out = _wfpc2_mosaic(bands, imagefile=imagefile)

    assert out.shape == (8, 8, 3)
    for detector, expected_fill in expected_fills.items():
        row_slice, col_slice = _WFPC2_QUADRANTS[detector]
        assert np.allclose(out[row_slice, col_slice], expected_fill)


# ---------------------------------------------------------------------------
# _acs_panel_mosaic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('imagefile', 'top_fill', 'bottom_fill'),
    [
        # Single-string imagefile uses the legacy `1 - b` indexing:
        # band 1 lands on top, band 0 on bottom.
        ('single.fits', 2.0, 1.0),
        # Per-detector filenames place WFC1 on top and WFC2 below
        # regardless of band order — here band 1 (fill 2.0) carries the
        # WFC1 token, so it goes on top.
        (['data_WFC2_x.fits', 'data_WFC1_x.fits'], 2.0, 1.0),
    ],
    ids=['string-imagefile', 'per-detector-filenames'],
)
def test_acs_panel_mosaic_panel_placement(
    imagefile: Any,
    top_fill: float,
    bottom_fill: float,
) -> None:
    """The ACS panel mosaic is 8x4 with WFC1 (or band 1 in the
    fallback) on top and WFC2 (or band 0) on the bottom."""
    bands = [
        np.full((4, 4, 3), 1.0),  # band 0
        np.full((4, 4, 3), 2.0),  # band 1
    ]
    out = _acs_panel_mosaic(bands, imagefile=imagefile)

    assert out.shape == (8, 4, 3)
    assert np.allclose(out[:4], top_fill)
    assert np.allclose(out[4:], bottom_fill)


# ---------------------------------------------------------------------------
# apply_mosaic (HST mosaic hook)
# ---------------------------------------------------------------------------


def _hst_options(**overrides: object) -> PicmakerOptions:
    """Build a minimal PicmakerOptions suitable for HST mosaic tests."""
    base: dict[str, object] = {
        'replace': 'all', 'mosaic': True, 'bands': None,
        'samples': None, 'lines': None, 'valid': None, 'crop': None,
        'zebra': False, 'limits': (0.0, 3.0),
        'percentiles': None, 'trim': 0, 'trim_zeros': False, 'footprint': 0,
        'histogram': False, 'colormap': None,
        'below_color': None, 'above_color': None, 'invalid_color': 'black',
    }
    base.update(overrides)
    return PicmakerOptions(**base)  # type: ignore[arg-type]  # kwargs widen to typed fields


@pytest.mark.parametrize(
    ('colormap', 'expected_channels'),
    [
        # A real RGB colormap routes apply_colormap into the 3-channel
        # branch; the mosaic carries (lines, samples, 3).
        ('red-blue', 3),
        # colormap=None routes apply_colormap into the grayscale branch,
        # which produces a single channel.
        (None, 1),
    ],
    ids=['rgb-colormap', 'grayscale'],
)
def test_apply_mosaic_wfpc2_produces_2x2_mosaic(
    colormap: Any,
    expected_channels: int,
) -> None:
    """``WFPC2`` mode assembles four detectors into a 2x2 mosaic of
    twice the per-detector size. The per-band channel count follows
    the colormap: 3 for a named RGB colormap, 1 for ``colormap=None``
    (the grayscale branch of :func:`~picmaker.enhance.apply_colormap`).
    """
    array3d = np.tile(
        np.linspace(0.0, 3.0, 16, dtype=np.float32).reshape(1, 4, 4),
        (4, 1, 1),
    )
    image_info = ('HST', 'WFPC2', 'F555W')

    mosaic = apply_mosaic(
        array3d, image_info, _hst_options(),
        default_is_up=False, colormap=colormap, imagefile='single.fits',
    )

    assert mosaic is not None
    assert mosaic.shape == (8, 8, expected_channels)


def test_apply_mosaic_acs_two_panel() -> None:
    """``ACS/WFC`` mode with two bands produces a stacked panel mosaic
    (height doubles, width unchanged)."""
    array3d = np.tile(
        np.linspace(0.0, 3.0, 16, dtype=np.float32).reshape(1, 4, 4),
        (2, 1, 1),
    )
    image_info = ('HST', 'ACS/WFC', 'F606W')

    mosaic = apply_mosaic(
        array3d, image_info, _hst_options(),
        default_is_up=False, colormap='red-blue', imagefile='single.fits',
    )

    assert mosaic is not None
    assert mosaic.shape == (8, 4, 3)


def test_apply_mosaic_acs_single_band_no_mosaic() -> None:
    """A single-band ACS/WFC input returns the per-band RGB unchanged
    (no stacking, original per-band spatial shape preserved)."""
    array3d = np.linspace(0.0, 3.0, 16, dtype=np.float32).reshape(1, 4, 4)
    image_info = ('HST', 'ACS/WFC', 'F606W')

    mosaic = apply_mosaic(
        array3d, image_info, _hst_options(),
        default_is_up=False, colormap='red-blue', imagefile='single.fits',
    )

    assert mosaic is not None
    assert mosaic.shape == (4, 4, 3)


def test_apply_mosaic_flips_when_default_is_up() -> None:
    """``default_is_up=True`` reverses lines before mosaicking; the
    assembled mosaic differs from the ``default_is_up=False`` result."""
    array3d = np.arange(16, dtype=np.float32).reshape(1, 4, 4)
    array3d = np.tile(array3d, (4, 1, 1))
    image_info = ('HST', 'WFPC2', 'F555W')

    mosaic_no_flip = apply_mosaic(
        array3d, image_info, _hst_options(),
        default_is_up=False, colormap=None, imagefile='single.fits',
    )
    mosaic_flipped = apply_mosaic(
        array3d, image_info, _hst_options(),
        default_is_up=True, colormap=None, imagefile='single.fits',
    )

    assert mosaic_no_flip is not None
    assert mosaic_flipped is not None
    assert not np.array_equal(mosaic_no_flip, mosaic_flipped)


def test_apply_mosaic_returns_none_for_non_mosaic_instrument() -> None:
    """``apply_mosaic`` returns ``None`` for HST instruments other than
    ACS/WFC and WFPC2 (e.g. NICMOS), falling through to the standard
    single-band pipeline."""
    array3d = np.zeros((1, 4, 4), dtype=np.float32)
    image_info = ('HST', 'NICMOS/NIC1', 'F110W')
    result = apply_mosaic(array3d, image_info, _hst_options())
    assert result is None


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
        'gap_color': 'white', 'mosaic': False, 'valid': None, 'limits': None,
        'percentiles': None, 'trim': 0, 'trim_zeros': False, 'footprint': 0,
        'histogram': False, 'colormap': None, 'below_color': None,
        'above_color': None, 'invalid_color': 'black', 'gamma': 1.0,
        'tint': False, 'display_upward': False, 'display_downward': False,
        'rotate': 'none', 'filter_name': 'none', 'zebra': False,
    }
    base.update(overrides)
    return PicmakerOptions(**base)  # type: ignore[arg-type]  # kwargs widen to typed fields


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
