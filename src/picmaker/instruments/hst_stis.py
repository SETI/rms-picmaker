##########################################################################################
# picmaker/instruments/hst_stis.py
##########################################################################################
"""HST STIS detector and reader."""

from picmaker.instruments import ImageData, tint_by_nm
from picmaker.instruments._fits_support import get_fits_image_hdu
from picmaker.instruments._hst_support import get_sci_dq_mask, is_science_hdu, split_mask

_DEFAULT_UPWARD = True
_DEFAULT_UV_RETINT = 3.

# Pivot wavelengths in Angstroms for narrow filters from
# https://hst-docs.stsci.edu/stisihb/chapter-5-imaging/5-1-imaging-overview
_APERTURE_WAVELENGTHS = {
    'F28X50LP'  : 7229,
    'F28X50OIII': 5006,
    'F28X50OII' : 3737,

    'F25MGII'   : 2802,
    'F25CN270'  : 2709,
    'F25CIII'   : 1989,
    'F25CN182'  : 1981,
    'F25LYA'    : 1221,
}

# FLAG  Quality Condition Indicated
# 1     Error in the Reed-Solomon decoding (an algorithm for error correction in digital
#       communications).
# 2     Lost data replaced by fill values.
# 4     Bad detector pixel (e.g., bad column or row, mixed science and bias for overscan,
#       or beyond aperture).
# 8     Data masked by occulting bar.
# 16    Pixel having dark rate > 5 sigma times the median dark level.
# 32    Large blemish, depth < 40% of the normalized p-flat (repeller wire).
# 64    Vignetted pixel
# 128   Pixel in the overscan region.
# 256   Saturated pixel, count rate at 90% of max possible—local non-linearity turns over
#       and is multi-valued; pixels within 10% of turnover and all pixels within 4 pixels
#       of that pixel are flagged.
# 512   Bad pixel in reference file.
# 1024  Small blemish, depth between 40% and 70% of the normalized flat. Applies to MAMA
#       and CCD p-flats.
# 2048  >30% of background pixels rejected by sigma-clip, or flagged, during 1-D spectral
#       extraction.
# 4096  Extracted flux affected by bad input data.
# 8192  Data rejected in input pixel during image combination for cosmic ray rejection.
# 16384 Extracted flux not CTI corrected because gross counts are ≤ 0.


class HST_STIS(ImageData):
    """HST STIS detector and reader."""

    @staticmethod
    def detect_in_fits(hdulist, filepath, obj=None, pointers=None, retint=None, **kwargs):
        """Extract HST STIS data from an open HDUList.

        Parameters:
            hdulist (HDUList): The HDUList of the FITS file.
            filepath (str or Path): The path to this FITS file.
            obj (int, optional): The HDU index (starting at 0) of the image array. If not
                specified, the first image array in the file is used.
            pointers (str or list[str], optional): Name or alternative list of names of
                the IMAGE object within the HDU.
            retint (float, optional): Factor by which to scale wavelengths for purposes of
                tinting. Default is 3 for FUV and NUV, 1 for CCD.
            **kwargs: Additional input options, ignored here.

        If the image comes from a science ("SCI") HDU, the matching "DQ" extension in the
        same file supplies `hmask` and `imask`: every pixel with a nonzero data quality
        value is set in both.

        Returns:
            HST_STIS or None: Instrument subclass if the file describes an HST STIS
            product; None otherwise.
        """

        try:
            if hdulist[0].header['TELESCOP'] != 'HST':
                return None
            if hdulist[0].header['INSTRUME'] != 'STIS':
                return None
        except (KeyError, IndexError):
            return None

        hdu = get_fits_image_hdu(hdulist, obj=obj, pointers=pointers, **kwargs)
        default_tint = None
        if is_science_hdu(hdu):
            detector = hdulist[0].header['DETECTOR']
            aperture = hdulist[0].header['APERTURE']
            if aperture in _APERTURE_WAVELENGTHS:
                lambda_nm = _APERTURE_WAVELENGTHS[aperture] / 10.
                retint = retint or (1. if detector == 'CCD' else _DEFAULT_UV_RETINT)
                default_tint = tint_by_nm(lambda_nm * retint)

        (hmask, imask) = split_mask(get_sci_dq_mask(hdulist, hdu))
        return HST_STIS(hdu.data, hmask, imask, _DEFAULT_UPWARD, default_tint)


##########################################################################################
