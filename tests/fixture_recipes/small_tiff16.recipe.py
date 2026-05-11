"""Regenerate small_tiff16.tiff — 16-bit grayscale TIFF (WriteTiff16) so that
`read_array` exercises its 16-bit-TIFF branch.
"""
from pathlib import Path

import numpy as np

from picmaker.tiff16 import WriteTiff16

OUT = Path(__file__).parent.parent / 'fixtures' / 'small_tiff16.tiff'


def main() -> None:
    """Create an 8x8 uint16 array scaled by 1000 and write it to a TIFF.

    Uses WriteTiff16 to save the array. No arguments, returns None.
    Output destination is OUT.
    """
    arr = (np.arange(64, dtype=np.uint16) * 1000).reshape(8, 8)
    WriteTiff16(str(OUT), arr)


if __name__ == '__main__':
    main()
