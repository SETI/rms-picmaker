"""apply_gamma unit tests — identity, exact boundary values, NaN/Inf safety."""

import numpy as np

from picmaker import apply_gamma


class TestIdentity:
    def test_gamma_one_2d_returns_unchanged(self) -> None:
        arr = np.arange(64, dtype=np.float64).reshape(8, 8) / 63.0
        out = apply_gamma(arr.copy(), 1.0)
        np.testing.assert_array_equal(out, arr)

    def test_gamma_one_3d_rgb_returns_unchanged(self) -> None:
        arr = np.linspace(0, 1, 192, dtype=np.float64).reshape(8, 8, 3)
        out = apply_gamma(arr.copy(), 1.0)
        np.testing.assert_array_equal(out, arr)


class TestBoundaryValues:
    def test_gamma_2_0_squares(self) -> None:
        arr = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        out = apply_gamma(arr.copy(), 2.0)
        np.testing.assert_allclose(out, arr**2)

    def test_gamma_0_5_square_roots(self) -> None:
        arr = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        out = apply_gamma(arr.copy(), 0.5)
        np.testing.assert_allclose(out, np.sqrt(arr))

    def test_zero_and_one_are_fixed_points(self) -> None:
        # x**gamma fixes 0 and 1 for any gamma > 0.
        for gamma in (0.4, 1.0, 2.2, 3.0):
            out = apply_gamma(np.array([0.0, 1.0]), gamma)
            np.testing.assert_allclose(out, [0.0, 1.0])


class TestPathological:
    def test_finite_input_no_exception(self) -> None:
        arr = np.array([0.0, 0.5, 1.0], dtype=np.float64)
        out = apply_gamma(arr.copy(), 2.0)
        assert np.all(np.isfinite(out))

    def test_nan_passes_through_without_exception(self) -> None:
        arr = np.array([0.0, 0.5, np.nan, 1.0], dtype=np.float64)
        out = apply_gamma(arr.copy(), 2.0)
        # NaN stays NaN; finite values are squared.
        assert np.isnan(out[2])
        np.testing.assert_allclose(out[[0, 1, 3]], [0.0, 0.25, 1.0])

    def test_inf_passes_through_without_exception(self) -> None:
        arr = np.array([0.0, 0.5, np.inf, 1.0], dtype=np.float64)
        out = apply_gamma(arr.copy(), 2.0)
        assert np.isinf(out[2])
        np.testing.assert_allclose(out[[0, 1, 3]], [0.0, 0.25, 1.0])
