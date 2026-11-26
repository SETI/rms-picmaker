##########################################################################################
# picmaker/instruments/hst_foc.py
##########################################################################################
"""HST FOC detector and reader."""

import re

import numpy as np

from picmaker.instruments import ImageData, tint_by_nm
from picmaker.instruments._hst_support import (
    get_detector_cube,
    get_dq_mask,
    get_hst_filter_digits,
)

_DEFAULT_UPWARD = True

# Clear apertures, neutral-density, prism, and polarizer filters carry no diagnostic
# wavelength.
_IS_UNDIAGNOSTIC = re.compile(r'(|CLEAR.*|.*ND|PRISM.*|POL.*)$')

_IS_SCIENCE_DATA = re.compile(r'.*_[cd]0[fm](?![a-z]|\d).*', re.I)

# FOC's only data quality file is _q0f/_q0m, for the raw _d0f/_d0m file. The calibrated
# products are dezoomed and geometrically corrected, so they get no mask. (FOC's _c1f is a
# calibrated image, not a data quality file as it is for WF/PC and WFPC2.)
_DQ_CODES = {'d0': 'q0'}


class HST_FOC(ImageData):
    """HST FOC detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, filepath, retint=None, hst_dq=None, logger=None,
                       **kwargs):
        """Extract HST FOC data from an open HDUList.

        Parameters:
            hdulist (HDUList): The HDUList of the FITS file.
            filepath (str or Path): The path to this FITS file.
            retint (float, optional): Factor by which to scale wavelengths for purposes of
                tinting.
            hst_dq (str or Path, optional): Directory containing the "_q0f" or "_q0m"
                data quality file that goes with a raw "_d0f" or "_d0m" file. If None,
                the directory of this file is used. If the data quality file is found,
                every pixel with a nonzero data quality value is set in both `hmask` and
                `imask`. Calibrated FOC images are never masked.
            logger (Logger or PdsLogger, optional): Logger for reporting whether a data
                quality file was used.
            **kwargs: Additional input options, ignored here.

        Returns:
            HST_FOC or None: Instrument subclass if the file describes an HST FOC product;
            None otherwise.
        """

        try:
            if hdulist[0].header['INSTRUME'] != 'FOC':
                return None
        except (KeyError, IndexError):
            return None

        # Science data is in the _c0f, _d0f, _c0m, and _d0m files
        is_science_data = _IS_SCIENCE_DATA.fullmatch(str(filepath))
        default_tint = None
        if is_science_data:
            filters = [hdulist[0].header.get(f'FILTNAM{k}', '') for k in (1, 2, 3, 4)]
            filters = [f for f in filters if not _IS_UNDIAGNOSTIC.match(f)]
            lambda_nms = [get_hst_filter_digits(f) for f in filters]
            lambda_nms = [nm for nm in lambda_nms if nm]
            if lambda_nms:
                default_tint = tint_by_nm(np.mean(lambda_nms))

        # Both file layouts ("waiver" _d0f, multi-extension _d0m) are reduced to the same
        # cube of planes; FOC has a single detector, so use the first plane
        (array, _) = get_detector_cube(hdulist, filepath)

        # Load the data quality mask (_q0f/_q0m) of a raw file, if present
        dq_mask = get_dq_mask(filepath, array.shape, hst_dq, logger, dq_codes=_DQ_CODES)

        array = array[0]
        if dq_mask is None:
            (hmask, imask) = (None, None)
        else:
            (hmask, imask) = (dq_mask[0], dq_mask[0].copy())

        return HST_FOC(array, _DEFAULT_UPWARD, default_tint, hmask=hmask, imask=imask)


##########################################################################################
