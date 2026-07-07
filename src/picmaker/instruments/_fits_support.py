##########################################################################################
# picmaker/instruments/_fits_support.py
##########################################################################################
"""Shared FITS tools."""


def hdu_is_image(hdu):
    """True if the given HDU describes a FITS IMAGE."""
    if 'XTENSION' in hdu.header:
        return hdu.header['XTENSION'] == 'IMAGE'
    if hdu.header['NAXIS'] < 2:
        return False
    if 'TFIELDS' in hdu.header:
        return False
    return True


def get_fits_image_hdus(hdulist, pointers=None, **kwargs):
    """Return a list of selected HDUs from an HDUList.

    Parameters:
        hdulist (HDUList): HDUList of the FITS file.
        pointers (str or list[str], optional): Name or alternative list of names of the
            IMAGE object pointer in the PDS3 label.
        **kwargs: Additional input parameters, ignored here.

    Returns:
        list[HDU]: The selected image HDUs.

    Raises:
        KeyError: If none of the named `pointers` are found in the HDUList.
        ValueError: If the file does not contain an image array.
    """

    if pointers:
        if not isinstance(pointers, (list, tuple)):
            pointers = [pointers]

        selected_hdus = []
        for hdu in hdulist:
            if hdu.header.get('EXTNAME') in pointers:
                selected_hdus.append(hdu)
        if not selected_hdus:
            raise KeyError(f'HDU {pointers[0]} not found in {hdulist.filename()}')

        return selected_hdus

    selected_hdus = [hdu for hdu in hdulist if hdu_is_image(hdu)]
    if not selected_hdus:
        raise ValueError(f'No IMAGE HDU found in {hdulist.filename()}')

    return selected_hdus


def get_fits_image_hdu(hdulist, obj=None, pointers=None, **kwargs):
    """Return an image HDU from a FITS file.

    Parameters:
        hdulist (HDUList): HDUList of the FITS file.
        obj (int, optional): The HDU index (starting at 0) of the IMAGE HDU. If not
            specified, the first image HDU in the file is used.
        pointers (str or list[str], optional): Name or alternative list of names of the
            IMAGE object pointer in the PDS3 label.
        **kwargs: Additional input parameters, ignored here.

    Returns:
        HDU: The selected HDU.

    Raises:
        IndexError: If `obj` is out of range.
        KeyError: If none of the named `pointers` are found in the HDUList.
        ValueError: If the file does not contain an image array.
        ValueError: If the selected HDU does not contain an image.
    """

    selected_hdus = get_fits_image_hdus(hdulist, pointers=pointers)
    if obj is None:
        selected_hdu = selected_hdus[0]
    else:
        count = len(selected_hdus)
        if -count <= obj < count:
            selected_hdu = selected_hdus[obj]
        else:
            raise IndexError(f'{obj} is out of range for {hdulist.filename()}')

    if not hdu_is_image(selected_hdu):
        raise ValueError(f'Selected HDU is not an IMAGE in {hdulist.filename()}')

    return selected_hdu


def get_fits_array(hdulist, obj=None, pointers=None, **kwargs):
    """Return an image array from a FITS file.

    Parameters:
        hdulist (HDUList): HDUList of the FITS file.
        obj (int, optional): The HDU index (starting at 0) of the image array. If not
            specified, the first image array in the file is used.
        pointers (str or list[str], optional): Name or alternative list of names of the
            IMAGE object pointer in the PDS3 label.
        **kwargs: Additional input parameters, ignored here.

    Returns:
        array: The selected image array.

    Raises:
        IndexError: If `obj` is out of range.
        KeyError: If none of the named `pointers` are found in the HDUList.
        ValueError: If the file does not contain an image array.
        ValueError: If the selected HDU does not contain an image.
    """

    return get_fits_image_hdu(hdulist, obj=obj, pointers=pointers).data


__all__ = ['get_fits_array', 'get_fits_image_hdu', 'get_fits_image_hdus']

##########################################################################################
