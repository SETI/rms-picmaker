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

    def apply_mosaic(arrays_rgb, **kwargs):
        """Construct the ACS/WFC mosaic."""

        # TBD
        pass

    def _acs_wfc_panel_mosaic(arrays_rgb, imagefile):
        """Assemble ACS/WFC's two detectors (WFC1 above, WFC2 below).

        When ``imagefile`` is a list of per-detector file paths, the panel order is
        inferred from substrings (``WFC1``, ``WFC2``) in each filename. When
        ``imagefile`` is a single string, band 0 is placed below and band 1 above
        (matching the legacy ``1 - b`` indexing).

        Parameters:
            arrays_rgb: Per-band RGB arrays (length 2), each ``(lines, samples, 3)``.
            imagefile: Either a single string or a list of strings.

        Returns:
            The assembled panel mosaic, shape ``(2 * lines, samples, 3)``.
        """
        panels_rgb = np.zeros((2, *arrays_rgb[0].shape))
        for b in range(2):
            if isinstance(imagefile, str):
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
        mosaic[:dl] = panels_rgb[0]
        mosaic[-dl:] = panels_rgb[1]
        return mosaic




register_instrument(HST_ACS)

##########################################################################################
