"""BC contract: every name re-exported from `picmaker.picmaker` must be
identity-equal to the canonical leaf-module object.

This pins down the PR 3 promise that the legacy import path
``from picmaker.picmaker import X`` still resolves to the *same* function
object as the new path ``from picmaker import X`` — so user code that
swapped between paths keeps working with no shim layer.
"""

import picmaker
import picmaker.picmaker as legacy
from picmaker import _filters, color, enhance, geometry, io, pil_utils, pipeline


def test_cli_main_is_canonical():
    from picmaker.cli import main as cli_main

    assert legacy.main is cli_main
    assert picmaker.main is cli_main


def test_pipeline_symbols_are_canonical():
    assert legacy.images_to_pics is pipeline.images_to_pics
    assert legacy.process_images is pipeline.process_images
    assert legacy.find_common_path is pipeline.find_common_path
    assert picmaker.images_to_pics is pipeline.images_to_pics


def test_io_symbols_are_canonical():
    assert legacy.read_image_array is io.read_image_array
    assert legacy.read_one_image_array is io.read_one_image_array
    assert legacy.read_pds_labeled_image_array is io.read_pds_labeled_image_array
    assert legacy.read_pil is io.read_pil
    assert legacy.read_array is io.read_array
    assert legacy.get_outfile is io.get_outfile


def test_enhance_symbols_are_canonical():
    assert legacy.get_limits is enhance.get_limits
    assert legacy.apply_gamma is enhance.apply_gamma
    assert legacy.apply_colormap is enhance.apply_colormap
    assert legacy.fill_zebra_stripes is enhance.fill_zebra_stripes
    assert legacy._percentile_lookup is enhance._percentile_lookup


def test_geometry_symbols_are_canonical():
    assert legacy.slice_array is geometry.slice_array
    assert legacy.crop_array is geometry.crop_array
    assert legacy.rotate_array_rgb is geometry.rotate_array_rgb
    assert legacy.circle_mask is geometry.circle_mask
    assert legacy.get_size is geometry.get_size
    assert legacy.resize_image is geometry.resize_image
    assert legacy.wrap_image is geometry.wrap_image
    assert legacy.pad_image is geometry.pad_image
    assert legacy._get_size_for_size is geometry._get_size_for_size
    assert legacy._get_size_for_frame is geometry._get_size_for_frame
    assert legacy._resize_one_image is geometry._resize_one_image


def test_color_symbols_are_canonical():
    assert legacy.tinted_colormap is color.tinted_colormap
    assert legacy.RGB_BY_NM is color.RGB_BY_NM
    assert legacy.RFUNC is color.RFUNC
    assert legacy.GFUNC is color.GFUNC
    assert legacy.BFUNC is color.BFUNC


def test_pil_utils_symbols_are_canonical():
    assert legacy.array_to_pil is pil_utils.array_to_pil
    assert legacy.pil_to_array is pil_utils.pil_to_array
    assert legacy.write_pil is pil_utils.write_pil
    assert legacy._one_pil_to_array is pil_utils._one_pil_to_array


def test_filter_symbols_are_canonical():
    assert legacy.filter_image is _filters.filter_image
    assert legacy.FILTER_DICT is _filters.FILTER_DICT


def test_sibling_reexports_are_canonical():
    from vicar import VicarError, VicarImage

    from picmaker.colornames import ColorNames
    from picmaker.tiff16 import ReadTiff16, WriteTiff16

    assert legacy.ColorNames is ColorNames
    assert legacy.WriteTiff16 is WriteTiff16
    assert legacy.ReadTiff16 is ReadTiff16
    assert legacy.VicarImage is VicarImage
    assert legacy.VicarError is VicarError


def test_instrument_dicts_aliased_for_bc():
    from picmaker.instruments import galileo, nh, voyager

    assert legacy.VOYAGER_ISS_DICT is voyager.FILTER_DICT
    assert legacy.NH_MVIC_DICT is nh.FILTER_DICT
    assert legacy.GALILEO_SSI_DICT is galileo.FILTER_DICT
    assert legacy.GALILEO_SSI_NAMES is galileo.FILTER_NAMES


def test_package_level_imports_match_leaf_modules():
    """Smoke: every name in __all__ of picmaker resolves to the same
    object as ``picmaker.picmaker.<name>`` (for symbols that exist on
    both)."""
    for name in picmaker.__all__:
        if name == '__version__':
            continue
        pkg_obj = getattr(picmaker, name)
        if hasattr(legacy, name):
            assert getattr(legacy, name) is pkg_obj, (
                f'{name} differs between picmaker and picmaker.picmaker'
            )
