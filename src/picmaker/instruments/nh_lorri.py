##########################################################################################
# picmaker/instruments/nh_lorri.py
##########################################################################################
"""New Horizons LORRI detector and reader."""

from picmaker.instruments import ImageData
from picmaker.instruments._pds3_support import read_pds3_image_array

_DEFAULT_UPWARD = True


class NH_LORRI(ImageData):
    """New Horizons LORRI detector and reader."""

    @staticmethod
    def detect_in_pds3(label, filepath, **kwargs):
        """Extract New Horizons LORRI data from a parsed Pds3Label.

        Parameters:
            label (Pds3Label): A parsed PDS3 label.
            filepath (str or Path): The path to this PDS3 label.
            **kwargs: Additional input options, ignored here.

        Returns:
            NH_LORRI or None: Instrument subclass if `label` describes a New Horizons
            LORRI product; None otherwise.
        """

        try:
            if label['INSTRUMENT_HOST_ID'] != 'NH':
                return None
            if label['INSTRUMENT_ID'] != 'LORRI':
                return None
        except KeyError:
            return None

        array = read_pds3_image_array(label, filepath, **kwargs)
        return NH_LORRI(array, _DEFAULT_UPWARD, None)

    @staticmethod
    def detect_in_fits(hdulist, filepath, **kwargs):
        """Extract New Horizons LORRI data from an open HDUList.

        Parameters:
            hdulist (HDUList): The HDUList of an opened FITS file.
            filepath (str or Path): The path to this FITS file.
            **kwargs: Additional input options, ignored here.

        Returns:
            NH_LORRI or None: Instrument subclass if `hdulist` describes a New Horizons
            LORRI product; None otherwise.
        """

        try:
            if hdulist[0].header['HOSTNAME'] != 'NEW HORIZONS':
                return None
            if hdulist[0].header['INSTRU'].rstrip() != 'lor':
                return None
        except (KeyError, IndexError):
            return None

        return NH_LORRI(hdulist[0].data, _DEFAULT_UPWARD, None)


##########################################################################################
