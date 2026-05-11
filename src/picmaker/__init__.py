"""picmaker: convert PDS3 / VICAR / FITS astronomy images into JPEG, TIFF, etc.

This package ships both as a CLI (`picmaker`) and as an importable library. The full
public API still lives at `picmaker.picmaker` for backward compatibility; this
`__init__` only exposes `__version__` for now (re-exports follow in a later PR).
"""

try:
    from importlib.metadata import version

    __version__ = version('rms-picmaker')
except Exception:
    try:
        from picmaker._version import __version__
    except ImportError:
        __version__ = '0.0.0+unknown'

__all__ = ['__version__']
