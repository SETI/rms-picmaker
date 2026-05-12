"""Smoke check that ``picmaker.__init__`` re-exports the core public API."""

from typing import Any


def test_package_imports_resolve(tiny_array: Any) -> None:
    """The top-level :mod:`picmaker` re-exports the core entry points."""
    import picmaker

    assert callable(picmaker.images_to_pics)
    assert callable(picmaker.process_images)
    assert callable(picmaker.read_one_image_array)
    assert callable(picmaker.tinted_colormap)
    assert callable(picmaker.apply_colormap)
    assert callable(picmaker.get_limits)
    # tiny_array fixture verifies the conftest plumbing still works.
    assert tiny_array.shape == (16, 16)
