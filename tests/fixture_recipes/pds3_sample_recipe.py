"""Regenerate pds3_sample.IMG — minimal PDS3-labeled image with 512-byte records.

The header uses RECORD_BYTES=512 / LABEL_RECORDS=1 because pdsparser's PDS3
parser rejects the 8-byte-record sketch from the modernization plan (the LABEL
contents themselves are ~480 bytes). Image data is an 8x8 uint8 ramp 0..63
padded out to 512 bytes.

NOTE: as of the current pdsparser version, `read_pds_labeled_image_array` does
not successfully consume this fixture — it iterates `for node in label` and
expects each element to have a `.name` attribute, which the dict-style Pds3Label
no longer supplies, and it references `pdsparser.PdsOffsetPointer` which no
longer exists in the package. The fixture is kept for use by the test cascade
(`read_one_image_array(fn, None)` falls through to the final IOError) and as a
ready-made regression fixture once PR 3 modernizes the reader.

Run from this directory:
    python pds3_sample_recipe.py
"""
from pathlib import Path

OUT = Path(__file__).parent.parent / 'fixtures' / 'pds3_sample.IMG'

LABEL = (
    b"PDS_VERSION_ID                 = PDS3\r\n"
    b"RECORD_TYPE                    = FIXED_LENGTH\r\n"
    b"RECORD_BYTES                   = 512\r\n"
    b"FILE_RECORDS                   = 2\r\n"
    b"LABEL_RECORDS                  = 1\r\n"
    b"^IMAGE                         = 2\r\n"
    b"OBJECT                         = IMAGE\r\n"
    b"  LINES                        = 8\r\n"
    b"  LINE_SAMPLES                 = 8\r\n"
    b"  SAMPLE_BITS                  = 8\r\n"
    b"  SAMPLE_TYPE                  = UNSIGNED_INTEGER\r\n"
    b"END_OBJECT                     = IMAGE\r\n"
    b"END\r\n"
)


def main() -> None:
    padded_label = LABEL + b' ' * (512 - len(LABEL))
    image = bytes(range(8 * 8))
    padded_image = image + b'\0' * (512 - len(image))
    OUT.write_bytes(padded_label + padded_image)


if __name__ == '__main__':
    main()
