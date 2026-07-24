##########################################################################################
# picmaker/preprocessing.py
##########################################################################################
"""Pre-stretch array cleanup applied before the limits and colormap are computed."""

import numpy as np


def fill_zebra_stripes(array, **kwargs):
    """Fill zero zebra stripes around the edges of rows.

    Fills lines of zeros at the beginning and end of each row when the rows immediately
    above and below have nonzero values at the same columns. This removes an artifact
    associated with some spacecraft compression procedures.

    Parameters:
        array (array): A 2-D or 3-D array. It is not modified.
        **kwargs: Additional input options, ignored here.

    Returns:
        array[float]: A new floating-point array with the zebra stripes filled. The input
        is never modified, so a caller may reuse it (e.g. for a following version in which
        "--zebra" is not set).
    """

    # Get the dimensions
    lines, samples = array.shape[-2:]
    if lines <= 2:
        return array

    # Work on a float copy; the caller's array (shared across versions) is left untouched.
    array = array.astype('float')
    if array.ndim == 2:
        arrays = [array]
    else:
        arrays = [array[b] for b in range(array.shape[0])]

    # Loop through lines
    # lprev starts at 1 (row 0 peeks at row 1 as its "above" neighbor)
    for array2d in arrays:
        lprev = 1
        for line in range(lines):
            lnext = line + 1 if line + 1 < lines else line - 1

            row = array2d[line]
            above = array2d[lprev]
            below = array2d[lnext]

            nonzero = np.flatnonzero(row)
            if len(nonzero):
                ranges = [(0, nonzero[0]), (nonzero[-1]+1, samples)]
            else:
                ranges = [(0, samples)]

            for (s0, s1) in ranges:
                srange = np.arange(s0, s1)
                srange = srange[(above[srange] != 0) & (below[srange] != 0)]
                row[srange] = (above[srange] + below[srange]) / 2

            lprev = line

    return array


__all__ = ['fill_zebra_stripes']

##########################################################################################
