##########################################################################################
# picmaker/instruments/_fits_support.py
##########################################################################################
"""Shared FITS tools."""


def get_fits_array(hdulist, obj=None):
    """Return an image array from a FITS file.

    Parameters:
        hdulist (pyfits.HDUList): HDUList of opened FITS file.
        obj (int, optional): The HDU index of the image array. If not specified, the first
            image array in the file is used.

    Returns:
        (np.ndarray): The selected image array.

    Raises:
        IndexError: If `obj` is out of range.
        ValueError: If the file does not contain an image array.
        ValueError: If the selected HDU does not contain an image.
    """

    if obj is None:
        if hdulist[0].header['NAXIS'] >= 2:
            return hdulist[0].data
        for hdu in hdulist[1:]:
            if hdu.header['XTENSION'] == 'IMAGE':
                return hdu.data
        raise ValueError('no FITS image object found')

    hdu = hdulist[obj]  # forward IndexError
    if obj > 0 and hdu.header['XTENSION'] != 'IMAGE':
        raise ValueError(f'HDU {obj} is not an image')
    return hdu.data


__all__ = ['get_fits_array']

##########################################################################################
