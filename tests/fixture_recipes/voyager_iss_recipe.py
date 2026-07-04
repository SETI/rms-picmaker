"""Regenerate voyager_iss.vic — synthetic 16x16 Voyager ISS VICAR fixture.

Detection logic checks if LAB02[:3] == 'VGR', then extracts filter_name from
LAB03[37:43] and returns ('VOYAGER', 'ISS', filter_name).

Result: ('VOYAGER', 'ISS', 'GREEN').

Run from this directory:
    python voyager_iss_recipe.py
"""
from pathlib import Path

import numpy as np
from vicar import VicarImage

OUT = Path(__file__).parent.parent / 'fixtures' / 'voyager_iss.vic'


def main() -> None:
    """Build a test VicarImage with Voyager ISS label fields.

    Uses VicarImage.from_array to create the image, sets label fields LAB01,
    LAB02, and LAB03, asserts expected content for LAB03, and writes the image
    via vic.write_file. Returns None.
    """
    vic = VicarImage.from_array(np.zeros((16, 16), dtype=np.int16))
    vic['LAB01'] = 'VGR ISS'
    vic['LAB02'] = 'VGR' + ' ' * 20             # LAB02[:3] == 'VGR'
    vic['LAB03'] = ' ' * 37 + 'GREEN ' + ' ' * 20  # GREEN at [37:43]
    assert vic['LAB03'][37:43] == 'GREEN '
    vic.write_file(str(OUT))


if __name__ == '__main__':
    main()
