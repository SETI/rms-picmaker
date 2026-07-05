##########################################################################################
# picmaker/instruments/zzz_generic.py
##########################################################################################
"""Generic image reader."""

import pickle
import re

import numpy as np
import pdsparser
from PIL import Image

from picmaker.instruments import ImageData
from picmaker.instruments._fits_support import get_fits_array
from picmaker.instruments._pds3_support import DEFAULT_PDS3_METHOD, read_pds3_image_array
from picmaker.pil_utils import pil_to_array
from picmaker.tiff16 import read_tiff16

# A PDS3 label, attached or detached,  begins with the PDS_VERSION_ID keyword set to PDS3.
# We scan a head block rather than anchoring at the first byte so that an optional SFDU
# wrapper or leading comment does not defeat the match.
_PDS3_LABEL_SIGNATURE = re.compile(rb'PDS_VERSION_ID\s*=\s*"?PDS3')


class ZZZ_Generic(ImageData):
    """Generic image detector and reader."""

    @staticmethod
    def detect_in_pds3(label, filepath, obj=0, **kwargs):
        """Extract image data from a parsed Pds3Label.

        Parameters:
            label (Pds3Label): A parsed PDS3 label.
            filepath (str or Path): The path to this PDS3 label.
            obj (int, optional): Index of the IMAGE object if the label describes more
                than one.
            **kwargs: Instrument-specific keywords.

        Returns:
            ZZZ_Generic or None: The ImageData subclass if the label is recognized;
            otherwise, None.
        """

        array = read_pds3_image_array(label, obj)
        return ZZZ_Generic(array, False, None)

    @staticmethod
    def detect_in_vicar(vic, filepath, **kwargs):
        """Extract image data from an open :class:`vicar.VicarImage`.

        Parameters:
            vic (VicarImage): A VicarImage object.
            filepath (str or Path): The path to this Vicar file.
            **kwargs: Instrument-specific keywords; ignored here.

        Returns:
            ZZZ_Generic or None: The ImageData subclass if `vic` is recognized; otherwise,
            None.
        """

        array = vic.array
        if array.ndim > 2 and array.shape[0] == 1:
            array = array[0]
        return ZZZ_Generic(array, False, None)

    @staticmethod
    def detect_in_fits(hdulist, filepath, obj=None, **kwargs):
        """Extract image data from a FITS HDUlist.

        Parameters:
            hdulist (HDUList): The HDUList of the FITS file.
            filepath (str or Path): The path to this FITS file.
            obj (int, optional): The index of the HDUList describing the image. If not
                specified, the first HDU containing data is used.
            **kwargs: Instrument-specific keywords; ignored here.

        Returns:
            ZZZ_Generic or None: The ImageData subclass if `hdulist` is recognized;
            otherwise, None.
        """

        array = get_fits_array(hdulist, obj=obj)
        return ZZZ_Generic(array, True, None)

    @staticmethod
    def detect_in_file(filepath, **kwargs):
        """Extract image data from an alternative file format.

        Parameters:
            filepath (str or Path): The file path.
            **kwargs: Other input parameters

        Returns:
            ZZZ_Generic or None: The ImageData subclass if the format of `file` is
            recognized; otherwise, None.

        Raises:
            NotImplementedError: If a 16-bit TIFF file uses the "palette" option.
        """

        # Handle a PDS3 file with an attached label. A ".lbl" file is recognized earlier
        # in the reader cascade; a data file that is not named ".lbl" but carries a PDS3
        # label at its head, with the image attached in the same file, is recognized here
        # from that label's signature.
        with open(filepath, 'rb') as f:
            head = f.read(512)
        if _PDS3_LABEL_SIGNATURE.search(head):
            method = kwargs.get('pds3_method', DEFAULT_PDS3_METHOD)
            label = pdsparser.Pds3Label(filepath, method=method)
            array = read_pds3_image_array(label, kwargs.get('obj'))
            return ZZZ_Generic(array, False, None)

        # Handle pickle file
        try:
            with open(filepath, 'rb') as f:
                array = pickle.load(f)
            return ZZZ_Generic(array, False, None)
        except Exception:
            pass

        # Handle a Numpy ".npy" file
        try:
            array = np.load(filepath)
            return ZZZ_Generic(array, False, None)
        except Exception:
            pass

        # Handle 16-bit TIFF
        if filepath.suffix.lower() in {'.tiff', '.tif'}:
            try:
                (array, palette) = read_tiff16(filepath)
            except Exception:
                pass

            if palette is not None:
                raise NotImplementedError('16-bit palette option is not supported')

            return ZZZ_Generic(array, False, None)

        # Handle PIL Image
        try:
            array = pil_to_array(Image.open(filepath), rescale=False)
            return ZZZ_Generic(array, False, None)
        except Exception:
            pass

        return None


##########################################################################################
