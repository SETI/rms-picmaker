"""Regenerate cassini_iss.vic — synthetic 16x16 Cassini ISS VICAR fixture.

Detection path (read_one_image_array, current picmaker.py:1564-1567):
    if vic['INSTRUMENT_HOST_NAME'] == 'CASSINI ORBITER':
        (filter1, filter2) = vic['FILTER_NAME']
        return (array3d, False, ('CASSINI', 'ISS', filter1 + "+" + filter2))

Result: detected as ('CASSINI', 'ISS', 'CL1+GRN').

Run from this directory:
    python cassini_iss.recipe.py
"""
from pathlib import Path

import numpy as np
from vicar import VicarImage

OUT = Path(__file__).parent / 'cassini_iss.vic'


def main() -> None:
    data = np.zeros((16, 16), dtype=np.int16)
    vic = VicarImage.from_array(data)
    vic['INSTRUMENT_HOST_NAME'] = 'CASSINI ORBITER'
    vic['FILTER_NAME'] = ['CL1', 'GRN']
    vic.write_file(str(OUT))


if __name__ == '__main__':
    main()
