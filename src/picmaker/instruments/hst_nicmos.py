##########################################################################################
# picmaker/instruments/hst_nicmos.py
##########################################################################################
"""HST NICMOS detector and reader."""

from picmaker.instruments import ImageData, tint_by_nm
from picmaker.instruments._fits_support import get_fits_image_hdu
from picmaker.instruments._hst_support import get_hst_filter_digits, is_science_hdu

_DEFAULT_UPWARD = True
_DEFAULT_RETINT = 0.4


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
        if is_science_hdu(hdu):
            filter_name = hdulist[0].header['FILTER']
            if filter_name[:3] == 'POL':
                default_tint = None
            else:
                lambda_div_10 = get_hst_filter_digits(filter_name)
                if lambda_div_10 is None:
                    default_tint = None
                else:
                    lambda_nm = lambda_div_10 * 10.
                    retint = retint or _DEFAULT_RETINT
                    default_tint = tint_by_nm(lambda_nm * retint)
        else:
            default_tint = None

        return HST_NICMOS(hdu.data, _DEFAULT_UPWARD, default_tint)


##########################################################################################
