##########################################################################################
# picmaker/instruments/nh_lorri.py
##########################################################################################
"""New Horizons LORRI detector and reader."""

import pdsparser                # noqa
import astropy.io.fits as pyfits  # noqa

from picmaker.instruments import ImageData, register_instrument
from picmaker.instruments._pds3_support import read_pds3_image_array

_DEFAULT_UPWARD = True


class NH_LORRI(ImageData):
    """New Horizons LORRI detector and reader."""

    @staticmethod
    def detect_in_pds3(label, **kwargs):
        """Extract New Horizons LORRI data from a parsed :class:`pdsparser.Pds3Label`.

        Parameters:
            label (:class:`pdsparser.Pds3Label`): A parsed PDS3 label.
            **kwargs: Additional input options, ignored here.

        Returns:
            (NH_LORRI or None): Instrument subclass if ``label`` describes a New Horizons
            LORRI product; ``None`` otherwise.
        """

        try:
            if label['INSTRUMENT_HOST_ID'] != 'NH':
                return None
            if label['INSTRUMENT_ID'] != 'LORRI':
                return None
        except KeyError:
            return None

        array = read_pds3_image_array(label)
        return ImageData(array, _DEFAULT_UPWARD, None)

    @staticmethod
    def detect_in_fits(hdulist, **kwargs):
        """Extract New Horizons LORRI data from an open :class:`pyfits.HDUList`.

        Parameters:
            hdulist (:class:`pyfits.HDUList`): The HDUList of an opened FITS file.
            **kwargs: Additional input options, ignored here.

        Returns:
            (NH_LORRI or None): Instrument subclass if ``hdulist`` describes a New
            Horizons LORRI product; ``None`` otherwise.
        """

        try:
            if hdulist[0].header['HOSTNAME'] != 'NEW HORIZONS':
                return None
            if hdulist[0].header['INSTRU'].rstrip() != 'lor':
                return None
        except (KeyError, IndexError):
            return None

        return ImageData(hdulist[0].data, _DEFAULT_UPWARD, None)


register_instrument(NH_LORRI)

##########################################################################################
