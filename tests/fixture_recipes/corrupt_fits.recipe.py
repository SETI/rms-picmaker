"""Regenerate corrupt_fits.fits — FITS SIMPLE keyword followed by garbage.

picmaker.py:1602-1605 sniffs the first 9 bytes for b'SIMPLE  =' before calling
`astropy.io.fits.open`, which then raises AstropyUserWarning/OSError on the
malformed body. The cascade should fall through to PIL and finally raise
IOError('Unrecognized image file format ...').
"""
from pathlib import Path

OUT = Path(__file__).parent.parent / 'fixtures' / 'corrupt_fits.fits'


def main() -> None:
    OUT.write_bytes(b'SIMPLE  =' + b'\xff' * 100)


if __name__ == '__main__':
    main()
