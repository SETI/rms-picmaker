"""Alternate import path that re-exports the full :mod:`picmaker` public API.

Every name surfaced here is the same object as the canonical
leaf-module symbol (verified by ``tests/test_api_compat.py``), so
``from picmaker.picmaker import images_to_pics`` and
``from picmaker import images_to_pics`` resolve to the same function.
"""

from vicar import VicarError, VicarImage

from picmaker._filters import FILTER_DICT, filter_image
from picmaker.cli import main
from picmaker.color import BFUNC, GFUNC, RFUNC, RGB_BY_NM, tinted_colormap
from picmaker.colornames import ColorNames
from picmaker.enhance import (
    _percentile_lookup,
    apply_colormap,
    apply_gamma,
    fill_zebra_stripes,
    get_limits,
)
from picmaker.geometry import (
    _get_size_for_frame,
    _get_size_for_size,
    _resize_one_image,
    circle_mask,
    crop_array,
    get_size,
    pad_image,
    resize_image,
    rotate_array_rgb,
    slice_array,
    wrap_image,
)
from picmaker.instruments.galileo import FILTER_DICT as GALILEO_SSI_DICT
from picmaker.instruments.galileo import FILTER_NAMES as GALILEO_SSI_NAMES
from picmaker.instruments.nh import FILTER_DICT as NH_MVIC_DICT
from picmaker.instruments.voyager import FILTER_DICT as VOYAGER_ISS_DICT
from picmaker.io import (
    get_outfile,
    read_array,
    read_image_array,
    read_one_image_array,
    read_pds_labeled_image_array,
    read_pil,
)
from picmaker.options import PicmakerOptions
from picmaker.pil_utils import _one_pil_to_array, array_to_pil, pil_to_array, write_pil
from picmaker.pipeline import find_common_path, images_to_pics, process_images
from picmaker.tiff16 import ReadTiff16, WriteTiff16

__all__ = [
    'BFUNC',
    'FILTER_DICT',
    'GALILEO_SSI_DICT',
    'GALILEO_SSI_NAMES',
    'GFUNC',
    'NH_MVIC_DICT',
    'RFUNC',
    'RGB_BY_NM',
    'VOYAGER_ISS_DICT',
    'ColorNames',
    'PicmakerOptions',
    'ReadTiff16',
    'VicarError',
    'VicarImage',
    'WriteTiff16',
    '_get_size_for_frame',
    '_get_size_for_size',
    '_one_pil_to_array',
    '_percentile_lookup',
    '_resize_one_image',
    'apply_colormap',
    'apply_gamma',
    'array_to_pil',
    'circle_mask',
    'crop_array',
    'fill_zebra_stripes',
    'filter_image',
    'find_common_path',
    'get_limits',
    'get_outfile',
    'get_size',
    'images_to_pics',
    'main',
    'pad_image',
    'pil_to_array',
    'process_images',
    'read_array',
    'read_image_array',
    'read_one_image_array',
    'read_pds_labeled_image_array',
    'read_pil',
    'resize_image',
    'rotate_array_rgb',
    'slice_array',
    'tinted_colormap',
    'wrap_image',
    'write_pil',
]

if __name__ == '__main__':
    main()
