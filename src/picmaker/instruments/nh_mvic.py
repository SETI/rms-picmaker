##########################################################################################
# picmaker/instruments/nh_mvic.py
##########################################################################################
"""New Horizons MVIC detector and reader."""

import pdsparser                # noqa
import astropy.io.fits as pyfits  # noqa

from picmaker.instruments import ImageData, register_instrument
from picmaker.instruments._pds3_support import read_pds3_image_array

_FILTER_TINTS = {
    'BLUE': (110, 110, 210),
    'RED' : (190, 100, 100),
    'NIR' : (210,  65,  45),
    'CH4' : (230,  35,  35),
}
_DEFAULT_UPWARD = True


class NH_MVIC(ImageData):
    """New Horizons MVIC detector and reader."""

    @staticmethod
    def detect_in_pds3(label, filepath, **kwargs):
        """Extract New Horizons MVIC data from a parsed Pds3Label.

        Parameters:
            label (Pds3Label): A parsed PDS3 label.
            filepath (str or Path): The path to this PDS3 label.
            **kwargs: Additional input options, ignored here.

        Returns:
            NH_MVIC or None: Instrument subclass if `label` describes a New Horizons MVIC
            product; None otherwise.
        """

        try:
            if label['INSTRUMENT_HOST_ID'] != 'NH':
                return None
            if label['INSTRUMENT_ID'] != 'MVIC':
                return None
        except KeyError:
            return None

        array = read_pds3_image_array(label)
        filter_name = label.get('FILTER_NAME', '')
        return NH_MVIC(array, _DEFAULT_UPWARD, _FILTER_TINTS.get(filter_name))

    @staticmethod
    def detect_in_fits(hdulist, filepath, **kwargs):
        """Extract New Horizons MVIC data from an open HDUList.

        Parameters:
            hdulist (HDUList): The HDUList of an opened FITS file.
            filepath (str or Path): The path to this FITS file.
            **kwargs: Additional input options, ignored here.

        Returns:
            NH_MVIC or None: Instrument subclass if `hdulist` describes a New Horizons
            MVIC product; None otherwise.
        """

        try:
            if hdulist[0].header['HOSTNAME'] != 'NEW HORIZONS':
                return None
            if hdulist[0].header['INSTRU'].rstrip() != 'mvi':
                return None
        except (KeyError, IndexError):
            return None

        filter_name = hdulist[0].header.get('FILTER', '')
        return NH_MVIC(hdulist[0].data, _DEFAULT_UPWARD, _FILTER_TINTS.get(filter_name))


register_instrument(NH_MVIC)

##########################################################################################
