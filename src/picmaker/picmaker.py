"""Legacy import location. New code should import from :mod:`picmaker` directly.

This module re-exports the public API and selected internals to
preserve backward compatibility for ``from picmaker.picmaker import X``
callers. The functions here are the **same objects** as in their
canonical leaf modules (identity-equal — verified by
``tests/test_api_compat.py``).
"""



# CLI
from vicar import VicarError, VicarImage

# Filters
from picmaker._filters import FILTER_DICT, filter_image
from picmaker.cli import main

# Color (RGB constants re-exported from _rgb via color.py)
from picmaker.color import BFUNC, GFUNC, RFUNC, RGB_BY_NM, tinted_colormap

# Sibling-package re-exports (these were importable from picmaker.picmaker
# before PR 3 because the legacy module imported them at the top).
from picmaker.colornames import ColorNames

# Enhancement (incl. private helpers preserved for BC)
from picmaker.enhance import (
    _percentile_lookup,
    apply_colormap,
    apply_gamma,
    fill_zebra_stripes,
    get_limits,
)

# Geometry (incl. private helpers preserved for BC)
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

# Instrument dicts (legacy module-level access — pre-PR-3 picmaker.py:2245-2274).
# Aliased to preserve the original names that downstream scripts may import.
from picmaker.instruments.galileo import FILTER_DICT as GALILEO_SSI_DICT
from picmaker.instruments.galileo import FILTER_NAMES as GALILEO_SSI_NAMES
from picmaker.instruments.nh import FILTER_DICT as NH_MVIC_DICT
from picmaker.instruments.voyager import FILTER_DICT as VOYAGER_ISS_DICT

# I/O
from picmaker.io import (
    get_outfile,
    read_array,
    read_image_array,
    read_one_image_array,
    read_pds_labeled_image_array,
    read_pil,
)

# PIL utilities (incl. private helper preserved for BC)
from picmaker.pil_utils import _one_pil_to_array, array_to_pil, pil_to_array, write_pil

# Pipeline orchestrators
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
    # Instrument dicts (legacy)
    'VOYAGER_ISS_DICT',
    # Sibling re-exports
    'ColorNames',
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
    # PIL utilities
    'array_to_pil',
    'circle_mask',
    'crop_array',
    'fill_zebra_stripes',
    # Filters
    'filter_image',
    'find_common_path',
    # Enhancement (incl. private helpers preserved for BC)
    'get_limits',
    'get_outfile',
    'get_size',
    # Pipeline
    'images_to_pics',
    # CLI
    'main',
    'pad_image',
    'pil_to_array',
    'process_images',
    'read_array',
    # I/O
    'read_image_array',
    'read_one_image_array',
    'read_pds_labeled_image_array',
    'read_pil',
    'resize_image',
    'rotate_array_rgb',
    # Geometry (incl. private helpers preserved for BC)
    'slice_array',
    # Color
    'tinted_colormap',
    'wrap_image',
    'write_pil',
]

if __name__ == '__main__':
    main()
