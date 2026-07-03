##########################################################################################
# picmaker/picmaker.py
##########################################################################################
"""Complete ``picmaker`` functionality in a single function call."""

# ruff: noqa: I001
import logging

import numpy as np
from pdslogger import PdsLogger

from picmaker.control     import get_filepaths, get_outfile
from picmaker.instruments import read_image_array
from picmaker.layout      import pad_pil_image, wrap_pil_image
from picmaker.options     import deconflict_options, get_versions, validate_options
from picmaker.orientation import rotate_rgb_array
from picmaker.pil_utils   import array_to_pil, write_pil
from picmaker.processing  import fill_zebra_stripes, filter_pil_image
from picmaker.sizing      import get_size, resize_pil_image
from picmaker.slicing     import slice_array
from picmaker.stretch     import get_limits


def picmaker(logger=None, **options):
    """Validate options, resolve the input files, and drive :func:`picmaker1` over each.

    Parameters:
        logger (Logger or PdsLogger, optional): Logger to use.
        **options: The dictionary of command options.

    In "movie" mode, common enhancement limits are computed across all images before
    writing; otherwise each input file is processed once per version.
    """

    if type(logger) is logging.Logger:
        logger = PdsLogger(logger)

    log_level = options.get('logging', 'info')
    logger and logger.set_level(log_level)

    validate_options(options, logger=logger)
    options['logger'] = logger  # many functions get the logger out of the options dict

    infiles_and_outdirs = get_filepaths(**options)
    if not infiles_and_outdirs:
        logger and logger.error('no input files identified')
        raise ValueError('no input files identified')

    movie = options.get('movie', False)
    proceed = options.get('proceed', False)
    versions = options.get('versions', None)

    # Remove fully-handled options now
    for name in ('files', 'directory', 'recursive', 'patterns', 'movie', 'logging',
                 'versions'):
        if name in options:
            del options[name]  # noqa: RUF051

    if movie:
        deconflict_options(options)
        entries = []        # (infile, outdir, image_data) for each readable file
        min_limit = np.inf
        max_limit = -np.inf
        for infile, outdir in infiles_and_outdirs:
            try:
                image_data, limits = picmaker1(infile, '', options, return_limits=True)
            except Exception:
                if not proceed:
                    raise
                logger and logger.info('Proceeding after error')
            else:
                entries.append((infile, outdir, image_data))
                min_limit = min(min_limit, limits[0])
                max_limit = max(max_limit, limits[1])

        options['limits'] = (min_limit, max_limit)
        options['percentiles'] = None

        for infile, outdir, image_data in entries:
            try:
                outfile = get_outfile(infile, outdir=outdir, **options)
                if not outfile:     # if replace='none' and the output file exists
                    continue
                picmaker1(infile, outfile, options, image_data=image_data)
            except Exception:
                if not proceed:
                    raise
                logger and logger.info('Proceeding after error')

    else:
        options_list = get_versions(versions=versions, **options)
        for infile, outdir in infiles_and_outdirs:
            image_data = None
            for options in options_list:
                try:
                    outfile = get_outfile(infile, outdir=outdir, **options)
                    if not outfile:     # replace='none' and the output already exists
                        continue
                    image_data = picmaker1(infile, outfile, options,
                                           image_data=image_data)
                except Exception:
                    if not proceed:
                        raise
                    logger and logger.info('Proceeding after error')


def picmaker1(infile, outfile, options, *, image_data=None, return_limits=False):
    """Write one picmaker image.

    Parameters:
        infile (str or Path): Input data file path.
        outfile (str or Path): Output file path.
        options (dict): Dictionary of all input parameters.
        image_data (ImageData): ImageData object if `infile` was already read; None
            otherwise.
        return_limits (bool, optional): Return limits tuple along with image_data

    Returns:
        ImageData or tuple[ImageData, tuple[float, float]]: The ImageData object from
        `infile`. If `return_limits` is True, also include the minimum and maximum limits
        obtained, and do not save a file.
    """

    logger = options.get('logger', None)

    # Read the image only if necessary
    if image_data is None:
        logger and logger.debug('Reading data file', infile)
        image_data = read_image_array(infile, **options)

    # Slice out the part we care about
    array, invalid_mask = slice_array(image_data.array, **options)

    # Fill zebra stripes
    if options.get('zebra', False):
        array = fill_zebra_stripes(array, **options)

    # Assemble a mosaic if necessary; convert to RGB or grayscale arrays scaled 0-1
    mosaic = options.get('mosaic', False)
    if mosaic and array.ndim == 3 and hasattr(image_data, 'apply_mosaic'):
        # Get the scaling limits and apply the colormap to each band
        rgb_arrays = []
        min_limits = []
        max_limits = []
        for b in range(array.shape[0]):
            # slice_array returns None when no pixels are masked; index per band only
            # when there is a mask.
            mask_b = None if invalid_mask is None else invalid_mask[b]
            limits = get_limits(array[b], mask_b, **options)
            array_rgb = image_data.apply_colormap(array[b], limits,
                                                  invalid_mask=mask_b, **options)
            rgb_arrays.append(array_rgb)
            min_limits.append(limits[0])
            max_limits.append(limits[1])
        limits = (np.min(min_limits), np.max(max_limits))
        if return_limits:
            return (image_data, limits)
        array_rgb = image_data.apply_mosaic(rgb_arrays, **options)

    else:
        # Just get the scaling limits and apply the colormap; merge bands into one
        limits = get_limits(array, invalid_mask, **options)
        if return_limits:
            return (image_data, limits)
        array_rgb = image_data.apply_colormap(array, limits, invalid_mask=invalid_mask,
                                              **options)

    # Set the orientation
    array_rgb = rotate_rgb_array(array_rgb, default_upward=image_data.default_upward,
                                 **options)

    # Determine the size and layout
    (unwrapped_size, wrapped_size, sections, wrap_axis) = get_size(array_rgb.shape,
                                                                   **options)

    # Convert to PIL
    image = array_to_pil(array_rgb, twobytes=options.get('twobytes', False))

    # Apply filter
    image = filter_pil_image(image, **options)

    # Resize PIL image
    image = resize_pil_image(image, unwrapped_size)

    # Wrap the PIL image if necessary
    if sections > 1:
        image = wrap_pil_image(image, wrapped_size, sections, wrap_axis, **options)

    # Pad the PIL image if necessary
    image = pad_pil_image(image, **options)

    # Write image via PIL or as a 16-bit TIFF
    logger and logger.info('Writing', outfile)
    write_pil(image, outfile, options.get('quality', 75))

    return image_data


__all__ = ['picmaker', 'picmaker1']

##########################################################################################
