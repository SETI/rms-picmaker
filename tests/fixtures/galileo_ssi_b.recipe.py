"""Regenerate galileo_ssi_b.vic — Galileo SSI VICAR (LAB01-keyword path).

Detection path (picmaker.py:1581-1584):
    if vic['LAB01'][:7] == 'GLL/SSI':
        filtno = int(vic['LAB03'].partition('FILTER=')[2][0])
        filter_name = GALILEO_SSI_NAMES[filtno]
        return (array3d, False, ('GALILEO', 'SSI', filter_name))

Run from this directory:
    python galileo_ssi_b.recipe.py
"""
from pathlib import Path

import numpy as np
from vicar import VicarImage

OUT = Path(__file__).parent / 'galileo_ssi_b.vic'


def main() -> None:
    vic = VicarImage.from_array(np.zeros((16, 16), dtype=np.int16))
    vic['LAB01'] = 'GLL/SSI'
    vic['LAB03'] = 'FILTER=1'
    vic.write_file(str(OUT))


if __name__ == '__main__':
    main()
