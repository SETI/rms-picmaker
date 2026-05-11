"""Regenerate small_rgb.png — tiny 8-bit RGB PNG fixture."""
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).parent.parent / 'fixtures' / 'small_rgb.png'


def main() -> None:
    arr = np.zeros((8, 8, 3), dtype=np.uint8)
    arr[..., 0] = np.arange(64).reshape(8, 8)
    arr[..., 1] = 128
    arr[..., 2] = 200
    Image.fromarray(arr, mode='RGB').save(OUT)


if __name__ == '__main__':
    main()
