"""Regenerate small_grayscale.png — tiny 8-bit grayscale PNG for read_pil /
read_array / write_pil round-trip tests.
"""
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).parent / 'small_grayscale.png'


def main() -> None:
    arr = np.arange(64, dtype=np.uint8).reshape(8, 8)
    Image.fromarray(arr, mode='L').save(OUT)


if __name__ == '__main__':
    main()
