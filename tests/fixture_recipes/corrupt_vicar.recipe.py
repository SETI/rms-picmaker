"""Regenerate corrupt_vicar.vic — VICAR-flavored header followed by truncated body.

Triggers VicarError inside the VICAR branch of `read_one_image_array`; the
cascade should fall through to FITS, PIL, and finally raise IOError
('Unrecognized image file format ...').
"""
from pathlib import Path

OUT = Path(__file__).parent.parent / 'fixtures' / 'corrupt_vicar.vic'


def main() -> None:
    # Garbage bytes with no LBLSIZE keyword. The VICAR parser raises VicarError
    # ("Missing LBLSIZE keyword") which read_one_image_array catches at the
    # outer `except VicarError:` so the cascade can continue.
    OUT.write_bytes(b'\xff' * 200)


if __name__ == '__main__':
    main()
