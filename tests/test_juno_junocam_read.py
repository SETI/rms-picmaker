"""Read, mosaic-assembly, and ``--tint`` checks for Juno JunoCam.

The bundled samples cover every filter combination the archive uses in more than
one form: ``A`` (METHANE/BLUE/GREEN/RED, the only combination that mixes the
neutral methane filter with colored ones), ``B`` (a lone BLUE framelet stack),
``T`` (BLUE/RED, and a 16-bit RDR rather than an 8-bit EDR), and ``P`` (a
band-sequential global map, block-averaged 8x to stay committable).

Each product is read both from its PDS3 label and, where the archive filename
survives, from the raw ``.IMG``, which takes the two detectors down separate
code paths: the label supplies FILTER_NAME and the array shape, while the raw
read infers both from the filename via ``_FILTER_NAMES`` and ``_SHAPES``. The
two must agree. The shrunk map is the exception -- its ``_shrunk`` suffix no
longer matches the archive naming pattern, so it reads only through its label.
"""

from pathlib import Path
from typing import NamedTuple

import numpy as np
import pytest
from PIL import Image

from picmaker.instruments import read_image_array
from picmaker.instruments.juno_junocam import Juno_JunoCam
from tests import generate_previews

DATA_DIR = Path(__file__).parent.parent / 'test_files' / 'juno_junocam'


class Product(NamedTuple):
    """One bundled sample and everything the tests below assert about it."""

    stem: str
    filters: tuple[str, ...]
    plain_shape: tuple[int, ...]    # array as read without --tint
    tint_shape: tuple[int, ...]     # array as read with --tint
    mosaic: bool                    # whether --tint builds a framelet mosaic
    default_tint: tuple[int, int, int] | None
    jpeg_size: tuple[int, int]      # rendered (width, height)
    plain_mode: str                 # rendered mode without --tint
    has_raw: bool                   # whether the .IMG reads on its own


PRODUCTS = (
    # EDR, 8-bit, four filters: the only combination mixing METHANE with colors.
    Product('JNCE_2011238_00A00002_V01', ('METHANE', 'BLUE', 'GREEN', 'RED'),
            (2048, 1648), (4, 512, 1648), True, None, (1648, 2048), 'L', True),
    # EDR, 8-bit, single filter: gets a default tint, unlike the multi-filter ones.
    Product('JNCE_2016192_00B01589_V01', ('BLUE',),
            (1024, 1648), (1, 1024, 1648), True, (100, 100, 200), (1648, 1024),
            'L', True),
    # RDR, 16-bit big-endian, two filters.
    Product('JNCR_2024134_61T00209_V01', ('BLUE', 'RED'),
            (768, 1648), (2, 384, 1648), True, None, (1648, 768), 'L', True),
    # RDR global map: already band-separated, so --tint builds no framelet mosaic.
    Product('JNCR_2023136_51P00000_V01_shrunk', ('BLUE', 'GREEN', 'RED'),
            (3, 360, 720), (3, 360, 720), False, None, (720, 360), 'RGB', False),
)

# Every readable input: each product's label, plus the raw image where it reads.
INPUTS = [pytest.param(product, ext, id=f'{product.stem}-{ext}')
          for product in PRODUCTS
          for ext in (('LBL', 'IMG') if product.has_raw else ('LBL',))]

# Just the framelet stacks. A global map arrives band-separated, so --tint assembles
# no mosaic and it has no framelet boundaries for a line slice to fall across.
MOSAIC_INPUTS = [pytest.param(product, ext, id=f'{product.stem}-{ext}')
                 for product in PRODUCTS if product.mosaic
                 for ext in (('LBL', 'IMG') if product.has_raw else ('LBL',))]


# --- reading the bundled products ----------------------------------------------------

@pytest.mark.parametrize(('product', 'ext'), INPUTS)
def test_reads_expected_array(product: Product, ext: str) -> None:
    """Without ``--tint`` the array keeps its on-disk shape, the filter names come
    out in the order the file stores the bands, and no mosaic is assembled."""
    data = read_image_array(DATA_DIR / f'{product.stem}.{ext}')

    assert np.asarray(data.array).shape == product.plain_shape
    assert tuple(data.filter_names) == product.filters
    assert data.mosaic is False
    assert data.default_upward is False


@pytest.mark.parametrize(('product', 'ext'), INPUTS)
def test_tint_destacks_framelets(product: Product, ext: str) -> None:
    """``--tint`` splits a framelet stack into one band per filter, so each can be
    tinted separately. A global map arrives band-separated already and is left
    alone -- reshaping it as framelets would be nonsense."""
    data = read_image_array(DATA_DIR / f'{product.stem}.{ext}', tint=True)

    assert data.mosaic is product.mosaic
    assert data.array is not None, 'the destacked array must be returned, not dropped'

    array = np.asarray(data.array)
    assert array.shape == product.tint_shape
    assert array.shape[0] == len(product.filters)


@pytest.mark.parametrize(('product', 'ext'), INPUTS)
def test_default_tint(product: Product, ext: str) -> None:
    """A single-filter product carries that filter's tint; a multi-filter product
    has none, because each of its bands is tinted individually instead."""
    data = read_image_array(DATA_DIR / f'{product.stem}.{ext}')

    if product.default_tint is None:
        assert data.default_tint is None
    else:
        assert tuple(data.default_tint) == product.default_tint


@pytest.mark.parametrize('product', [p for p in PRODUCTS if p.has_raw],
                         ids=lambda p: p.stem)
def test_label_and_raw_reads_agree(product: Product) -> None:
    """Reading the raw ``.IMG`` reproduces the labeled read exactly. This is what
    pins ``_FILTER_NAMES`` and ``_SHAPES`` to the labels: a wrong band order or
    sample count would still produce an array, just not this one."""
    from_label = np.asarray(read_image_array(DATA_DIR / f'{product.stem}.LBL').array)
    from_raw = np.asarray(read_image_array(DATA_DIR / f'{product.stem}.IMG').array)

    np.testing.assert_array_equal(from_label, from_raw)


def test_shrunk_map_needs_its_label() -> None:
    """The block-averaged map reads only through its label: the ``_shrunk`` suffix
    breaks the archive filename pattern, and its dimensions no longer match the
    hard-coded map shape that a raw read would assume."""
    with pytest.raises(OSError, match='unrecognized file format'):
        read_image_array(DATA_DIR / 'JNCR_2023136_51P00000_V01_shrunk.IMG')


# --- rendering with --tint -----------------------------------------------------------

@pytest.mark.parametrize(('product', 'ext'), INPUTS)
def test_tint_renders_rgb(product: Product, ext: str, tmp_path: Path) -> None:
    """Every input renders end to end under ``--tint``, in color. The four-filter
    product is the one at risk here: its METHANE band is tinted a neutral gray,
    which yields one channel where the colored bands yield three, and the bands
    cannot be stacked until that band is broadcast up to three."""
    generate_previews(DATA_DIR / f'{product.stem}.{ext}', tmp_path,
                      extra_args=('--tint', '--extension=jpg'))

    with Image.open(tmp_path / f'{product.stem}.jpg') as rendered:
        assert rendered.size == product.jpeg_size
        assert rendered.mode == 'RGB'


@pytest.mark.parametrize(('product', 'ext'), INPUTS)
def test_tint_renders_sliced_mosaic(product: Product, ext: str, tmp_path: Path) -> None:
    """``--tint`` survives a sample slice. Dropping the leading columns is the way
    to keep JunoCam's near-saturated per-framelet marker block out of a percentile
    stretch, which otherwise pins the upper limit near 255 and leaves the faintest
    band -- usually BLUE -- rendered far too dark."""
    trimmed = 8
    generate_previews(DATA_DIR / f'{product.stem}.{ext}', tmp_path,
                      extra_args=('--tint', '--extension=jpg',
                                  '--samples', str(trimmed),
                                  str(product.jpeg_size[0])))

    rendered_path = tmp_path / f'{product.stem}.jpg'
    assert rendered_path.exists(), 'the sliced mosaic must render, not be skipped'
    with Image.open(rendered_path) as rendered:
        width, height = product.jpeg_size
        assert rendered.size == (width - trimmed, height)
        assert rendered.mode == 'RGB'


@pytest.mark.parametrize(('product', 'ext'), MOSAIC_INPUTS)
def test_tint_renders_unaligned_line_slice(product: Product, ext: str,
                                           tmp_path: Path) -> None:
    """A ``--lines`` slice that neither starts on a framelet boundary nor spans whole
    framelets renders, and renders at the height the interleave implies: one band's
    worth of lines per filter. Lines here count within a band, not within the file,
    so the mosaic comes out `len(filters)` times as tall as the slice."""
    row0, row1 = 100, 300                           # 200 lines, both ends mid-framelet
    generate_previews(DATA_DIR / f'{product.stem}.{ext}', tmp_path,
                      extra_args=('--tint', '--extension=jpg',
                                  '--lines', str(row0), str(row1)))

    rendered_path = tmp_path / f'{product.stem}.jpg'
    assert rendered_path.exists(), 'the unaligned mosaic must render, not be skipped'
    with Image.open(rendered_path) as rendered:
        assert rendered.size == (product.jpeg_size[0],
                                 (row1 - row0) * len(product.filters))


@pytest.mark.parametrize(('product', 'ext'), INPUTS)
def test_plain_render_keeps_size(product: Product, ext: str, tmp_path: Path) -> None:
    """Without ``--tint`` the same input renders at the same size, grayscale for a
    framelet stack and RGB for the three-band map."""
    generate_previews(DATA_DIR / f'{product.stem}.{ext}', tmp_path,
                      extra_args=('--extension=jpg',))

    with Image.open(tmp_path / f'{product.stem}.jpg') as rendered:
        assert rendered.size == product.jpeg_size
        assert rendered.mode == product.plain_mode


# --- mosaic assembly (no data files) -------------------------------------------------

def test_reshape_for_mosaic_returns_band_cube() -> None:
    """Destacking returns the cube it built. It used to reshape and then drop the
    result, handing ``None`` to the constructor."""
    array = np.zeros((2 * 128, 1648), dtype='u1')
    array[128:] = 1                                 # second framelet, RED

    cube = Juno_JunoCam._reshape_for_mosaic(array, ('BLUE', 'RED'))

    assert cube is not None
    assert cube.shape == (2, 128, 1648)
    assert int(cube[0, 0, 0]) == 0                  # band 0 = BLUE framelet
    assert int(cube[1, 0, 0]) == 1                  # band 1 = RED framelet


def test_apply_mosaic_interleaves_framelets() -> None:
    """Assembly reverses the destacking: bands go back to alternating framelets in
    filter order, 128 lines at a time."""
    blue = np.full((256, 1648, 3), 0.25)
    red = np.full((256, 1648, 3), 0.75)

    mosaic = Juno_JunoCam.apply_mosaic([blue, red])

    assert mosaic.shape == (512, 1648, 3)
    assert mosaic[0, 0, 0] == 0.25                  # framelet 0, band 0 = BLUE
    assert mosaic[128, 0, 0] == 0.75                # framelet 0, band 1 = RED
    assert mosaic[256, 0, 0] == 0.25                # framelet 1, band 0 = BLUE


def test_apply_mosaic_accepts_a_narrower_array() -> None:
    """Assembly takes its sample count from the arrays it is handed, not from the
    detector width. Slicing (``--samples``, ``--crop``) narrows the bands before
    they reach here, and a hard-coded 1648 made the reshape fail outright."""
    narrow = 1648 - 8                               # e.g. --samples 8 1648
    blue = np.full((256, narrow, 3), 0.25)
    red = np.full((256, narrow, 3), 0.75)

    mosaic = Juno_JunoCam.apply_mosaic([blue, red])

    assert mosaic.shape == (512, narrow, 3)
    assert mosaic[0, 0, 0] == 0.25                  # framelet 0, band 0 = BLUE
    assert mosaic[128, 0, 0] == 0.75                # framelet 0, band 1 = RED
    assert mosaic[256, 0, 0] == 0.25                # framelet 1, band 0 = BLUE


def _tagged_bands(bands: int, rows: int, samples: int = 4) -> list[np.ndarray]:
    """One array per band, every line tagged with its band and its line number.

    Channel 0 carries the band index and channel 1 the line index, so a line that
    lands in the wrong place in the mosaic says exactly where it came from.
    """
    tagged = []
    for band in range(bands):
        array = np.zeros((rows, samples, 3))
        array[..., 0] = band
        array[..., 1] = np.arange(rows)[:, np.newaxis]
        tagged.append(array)
    return tagged


def _expected_mosaic(bands: list[np.ndarray], row0: int) -> np.ndarray:
    """Interleave `bands` the long way round: walk the lines framelet by framelet,
    emitting every band's share of each framelet before moving to the next."""
    pieces = []
    row = row0
    end_row = row0 + bands[0].shape[0]
    while row < end_row:
        edge = min(end_row, (row // 128 + 1) * 128)
        pieces += [band[row-row0:edge-row0] for band in bands]
        row = edge
    return np.concatenate(pieces, axis=0)


@pytest.mark.parametrize(('row0', 'rows'), [
    (0, 512),       # aligned, whole framelets: the ordinary case
    (64, 256),      # unaligned start, whole number of framelets' worth of lines
    (0, 300),       # aligned start, partial framelet at the end
    (64, 236),      # unaligned at both ends
    (200, 50),      # entirely inside one framelet
    (127, 2),       # straddling a boundary by a single line
])
def test_apply_mosaic_regroups_at_framelet_boundaries(row0: int, rows: int) -> None:
    """Assembly splits the lines at framelet boundaries, wherever the slice starts.

    Reshaping against a fixed 128 instead used to assume line 0 was the top of a
    framelet. A ``--lines`` slice starting mid-framelet then spliced the bottom of
    one framelet onto the top of the next -- and when the line count happened to be
    a multiple of 128 it did so without raising, quietly scrambling the mosaic.
    """
    sliced = _tagged_bands(3, rows)

    mosaic = Juno_JunoCam.apply_mosaic(sliced, lines=(row0, row0 + rows))

    assert mosaic.shape == (3 * rows, 4, 3)
    np.testing.assert_array_equal(mosaic, _expected_mosaic(sliced, row0))


def test_apply_mosaic_rejects_crop() -> None:
    """Cropping runs after the line slice and removes lines by value, so it destroys
    the only means of locating the framelet boundaries. Better to say so than to
    interleave against an offset that is no longer true.

    The value here is deliberately non-zero: ``validate_options`` treats a falsy
    ``crop`` as unset, so ``--crop 0`` never reaches this code at all.
    """
    bands = _tagged_bands(2, 256)

    with pytest.raises(ValueError, match='crop'):
        Juno_JunoCam.apply_mosaic(bands, crop=5.)


def test_apply_mosaic_broadcasts_neutral_band() -> None:
    """A neutrally tinted band (METHANE) comes back one-channel while colored bands
    come back three-channel; the odd band out is broadcast so the stack is
    rectangular."""
    methane = np.full((128, 1648, 1), 0.5)          # neutral gray -> one channel
    blue = np.full((128, 1648, 3), 0.25)

    mosaic = Juno_JunoCam.apply_mosaic([methane, blue])

    assert mosaic.shape == (256, 1648, 3)
    np.testing.assert_array_equal(mosaic[0, 0], [0.5, 0.5, 0.5])
    np.testing.assert_array_equal(mosaic[128, 0], [0.25, 0.25, 0.25])
