##########################################################################################
# picmaker/instruments/hst_wfpc.py
##########################################################################################
"""HST WF/PC detector and reader."""

import re
import warnings

import numpy as np
from astropy.io.fits.verify import VerifyWarning

from picmaker.instruments import ImageData, tint_by_nm
from picmaker.instruments._hst_support import get_hst_filter_digits

_DEFAULT_UPWARD = True
_IS_UNDIAGNOSTIC = re.compile(r'(|POL.*|.*ND)$')
_IS_SCIENCE_DATA = re.compile(r'.*_[cd]0f(?![a-z]|\d).*', re.I)


class HST_WFPC(ImageData):
    """HST WF/PC detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, filepath, obj=None, mosaic=False, retint=1., **kwargs):
        """Extract HST WFPC2 data from an open HDUList.

        Parameters:
            hdulist (HDUList): The HDUList of the FITS file.
            filepath (str or Path): The path to this FITS file.
            obj (int, optional): The HDU index (starting at 0) of the image array. If not
                specified, the first image array in the file is used.
            mosaic (bool, optional): True to enable the construction of a mosaic of the
                four WF or PC detectors; False to return the array from just a single
                selected detector.
            retint (float, optional): Factor by which to scale wavelengths for purposes of
                tinting.
            **kwargs: Additional input options, ignored here.

        Returns:
            HST_WFPC or None: Instrument subclass if the file describes an HST WF/PC
            product; None otherwise.
        """

        try:
            if hdulist[0].header['INSTRUME'] != 'WFPC':
                return None
        except (KeyError, IndexError):
            return None

        # Science data is in the _c0f and _d0f files
        is_science_data = _IS_SCIENCE_DATA.fullmatch(str(filepath))
        default_tint = None
        if is_science_data:
            header = hdulist[0].header
            filters = [header.get('FILTNAM1', ''), header.get('FILTNAM2', '')]
            filters = [f for f in filters if not _IS_UNDIAGNOSTIC.match(f)]
            lambda_nms = [get_hst_filter_digits(f) for f in filters]
            if lambda_nms:
                default_tint = tint_by_nm(np.mean(lambda_nms) * retint)

        # Select detector(s), allowing for the possibility of fewer than four
        array = hdulist[0].data
        array = array[np.newaxis] if array.ndim == 2 else array

        # Favor `obj` over `mosaic`
        if obj is None and mosaic and array.shape[0] > 1:
            # Handle case of fewer than 4 images; otherwise, the array is already fine
            if array.shape[0] < 4:
                # The detector selection reads the group-parameters table (HDU[1]), which
                # trips a benign astropy VerifyWarning about a non-standard TDISP keyword
                # in the archived file; read it once here with just that warning
                # suppressed.
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', VerifyWarning)
                    detectors = hdulist[1].data['DETECTOR']

                new_array = np.zeros((4,) + array.shape[-2:])
                for b, det in enumerate(detectors):
                    new_array[(det - 1) % 4] = array[b]  # 1-4 for WF, 5-8 for PC
                array = new_array
        else:
            array = array[obj or 0]     # forward IndexError

        return HST_WFPC(array, _DEFAULT_UPWARD, default_tint)

    def apply_mosaic(self, arrays_rgb, **kwargs):
        """Assemble WF/PC's four WF or PC detectors into a 2x2 mosaic.

        Parameters:
            arrays_rgb (list[array]): Per-detector RGB arrays (usually length 4), each
                indexed (lines, samples, color).
            **kwargs: Additional input options, ignored here.

        Returns:
            array: The assembled 2x2 mosaic, with shape (2*lines, 2*samples, colors).
        """

        # Note that images all display upward. This is inverted afterward.
        quads = [np.rot90(arrays_rgb[b], -b) for b in range(len(arrays_rgb))]

        # Assemble directly in display orientation with W1/P5 at upper right
        (nl, ns, nc) = quads[0].shape
        mosaic = np.empty((2 * nl, 2 * ns, nc))
        mosaic[-nl:, -ns:] = quads[0]   # W1 or P5
        mosaic[-nl:, :ns ] = quads[1]   # W2 or P6
        mosaic[:nl , :ns ] = quads[2]   # W3 or P7
        mosaic[:nl , -ns:] = quads[3]   # W4 or P8

        return mosaic


##########################################################################################
