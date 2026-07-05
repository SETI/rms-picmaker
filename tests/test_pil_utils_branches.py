"""Cover the pil_utils branches that the existing tests don't reach:
16-bit grayscale / 16-bit RGB round trip, list-of-three handling, the
unsupported PIL mode error path, and the write_pil parent-directory and
write paths.
"""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from picmaker.pil_utils import (
    _one_pil_to_array,
    array_to_pil,
    pil_to_array,
    write_pil,
)


def test_array_to_pil_sixteen_bit_grayscale_no_rescale() -> None:
    """16-bit grayscale arrays (no rescale) round-trip via PIL ``I`` mode."""
    array = np.zeros((4, 4, 1), dtype='float64')
    array[:] = 0.5  # mid-grey
    im = array_to_pil(array, twobytes=True)
    assert im.mode == 'I'
    out = _one_pil_to_array(im, rescale=False)
    assert out.shape == (4, 4)


def test_array_to_pil_sixteen_bit_rgb_yields_three_images() -> None:
    """16-bit RGB arrays produce a list of three PIL ``I`` images."""
    array = np.zeros((4, 4, 3), dtype='float64')
    array[..., 0] = 0.25
    array[..., 1] = 0.5
    array[..., 2] = 0.75
    result = array_to_pil(array, twobytes=True)
    assert isinstance(result, list)
    assert len(result) == 3
    for im in result:
        assert im.mode == 'I'
        assert im.size == (4, 4)


def test_pil_to_array_handles_list_of_three() -> None:
    """A list of three PIL images is depth-stacked into an RGB array."""
    ims = [Image.new('L', (4, 4), color=c) for c in (10, 20, 30)]
    arr = pil_to_array(ims, rescale=False)
    assert arr.shape == (4, 4, 3)
    assert arr[0, 0, 0] == 10
    assert arr[0, 0, 1] == 20
    assert arr[0, 0, 2] == 30


def test_one_pil_to_array_unsupported_mode_raises() -> None:
    """``_one_pil_to_array`` rejects PIL modes other than ``L`` and ``I``."""
    im = Image.new('RGB', (4, 4))
    with pytest.raises(OSError, match='Unsupported PIL image format'):
        _one_pil_to_array(im, rescale=False)


def test_write_pil_sixteen_bit_rgb_writes_tiff(tmp_path: Path) -> None:
    """``write_pil`` on a 3-image list calls ``write_tiff16`` and produces
    an RGB TIFF.
    """
    ims = [Image.new('I', (4, 4), color=10000 * (c + 1)) for c in range(3)]
    out = tmp_path / 'rgb16.tiff'
    write_pil(ims, str(out))
    assert out.exists()


def test_write_pil_sixteen_bit_grayscale_writes_tiff(tmp_path: Path) -> None:
    """``write_pil`` on a single ``I``-mode PIL image writes a 16-bit TIFF."""
    im = Image.new('I', (4, 4), color=30000)
    out = tmp_path / 'gray16.tiff'
    write_pil(im, str(out))
    assert out.exists()


def test_write_pil_creates_parent_directory(tmp_path: Path) -> None:
    """``write_pil`` creates a missing parent directory before writing."""
    nested = tmp_path / 'a' / 'b' / 'c'
    im = Image.new('L', (4, 4))
    out = nested / 'out.png'
    write_pil(im, str(out))
    assert out.exists()
