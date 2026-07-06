##########################################################################################
# picmaker/instruments/voyager_iss.py
##########################################################################################
"""Voyager ISS detector and reader."""

from picmaker.instruments import ImageData
from picmaker.instruments._pds3_support import read_pds3_image_array

_FILTER_TINTS = {
    'UV'    : (200,  60, 255),
    'VIOLET': (200, 120, 255),
    'BLUE'  : (110, 110, 255),
    'GREEN' : (110, 255, 110),
    'ORANGE': (255, 170, 100),
    'NAD'   : (110, 255, 110),
    'SODIUM': (110, 255, 110),
    'CH4_U' : (255,  60,  60),
    'CH4/U' : (255,  60,  60),
    'CH4_JS': (255,  60,  60),
    'CH4/JS': (255,  60,  60),
}

_DEFAULT_UPWARD = False


class Voyager_ISS(ImageData):
    """Voyager ISS detector and reader."""

    @staticmethod
    def detect_in_pds3(label, filepath, **kwargs):
        """Extract Voyager ISS data from a parsed Pds3Label.

        Parameters:
            label (Pds3Label): A parsed PDS3 label.
            filepath (str or Path): The path to this PDS3 label.
            **kwargs: Additional input options, ignored here.

        Returns:
            Voyager_ISS or None: Instrument subclass if `label` describes a Voyager ISS
            product; None otherwise.
        """

        try:
            if label['INSTRUMENT_HOST_NAME'][:7] != 'VOYAGER':
                return None
            if label['INSTRUMENT_ID'][:3] != 'ISS':
                return None
        except (KeyError, TypeError, IndexError):
            return None

        array = read_pds3_image_array(label, filepath, **kwargs)
        filter_name = label.get('FILTER_NAME', '')
        return Voyager_ISS(array, _DEFAULT_UPWARD, _FILTER_TINTS.get(filter_name, None))

    @staticmethod
    def detect_in_vicar(vic, filepath, **kwargs):
        """Extract Voyager ISS data from an open VicarImage.

        Voyager VICAR labels carry their identifying string in "LAB02" (a VGR prefix) and
        the filter name in characters 37-43 of "LAB03"; trailing spaces are stripped.

        Parameters:
            vic (VicarImage): A VicarImage object.
            filepath (str or Path): The path to this Vicar file.
            **kwargs: Additional input options, ignored here.

        Returns:
            Voyager_ISS or None: Instrument subclass if `vic` describes a Voyager ISS
            product; None otherwise.
        """

        try:
            if vic['LAB02'][:3] != 'VGR' or vic['LAB03'][1:9] != 'A CAMERA':
                return None
        except (IndexError, KeyError):
            return None

        try:
            filter_name = vic['LAB03'][37:43].rstrip()
        except (IndexError, KeyError):
            filter_name = ''

        return Voyager_ISS(vic.array[0], _DEFAULT_UPWARD,
                           _FILTER_TINTS.get(filter_name, None))


##########################################################################################
