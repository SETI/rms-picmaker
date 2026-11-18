##########################################################################################
# picmaker/instruments/hst_wfpc2.py
##########################################################################################
"""HST WFPC2 detector and reader."""

import re
import warnings

import numpy as np
from astropy.io.fits.verify import VerifyWarning

from picmaker.instruments import ImageData, tint_by_nm
from picmaker.instruments._hst_support import get_hst_filter_digits

_DEFAULT_UPWARD = True
_IS_UNDIAGNOSTIC = re.compile(r'(|F130LP|F165LP|F606W|FQCH4.*|POL.*)$')
_IS_SCIENCE_DATA = re.compile(r'.*_[cd]0[fm](?![a-z]|\d).*', re.I)


class HST_WFPC2(ImageData):
    """HST WFPC2 detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, filepath, obj=None, mosaic=False, retint=1., **kwargs):
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

        # Favor `obj` over `mosaic`
        if obj is None and mosaic and array.shape[0] > 1:
            # Place each plane by its detector number, leaving any missing detectors
            # zero-filled
            cube = np.zeros((4,) + array.shape[-2:], dtype=array.dtype)
            for b, det in enumerate(detectors):
                cube[det - 1] = array[b]
            array = cube
        else:
            array = array[obj or 0]  # forward IndexError

        return HST_WFPC2(array, _DEFAULT_UPWARD, default_tint)

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


##########################################################################################
