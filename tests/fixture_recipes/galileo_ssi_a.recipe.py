"""Regenerate galileo_ssi_a.vic — Galileo SSI VICAR (MISSION-keyword path).

Detection path (picmaker.py:1572-1576):
    if vic['MISSION'] == 'GALILEO':
        filtno = vic['FILTER']
        filter_name = GALILEO_SSI_NAMES[filtno]
        return (array3d, False, ('GALILEO', 'SSI', filter_name))

FILTER=1 maps to 'GREEN' in GALILEO_SSI_NAMES.

Run from this directory:
    python galileo_ssi_a.recipe.py
"""
from pathlib import Path

import numpy as np
from vicar import VicarImage

OUT = Path(__file__).parent.parent / 'fixtures' / 'galileo_ssi_a.vic'


def main() -> None:
    vic = VicarImage.from_array(np.zeros((16, 16), dtype=np.int16))
    vic['MISSION'] = 'GALILEO'
    vic['FILTER'] = 1   # index into GALILEO_SSI_NAMES → 'GREEN'
    vic.write_file(str(OUT))


if __name__ == '__main__':
    main()
