"""Regenerate malformed_pickle.bin — bytes that look like a pickle header but
are unloadable. Exercises the pickle branch's broad `except Exception:` in
`read_one_image_array`; the cascade should fall through to numpy → VICAR → FITS
→ PIL and ultimately raise IOError('Unrecognized image file format ...').
"""
from pathlib import Path

OUT = Path(__file__).parent / 'malformed_pickle.bin'


def main() -> None:
    OUT.write_bytes(b'\x80\x04' + b'\xff' * 100)


if __name__ == '__main__':
    main()
