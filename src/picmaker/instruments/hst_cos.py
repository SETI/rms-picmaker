##########################################################################################
# picmaker/instruments/hst_cos.py
##########################################################################################
"""HST COS detector and reader."""

from picmaker.instruments import ImageData
from picmaker.instruments._fits_support import get_fits_image_hdu

_DEFAULT_UPWARD = True


class HST_COS(ImageData):
    """HST COS detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, filepath, obj=None, pointers=None, **kwargs):
        """Extract HST COS data from an open HDUList.

        Parameters:
            hdulist (HDUList): The HDUList of the FITS file.
            filepath (str or Path): The path to this FITS file.
            obj (int, optional): The HDU index (starting at 0) of the image array. If not
                specified, the first image array in the file is used.
            pointers (str or list[str], optional): Name or alternative list of names of
                the IMAGE object within the HDU.
            **kwargs: Additional input options, ignored here.

        Returns:
            HST_COS or None: Instrument subclass if the file describes an HST COS product;
            None otherwise.
        """

        try:
            if hdulist[0].header['TELESCOP'] != 'HST':
                return None
            if hdulist[0].header['INSTRUME'] != 'COS':
                return None
        except (KeyError, IndexError):
            return None

        # COS NUV imaging uses a broadband mirror (MIRRORA/MIRRORB) rather than a
        # wavelength filter, so there is no diagnostic wavelength for a default tint.
        hdu = get_fits_image_hdu(hdulist, obj=obj, pointers=pointers)
        return HST_COS(hdu.data, _DEFAULT_UPWARD, None)


##########################################################################################
