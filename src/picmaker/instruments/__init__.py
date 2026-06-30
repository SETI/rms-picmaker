##########################################################################################
# picmaker/instruments/__init__.py
##########################################################################################
"""Instrument reader modules."""

# The wrapped import below uses a hand-formatted hanging indent; skip isort reformatting.
# ruff: noqa: I001
import importlib
import pathlib
import pkgutil

import astropy.io.fits as pyfits
import numpy as np
import pdsparser
import vicar
from tabulation import Tabulation

from picmaker.instruments._fits_support import get_fits_array
from picmaker.instruments._pds3_support import (DEFAULT_PDS3_METHOD, PDS3_METHODS,
                                                read_pds3_image_array)

_INSTRUMENTS = []


def register_instrument(subclass):
    _INSTRUMENTS.append(subclass)
    _INSTRUMENTS.sort(key=lambda k: k.__name__)


def _register_all_instruments():
    """Import every instrument submodule so that each registers itself.

    Any module in this package whose name does not begin with an underscore is imported
    for its side effects: defining an :class:`ImageData` subclass and calling
    :func:`register_instrument`. Support modules (``_pds3_support``, ``_fits_support``,
    ``_hst_support``) are skipped. A new instrument is picked up automatically by dropping
    a module into this package; this file does not need to be edited.
    """

    for module_info in pkgutil.iter_modules(__path__):
        if not module_info.name.startswith('_'):
            importlib.import_module(f'{__name__}.{module_info.name}')


class ImageData:
    def __init__(self, array, default_upward, default_tint):
        self.array = array
        self.default_upward = default_upward
        self.default_tint = default_tint


def read_image_array(filepath, **kwargs):
    """Read one or more image files and return a stacked 3-D array.

    Parameters:
        filepath (str, pathlib.Path, or list): One or more input file paths.
        **kwargs: Instrument-specific options.

    Returns:
        (:class:`ImageData`): The image data. When multiple files are given, their arrays
        are stacked along the leading band axis.
    """

    if isinstance(filepath, (str, pathlib.Path)):
        return _read_one_image_array(filepath, **kwargs)

    results = [_read_one_image_array(f, **kwargs) for f in filepath]

    arrays = [r.array for r in results]
    arrays = [np.reshape(a, (1, *a.shape)) if len(a.shape) < 3 else a for a in arrays]
    array3d = np.vstack(arrays)
    return ImageData(array3d, results[0].default_upward, results[0].default_tint)


def _read_one_image_array(filepath, **kwargs):
    """Read a single image array, trying each known format in turn.

    Parameters:
        filepath (str or pathlib.Path): Path to the input file.
        **kwargs: Instrument-specific options.

    Returns:
        (:class:`ImageData`): The image data from the first reader that recognizes the
        file.

    Raises:
        OSError: If none of the format readers succeed.
    """

    filepath = pathlib.Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError('No such file or directory: "{filepath}"')
    if not filepath.is_file():
        raise IsADirectoryError('File is a directory: "{filepath}"')

    # Handle a PDS3 label
    if filepath.suffix.lower() == '.lbl':
        method = kwargs.get('pds3_method', DEFAULT_PDS3_METHOD)
        label = pdsparser.Pds3Label(filepath, method=method)  # forward parsing error
        for instrument in _INSTRUMENTS:
            if hasattr(instrument, 'detect_in_pds3'):
                test = instrument.detect_in_pds3(label, **kwargs)
                if test:
                    return test

    # Handle a VICAR file
    try:
        vic = vicar.VicarImage.from_file(filepath)
    except Exception:
        pass
    else:
        for instrument in _INSTRUMENTS:
            if hasattr(instrument, 'detect_in_vicar'):
                test = instrument.detect_in_vicar(vic, **kwargs)
                if test:
                    return test

    # Handle a FITS file
    try:
        hdulist = pyfits.open(filepath)
    except Exception:
        pass
    else:
        with hdulist:
            for instrument in _INSTRUMENTS:
                if hasattr(instrument, 'detect_in_fits'):
                    test = instrument.detect_in_fits(hdulist, **kwargs)
                    if test:
                        # Copy the pixels out of the memory-mapped HDU before the
                        # enclosing 'with' closes the file.
                        test.array = np.array(test.array)
                        return test

    # Handle another file format
    try:
        for instrument in _INSTRUMENTS:
            if hasattr(instrument, 'detect_in_file'):
                test = instrument.detect_in_file(filepath, **kwargs)
                if test:
                    return test
    except Exception:
        pass

    raise OSError('unrecognized file format in {filepath}')


# [wavelength_nm, r, g, b]
_RGB_BY_NM = np.array([
    [380.0, 200.500,  60.500, 255.999],  # uv
    [410.0, 200.500, 110.500, 255.999],  # violet
    [480.0, 110.500, 110.500, 255.999],  # blue
    [540.0, 110.500, 255.999, 110.500],  # green
    [580.0, 255.999, 255.999, 110.500],  # yellow
    [610.0, 255.999, 180.500, 110.500],  # orange
    [650.0, 255.999, 110.500, 110.500],  # red
    [750.0, 255.999,  60.500,  60.500],  # ir
])

_RFUNC = Tabulation(_RGB_BY_NM[:, 0], _RGB_BY_NM[:, 1])
_GFUNC = Tabulation(_RGB_BY_NM[:, 0], _RGB_BY_NM[:, 2])
_BFUNC = Tabulation(_RGB_BY_NM[:, 0], _RGB_BY_NM[:, 3])


def tint_by_nm(wavelength):
    """An RGB tint color based on a wavelength of light in nm."""

    wavelength = max(wavelength, _RGB_BY_NM[0, 0])
    wavelength = min(wavelength, _RGB_BY_NM[-1, 0])

    r = int(_RFUNC(wavelength))
    g = int(_GFUNC(wavelength))
    b = int(_BFUNC(wavelength))
    return (r, g, b)


__all__ = ['ImageData', 'PDS3_METHODS', 'DEFAULT_PDS3_METHOD',
           'read_image_array', 'read_pds3_image_array', 'get_fits_array', 'tint_by_nm']

# Discover and import the instrument modules so each registers itself.
_register_all_instruments()

##########################################################################################
