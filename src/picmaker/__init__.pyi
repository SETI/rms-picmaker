##########################################################################################
# picmaker/__init__.pyi
##########################################################################################
"""Type stub for the top-level picmaker package.

Mirrors the public objects re-exported by ``__init__.py``; the names listed in ``__all__``
are re-exported with the types defined in their source modules.
"""

# ruff: noqa: I001
from picmaker.cli         import main
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
from picmaker.stretch     import get_limits
from picmaker.sizing      import get_size, resize_pil_image
from picmaker.slicing     import slice_array
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
    'main',
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
