##########################################################################################
# picmaker/instruments/hst_acs.py
##########################################################################################
"""HST ACS detector and reader."""

import re

import numpy as np

from picmaker.instruments import ImageData, tint_by_nm
from picmaker.instruments._fits_support import (
    get_fits_image_hdu,
    get_fits_image_hdus,
    hdu_is_image,
)
from picmaker.instruments._hst_support import (
    get_chip_dq_mask,
    get_hst_filter_digits,
    get_sci_dq_mask,
    is_science_hdu,
    split_mask,
)

_IS_UNDIAGNOSTIC = re.compile(r'(|CLEAR.*|POL.*|G800L|N/A)$')
_DEFAULT_UPWARD = True
_DEFAULT_SBC_RETINT = 3.

# Flag  Definition
# 0     Good pixel.
# 1     Reed-Solomon decoding error; e.g., data lost during compression.
# 2     Data replaced by fill value; e.g., neighboring cosmic ray contaminated pixels.
# 4     Bad detector pixel, or vignetted pixel. In the HRC BPIXTAB, this identifies a
#       small detector defect in the "upper right" corner.
# 8     Masked by aperture feature, e.g., the HRC occulting finger.
# 16    Hot pixel, i.e., pixel with dark current > 0.14 e-/sec, flagged in superdark DQ
#       arrays.
# 32    Pixels with unstable dark current; includes random telegraph signal noise and
#       fading hot pixels. See section 3.2 of ACS ISR 2017-05 and ACS ISR 2022-07.
# 64    Warm pixel, i.e., pixel with 0.06 e-/s ≤ dark current ≤ 0.14 e-/s, flagged in
#       superdark DQ arrays.
# 128   Bias structure, e.g., bad columns. Since 08 Oct 2004, bias structure has been
#       flagged in the superbias DQ arrays. Before 08 Oct 2004, bias structure was only
#       flagged in an increasingly outdated BPIXTAB which was created in July 2002.
# 256   CCD full-well saturated pixel (usable at gain = 2). See ACS ISR 2020-02.
# 512   Bad pixel in reference file. Used in the flatfield DQ arrays to indicate a portion
#       of the flat which is not defined or not calibrated with the same accuracy as the
#       other regions, often around the detector edges. Used for F892N and WFC polarizer
#       observations, where the filter only subtends a portion of the chip. Used to
#       identify dust mote replacement patches. Used to identify a saturated pixel in
#       superdark reference files.
# 1024  Sink pixel or pixel affected by sink pixel charge traps. See ACS ISR 2017-01.
# 2048  A-to-D saturated pixel (never usable, even at higher gain settings). See ACS ISR
#       2020-03.
# 4096  Cosmic ray and detector artifact rejected during the combination DITHERED exposure
#       in AstroDrizzle. These flags are not present in the drizzled output images
#       (*drz.fits). Rather, they are propagated "backwards" to the DQ arrays of the
#       calibrated input images (*flt.fits/*flc.fits).
# 8192  Cosmic ray rejected during the combination of CR-SPLIT images in the pipeline
#       (CALACS/ACSREJ) -- flagged in the DQ arrays of *crj.fits images. As with the 4096
#       flag, these values are propagated "backwards" to the DQ arrays of the calibrated
#       input images (*flt.fits/*flc.fits).
# 16384 Reserved. Can be used for manual flagging by the user, e.g., for uncorrected
#       detector artifacts, satellite trails, optical ghosts.

# DQ flag bits that do not mask a pixel: 64 = warm pixel
_DQ_IGNORE = 64


class HST_ACS(ImageData):
    """HST ACS detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, filepath, obj=None, pointers=None, retint=None,
                       mosaic=False, **kwargs):
        """Extract HST ACS data from an open HDUList.

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
                two WFC frames; ignored for HRC and SBC.
            **kwargs: Additional input options, ignored here.

        If the image comes from a science ("SCI") HDU, the matching "DQ" extension in the
        same file supplies `hmask` and `imask`: every pixel with a nonzero data quality
        value is set in both, except where the value is 64 (warm pixel) alone.

        Returns:
            HST_ACS or None: Instrument subclass if the file describes an HST ACS product;
            None otherwise.
        """

        def get_lambda_nm(hdulist):
            hdu = hdulist[0]
            filters = [hdu.header.get('FILTER1', ''), hdu.header.get('FILTER2', '')]
            filters = [f for f in filters if not _IS_UNDIAGNOSTIC.match(f)]
            lambda_nms = [get_hst_filter_digits(name) for name in filters]
            lambda_nms = [l for l in lambda_nms if l]
            if lambda_nms:
                return np.mean(lambda_nms)
            else:
                return None

        try:
            if hdulist[0].header['TELESCOP'] != 'HST':
                return None
            if hdulist[0].header['INSTRUME'] != 'ACS':
                return None
        except (KeyError, IndexError):
            return None

        # Determine whether this file can be mosaicked
        detector = hdulist[0].header['DETECTOR']
        # "ERR" HDUs only appear in WFC files that have not been drizzled. After drizzle,
        # the data from both chips has been combined into a single array, so no mosaicking
        # can be performed.
        use_mosaic = detector == 'WFC' and obj is None and mosaic and 'ERR' in hdulist
        if len([hdu for hdu in hdulist if hdu.header.get('EXTNAME') == 'SCI']) == 1:
            use_mosaic = False

        # Determine the default_tint
        hdu = get_fits_image_hdu(hdulist, obj=obj, pointers=pointers)
        default_tint = None
        if is_science_hdu(hdu):
            lambda_nm = get_lambda_nm(hdulist)
            if lambda_nm:
                retint = retint or (_DEFAULT_SBC_RETINT if detector == 'SBC' else 1.)
                default_tint = tint_by_nm(lambda_nm * retint)

        # Handle the non-mosaicked case
        if not use_mosaic:
            (hmask, imask) = split_mask(get_sci_dq_mask(hdulist, hdu, _DQ_IGNORE))
            return HST_ACS(hdu.data, hmask, imask, _DEFAULT_UPWARD, default_tint)

        # Determine the first CCD chip in the file. Should be 2 but could be 1 if only one
        # detector was used.
        ccds = [hdu.header.get('CCDCHIP') for hdu in hdulist[1:]]
        ccds = [ccd for ccd in ccds if ccd is not None]
        if not ccds:
            raise ValueError(f'Unrecognized ACS/WFC image file structure {filepath}')
        first_ccd = ccds[0]

        # Select the HDUs
        hdus = get_fits_image_hdus(hdulist, pointers=pointers)
        if not hdu_is_image(hdus[0]):
            raise ValueError(f'Selected HDU is not an IMAGE in {hdulist.filename()}')
        extname = hdus[0].header['EXTNAME']  # make sure all HDUs have the same EXTNAME
        hdus = [hdu for hdu in hdus if hdu.header['EXTNAME'] == extname]

        # Construct the merged array and return
        array = np.zeros((2,) + hdus[0].data.shape)
        array[first_ccd - 1] = hdus[0].data
        if len(hdus) > 1:
            array[2 - first_ccd] = hdus[1].data
        dq_mask = get_chip_dq_mask(hdulist, hdus, first_ccd, array.shape,
                                   ignore=_DQ_IGNORE)
        (hmask, imask) = split_mask(dq_mask)
        return HST_ACS(array, hmask, imask, _DEFAULT_UPWARD, default_tint)

    @staticmethod
    def apply_mosaic(arrays_rgb, **kwargs):
        """Assemble ACS/WFC's two CCDs (WFC2 above, WFC1 below) into a mosaic.

        Parameters:
            arrays_rgb (list[array]): Per-detector RGB arrays (usually length 2), each
                indexed (lines, samples, color).
            **kwargs: Additional input options, ignored here.

        Returns:
            array: The assembled mosaic, with shape (2*lines, samples, colors) for WFC.
            HRC and SBC images are not mosaicked.
        """

        # Only WFC has two CCDs to stack; HRC and SBC are single-detector.
        if len(arrays_rgb) < 2:
            return arrays_rgb[0]

        # WFC2 on top; WFC1 on the bottom. Display direction is up.
        (nl, ns, nc) = arrays_rgb[0].shape
        mosaic = np.zeros((2 * nl, ns, nc))
        mosaic[-nl:] = arrays_rgb[0]    # WFC1 (bottom)
        mosaic[:nl ] = arrays_rgb[1]    # WFC2 (top)
        return mosaic


##########################################################################################
