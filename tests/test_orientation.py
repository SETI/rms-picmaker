"""Tests for picmaker.orientation: rotate_rgb_array flips and rotations."""

import numpy as np
import pytest

from picmaker.orientation import rotate_rgb_array


def test_rotate_rgb_array_rot90() -> None:
    """``rotation='ROT90'`` preserves shape."""
    arr = np.zeros((8, 8, 3), dtype='float32')
    arr[0, 0] = 1.0
    out = rotate_rgb_array(arr, default_upward=False, rotation='ROT90')
    assert out.shape == arr.shape


def test_rotate_rgb_array_fliplr() -> None:
    """``rotation='FLIPLR'`` mirrors horizontally."""
    arr = np.zeros((8, 8, 3), dtype='float32')
    arr[0, 0] = 1.0
    out = rotate_rgb_array(arr, default_upward=False, rotation='FLIPLR')
    assert out[0, -1, 0] == pytest.approx(1.0)


def test_rotate_rgb_array_fliptb_and_rot180() -> None:
    """``FLIPTB`` and ``ROT180`` both end up with the corner at the bottom."""
    arr = np.zeros((8, 8, 3), dtype='float32')
    arr[0, 0] = 1.0
    out_flip = rotate_rgb_array(arr.copy(), default_upward=False, rotation='FLIPTB')
    assert out_flip[-1, 0, 0] == pytest.approx(1.0)
    out_rot = rotate_rgb_array(arr.copy(), default_upward=False, rotation='ROT180')
    assert out_rot[-1, -1, 0] == pytest.approx(1.0)


def test_rotate_rgb_array_rot270() -> None:
    """``rotation='ROT270'`` preserves shape."""
    arr = np.zeros((8, 8, 3), dtype='float32')
    out = rotate_rgb_array(arr, default_upward=False, rotation='ROT270')
    assert out.shape == arr.shape


def test_rotate_rgb_array_unknown_raises() -> None:
    """An unrecognised rotation name raises ``KeyError``."""
    arr = np.zeros((4, 4, 3), dtype='float32')
    with pytest.raises(KeyError, match='unrecognized rotation'):
        rotate_rgb_array(arr, default_upward=False, rotation='tumble')


def test_rotate_rgb_array_display_upward() -> None:
    """``display_upward=True`` pre-flips the image vertically."""
    arr = np.zeros((4, 4, 3), dtype='float32')
    arr[0, 0] = 1.0
    out = rotate_rgb_array(arr, default_upward=False, display_upward=True, rotation='NONE')
    assert out[-1, 0, 0] == pytest.approx(1.0)


class TestRotateRgbArray:
    def _make(self) -> np.ndarray:
        return np.arange(12, dtype=np.uint8).reshape(3, 4)

    def test_no_rotation_downward(self) -> None:
        arr = self._make()
        out = rotate_rgb_array(arr.copy(), default_upward=False,
                               display_upward=False, rotation='NONE')
        np.testing.assert_array_equal(out, arr)

    def test_upward_flips(self) -> None:
        arr = self._make()
        out = rotate_rgb_array(arr.copy(), default_upward=False,
                               display_upward=True, rotation='NONE')
        np.testing.assert_array_equal(out, np.flipud(arr))

    @pytest.mark.parametrize(('name', 'expected_shape'), [
        ('FLIPLR', (3, 4)),
        ('FLIPTB', (3, 4)),
        ('ROT90', (4, 3)),
        ('ROT180', (3, 4)),
        ('ROT270', (4, 3)),
    ])
    def test_named_rotations_run(
        self, name: str, expected_shape: tuple[int, ...]
    ) -> None:
        arr = self._make()
        out = rotate_rgb_array(arr.copy(), default_upward=False,
                               display_upward=False, rotation=name)
        assert out.shape == expected_shape

    def test_unknown_rotation_raises(self) -> None:
        arr = self._make()
        with pytest.raises(KeyError, match='unrecognized rotation'):
            rotate_rgb_array(arr.copy(), default_upward=False,
                             display_upward=False, rotation='BAD')
