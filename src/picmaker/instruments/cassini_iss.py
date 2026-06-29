##########################################################################################
# picmaker/instruments/cassini_iss.py
##########################################################################################
"""Cassini ISS detector and reader."""

import pdsparser    # noqa
import vicar        # noqa

from picmaker.instruments import ImageData, register_instrument
from picmaker.instruments._pds3_support import read_pds3_image_array

_DEFAULT_UPWARD = False


class Cassini_ISS(ImageData):
    """Cassini ISS detector and reader."""

    @staticmethod
    def detect_in_pds3(label, **kwargs):
        """Extract Cassini ISS data from a parsed :class:`pdsparser.Pds3Label`.

        Parameters:
            label (:class:`pdsparser.Pds3Label`): A parsed PDS3 label.
            **kwargs: Additional input options, ignored here.

        Returns:
            (Cassini_ISS or None): Instrument subclass if `label` describes a Cassini ISS
            product; ``None`` otherwise.
        """

        try:
            if label['INSTRUMENT_HOST_NAME'][:7] != 'CASSINI':
                return None
            if label['INSTRUMENT_ID'][:3] != 'ISS':
                return None
        except (KeyError, TypeError, IndexError):
            return None

        array = read_pds3_image_array(label)
        filters = label.get('FILTER_NAME', ('', ''))
        return ImageData(array, _DEFAULT_UPWARD, Cassini_ISS._default_tint(*filters))

    @staticmethod
    def detect_in_vicar(vic, **kwargs):
        """Extract Cassini ISS data from an open :class:`vicar.VicarImage`.

        Parameters:
            vic (:class:`vicar.VicarImage`): A VicarImage object.
            **kwargs: Additional input options, ignored here.

        Returns:
            (Cassini_ISS or None): Instrument subclass if ``vic`` describes a Cassini ISS
            product; ``None`` otherwise.
        """

        try:
            if vic['INSTRUMENT_HOST_NAME'] != 'CASSINI ORBITER':
                return None
            if vic['INSTRUMENT_ID'] not in {'ISSNA', 'ISSWA'}:
                return None
        except (IndexError, KeyError):
            return None

        filters = vic.get('FILTER_NAME', ('', ''))
        return ImageData(vic.array, _DEFAULT_UPWARD, Cassini_ISS._default_tint(*filters))

    @staticmethod
    def _default_tint(filter1, filter2):
        """The default tint for a Cassini ISS image."""

        filter_name = filter1 + '+' + filter2

        if 'IR' in filter_name:
            return (200, 80, 80)
        elif 'UV' in filter_name:
            return (160, 80, 220)
        elif 'VIO' in filter_name:
            return (160, 120, 200)
        elif 'BL' in filter_name:
            return (110, 180, 180) if 'GRN' in filter_name else (110, 110, 180)
        elif 'GRN' in filter_name:
            return (190, 190, 110) if 'RED' in filter_name else (110, 190, 110)
        elif 'RED' in filter_name:
            return (190, 110, 100)
        elif 'MT1' in filter_name:
            return (190, 110, 100)
        elif 'CB1' in filter_name:
            return (190, 110, 100)
        elif 'HAL' in filter_name:
            return (190, 110, 100)
        elif 'MT' in filter_name:
            return (200, 80, 80)
        elif 'CB' in filter_name:
            return (200, 80, 80)

        return None


register_instrument(Cassini_ISS)

##########################################################################################
