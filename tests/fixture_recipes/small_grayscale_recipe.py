"""Regenerate small_grayscale.png — tiny 8-bit grayscale PNG.

For :func:`read_pil` / :func:`read_array` / :func:`write_pil` round-trip tests.
"""
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).parent.parent / 'fixtures' / 'small_grayscale.png'


def main() -> None:
    """Create an 8x8 grayscale PNG for round-trip testing.

    Generates a uint8 array with values 0-63 and saves it as a grayscale PNG.

    Args:
        None

    Returns:
        None
    """
    arr = np.arange(64, dtype=np.uint8).reshape(8, 8)
    Image.fromarray(arr, mode='L').save(OUT)


if __name__ == '__main__':
    main()
