##########################################################################################
# picmaker/instruments/hst_foc.py
##########################################################################################
"""HST FOC detector and reader."""

import re

import numpy as np

from picmaker.instruments import ImageData, tint_by_nm
from picmaker.instruments._hst_support import get_hst_filter_digits

_DEFAULT_UPWARD = True

# Clear apertures, neutral-density, prism, and polarizer filters carry no diagnostic
# wavelength.
_IS_UNDIAGNOSTIC = re.compile(r'(|CLEAR.*|.*ND|PRISM.*|POL.*)$')

_IS_SCIENCE_DATA = re.compile(r'.*_[cd]0f(?![a-z]|\d).*', re.I)


class HST_FOC(ImageData):
    """HST FOC detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, filepath, retint=None, **kwargs):
        """Extract HST FOC data from an open HDUList.

        Parameters:
            hdulist (HDUList): The HDUList of the FITS file.
            filepath (str or Path): The path to this FITS file.
            retint (float, optional): Factor by which to scale wavelengths for purposes of
                tinting.
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

        # Science data is in the _c0f and _d0f files
        is_science_data = _IS_SCIENCE_DATA.fullmatch(str(filepath))
        default_tint = None
        if is_science_data:
            filters = [hdulist[0].header.get(f'FILTNAM{k}', '') for k in (1, 2, 3, 4)]
            filters = [f for f in filters if not _IS_UNDIAGNOSTIC.match(f)]
            lambda_nms = [get_hst_filter_digits(f) for f in filters]
            lambda_nms = [nm for nm in lambda_nms if nm]
            if lambda_nms:
                default_tint = tint_by_nm(np.mean(lambda_nms))

        return HST_FOC(hdulist[0].data, _DEFAULT_UPWARD, default_tint)


##########################################################################################
