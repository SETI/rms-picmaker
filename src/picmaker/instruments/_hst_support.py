##########################################################################################
# picmaker/instruments/_hst_support.py
##########################################################################################
"""Shared HST tools."""

import re

_FILTER_PATTERN = re.compile(r'[A-Z]+(\d\d\d+)[A-Z]+')


def get_hst_filter_digits(filter_name):
    """The integer embedded within the given filter name; ``None`` otherwise."""

    match = _FILTER_PATTERN.fullmatch(filter_name)
    if match:
        return int(match.group(1))

    return None


def is_science_hdu(hdu):
    """True if the HDU is a science ('SCI') extension."""
    if hdu.header.get('EXTNAME', '') == 'SCI':
        return True


__all__ = ['get_hst_filter_digits', 'is_science_hdu']

##########################################################################################
