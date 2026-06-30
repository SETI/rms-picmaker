##########################################################################################
# picmaker/instruments/hst_acs.py
##########################################################################################
"""HST ACS detector and reader."""

import astropy.io.fits as pyfits  # noqa
import numpy as np

from picmaker.instruments import ImageData, register_instrument
from picmaker.instruments._hst_support import get_hst_filter_digits, hst_tint_from_nm

_DEFAULT_UPWARD = True


class HST_ACS(ImageData):
    """HST ACS detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, obj=None, **kwargs):
        """Extract HST ACS data from an open :class:`pyfits.HDUList`.

        Parameters:
            hdulist (:class:`pyfits.HDUList`): The HDUList of an opened FITS file.
            obj (int, optional): An object index within the file; ignored for HST ACS
                images.
            **kwargs: Additional input options, ignored here.

        Returns:
            (HST_ACS or None): Instrument subclass if ``label`` describes a HST ACS
            product; ``None`` otherwise.
        """

        try:
            if hdulist[0].header['TELESCOP'] != 'HST':
                return None
            if hdulist[0].header['INSTRUME'][:3] != 'ACS':
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

    @staticmethod
    def apply_mosaic(arrays_rgb, *, imagefile=None, **kwargs):
        """Assemble ACS/WFC's two CCDs (WFC1 above, WFC2 below) into a mosaic.

        Only the WFC detector is built from two CCDs; HRC and SBC are single-detector, so a
        single-element ``arrays_rgb`` is returned unchanged. When ``imagefile`` is a list
        of per-CCD file paths, the panel order is inferred from substrings (``WFC1``,
        ``WFC2``) in each file name; otherwise band 0 is placed below and band 1 above.

        Parameters:
            arrays_rgb (list[np.ndarray]): Per-CCD RGB arrays, each ``(lines, samples,
                3)``. WFC supplies two; HRC and SBC supply one.
            imagefile (str, list[str], or None, optional): The source file path, or a list
                of per-CCD paths used to order the panels by name.
            **kwargs: Additional input options, ignored here.

        Returns:
            (np.ndarray): The assembled mosaic ``(2 * lines, samples, 3)`` for WFC, or the
            single RGB array unchanged for HRC and SBC.
        """

        # Only WFC has two CCDs to stack; HRC and SBC are single-detector.
        if len(arrays_rgb) < 2:
            return arrays_rgb[0]

        panels_rgb = np.zeros((2,) + arrays_rgb[0].shape)
        for b in range(2):
            if not isinstance(imagefile, (list, tuple)):
                panels_rgb[1 - b] = arrays_rgb[b]
            else:
                testfile = imagefile[b].upper()
                if 'WFC1' in testfile:
                    panels_rgb[0] = arrays_rgb[b]
                elif 'WFC2' in testfile:
                    panels_rgb[1] = arrays_rgb[b]
                else:
                    panels_rgb[b] = arrays_rgb[b]

        (dl, ds, db) = arrays_rgb[0].shape
        mosaic = np.zeros((2 * dl, ds, db))
        mosaic[:dl] = panels_rgb[0]     # WFC1 on top
        mosaic[-dl:] = panels_rgb[1]    # WFC2 on bottom
        return mosaic


register_instrument(HST_ACS)

##########################################################################################
