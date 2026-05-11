"""Regenerate malformed_numpy.bin — numpy .npy magic followed by garbage.

Exercises `read_one_image_array`'s numpy branch (`np.load` raises
ValueError/IOError on parse failure); the cascade should fall through to VICAR,
FITS, PIL, and finally raise IOError('Unrecognized image file format ...').
"""
from pathlib import Path

OUT = Path(__file__).parent.parent / 'fixtures' / 'malformed_numpy.bin'


def main() -> None:
    OUT.write_bytes(b'\x93NUMPY\x01\x00' + b'\xff' * 50)


if __name__ == '__main__':
    main()
