##########################################################################################
# picmaker/instruments/hst_wfpc2.py
##########################################################################################
"""HST WFPC2 detector and reader."""

import re

import numpy as np

from picmaker.instruments import ImageData, tint_by_nm
from picmaker.instruments._hst_support import (
    get_detector_cube,
    get_dq_mask,
    get_hst_filter_digits,
    place_by_detector,
)

_DEFAULT_UPWARD = True
_IS_UNDIAGNOSTIC = re.compile(r'(|F130LP|F165LP|F606W|FQCH4.*|POL.*)$')
_IS_SCIENCE_DATA = re.compile(r'.*_[cd]0[fm](?![a-z]|\d).*', re.I)


class HST_WFPC2(ImageData):
    """HST WFPC2 detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, filepath, obj=None, mosaic=False, retint=1.,
                       hst_dq=None, logger=None, **kwargs):
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
            hst_dq (str or Path, optional): Directory containing the data quality file
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
        (array, detectors) = get_detector_cube(hdulist, filepath)

        # Load the matching data quality mask, if the file is present
        dq_mask = get_dq_mask(filepath, array.shape, hst_dq, logger)

        # Favor `obj` over `mosaic`. The mask planes are selected exactly like the data.
        if obj is None and mosaic and array.shape[0] > 1:
            array = place_by_detector(array, detectors)
            if dq_mask is not None:
                dq_mask = place_by_detector(dq_mask, detectors)
        else:
            array = array[obj or 0]  # forward IndexError
            if dq_mask is not None:
                dq_mask = dq_mask[obj or 0]

        (hmask, imask) = (None, None) if dq_mask is None else (dq_mask, dq_mask.copy())
        return HST_WFPC2(array, _DEFAULT_UPWARD, default_tint, hmask=hmask, imask=imask)

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


##########################################################################################
