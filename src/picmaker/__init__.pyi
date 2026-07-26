##########################################################################################
# picmaker/__init__.pyi
##########################################################################################
"""Type stub for the top-level picmaker package.

Mirrors the public objects re-exported by ``__init__.py``; the names listed in ``__all__``
are re-exported with the types defined in their source modules.
"""

# ruff: noqa: I001
from picmaker.colornames  import ColorNames
from picmaker.control     import get_filepaths, get_outfile
from picmaker.enhancement import apply_colormap
from picmaker.instruments import ImageData, read_image_array, tint_by_nm
from picmaker.layout      import pad_pil_image, wrap_pil_image
from picmaker.options     import deconflict_options, get_versions, validate_options
from picmaker.orientation import rotate_rgb_array
from picmaker.picmaker    import picmaker, picmaker1
from picmaker.pil_utils   import array_to_pil, pil_to_array, write_pil
from picmaker.postprocessing import adjust_pil_image, filter_pil_image
from picmaker.preprocessing  import fill_zebra_stripes
from picmaker.sizing      import get_size, resize_pil_image
from picmaker.slicing     import slice_array
from picmaker.stretch     import get_limits
from picmaker.tiff16      import read_tiff16, write_tiff16

__all__ = [
    'ColorNames',
    'ImageData',
    'adjust_pil_image',
    'apply_colormap',
    'array_to_pil',
    'deconflict_options',
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
