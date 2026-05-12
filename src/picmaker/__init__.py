"""rms-picmaker — convert PDS3/VICAR/FITS images to JPEG, TIFF, etc.

The package's public surface is re-exported from this module so that
consumers can write::

    from picmaker import images_to_pics, read_one_image_array

The top-level pipeline entry point is :func:`images_to_pics`; the
single-image reader is :func:`read_one_image_array`. The full set of
public names is in :data:`__all__`.
"""

try:
    from importlib.metadata import version as _version

    __version__ = _version('rms-picmaker')
except Exception:  # pragma: no cover — only fires when the package isn't installed
    try:
        from picmaker._version import __version__
    except ImportError:
        __version__ = '0.0.0+unknown'

from picmaker._filters import FILTER_DICT, filter_image
from picmaker.cli import main
from picmaker.color import BFUNC, GFUNC, RFUNC, RGB_BY_NM, tinted_colormap
from picmaker.enhance import (
    apply_colormap,
    apply_gamma,
    fill_zebra_stripes,
    get_limits,
)
from picmaker.geometry import (
    circle_mask,
    crop_array,
    get_size,
    pad_image,
    resize_image,
    rotate_array_rgb,
    slice_array,
    wrap_image,
)
from picmaker.io import (
    get_outfile,
    read_array,
    read_image_array,
    read_one_image_array,
    read_pds_labeled_image_array,
    read_pil,
)
from picmaker.pil_utils import array_to_pil, pil_to_array, write_pil
from picmaker.pipeline import find_common_path, images_to_pics, process_images

__all__ = [
    'BFUNC',
    'FILTER_DICT',
    'GFUNC',
    'RFUNC',
    'RGB_BY_NM',
    '__version__',
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
