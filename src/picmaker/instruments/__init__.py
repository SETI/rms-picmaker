##########################################################################################
# picmaker/instruments/__init__.py
##########################################################################################
"""Instrument modules for file reading and special processing."""

# ruff: noqa: I001
import importlib
import pathlib
import pkgutil

import astropy.io.fits as pyfits
import numpy as np
import pdsparser
import vicar
from tabulation import Tabulation

from picmaker.enhancement import apply_colormap as default_apply_colormap
from picmaker.instruments._fits_support import get_fits_array
from picmaker.instruments._pds3_support import (DEFAULT_PDS3_METHOD, PDS3_METHODS,
                                                read_pds3_image_array)

_INSTRUMENTS = []


def _register_instrument(subclass):
    if subclass not in _INSTRUMENTS:
        _INSTRUMENTS.append(subclass)
        # Note that ZZZ_Generic has to come last in the list
        _INSTRUMENTS.sort(key=lambda k: k.__name__)


def _register_all_instruments():
    """Import every instrument submodule so that each registers itself.

    Any module in this package whose name does not begin with an underscore is imported
    for its side effect of defining an ImageData subclass; each subclass registers itself
    automatically via `ImageData.__init_subclass__`. Support modules (`_pds3_support`,
    `_fits_support`, etc.) are skipped. A new instrument is picked up automatically by
    dropping a module into this package.
    """

    for module_info in pkgutil.iter_modules(__path__):
        if not module_info.name.startswith('_'):
            importlib.import_module(f'{__name__}.{module_info.name}')


class ImageData:
    def __init_subclass__(cls, **kwargs):
        # Every ImageData subclass is an instrument reader; register it as soon as its
        # class body runs (i.e. when its module is imported), so modules never have to
        # call _register_instrument themselves.
        super().__init_subclass__(**kwargs)
        _register_instrument(cls)

    def __init__(self, array, default_upward, default_tint):
        self.array = array
        self.default_upward = default_upward
        self.default_tint = default_tint

    def apply_colormap(self, array, valid_limits, invalid_mask=None, **kwargs):
        """Apply a colormap to up to three grayscale images.

        Produces a 3-D array with one band (grayscale) or three bands (RGB), in axis order
        (line, sample, channel). Values are scaled zero to one.

        This is overridden by instruments that require a special method for applying a
        colormap. Here, the default procedure is called.

        Parameters:
            array (array): The image array, after slicing and "zebra" operations.
            valid_limits (tuple[float, float]): The values that correspond to the minimum
                and maximum of the mapping.
            invalid_mask (array[bool], optional): Boolean mask of invalid pixels.
            **kwargs: Additional input options, forwarded to the default procedure.

        Returns:
            array[float]: A 3-D array in axis order (line, sample, channel) scaled zero to
            one. For a grayscale image, the last axis has length 1; otherwise, it has
            length 3.
        """

        return default_apply_colormap(array, valid_limits, invalid_mask,
                                      default_tint=self.default_tint, **kwargs)


def read_image_array(filepath, **kwargs):
    """Read one or more image files and return a stacked 3-D array.

    Parameters:
        filepath (str, Path, or list[str or Path]): One or more input file paths.
        **kwargs: Additoinal input options.

    Returns:
        ImageData: The ImageData subclass associated with the file(s). When multiple files
        are given, their arrays are stacked along the leading band axis.
    """

    if isinstance(filepath, (str, pathlib.Path)):
        return _read_one_image_array(filepath, **kwargs)

    results = [_read_one_image_array(f, **kwargs) for f in filepath]

    arrays = [r.array for r in results]
    arrays = [np.reshape(a, (1, *a.shape)) if len(a.shape) < 3 else a for a in arrays]
    array3d = np.vstack(arrays)
    # Note that the `default_upward` and `default_tint` are defined by the first filepath
    # in cases where there is more than one.
    return ImageData(array3d, results[0].default_upward, results[0].default_tint)


def _read_one_image_array(filepath, **kwargs):
    """Read a single image array, trying each known format in turn.

    Parameters:
        filepath (str or Path): Path to the input file.
        **kwargs: Instrument-specific options.

    Returns:
        ImageData or None: The ImageData subclass from the reader that recognized the
        file.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path refers to a directory.
        OSError: If none of the format readers recognized the file.
    """

    filepath = pathlib.Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f'No such file or directory: "{filepath}"')
    if not filepath.is_file():
        raise IsADirectoryError(f'File is a directory: "{filepath}"')

    # Handle a PDS3 label
    if filepath.suffix.lower() == '.lbl':
        method = kwargs.get('pds3_method', DEFAULT_PDS3_METHOD)
        label = pdsparser.Pds3Label(filepath, method=method)  # forward parsing error
        for instrument in _INSTRUMENTS:
            if hasattr(instrument, 'detect_in_pds3'):
                test = instrument.detect_in_pds3(label, filepath, **kwargs)
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
                test = instrument.detect_in_vicar(vic, filepath, **kwargs)
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
                    test = instrument.detect_in_fits(hdulist, filepath, **kwargs)
                    if test:
                        # Copy the pixels out of the memory-mapped HDU before the
                        # enclosing 'with' closes the file.
                        test.array = np.array(test.array)
                        return test

    # Handle another file format
    for instrument in _INSTRUMENTS:
        if hasattr(instrument, 'detect_in_file'):
            test = instrument.detect_in_file(filepath, **kwargs)
            if test:
                return test

    raise OSError(f'unrecognized file format in {filepath}')


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


__all__ = [
    'DEFAULT_PDS3_METHOD',
    'PDS3_METHODS',
    'ImageData',
    'get_fits_array',
    'read_image_array',
    'read_pds3_image_array',
    'tint_by_nm',
]

# Discover and import the instrument modules so each registers itself.
_register_all_instruments()

##########################################################################################
