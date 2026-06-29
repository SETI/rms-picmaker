##########################################################################################
# picmaker/instruments/_hst_support.py
##########################################################################################
"""Shared HST tools."""

import re

import numpy as np
from tabulation import Tabulation

_FILTER_PATTERN = re.compile(r'[A-Z]+(\d\d\d+)[A-Z]+')


def get_hst_filter_digits(filter_name):
    """The integer embedded within the given filter name; ``None`` otherwise."""

    match = _FILTER_PATTERN.fullmatch(filter_name)
    if match:
        return int(match.group(1))

    return None


# [wavelength_nm, r, g, b]
_RGB_BY_NM = np.array([
    [380.0, 200.500,  60.500, 255.999],  # uv
    [410.0, 200.500, 110.500, 255.999],  # violet
    [480.0, 110.500, 110.500, 255.999],  # blue
    [540.0, 110.500, 255.999, 110.500],  # green
    [580.0, 255.999, 255.999, 110.500],  # yellow
    [610.0, 255.999, 180.500, 110.500],  # orange
    [650.0, 255.999, 110.500, 110.500],  # red
    [750.0, 255.999,  60.500,  60.500],  # ir
])
_RFUNC = Tabulation(_RGB_BY_NM[:, 0], _RGB_BY_NM[:, 1])
_GFUNC = Tabulation(_RGB_BY_NM[:, 0], _RGB_BY_NM[:, 2])
_BFUNC = Tabulation(_RGB_BY_NM[:, 0], _RGB_BY_NM[:, 3])


def hst_tint_from_nm(wavelength):
    """An RGB tint color based on a wavelength of light in nm."""

    wavelength = max(wavelength, _RGB_BY_NM[0, 0])
    wavelength = min(wavelength, _RGB_BY_NM[-1, 0])

    r = int(_RFUNC(wavelength))
    g = int(_GFUNC(wavelength))
    b = int(_BFUNC(wavelength))
    return (r, g, b)


__all__ = ['get_hst_filter_digits', 'hst_tint_from_nm']

##########################################################################################
