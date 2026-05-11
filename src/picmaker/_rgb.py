"""Wavelength → RGB lookup tables.

Leaf module — no internal package imports — so that `color.py`,
`instruments/hst.py`, and anyone else can use these tables without
producing an import cycle.

Source: ``picmaker.picmaker.py`` (pre-PR-3) module-level constants at
lines 2279-2292.
"""

import numpy as np
from numpy.typing import NDArray
from tabulation import Tabulation

# [wavelength_nm, r, g, b] — values are floats (RGB channels can fall
# between 60.5 and 255.999), NOT uint8.
RGB_BY_NM: NDArray[np.float64] = np.array(
    [
        [380.0, 200.500, 60.500, 255.999],  # uv
        [410.0, 200.500, 110.500, 255.999],  # violet
        [480.0, 110.500, 110.500, 255.999],  # blue
        [540.0, 110.500, 255.999, 110.500],  # green
        [580.0, 255.999, 255.999, 110.500],  # yellow
        [610.0, 255.999, 180.500, 110.500],  # orange
        [650.0, 255.999, 110.500, 110.500],  # red
        [750.0, 255.999, 60.500, 60.500],  # ir
    ]
)

RFUNC: Tabulation = Tabulation(RGB_BY_NM[:, 0], RGB_BY_NM[:, 1])
GFUNC: Tabulation = Tabulation(RGB_BY_NM[:, 0], RGB_BY_NM[:, 2])
BFUNC: Tabulation = Tabulation(RGB_BY_NM[:, 0], RGB_BY_NM[:, 3])

__all__ = ['BFUNC', 'GFUNC', 'RFUNC', 'RGB_BY_NM']
