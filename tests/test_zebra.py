"""fill_zebra_stripes unit tests."""

from __future__ import annotations

import numpy as np

from picmaker.picmaker import fill_zebra_stripes


class TestFillZebraStripes:
    def test_zero_pixel_between_nonzero_neighbors_is_filled(self) -> None:
        # Row 1's left column is zero, but row 0 and row 2's left column are
        # nonzero — fill should set row1[0] to their average.
        arr = np.zeros((3, 3), dtype=np.int32)
        arr[0, 0] = 10
        arr[2, 0] = 20
        arr[1, 1] = 5  # so the inner row isn't all zero (break condition)
        arr[0, 1] = 4
        arr[2, 1] = 6
        out = fill_zebra_stripes(arr.copy())
        # row1[0] gets filled with (10 + 20) // 2 = 15 (integer division).
        assert out[1, 0] == 15

    def test_nonzero_pixel_left_alone(self) -> None:
        arr = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.int32)
        out = fill_zebra_stripes(arr.copy())
        np.testing.assert_array_equal(out, arr)

    def test_in_place_modification(self) -> None:
        arr = np.zeros((3, 3), dtype=np.int32)
        arr[0, 0] = 100
        arr[2, 0] = 50
        arr[1, 1] = 99
        out = fill_zebra_stripes(arr)
        # Return is the same object, modified in place.
        assert out is arr

    def test_right_edge_fill(self) -> None:
        # Zero on the right edge between nonzero rows.
        arr = np.zeros((3, 3), dtype=np.int32)
        arr[0, 2] = 10
        arr[2, 2] = 30
        # Force the row scan to enter the "from right" loop:
        # both row1 endpoints zero, but inner pixels stop the left scan.
        arr[1, 1] = 5
        arr[0, 1] = 4
        arr[2, 1] = 6
        out = fill_zebra_stripes(arr.copy())
        # row1[2] fills with (10 + 30) // 2 = 20.
        assert out[1, 2] == 20
