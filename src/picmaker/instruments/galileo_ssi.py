##########################################################################################
# picmaker/instruments/galileo_ssi.py
##########################################################################################
"""Galileo SSI detector and reader."""

from picmaker.instruments import ImageData
from picmaker.instruments._pds3_support import read_pds3_image_array

_FILTER_NAMES = ['CLEAR', 'GREEN', 'RED', 'VIOLET', 'IR-7560', 'IR-9680', 'IR-7270',
                 'IR-8890']
_FILTER_TINTS = {
    'RED'    : (190, 130, 100),
    'GREEN'  : (110, 190, 110),
    'VIOLET' : (160, 100, 200),
    'IR-7270': (200, 100, 100),
    'IR-7560': (210,  80,  80),
    'IR-8890': (220,  60,  60),
    'IR-9680': (230,  40,  40),
}
_DEFAULT_UPWARD = False


class Galileo_SSI(ImageData):
    """Galileo SSI detector and reader."""

    @staticmethod
    def detect_in_pds3(label, filepath, **kwargs):
        """Extract Galileo SSI data from a parsed Pds3Label.

        Parameters:
            label (Pds3Label): A parsed PDS3 label.
            filepath (str or Path): The path to this PDS3 label.
            **kwargs: Additional input options, ignored here.

        Returns:
            Galileo_SSI or None: Instrument subclass if `label` describes a Galileo SSI
            product; None otherwise.
        """

        try:
            if label['SPACECRAFT_NAME'] != 'GALILEO ORBITER':
                return None
            if label['INSTRUMENT_NAME'] != 'SOLID STATE IMAGING SYSTEM':
                return None
        except (KeyError, TypeError, IndexError):
            return None

        array = read_pds3_image_array(label, filepath, **kwargs)
        filter_name = label.get('FILTER_NAME', '')
        return Galileo_SSI(array, _DEFAULT_UPWARD, _FILTER_TINTS.get(filter_name))

    @staticmethod
    def detect_in_vicar(vic, filepath, **kwargs):
        """Extract Galileo SSI data from an open VicarImage.

        Parameters:
            vic (VicarImage): A VicarImage object.
            filepath (str or Path): The path to this Vicar file.
            **kwargs: Additional input options, ignored here.

        Returns:
            Galileo_SSI or None: Instrument subclass if `vic` describes a Galileo SSI
            product; None otherwise.
        """

        try:
            if vic['MISSION'] != 'GALILEO':
                return None
            if vic['SENSOR'] != 'SSI':
                return None
        except KeyError:
            return None

        ifilter = vic.get('FILTER', 0)
        filter_name = _FILTER_NAMES[ifilter]  # ifilter is never out of range
        return Galileo_SSI(vic.array[0], _DEFAULT_UPWARD, _FILTER_TINTS.get(filter_name))


##########################################################################################
