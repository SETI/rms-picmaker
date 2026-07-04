##########################################################################################
# picmaker/instruments/hst_wfc3.py
##########################################################################################
"""HST WFC3 detector and reader."""

# ruff: noqa: I001
import re

import numpy as np

from picmaker.instruments import ImageData, tint_by_nm
from picmaker.instruments._fits_support import (get_fits_image_hdu, get_fits_image_hdus,
                                                hdu_is_image)
from picmaker.instruments._hst_support import get_hst_filter_digits, is_science_hdu

_IS_UNDIAGNOSTIC = re.compile(r'(F200LP|F350LP)$')
_DEFAULT_UPWARD = True
_DEFAULT_IR_RETINT = 0.4


class HST_WFC3(ImageData):
    """HST WFC3 detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, filepath, obj=None, pointers=None, retint=None,
                       mosaic=False, **kwargs):
        """Extract HST WFC3 data from an open HDUList.

        Parameters:
            hdulist (HDUList): The HDUList of the FITS file.
            filepath (str or Path): The path to this FITS file.
            obj (int, optional): The HDU index (starting at 0) of the image array. If not
                specified, the first image array in the file is used.
            pointers (str or list[str], optional): Name or alternative list of names of
                the IMAGE object within the HDU.
            retint (float, optional): Factor by which to scale wavelengths for purposes of
                tinting.
            mosaic (bool, optional): True to enable the construction of a mosaic from the
                two UVIS frames.
            **kwargs: Additional input options, ignored here.

        Returns:
            HST_WFC3 or None: Instrument subclass if the file describes an HST WFC3
            product; None otherwise.
        """

        try:
            if hdulist[0].header['TELESCOP'] != 'HST':
                return None
            if hdulist[0].header['INSTRUME'] != 'WFC3':
                return None
        except (KeyError, IndexError):
            return None

        # Determine whether this file can be mosaicked
        detector = hdulist[0].header['DETECTOR']
        # "ERR" HDUs only appear in UVIS files that have not been drizzled. After drizzle,
        # the data from both chips has been combined into a single array, so no mosaicking
        # can be performed.
        use_mosaic = detector == 'UVIS' and obj is None and mosaic and 'ERR' in hdulist
        if len([hdu for hdu in hdulist[1:] if hdu.header['EXTNAME'] == 'SCI']) == 1:
            use_mosaic = False

        # Determine the default_tint
        hdu = get_fits_image_hdu(hdulist, obj=obj, pointers=pointers)
        default_tint = None
        if is_science_hdu(hdu):
            filter_name = hdulist[0].header['FILTER']
            if not _IS_UNDIAGNOSTIC.fullmatch(filter_name):
                digits = get_hst_filter_digits(filter_name)
                if detector == 'UVIS':
                    default_tint = tint_by_nm(digits * (retint or 1))
                else:
                    # IR filter names encode wavelength/10 (F160W -> 1600 nm).
                    default_tint = tint_by_nm(
                        digits * 10. * (retint or _DEFAULT_IR_RETINT))

        # Handle the non-mosaicked case
        if not use_mosaic:
            return HST_WFC3(hdu.data, _DEFAULT_UPWARD, default_tint)

        # Determine the first chip in the file. Should be 2 but could be 1 if only one
        # detector was used.
        ccds = [hdu.header.get('CCDCHIP') for hdu in hdulist[1:]]
        ccds = [ccd for ccd in ccds if ccd is not None]
        if not ccds:
            raise ValueError(f'Unrecognized WFC3 image file structure {filepath}')
        first_ccd = ccds[0]

        # Select the HDUs
        hdus = get_fits_image_hdus(hdulist, pointers=pointers)
        if not hdu_is_image(hdus[0]):
            raise ValueError(f'selected HDU is not an IMAGE in {hdulist.filename()}')
        extname = hdus[0].header['EXTNAME']  # make sure all HDUs have the same EXTNAME
        hdus = [hdu for hdu in hdus if hdu.header['EXTNAME'] == extname]

        # Construct the merged array and return
        array = np.zeros((2,) + hdus[0].data.shape)
        array[first_ccd - 1] = hdus[0].data
        if len(hdus) > 1:
            array[2 - first_ccd] = hdus[1].data
        return HST_WFC3(array, _DEFAULT_UPWARD, default_tint)

    @staticmethod
    def apply_mosaic(arrays_rgb, **kwargs):
        """Assemble WFC3's two UVIS CCDs into a mosaic.

        Parameters:
            arrays_rgb (list[array]): Per-detector RGB arrays (usually length 2), each
                indexed (lines, samples, color).
            **kwargs: Additional input options, ignored here.

        Returns:
            array: The assembled mosaic, with shape (2*lines, samples, colors) for UVIS.
            IR images are single-detector and not mosaicked.
        """

        # Only UVIS has two CCDs to stack; IR is single-detector.
        if len(arrays_rgb) < 2:
            return arrays_rgb[0]

        # UVIS2 on top; UVIS1 on the bottom. Display direction is up.
        (nl, ns, nc) = arrays_rgb[0].shape
        mosaic = np.zeros((2 * nl, ns, nc))
        mosaic[-nl:] = arrays_rgb[0]    # UVIS1 (bottom)
        mosaic[:nl ] = arrays_rgb[1]    # UVIS2 (top)
        return mosaic


##########################################################################################
