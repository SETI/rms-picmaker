##########################################################################################
# picmaker/instruments/juno_junocam.py
##########################################################################################
"""Juno JunoCam detector and reader."""

import pathlib
import re

import numpy as np

from picmaker.enhancement import apply_colormap as default_apply_colormap
from picmaker.instruments import ImageData
from picmaker.instruments._pds3_support import read_pds3_image_array

_FILTER_NAMES = {
    'A': ('METHANE', 'BLUE', 'GREEN', 'RED'),
    'B': ('BLUE',),
    'C': ('BLUE', 'GREEN', 'RED'),
    'G': ('GREEN',),
    'M': ('METHANE',),
    'R': ('RED',),
    'T': ('BLUE', 'RED'),
    'P': ('BLUE', 'GREEN', 'RED'),
    'H': ('METHANE',),
}

_DEFAULT_TINTS = {
    'RED'    : (200, 100, 100),
    'GREEN'  : (100, 200, 100),
    'BLUE'   : (100, 100, 200),
    'METHANE': (128, 128, 128),
}

_SHAPES = {
    'P': (3, 2880, 5760),
    'H': (2880, 5760),
}
_DEFAULT_SHAPE = (-1, 1648)
_WIDTH = 1648
_HEIGHT = 128  # height of one strip

_DEFAULT_UPWARD = False
_BASENAME_PATTERN = re.compile(r'JNC([ER])_20[123]\d[0-3]\d\d_\d\d([ABCGMRTPH])\d{5}'
                               r'_V0\d\.IMG')


class Juno_JunoCam(ImageData):
    """Juno JunoCam detector and reader."""

    @staticmethod
    def detect_in_pds3(label, filepath, *, colormap=None, tint=False, **kwargs):
        """Extract Juno JunoCam data from a parsed Pds3Label.

        Parameters:
            label (Pds3Label): A parsed PDS3 label.
            filepath (str or Path): The path to this PDS3 label.
            colormap (str, tuple[int, int, int], or list, optional): Colormap to use.
            tint (bool, optional): True for separate RGB tinting.
            **kwargs: Additional input options, ignored here.

        Returns:
            Juno_JunoCam or None: Instrument subclass if `label` describes a Juno JunoCam
            product; None otherwise.
        """

        try:
            if label['INSTRUMENT_HOST_NAME'] != 'JUNO':
                return None
            if label['INSTRUMENT_ID'] != 'JNC':
                return None
        except (KeyError, TypeError, IndexError):
            return None

        array = read_pds3_image_array(label, filepath, **kwargs)
        filter_names = label.get('FILTER_NAME', [])
        is_map = array.shape[-1] != _DEFAULT_SHAPE[1]

        # Mosaics apply to framelet products only; map products are already band-separated
        mosaic = colormap is None and tint and not is_map
        if mosaic:
            array = Juno_JunoCam._reshape_for_mosaic(array, filter_names)

        result = Juno_JunoCam(array, _DEFAULT_UPWARD,
                              Juno_JunoCam._default_tint(filter_names))
        result.mosaic = mosaic
        result.filter_names = filter_names
        return result

    @staticmethod
    def detect_in_file(filepath, *, colormap=None, tint=False, **kwargs):
        """Extract image data from a Juno JunoCam data data file.

        Parameters:
            filepath (str or Path): The file path.
            colormap (str, tuple[int, int, int], or list, optional): Colormap to use.
            tint (bool, optional): True for separate RGB tinting.
            **kwargs: Other input parameters

        Returns:
            Juno_JunoCam or None: The ImageData subclass if the format of `file` is
            recognized; otherwise, None.
        """

        basename = pathlib.Path(filepath).name
        match = _BASENAME_PATTERN.fullmatch(basename.upper())
        if not match:
            return None

        level, filter_key = match.groups()
        filter_names = _FILTER_NAMES[filter_key]
        is_map = filter_key in 'PH'

        dtype = 'u1' if (level.upper() == 'E' or is_map) else '>u2'
        array = np.fromfile(filepath, dtype=dtype)
        shape = _SHAPES.get(filter_key, _DEFAULT_SHAPE)
        array = array.reshape(shape)

        mosaic = colormap is None and tint and not is_map
        if mosaic:
            array = Juno_JunoCam._reshape_for_mosaic(array, filter_names)

        result = Juno_JunoCam(array, _DEFAULT_UPWARD,
                              Juno_JunoCam._default_tint(filter_names))
        result.mosaic = mosaic
        result.filter_names = filter_names
        return result

    def apply_colormap(self, array, valid_limits, invalid_mask=None, *, layer=None,
                       **kwargs):
        """Apply a colormap to up to three grayscale images.

        Produces a 3-D array with one band (grayscale) or three bands (RGB), in axis order
        (line, sample, channel). Values are scaled zero to one.

        This override handles the case where a JunoCam image uses multiple filters and the
        strips are therefore tinted different colors by default. It ensures that no
        colormap is applied at this phase of the processing.

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

        if layer is None:
            return default_apply_colormap(array, valid_limits, invalid_mask,
                                          default_tint=self.default_tint, **kwargs)

        # `layer` shows up only for the mosaic option
        tint = _DEFAULT_TINTS[self.filter_names[layer]]
        return default_apply_colormap(array[layer], valid_limits, invalid_mask,
                                      default_tint=tint, **kwargs)

    @staticmethod
    def apply_mosaic(arrays_rgb, **kwargs):
        """Assemble the mosaic, applying the proper tint to each band.

        Parameters:
            arrays_rgb (list[array]): Arrays for the separate filters in the order given
                in the file, each of shape (frames * :data:`_HEIGHT`, :data:`_WIDTH`, 3)
                or, for a band tinted a neutral gray, (frames * :data:`_HEIGHT`,
                :data:`_WIDTH`, 1).
            **kwargs: Additional input options, ignored here.

        Returns:
            array: The array re-assembled to its original shape,
            (frames * bands * :data:`_HEIGHT`, :data:`_WIDTH`, 3), with the frames for
            each filter interleaved as they appear in the file.
        """

        # The METHANE channel shape might not match RED, GREEN, and BLUE
        arrays_rgb = [np.broadcast_to(a, a.shape[:-1] + (3,)) for a in arrays_rgb]

        array = np.array(arrays_rgb)        # (bands, frames*_HEIGHT, _WIDTH, 3)

        bands = len(arrays_rgb)
        frames = array.shape[1] // _HEIGHT
        array = array.reshape((bands, frames, _HEIGHT, _WIDTH, 3))
        array = array.swapaxes(0, 1)        # (frames, bands, _HEIGHT, _WIDTH, 3)
        array = array.reshape((frames * bands * _HEIGHT, _WIDTH, 3))
        return array

    @staticmethod
    def _default_tint(filter_names):
        if len(filter_names) == 1:
            return _DEFAULT_TINTS[filter_names[0]]
        return None

    @staticmethod
    def _reshape_for_mosaic(array, filter_names):
        """Reshape a stacked array so that each filter occupies its own band.

        Parameters:
            array (array): The image array as read from the file, of shape
                (frames * bands * :data:`_HEIGHT`, :data:`_WIDTH`), with the frames for
                each filter interleaved.
            filter_names (list[str]): The filter names in the order they appear in the
                file; its length defines the number of bands.

        Returns:
            array: The array reshaped to (bands, frames * :data:`_HEIGHT`,
            :data:`_WIDTH`), with every frame of a given filter contiguous.
        """

        bands = len(filter_names)
        frames = array.shape[0] // (_HEIGHT * bands)
        array = array.reshape(frames, bands, _HEIGHT, _WIDTH)
        array = array.swapaxes(0, 1)    # (bands, frames, _HEIGHT, _WIDTH)
        array = array.reshape(bands, frames * _HEIGHT, _WIDTH)
        return array


##########################################################################################
