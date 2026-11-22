##########################################################################################
# picmaker/instruments/hst_nicmos.py
##########################################################################################
"""HST NICMOS detector and reader."""

from picmaker.instruments import ImageData, tint_by_nm
from picmaker.instruments._fits_support import get_fits_image_hdu
from picmaker.instruments._hst_support import (
    get_hst_filter_digits,
    get_sci_dq_mask,
    is_science_hdu,
    split_mask,
)

_DEFAULT_UPWARD = True
_DEFAULT_RETINT = 0.4

# Flag  Condition / Meaning
# 0     No known problems
# 1     Reed-Solomon decoding error in telemetry
# 2     Poor or uncertain linearity correction
# 4     Poor or uncertain dark correction
# 8     Poor or uncertain flat-field correction
# 16    Pixel affected by "grot" (particulate debris) on the detector
# 32    Defective (hot or cold) pixel
# 64    Saturated pixel
# 128   Missing data in telemetry
# 256   Bad pixel determined during calibration (calnica)
# 512   Pixel contains cosmic ray
# 1024  Pixel contains astrophysical source
# 2048  Pixel has detectable signal in the 0th readout
# 4096  Cosmic ray detected by MultiDrizzle (or User flag in earlier pipelines)
# 8192  User flag (reserved for manual masking)
# 16384 Curvature in detector response (or Reserved in earlier pipelines)

# DQ flag bits that do not mask a pixel: 1024 = pixel contains an astrophysical source
_DQ_IGNORE = 1024

class HST_NICMOS(ImageData):
    """HST NICMOS detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, filepath, obj=None, pointers=None, retint=None, **kwargs):
        """Extract HST NICMOS data from an open HDUList.

        Parameters:
            hdulist (HDUList): The HDUList of the FITS file.
            filepath (str or Path): The path to this FITS file.
            obj (int, optional): The HDU index (starting at 0) of the image array. If not
                specified, the first image array in the file is used.
            pointers (str or list[str], optional): Name or alternative list of names of
                the IMAGE object within the HDU.
            retint (float, optional): Factor by which to scale wavelengths for purposes of
                tinting.
            **kwargs: Additional input options, ignored here.

        If the image comes from a science ("SCI") HDU, the matching "DQ" extension in the
        same file supplies `hmask` and `imask`: every pixel with a nonzero data quality
        value is set in both, except where the value is 1024 (astrophysical source)
        alone.

        Returns:
            HST_NICMOS or None: Instrument subclass if the file describes an HST NICMOS
            product; None otherwise.
        """

        try:
            if hdulist[0].header['TELESCOP'] != 'HST':
                return None
            if hdulist[0].header['INSTRUME'] != 'NICMOS':
                return None
        except (KeyError, IndexError):
            return None

        hdu = get_fits_image_hdu(hdulist, obj=obj, pointers=pointers, **kwargs)
        default_tint = None
        if is_science_hdu(hdu):
            filter_name = hdulist[0].header['FILTER']
            if filter_name[:3] != 'POL':
                lambda_div_10 = get_hst_filter_digits(filter_name)
                if lambda_div_10 is not None:
                    lambda_nm = lambda_div_10 * 10.
                    retint = retint or _DEFAULT_RETINT
                    default_tint = tint_by_nm(lambda_nm * retint)

        (hmask, imask) = split_mask(get_sci_dq_mask(hdulist, hdu, _DQ_IGNORE))
        return HST_NICMOS(hdu.data, hmask, imask, _DEFAULT_UPWARD, default_tint)


##########################################################################################
