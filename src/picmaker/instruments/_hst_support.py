##########################################################################################
# picmaker/instruments/_hst_support.py
##########################################################################################
"""Shared HST tools."""

import pathlib
import re
import warnings

import astropy.io.fits as pyfits
import numpy as np
from astropy.io.fits.verify import VerifyWarning

_FILTER_PATTERN = re.compile(r'[A-Z]+(\d\d\d+)[A-Z]+')

# Splits an older HST data file name around its suffix code, e.g. "u2tf0504t_c0f.fits"
# -> ("u2tf0504t", "c0", "f", ".fits"); the first group is greedy so the last match wins
_DATA_FILENAME = re.compile(r'(.*)_([a-z]\d)([fm])((?![a-z\d]).*)', re.I)

# For WF/PC and WFPC2, the suffix code of each science file type and that of its data
# quality file: calibrated _c0f/_c0m -> _c1f/_c1m; raw _d0f/_d0m -> _q0f/_q0m
WFPC_DQ_CODES = {'c0': 'c1', 'd0': 'q0'}


def get_hst_filter_digits(filter_name):
    """The integer embedded within the given filter name; None otherwise."""

    match = _FILTER_PATTERN.fullmatch(filter_name)
    if match:
        return int(match.group(1))

    return None


def is_science_hdu(hdu):
    """True if the HDU is a science ('SCI') extension."""
    return hdu.header.get('EXTNAME', '') == 'SCI'


def get_detector_cube(hdulist, filepath):
    """Return a WF/PC, WFPC2, or FOC detector cube and the detector number of each plane.

    These files come in two layouts holding the same content:

    * "Waiver" FITS (_c0f etc.): the PRIMARY HDU holds a (n, lines, samples) cube, and
      HDU[1] is a group-parameters table whose DETECTOR column gives the detector of
      each plane.
    * Multi-extension FITS (_c0m etc.): the PRIMARY HDU is empty, and each detector is
      in its own image extension, which carries a DETECTOR keyword.

    Parameters:
        hdulist (HDUList): The HDUList of the FITS file.
        filepath (str or Path): The path to this FITS file.

    Returns:
        tuple[array, list[int]]: The (n, lines, samples) detector cube and the
        detector number of each of its n planes: 1-4 for WFPC2 and the WF/PC WF chips;
        5-8 for the WF/PC PC chips. Without DETECTOR values (e.g., FOC), the planes
        are numbered 1 to n.

    Raises:
        ValueError: If the file contains no image data.
    """

    array = hdulist[0].data

    # Multi-extension layout
    if array is None:
        hdus = [hdu for hdu in hdulist[1:] if hdu.is_image and hdu.data is not None]
        if not hdus:
            raise ValueError(f'No image data found in {filepath}')
        array = np.stack([hdu.data for hdu in hdus])
        detectors = [hdu.header.get('DETECTOR', b + 1) for b, hdu in enumerate(hdus)]
        return (array, detectors)

    # Waiver layout
    array = array[np.newaxis] if array.ndim == 2 else array

    # Reading the group-parameters table trips a benign astropy VerifyWarning about a
    # non-standard TDISP keyword in the archived files; suppress just that warning.
    detectors = list(range(1, array.shape[0] + 1))
    if len(hdulist) > 1 and not hdulist[1].is_image:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', VerifyWarning)
            columns = hdulist[1].columns.names
            if 'DETECTOR' in columns:
                detectors = [int(d) for d in hdulist[1].data['DETECTOR']]

    return (array, detectors)

def place_by_detector(cube, detectors):
    """Expand a detector cube to all four detectors, placing each plane by its detector
    number and leaving any missing detectors zero (or False).

    Detector numbers 1-4 map to planes 0-3; WF/PC's PC detectors 5-8 also map to planes
    0-3.
    """

    result = np.zeros((4,) + cube.shape[-2:], dtype=cube.dtype)
    for b, det in enumerate(detectors):
        result[(det - 1) % 4] = cube[b]
    return result


def get_dq_path(filepath, hst_dq=None, dq_codes=None):
    """The path to the data quality file that goes with an older HST science file.

    Parameters:
        filepath (str or Path): Path to a science file, e.g., "_c0f" or "_d0m".
        hst_dq (str or Path, optional): Directory of the data quality file; None for
            the directory of `filepath`.
        dq_codes (dict[str, str], optional): Maps the suffix code of each science file
            type that has a data quality file (e.g., "c0" for "_c0f" or "_c0m") to the
            code of that data quality file (e.g., "c1"). The "f" or "m" layout letter is
            kept. Default is `WFPC_DQ_CODES`, for WF/PC and WFPC2.

    Returns:
        Path or None: The data quality file path, preserving the case of the original
        name; None if `filepath` is not one of the science file types in `dq_codes`.
    """

    dq_codes = WFPC_DQ_CODES if dq_codes is None else dq_codes

    filepath = pathlib.Path(filepath)
    match = _DATA_FILENAME.fullmatch(filepath.name)
    if not match:
        return None

    (head, code, layout, tail) = match.groups()
    dq_code = dq_codes.get(code.lower())
    if dq_code is None:
        return None
    if code.isupper():
        dq_code = dq_code.upper()

    directory = pathlib.Path(hst_dq) if hst_dq else filepath.parent
    return directory / f'{head}_{dq_code}{layout}{tail}'


def get_dq_mask(filepath, shape, hst_dq=None, logger=None, dq_codes=None):
    """Read the data quality file for an older HST science file as a boolean mask.

    Parameters:
        filepath (str or Path): Path to the science file.
        shape (tuple[int, int, int]): Shape of the science file's detector cube.
        hst_dq (str or Path, optional): Directory of the data quality file; None for
            the directory of `filepath`.
        logger (Logger or PdsLogger, optional): Logger for debug messages.
        dq_codes (dict[str, str], optional): The science file types that have data
            quality files, and the suffix codes of those files; see :func:`get_dq_path`.

    Returns:
        array[bool] or None: A detector cube that is True wherever the data quality value
        is nonzero; None if `filepath` has no data quality counterpart or the file is not
        found.

    Raises:
        ValueError: If the data quality cube does not match the science cube's shape.
    """

    dq_path = get_dq_path(filepath, hst_dq, dq_codes)
    if dq_path is None or not dq_path.is_file():
        if dq_path is not None:
            logger and logger.debug('Data quality file not found', dq_path)
        return None

    with pyfits.open(dq_path) as dq_hdulist:
        (dq, _) = get_detector_cube(dq_hdulist, dq_path)
        mask = np.asarray(dq != 0)

    if mask.shape != tuple(shape):
        raise ValueError(f'Data quality file {dq_path} has shape {mask.shape}; '
                         f'expected {tuple(shape)}')

    logger and logger.debug('Using data quality file', dq_path)
    return mask


def get_sci_dq_mask(hdulist, hdu, ignore=0):
    """The data quality mask paired with a science HDU in the same file.

    Newer HST files (ACS, COS, NICMOS, STIS, WFC3) store each science ("SCI") image with
    a "DQ" extension of the same EXTVER. A DQ extension may be a constant, with no data
    array and its value in the PIXVALUE keyword.

    Parameters:
        hdulist (HDUList): The HDUList of the FITS file.
        hdu (HDU): The selected image HDU.
        ignore (int, optional): Data quality flag bits to ignore; e.g., 64 leaves pixels
            whose only flag is 64 unmasked.

    Returns:
        array[bool] or None: A mask that is True wherever the data quality value has any
        flag bit set other than those in `ignore`; None if `hdu` is not a science HDU or
        has no matching DQ extension.

    Raises:
        ValueError: If the DQ array does not match the shape of the science array.
    """

    if not is_science_hdu(hdu) or hdu.data is None:
        return None

    extver = hdu.header.get('EXTVER', 1)
    for dq_hdu in hdulist:
        if (dq_hdu.header.get('EXTNAME') == 'DQ'
                and dq_hdu.header.get('EXTVER', 1) == extver):
            break
    else:
        return None

    shape = hdu.data.shape
    if dq_hdu.data is None:
        pixvalue = int(dq_hdu.header.get('PIXVALUE', 0))
        return np.full(shape, (pixvalue & ~ignore) != 0)

    # Use a signed 64-bit copy so the complement of `ignore` is valid for any DQ dtype
    dq = np.asarray(dq_hdu.data, dtype=np.int64) if ignore else dq_hdu.data
    mask = np.asarray((dq & ~ignore) != 0 if ignore else dq != 0)
    if mask.shape != shape:
        raise ValueError(f'DQ extension {extver} has shape {mask.shape}; '
                         f'expected {shape}')
    return mask


def get_chip_dq_mask(hdulist, hdus, first_ccd, shape, ignore=0):
    """The data quality mask for a two-chip (ACS/WFC or WFC3/UVIS) mosaic cube.

    Parameters:
        hdulist (HDUList): The HDUList of the FITS file.
        hdus (list[HDU]): The image HDUs of the two chips, in file order.
        first_ccd (int): The CCD chip number (1 or 2) of the first HDU.
        shape (tuple[int, int, int]): Shape of the (2, lines, samples) mosaic cube.
        ignore (int, optional): Data quality flag bits to ignore; see
            :func:`get_sci_dq_mask`.

    Returns:
        array[bool] or None: A mask cube with each chip's DQ mask in the same plane as its
        data; None if no chip has a DQ mask.
    """

    masks = [get_sci_dq_mask(hdulist, hdu, ignore) for hdu in hdus[:2]]
    if all(mask is None for mask in masks):
        return None

    cube = np.zeros(shape, dtype=bool)
    for plane, mask in zip((first_ccd - 1, 2 - first_ccd), masks, strict=False):
        if mask is not None:
            cube[plane] = mask
    return cube


def split_mask(mask):
    """The (hmask, imask) pair for a data quality mask: two separate copies, or (None,
    None) if the mask is None."""

    if mask is None:
        return (None, None)
    return (mask, mask.copy())


__all__ = ['WFPC_DQ_CODES', 'get_chip_dq_mask', 'get_detector_cube', 'get_dq_mask',
           'get_dq_path', 'get_hst_filter_digits', 'get_sci_dq_mask', 'is_science_hdu',
           'place_by_detector', 'split_mask']

##########################################################################################
