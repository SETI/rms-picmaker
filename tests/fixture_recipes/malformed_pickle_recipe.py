"""Regenerate malformed_pickle.bin — bytes that look like a pickle header but
are unloadable. Exercises the pickle branch's broad `except Exception:` in
:func:`read_one_image_array`; the cascade should fall through to numpy → VICAR →
FITS → :mod:`PIL` and ultimately raise :class:`IOError`.
"""
from pathlib import Path

OUT = Path(__file__).parent.parent / 'fixtures' / 'malformed_pickle.bin'


def main() -> None:
    """Write malformed pickle bytes to OUT for testing error handling.

    Writes pickle protocol 4 header followed by garbage bytes.

    Args:
        None

    Returns:
        None

    Side Effects:
        Writes bytes to OUT via OUT.write_bytes.
    """
    OUT.write_bytes(b'\x80\x04' + b'\xff' * 100)


if __name__ == '__main__':
    main()
