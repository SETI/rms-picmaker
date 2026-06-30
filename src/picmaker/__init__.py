##########################################################################################
# picmaker/__init__.py
##########################################################################################
"""Top-level picmaker package.

Re-exports the public objects defined across the package's public modules so that each
can be imported directly from ``picmaker``. Private modules (those whose names begin with
an underscore), the instrument subclasses of :class:`ImageData`, and ALL_CAPS module
constants are intentionally not re-exported.
"""

# ruff: noqa: I001
from picmaker.colornames  import ColorNames
from picmaker.control     import get_filepaths, get_outfile
from picmaker.enhancement import apply_colormap
from picmaker.instruments import (ImageData, read_image_array, register_instrument,
                                  tint_by_nm)
from picmaker.layout      import pad_pil_image, wrap_pil_image
from picmaker.orientation import rotate_rgb_array
from picmaker.picmaker    import get_versions, picmaker, picmaker1, validate_options
from picmaker.pil_utils   import array_to_pil, pil_to_array, write_pil
from picmaker.processing  import fill_zebra_stripes, filter_pil_image
from picmaker.sizing      import get_size, resize_pil_image
from picmaker.slicing     import slice_array
from picmaker.stretch     import get_limits
from picmaker.tiff16      import read_tiff16, write_tiff16

__all__ = [
    'ColorNames',
    'ImageData',
    'apply_colormap',
    'array_to_pil',
    'fill_zebra_stripes',
    'filter_pil_image',
    'get_filepaths',
    'get_limits',
    'get_outfile',
    'get_size',
    'get_versions',
    'pad_pil_image',
    'picmaker',
    'picmaker1',
    'pil_to_array',
    'read_image_array',
    'read_tiff16',
    'register_instrument',
    'resize_pil_image',
    'rotate_rgb_array',
    'slice_array',
    'tint_by_nm',
    'validate_options',
    'wrap_pil_image',
    'write_pil',
    'write_tiff16',
]

##########################################################################################
