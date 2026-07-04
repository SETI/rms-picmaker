"""Regenerate corrupt_fits.fits — FITS SIMPLE keyword followed by garbage.

Sniffs the first 9 bytes for b'SIMPLE  =' before calling
:func:`astropy.io.fits.open`, which then raises AstropyUserWarning/OSError on the
malformed body. The cascade should fall through to :mod:`PIL` and finally raise
:class:`IOError`.
"""
from pathlib import Path

OUT = Path(__file__).parent.parent / 'fixtures' / 'corrupt_fits.fits'


def main() -> None:
    """Write corrupt FITS-like byte sequence to OUT.

    Writes a FITS magic header followed by garbage bytes to simulate a corrupt
    FITS file for testing error handling.

    Args:
        None

    Returns:
        None

    Side Effects:
        Writes bytes to OUT using OUT.write_bytes.
    """
    OUT.write_bytes(b'SIMPLE  =' + b'\xff' * 100)


if __name__ == '__main__':
    main()
