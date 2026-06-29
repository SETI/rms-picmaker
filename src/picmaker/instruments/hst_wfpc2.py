##########################################################################################
# picmaker/instruments/hst_wfpc2.py
##########################################################################################
"""HST WFPC2 detector and reader."""

import re

import astropy.io.fits as pyfits  # noqa
import numpy as np

from picmaker.instruments import ImageData, register_instrument
from picmaker.instruments._hst_support import get_hst_filter_digits, hst_tint_from_nm

_DEFAULT_UPWARD = True
_IS_UNDIAGNOSTIC = re.compile(r'(|F130LP|F165LP|F606W|FQCH4.*|POL.*)$')


class HST_WFPC2(ImageData):
    """HST WFPC2 detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, obj=None, **kwargs):
        """Extract HST WFPC2 data from an open :class:`pyfits.HDUList`.

        Parameters:
            hdulist (:class:`pyfits.HDUList`): The HDUList of an opened FITS file.
            obj (int, optional): An object index within the file; ignored for HST WFPC2
                images.
            **kwargs: Additional input options, ignored here.

        Returns:
            (HST_WFPC2 or None): Instrument subclass if ``label`` describes a HST WFPC2
            product; ``None`` otherwise.
        """

        try:
            if hdulist[0].header['TELESCOP'] != 'HST':
                return None
            if hdulist[0].header['INSTRUME'] != 'WFPC2':
                return None
        except (KeyError, IndexError):
            return None

        # Interpret the filter names
        filters = [hdulist.get('FILTNAM1', ''), hdulist.get('FILTNAM2', '')]
        filters = [f for f in filters if not _IS_UNDIAGNOSTIC.match(f)]

        # FQUVN has four nearby bands; this is the mean
        waves = [(387 if f[:5] == 'FQUVN' else get_hst_filter_digits(f))
                 for f in filters]
        if waves:
            default_tint = hst_tint_from_nm(np.mean(waves))
        else:
            default_tint = None

        return ImageData(hdulist[0].data, _DEFAULT_UPWARD, default_tint)

    @staticmethod
    def apply_mosaic(arrays_rgb, *, imagefile=None, **kwargs):
        """Assemble WFPC2's four detectors (PC1, WF2, WF3, WF4) into a 2x2 mosaic.

        When ``imagefile`` is a list of per-detector file paths, each detector's quadrant
        is inferred from substrings (``PC1``, ``WF2``, ``WF3``, ``WF4``) in the file name,
        and every non-PC1 detector is rotated to share PC1's pixel orientation. Otherwise
        (a single multi-extension file, or no file information), the bands are placed in
        order with a ``b``-step ``np.rot90`` rotation.

        Parameters:
            arrays_rgb (list[np.ndarray]): Per-detector RGB arrays (length 4), each
                ``(lines, samples, 3)``.
            imagefile (str, list[str], or None, optional): The source file path, or a list
                of per-detector paths used to order the quadrants by name.
            **kwargs: Additional input options, ignored here.

        Returns:
            (np.ndarray): The assembled 2x2 mosaic, shape ``(2 * lines, 2 * samples, 3)``.
        """

        quads_rgb = np.zeros((4,) + arrays_rgb[0].shape)
        for b in range(len(arrays_rgb)):
            if not isinstance(imagefile, (list, tuple)):
                quads_rgb[b] = np.rot90(arrays_rgb[b], b)
            else:
                testfile = imagefile[b].upper()
                if 'PC1' in testfile:
                    quads_rgb[0] = arrays_rgb[b]
                elif 'WF2' in testfile:
                    quads_rgb[1] = np.rot90(arrays_rgb[b], 1)
                elif 'WF3' in testfile:
                    quads_rgb[2] = np.rot90(arrays_rgb[b], 2)
                elif 'WF4' in testfile:
                    quads_rgb[3] = np.rot90(arrays_rgb[b], 3)
                else:
                    quads_rgb[b] = np.rot90(arrays_rgb[b], b)

        (_, dl, ds, db) = quads_rgb.shape
        mosaic = np.empty((2 * dl, 2 * ds, db))
        mosaic[:dl , -ds:] = quads_rgb[0]
        mosaic[:dl , :ds ] = quads_rgb[1]
        mosaic[-dl:, :ds ] = quads_rgb[2]
        mosaic[-dl:, -ds:] = quads_rgb[3]
        return mosaic


register_instrument(HST_WFPC2)

##########################################################################################
