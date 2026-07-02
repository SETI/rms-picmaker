##########################################################################################
# picmaker/instruments/hst_wfpc2.py
##########################################################################################
"""HST WFPC2 detector and reader."""

import re
import warnings

import astropy.io.fits as pyfits  # noqa
import numpy as np
from astropy.io.fits.verify import VerifyWarning

from picmaker.instruments import ImageData, register_instrument, tint_by_nm
from picmaker.instruments._hst_support import get_hst_filter_digits

_DEFAULT_UPWARD = True
_IS_UNDIAGNOSTIC = re.compile(r'(|F130LP|F165LP|F606W|FQCH4.*|POL.*)$')
_IS_SCIENCE_DATA = re.compile(r'.*_[cd]0f\.[a-z]+$', re.I)

class HST_WFPC2(ImageData):
    """HST WFPC2 detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, filepath, obj=None, mosaic=False, **kwargs):
        """Extract HST WFPC2 data from an open :class:`pyfits.HDUList`.

        Parameters:
            hdulist (:class:`pyfits.HDUList`): The HDUList of an opened FITS file.
            filepath (str or pathlib.Path): The path to this FITS file.
            obj (int, optional): The HDU index (starting at 0) of the image array. If not
                specified, the first image array in the file is used.
            mosaic (bool, optional): True to enable the construction of a mosaic of the
                four WFPC2 detectors; False to return the array from just a single
                selected detector.
            **kwargs: Additional input options, ignored here.

        Returns:
            (HST_WFPC2 or None): Instrument subclass if the file describes an HST WFPC2
            product; ``None`` otherwise.
        """

        try:
            if hdulist[0].header['TELESCOP'] != 'HST':
                return None
            if hdulist[0].header['INSTRUME'] != 'WFPC2':
                return None
        except (KeyError, IndexError):
            return None

        # Science data is in the _c0f and _d0f files
        is_science_data = _IS_SCIENCE_DATA.fullmatch(str(filepath))
        if is_science_data:
            header = hdulist[0].header
            filters = [header.get('FILTNAM1', ''), header.get('FILTNAM2', '')]
            filters = [f for f in filters if not _IS_UNDIAGNOSTIC.match(f)]

            # FQUVN has four nearby bands; this is the mean
            lambda_nms = [(387 if f[:5] == 'FQUVN' else get_hst_filter_digits(f))
                          for f in filters]
            if lambda_nms:
                default_tint = tint_by_nm(np.mean(lambda_nms))
            else:
                default_tint = None
        else:
            default_tint = None

        # Select detector(s), allowing for the possibility of fewer than four
        array = hdulist[0].data

        # The detector selection reads the group-parameters table (HDU[1]), which trips a
        # benign astropy VerifyWarning about a non-standard TDISP keyword in the archived
        # file; read it once here with just that warning suppressed.
        detectors = None
        if mosaic or obj is not None:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', VerifyWarning)
                detectors = hdulist[1].data['DETECTOR']

        if mosaic and obj is None:      # `obj` takes precedence over `mosaic`
            if len(detectors) < 4:
                if array.ndim == 2:
                    array = array.reshape((1,) + array.shape)
                new_array = np.zeros((4,) + array.shape[-2:])
                for b, det in enumerate(detectors):
                    new_array[det - 1] = array[b]
                array = new_array
        elif obj is None:
            array = array[0]
        else:
            indx = list(detectors).index(obj + 1)   # forward IndexError
            array = array[indx]

        return HST_WFPC2(array, _DEFAULT_UPWARD, default_tint)

    def apply_mosaic(self, arrays_rgb, **kwargs):
        """Assemble WFPC2's four detectors (PC1, WF2, WF3, WF4) into a 2x2 mosaic.

        Parameters:
            arrays_rgb (list[np.ndarray]): Per-detector RGB arrays (usually length 4),
                each indexed ``(lines, samples, color)``.
            **kwargs: Additional input options, ignored here.

        Returns:
            (np.ndarray): The assembled 2x2 mosaic, with shape ``(2*lines, 2*samples,
            colors)``.
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


register_instrument(HST_WFPC2)

##########################################################################################
