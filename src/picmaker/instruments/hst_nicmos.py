##########################################################################################
# picmaker/instruments/hst_nicmos.py
##########################################################################################
"""HST NICMOS detector and reader."""

import astropy.io.fits as pyfits  # noqa

from picmaker.instruments import ImageData, register_instrument
from picmaker.instruments._hst_support import get_hst_filter_digits, hst_tint_from_nm

_DEFAULT_UPWARD = True


class HST_NICMOS(ImageData):
    """HST NICMOS detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, obj=None, **kwargs):
        """Extract HST NICMOS data from an open :class:`pyfits.HDUList`.

        Parameters:
            hdulist (:class:`pyfits.HDUList`): The HDUList of an opened FITS file.
            obj (int, optional): An object index within the file; ignored for HST NICMOS
                images.
            **kwargs: Additional input options, ignored here.

        Returns:
            (HST_NICMOS or None): Instrument subclass if ``label`` describes a HST NICMOS
            product; ``None`` otherwise.
        """

        try:
            if hdulist[0].header['TELESCOP'] != 'HST':
                return None
            if hdulist[0].header['INSTRUME'][:3] != 'NIC':
                return None
        except (KeyError, IndexError):
            return None

        filter_name = hdulist.get('FILTER', '').rstrip()
        if filter_name[:3] == 'POL':
            default_tint = None
        else:
            wave = get_hst_filter_digits(filter_name)
            default_tint = hst_tint_from_nm(wave * 3.5)

        return ImageData(hdulist[0].data, _DEFAULT_UPWARD, default_tint)


register_instrument(HST_NICMOS)

##########################################################################################
