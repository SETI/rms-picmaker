"""Regenerate voyager_iss.vic — synthetic 16x16 Voyager ISS VICAR fixture.

Detection path (picmaker.py:1590-1592):
    if vic['LAB02'][:3] == 'VGR':
        filter_name = vic['LAB03'][37:43].rstrip()
        return (array3d, False, ('VOYAGER', 'ISS', filter_name))

Result: ('VOYAGER', 'ISS', 'GREEN').

Run from this directory:
    python voyager_iss.recipe.py
"""
from pathlib import Path

import numpy as np
from vicar import VicarImage

OUT = Path(__file__).parent.parent / 'fixtures' / 'voyager_iss.vic'


def main() -> None:
    vic = VicarImage.from_array(np.zeros((16, 16), dtype=np.int16))
    vic['LAB01'] = 'VGR ISS'
    vic['LAB02'] = 'VGR' + ' ' * 20             # LAB02[:3] == 'VGR'
    vic['LAB03'] = ' ' * 37 + 'GREEN ' + ' ' * 20  # GREEN at [37:43]
    assert vic['LAB03'][37:43] == 'GREEN '
    vic.write_file(str(OUT))


if __name__ == '__main__':
    main()
