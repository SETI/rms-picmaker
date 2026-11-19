##########################################################################################
# picmaker/instruments/hst_wfpc2.py
##########################################################################################
"""HST WFPC2 detector and reader."""

import pathlib
import re
import warnings

import astropy.io.fits as pyfits
import numpy as np
from astropy.io.fits.verify import VerifyWarning

from picmaker.instruments import ImageData, tint_by_nm
from picmaker.instruments._hst_support import get_hst_filter_digits

_DEFAULT_UPWARD = True
_IS_UNDIAGNOSTIC = re.compile(r'(|F130LP|F165LP|F606W|FQCH4.*|POL.*)$')
_IS_SCIENCE_DATA = re.compile(r'.*_[cd]0[fm](?![a-z]|\d).*', re.I)

# Splits a data file name around its suffix code, e.g. "u2tf0504t_c0f.fits" ->
# ("u2tf0504t", "c", "0", "f", ".fits"); the first group is greedy so the last match wins
_DATA_FILENAME = re.compile(r'(.*)_([cd])(0)([fm])((?![a-z\d]).*)', re.I)


class HST_WFPC2(ImageData):
    """HST WFPC2 detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, filepath, obj=None, mosaic=False, retint=1.,
                       wfpc2_dq=None, logger=None, **kwargs):
        """Extract HST WFPC2 data from an open HDUList.

        Parameters:
            hdulist (HDUList): The HDUList of the FITS file.
            filepath (str or Path): The path to this FITS file.
            obj (int, optional): The HDU index (starting at 0) of the image array. If not
                specified, the first image array in the file is used.
            mosaic (bool, optional): True to enable the construction of a mosaic of the
                four WFPC2 detectors; False to return the array from just a single
                selected detector.
            retint (float, optional): Factor by which to scale wavelengths for purposes of
                tinting.
            wfpc2_dq (str or Path, optional): Directory containing the data quality file
                that goes with this file: "_c1f" or "_c1m" for a "_c0f" or "_c0m" file;
                "_q0f" or "_q0m" for a "_d0f" or "_d0m" file. If None, the directory of
                this file is used. If the data quality file is found, every pixel with a
                nonzero data quality value is set in both `hmask` and `imask`.
            logger (Logger or PdsLogger, optional): Logger for reporting whether a data
                quality file was used.
            **kwargs: Additional input options, ignored here.

        Returns:
            HST_WFPC2 or None: Instrument subclass if the file describes an HST WFPC2
            product; None otherwise.
        """

        try:
            if hdulist[0].header['TELESCOP'] != 'HST':
                return None
            if hdulist[0].header['INSTRUME'] != 'WFPC2':
                return None
        except (KeyError, IndexError):
            return None

        # Science data is in the _c0f, _d0f, _c0m, and _d0m files
        is_science_data = _IS_SCIENCE_DATA.fullmatch(str(filepath))
        default_tint = None
        if is_science_data:
            header = hdulist[0].header
            filters = [header.get('FILTNAM1', ''), header.get('FILTNAM2', '')]
            filters = [f for f in filters if not _IS_UNDIAGNOSTIC.match(f)]

            # FQUVN has four nearby bands; this is the mean
            lambda_nms = [(387 if f[:5] == 'FQUVN' else get_hst_filter_digits(f))
                          for f in filters]
            lambda_nms = [nm for nm in lambda_nms if nm]
            if lambda_nms:
                default_tint = tint_by_nm(np.mean(lambda_nms) * retint)

        # Both file layouts are reduced to the same detector cube plus a list of the
        # detector number (1-4) of each plane; everything after that is shared.
        (array, detectors) = _get_detector_cube(hdulist, filepath)

        # Load the matching data quality mask, if the file is present
        dq_mask = _get_dq_mask(filepath, array.shape, wfpc2_dq, logger)

        # Favor `obj` over `mosaic`. The mask planes are selected exactly like the data.
        if obj is None and mosaic and array.shape[0] > 1:
            array = _place_by_detector(array, detectors)
            if dq_mask is not None:
                dq_mask = _place_by_detector(dq_mask, detectors)
        else:
            array = array[obj or 0]  # forward IndexError
            if dq_mask is not None:
                dq_mask = dq_mask[obj or 0]

        (hmask, imask) = (None, None) if dq_mask is None else (dq_mask, dq_mask.copy())
        return HST_WFPC2(array, hmask, imask, _DEFAULT_UPWARD, default_tint)

    def apply_mosaic(self, arrays_rgb, **kwargs):
        """Assemble WFPC2's four detectors (PC1, WF2, WF3, WF4) into a 2x2 mosaic.

        Parameters:
            arrays_rgb (list[array]): Per-detector RGB arrays (usually length 4), each
                indexed (lines, samples, color).
            **kwargs: Additional input options, ignored here.

        Returns:
            array: The assembled 2x2 mosaic, with shape (2*lines, 2*samples, colors).
        """

        # Note that images all display upward. This is inverted afterward.
        quads = [np.rot90(arrays_rgb[b], -b) for b in range(len(arrays_rgb))]

        # Assemble directly in display orientation: PC1 lower-right, WF2 lower-left, WF3
        # upper-left, WF4 upper-right (before inversion).
        (nl, ns, nc) = quads[0].shape
        mosaic = np.empty((2 * nl, 2 * ns, nc))
        mosaic[-nl:, -ns:] = quads[0]   # PC1
        mosaic[-nl:, :ns ] = quads[1]   # WF2
        mosaic[:nl , :ns ] = quads[2]   # WF3
        mosaic[:nl , -ns:] = quads[3]   # WF4

        return mosaic


def _get_detector_cube(hdulist, filepath):
    """Return the WFPC2 detector cube and the detector number of each of its planes.

    WFPC2 files come in two layouts holding the same content:

    * "Waiver" FITS (_c0f etc.): the PRIMARY HDU holds a (n, lines, samples) cube, and
      HDU[1] is a group-parameters table whose DETECTOR column gives the detector of
      each plane.
    * Multi-extension FITS (_c0m etc.): the PRIMARY HDU is empty, and each detector is
      in its own image extension, which carries a DETECTOR keyword.

    Parameters:
        hdulist (HDUList): The HDUList of the FITS file.
        filepath (str or Path): The path to this FITS file.

    Returns:
        tuple[array, list[int]]: The (n, lines, samples) detector cube and the
        detector number (1-4) of each of its n planes.

    Raises:
        ValueError: If the file contains no image data.
    """

    array = hdulist[0].data

    # Multi-extension layout
    if array is None:
        hdus = [hdu for hdu in hdulist[1:] if hdu.is_image and hdu.data is not None]
        if not hdus:
            raise ValueError(f'No WFPC2 image data found in {filepath}')
        array = np.stack([hdu.data for hdu in hdus])
        detectors = [hdu.header.get('DETECTOR', b + 1) for b, hdu in enumerate(hdus)]
        return (array, detectors)

    # Waiver layout
    array = array[np.newaxis] if array.ndim == 2 else array

    # Reading the group-parameters table trips a benign astropy VerifyWarning about a
    # non-standard TDISP keyword in the archived files; suppress just that warning.
    detectors = list(range(1, array.shape[0] + 1))
    if len(hdulist) > 1 and not hdulist[1].is_image:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', VerifyWarning)
            columns = hdulist[1].columns.names
            if 'DETECTOR' in columns:
                detectors = [int(d) for d in hdulist[1].data['DETECTOR']]

    return (array, detectors)


def _place_by_detector(cube, detectors):
    """Expand a detector cube to all four detectors, placing each plane by its detector
    number (1-4) and leaving any missing detectors zero (or False)."""

    result = np.zeros((4,) + cube.shape[-2:], dtype=cube.dtype)
    for b, det in enumerate(detectors):
        result[det - 1] = cube[b]
    return result


def _get_dq_path(filepath, wfpc2_dq=None):
    """The path to the data quality file that goes with a WFPC2 science file.

    Parameters:
        filepath (str or Path): Path to a "_c0f", "_c0m", "_d0f", or "_d0m" file.
        wfpc2_dq (str or Path, optional): Directory of the data quality file; None for
            the directory of `filepath`.

    Returns:
        Path or None: The "_c1f", "_c1m", "_q0f", or "_q0m" path, preserving the case of
        the original name; None if `filepath` is not one of the science file types.
    """

    filepath = pathlib.Path(filepath)
    match = _DATA_FILENAME.fullmatch(filepath.name)
    if not match:
        return None

    (head, kind, zero, layout, tail) = match.groups()
    if kind in 'cC':
        code = kind + '1'                                   # c0 -> c1
    else:
        code = ('q' if kind == 'd' else 'Q') + zero         # d0 -> q0

    directory = pathlib.Path(wfpc2_dq) if wfpc2_dq else filepath.parent
    return directory / f'{head}_{code}{layout}{tail}'


def _get_dq_mask(filepath, shape, wfpc2_dq=None, logger=None):
    """Read the data quality file for a WFPC2 science file as a boolean mask.

    Parameters:
        filepath (str or Path): Path to the science file.
        shape (tuple[int, int, int]): Shape of the science file's detector cube.
        wfpc2_dq (str or Path, optional): Directory of the data quality file; None for
            the directory of `filepath`.
        logger (Logger or PdsLogger, optional): Logger for a debug message.

    Returns:
        array[bool] or None: A detector cube that is True wherever the data quality value
        is nonzero; None if `filepath` has no data quality counterpart or the file is not
        found.

    Raises:
        ValueError: If the data quality cube does not match the science cube's shape.
    """

    dq_path = _get_dq_path(filepath, wfpc2_dq)
    if dq_path is None or not dq_path.is_file():
        if dq_path is not None:
            logger and logger.debug('WFPC2 data quality file not found', dq_path)
        return None

    with pyfits.open(dq_path) as dq_hdulist:
        (dq, _) = _get_detector_cube(dq_hdulist, dq_path)
        mask = np.asarray(dq != 0)

    if mask.shape != tuple(shape):
        raise ValueError(f'WFPC2 data quality file {dq_path} has shape {mask.shape}; '
                         f'expected {tuple(shape)}')

    logger and logger.debug('Using WFPC2 data quality file', dq_path)
    return mask


##########################################################################################
