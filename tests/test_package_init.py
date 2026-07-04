"""Smoke check that ``picmaker.__init__`` re-exports the core public API."""

from typing import Any


def test_package_imports_resolve(tiny_array: Any) -> None:
    """Every name in :data:`picmaker.__all__` resolves and is callable."""
    import picmaker

    assert picmaker.__all__, 'picmaker.__all__ should not be empty'
    for name in picmaker.__all__:
        obj = getattr(picmaker, name)
        assert callable(obj), f'picmaker.{name} is not callable'

    # A few representative entry points are present by name.
    for name in ('picmaker', 'validate_options', 'get_filepaths', 'get_outfile',
                 'get_versions', 'apply_colormap', 'get_limits'):
        assert name in picmaker.__all__
        assert callable(getattr(picmaker, name))

    # tiny_array fixture verifies the conftest plumbing still works.
    assert tiny_array.shape == (16, 16)
