"""Cover the pipeline branches that the snapshot / smoke tests miss:
the frame/size mutex, extension defaulting, the 16-bit guard, ``--zebra``,
movie mode, the ``--versions`` reuse path, wrap/pad, the unreadable-file
error path, a detached PDS3 label, and the display-orientation overrides.

Options are built the CLI way: parse argv through ``get_parser()`` and run it
through ``validate_options`` so the dict has every key ``picmaker`` expects.
"""

import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from picmaker.options import get_parser
from picmaker.picmaker import picmaker


def _run(infiles: list[str], tmp_path: Path, *extra: str) -> None:
    """Build a complete options dict the CLI way and run the pipeline."""
    options = vars(get_parser().parse_args(
        [*infiles, '--directory', str(tmp_path), *extra]
    ))
    picmaker(**options)


def _render(arr: np.ndarray, tmp_path: Path, *extra: str, name: str = 'in') -> np.ndarray:
    """Render a numpy array through the pipeline to a lossless PNG and read the
    result back as an array, so pixel-level assertions are exact (no JPEG loss)."""
    src = tmp_path / f'{name}.npy'
    np.save(src, arr)
    _run([str(src)], tmp_path, '--extension', 'png', *extra)
    with Image.open(tmp_path / f'{name}.png') as im:
        return np.asarray(im)


# ---------------------------------------------------------------------------
# Mutex / value-validity checks inside validate_options
# ---------------------------------------------------------------------------


def test_frame_size_incompatible(fixtures_dir: Path, tmp_path: Path) -> None:
    """``--frame`` plus ``--size`` is rejected before any I/O."""
    with pytest.raises(ValueError, match='frame and --size'):
        _run(
            [str(fixtures_dir / 'cassini_iss.vic')], tmp_path,
            '--frame', '50', '50', '--size', '20', '20',
        )


def test_twobytes_requires_tiff_extension(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``--16`` with an explicit non-TIFF extension is rejected; only tiffs may
    be written in 16-bit mode. (``--16`` alone defaults the extension to tiff.)
    """
    with pytest.raises(ValueError, match='Only tiffs can be written'):
        _run([str(fixtures_dir / 'cassini_iss.vic')], tmp_path,
             '--16', '--extension', 'jpg')


# ---------------------------------------------------------------------------
# extension default selection
# ---------------------------------------------------------------------------


def test_extension_default_jpg(fixtures_dir: Path, tmp_path: Path) -> None:
    """No ``--extension`` defaults to ``'jpg'`` when not in 16-bit mode."""
    _run([str(fixtures_dir / 'cassini_iss.vic')], tmp_path)
    assert (tmp_path / 'cassini_iss.jpg').exists()


# ---------------------------------------------------------------------------
# zebra fill
# ---------------------------------------------------------------------------


def test_zebra_fills_edge_zero_stripe(tmp_path: Path) -> None:
    """``--zebra`` interpolates leading/trailing zero stripes from the neighboring
    rows: the zeroed edge pixels become bright, unlike the un-zebra'd render.
    """
    # All 100 except row 4's first and last pixels, which are a zero "zebra" stripe.
    # Rows 3 and 5 are nonzero at those columns, so fill_zebra_stripes averages them.
    arr = np.full((8, 8), 100, dtype='uint8')
    arr[4, 0] = 0
    arr[4, 7] = 0
    # Fixed limits so both renders share one stretch and pixels compare directly.
    plain = _render(arr, tmp_path, '--limits', '0', '200', name='plain')
    zebra = _render(arr, tmp_path, '--limits', '0', '200', '--zebra', name='zebra')

    assert not np.array_equal(plain, zebra)                 # zebra changed the pixels
    # The zero stripe is dark without zebra and filled (bright) with it.
    assert plain[4, 0] == plain[4, 7] == 0
    assert zebra[4, 0] > 100
    assert zebra[4, 7] > 100
    # Interior pixels (never part of a stripe) are untouched.
    assert np.array_equal(plain[:, 3], zebra[:, 3])


# ---------------------------------------------------------------------------
# unreadable-file error path
# ---------------------------------------------------------------------------


def test_unreadable_file_raises(tmp_path: Path) -> None:
    """An unrecognized input file raises ``OSError``."""
    bogus = tmp_path / 'bogus.bin'
    bogus.write_bytes(b'not-an-image')
    with pytest.raises(OSError, match='unrecognized file format'):
        _run([str(bogus)], tmp_path)


# ---------------------------------------------------------------------------
# output-directory creation
# ---------------------------------------------------------------------------


def test_creates_output_directory(fixtures_dir: Path, tmp_path: Path) -> None:
    """``picmaker`` creates the output directory tree if it is missing."""
    out_dir = tmp_path / 'fresh' / 'subdir'
    _run([str(fixtures_dir / 'cassini_iss.vic')], out_dir)
    assert out_dir.is_dir()
    assert (out_dir / 'cassini_iss.jpg').exists()


# ---------------------------------------------------------------------------
# movie mode
# ---------------------------------------------------------------------------


def test_movie_mode_writes_every_frame(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """Movie mode scans all frames for a shared stretch, then writes each."""
    src1 = tmp_path / 'frame_001.vic'
    src2 = tmp_path / 'frame_002.vic'
    shutil.copy(fixtures_dir / 'cassini_iss.vic', src1)
    shutil.copy(fixtures_dir / 'cassini_iss.vic', src2)

    out_dir = tmp_path / 'out'
    _run([str(src1), str(src2)], out_dir, '--movie')
    assert (out_dir / 'frame_001.jpg').exists()
    assert (out_dir / 'frame_002.jpg').exists()


def test_movie_mode_unreadable_raises(tmp_path: Path) -> None:
    """Movie mode propagates ``OSError`` when a frame cannot be read."""
    bogus = tmp_path / 'b.bin'
    bogus.write_bytes(b'garbage')
    with pytest.raises(OSError, match='unrecognized file format'):
        _run([str(bogus)], tmp_path / 'out', '--movie')


# ---------------------------------------------------------------------------
# --versions reuse path
# ---------------------------------------------------------------------------


def test_versions_writes_each_variant(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """A ``--versions`` file layers per-line overrides onto the base options,
    reusing the single read of the input for every variant it writes.
    """
    versions = tmp_path / 'versions.txt'
    versions.write_text('--suffix _v1\n--suffix _v2 --gamma 2.0\n')
    _run(
        [str(fixtures_dir / 'cassini_iss.vic')], tmp_path,
        '--versions', str(versions),
    )
    assert (tmp_path / 'cassini_iss_v1.jpg').exists()
    assert (tmp_path / 'cassini_iss_v2.jpg').exists()


# ---------------------------------------------------------------------------
# wrap / pad branches
# ---------------------------------------------------------------------------


def test_wrap_reflows_elongated_image(tmp_path: Path) -> None:
    """``--wrap`` reflows a very elongated image (under ``--frame``) into stacked
    sections: the wrapped render is taller and narrower than the frame-fit strip.
    """
    # A wide 8x64 strip; --frame 40 40 fits it as a short, wide image.
    arr = np.tile((np.arange(64, dtype='uint8') * 3)[None, :], (8, 1))
    plain = _render(arr, tmp_path, '--frame', '40', '40', name='plain')
    wrapped = _render(arr, tmp_path, '--frame', '40', '40', '--wrap', name='wrapped')

    # np arrays are (H, W): wrap trades width for height (stacks the strip).
    assert wrapped.shape[0] > plain.shape[0]                # taller
    assert wrapped.shape[1] < plain.shape[1]                # narrower


def test_pad_fills_border_with_pad_color(tmp_path: Path) -> None:
    """``--frame`` + ``--pad`` centers the scaled image and fills the surrounding
    frame with a uniform pad color, rather than stretching to fill.
    """
    # A vertical gradient so image columns vary (distinguishable from flat padding).
    arr = np.tile((np.arange(8, dtype='uint8') * 30)[:, None], (1, 8))
    # 8x8 into a 32x16 frame -> scales to 16x16, then pads width to 32 (8px each side).
    out = _render(arr, tmp_path, '--frame', '32', '16', '--pad', name='pad')

    assert out.shape[:2] == (16, 32)                        # (H, W) == the frame
    assert np.ptp(out[:, 0]) == 0                           # left pad column uniform
    assert np.ptp(out[:, -1]) == 0                          # right pad column uniform
    assert out[0, 0] == out[0, -1]                          # same pad color both sides
    assert np.ptp(out[:, 16]) > 0                           # center holds the gradient
    assert out[0, 0] != out[8, 16]                          # pad color != image content


# ---------------------------------------------------------------------------
# PDS3 detached-label redirect
# ---------------------------------------------------------------------------


_LBL_TEMPLATE = """PDS_VERSION_ID = PDS3
INSTRUMENT_HOST_ID = 'CASSINI'
INSTRUMENT_ID = 'ISS'
DETECTOR_ID = 'NAC'
FILTER_NAME = ('CL1', 'GRN')
^IMAGE = "{image_filename}"
OBJECT = IMAGE
  LINES = 16
  LINE_SAMPLES = 16
  SAMPLE_BITS = 8
  SAMPLE_TYPE = UNSIGNED_INTEGER
END_OBJECT = IMAGE
END
"""


def test_pds3_label_redirects_to_vicar(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """A ``.LBL`` whose ``^IMAGE`` points at a VICAR file is parsed for its
    label metadata while the VICAR reader handles the actual pixels.
    """
    shutil.copy(fixtures_dir / 'cassini_iss.vic', tmp_path / 'cassini_iss.vic')
    lbl = tmp_path / 'sample.LBL'
    lbl.write_text(_LBL_TEMPLATE.format(image_filename='cassini_iss.vic'))
    out_dir = tmp_path / 'out'
    _run([str(lbl)], out_dir)
    assert (out_dir / 'sample.jpg').exists()


# ---------------------------------------------------------------------------
# empty input
# ---------------------------------------------------------------------------


def test_no_input_files_raises(tmp_path: Path) -> None:
    """When no input files resolve, ``picmaker`` raises ``ValueError``."""
    with pytest.raises(ValueError, match='No input files identified'):
        _run([], tmp_path)


# ---------------------------------------------------------------------------
# display orientation overrides
# ---------------------------------------------------------------------------


def test_up_and_down_are_vertical_mirrors(tmp_path: Path) -> None:
    """``--up`` and ``--down`` render the same input as vertical mirror images,
    with the bright band landing at opposite edges."""
    # Vertically asymmetric: a bright band across the top three rows only.
    arr = np.zeros((8, 8), dtype='uint8')
    arr[:3] = 200
    up = _render(arr, tmp_path, '--up', name='up')
    down = _render(arr, tmp_path, '--down', name='down')

    assert not np.array_equal(up, down)                     # orientation actually changed
    assert np.array_equal(up, np.flipud(down))              # vertical mirrors
    # --up makes lines increase upward, so the bright band moves to the bottom.
    assert up[-1].mean() > up[0].mean()
    assert down[0].mean() > down[-1].mean()


def test_rotate_actually_rotates(tmp_path: Path) -> None:
    """``--rotate`` rearranges pixels the way numpy's rot90 does. A no-op rotate
    (the old ``rotate``/``rotation`` wiring bug) would fail this outright."""
    # A distinct value per quadrant so every rotation is detectable.
    arr = np.zeros((8, 8), dtype='uint8')
    arr[:4, :4], arr[:4, 4:] = 60, 120
    arr[4:, :4], arr[4:, 4:] = 180, 240

    none = _render(arr, tmp_path, '--rotate', 'none', name='none')
    r90 = _render(arr, tmp_path, '--rotate', 'rot90', name='r90')
    r180 = _render(arr, tmp_path, '--rotate', 'rot180', name='r180')

    assert not np.array_equal(r90, none)                    # not a no-op
    assert np.array_equal(r90, np.rot90(none, 1))
    assert np.array_equal(r180, np.rot90(none, 2))


def test_tint_with_no_image_info_is_a_noop(tmp_path: Path) -> None:
    """``--tint`` on an image with no instrument ``default_tint`` leaves the render
    byte-for-byte identical to the un-tinted default (the override is a no-op)."""
    # A plain numpy array carries no instrument metadata for the tint to use.
    arr = (np.arange(64).reshape(8, 8) * 4).astype('uint8')
    plain = _render(arr, tmp_path, name='plain')
    tinted = _render(arr, tmp_path, '--tint', name='tinted')
    assert np.array_equal(plain, tinted)
