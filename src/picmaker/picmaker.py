##########################################################################################
# picmaker/picmaker.py
##########################################################################################
"""Complete ``picmaker`` functionality in a single function call."""

import argparse
import os

import numpy as np

from picmaker.cli         import PARSER
from picmaker.control     import get_filepaths, get_outfile
from picmaker.enhancement import apply_colormap
from picmaker.instruments import read_image_array
from picmaker.layout      import wrap_pil_image, pad_pil_image
from picmaker.orientation import rotate_rgb_array
from picmaker.pil_utils   import array_to_pil, write_pil, PIL_EXTENSIONS
from picmaker.processing  import fill_zebra_stripes, filter_pil_image
from picmaker.scaling     import get_limits
from picmaker.sizing      import get_size, resize_pil_image
from picmaker.slicing     import slice_array


def validate_options(options):
    """Convert an argparse Namespace to a dict if necessary and validate values.

    Parameters:
        options (argparse.Namespace or dict): Picmaker inputs.

    Returns:
        (dict): Dictionary of all input options. These are used as ``**kwargs`` input to
        many functions.

    Raises:
        ValueError: If any parameter has an invalid or contradictory value.
    """

    if not isinstance(options, dict):
        options = options.__dict__

    extension = options.get('extension') or 'jpg'
    if extension.lower() not in PIL_EXTENSIONS:
        raise ValueError(f'unrecognized --extension: {extension!r}')
    options['extension'] = extension

    names_to_delete = []

    # band vs. bands -> bands
    band = options.get('band', None)
    bands = options.get('bands', None)
    if band is not None:
        if bands is None:
            options['bands'] = (band, band)
        else:
            raise ValueError('--band and --bands options are incompatible')

    # scale vs. (wscale, hscale) -> scale, a pair of values (wscale, hscale)
    scale = options.get('scale', None)
    wscale = options.get('wscale', None)
    hscale = options.get('hscale', None)
    if scale is not None and wscale is not None:
        raise ValueError('--scale and --wscale options are incompatible')
    if scale is not None and hscale is not None:
        raise ValueError('--scale and --hscale options are incompatible')
    if scale is None:
        scale = 100.
    if np.isscalar(scale):
        options['scale'] = (wscale if wscale is not None else scale,
                            hscale if hscale is not None else scale)
    names_to_delete += ['wscale', 'hscale']

    # overlap vs. overlaps -> overlaps. A default-filled overlaps of (0., 0.), left by an
    # earlier validation of a versions base, does not conflict with a per-version
    # --overlap; the explicit --overlap wins.
    overlap = options.get('overlap', None)
    overlaps = options.get('overlaps', None)
    if overlap is not None and overlaps not in (None, (0., 0.)):
        raise ValueError('--overlap and --overlaps options are incompatible')
    if overlap is not None:
        options['overlaps'] = (overlap, overlap)
    elif overlaps is None:
        options['overlaps'] = (0., 0.)
    names_to_delete.append('overlap')

    # display_upward vs. display_downward -> display_upward
    display_upward = options.get('display_upward', None)
    display_downward = options.get('display_downward', None)
    if display_downward is not None:
        if display_upward is None:
            options['display_upward'] = not display_downward
        else:
            raise ValueError('--up and --down options are incompatible')
    names_to_delete.append('display_downward')

    # frame vs. size
    if options['frame'] is not None and options['size'] is not None:
        raise ValueError('--frame and --size options are incompatible')

    # two-byte vs. extension
    if options.get('twobytes', False):
        extension = options.get('extension', '')
        if extension and extension.lower() not in ('tif', 'tiff', '.tif', '.tiff'):
            raise ValueError('only tiffs can be written in 16-bit mode')

    # movie vs. versions
    versions = options.get('versions', None)
    if versions:
        if options.get('movie', False):
            raise ValueError('--movie and --versions options are incompatible')

        if not os.path.exists(versions):
            raise FileNotFoundError(f'--versions file not found: "{versions}"')

    for name in names_to_delete:
        if name in options:
            del options[name]

    return options


def get_versions(versions=None, **kwargs):
    """Read the versions file and return a list of options dictionaries."""

    if not versions:
        return [kwargs]

    with open(versions, 'r') as f:  # forward any OSErrors
        lines = f.readlines()

    # Each version line layers its option overrides onto a fresh copy of the base options,
    # so the versions are independent. Input files are optional in the parser, so a line
    # specifying only options parses cleanly; the resolved file list comes from the base
    # options, not from each version.
    options_list = []
    for line in lines:
        new_args = line.split()
        if not new_args:
            continue

        namespace = argparse.Namespace(**kwargs)
        alt_namespace = PARSER.parse_args(new_args, namespace=namespace)
        alt_options = validate_options(alt_namespace)
        options_list.append(alt_options)

    return options_list


def picmaker(logger=None, **options):

    validate_options(options)

    log_level = options.get('logging', 'info')
    if logger:
        logger.set_level(log_level)

    infiles_and_outdirs = get_filepaths(**options)
    if not infiles_and_outdirs:
        raise ValueError('no input files identified')

    movie = options.get('movie', False)
    options_list = get_versions(**options)

    names_to_delete = ['files', 'directory', 'recursive', 'patterns', 'movie', 'logging',
                       'versions']
    for options in options_list:
        for name in names_to_delete:
            if name in options:
                del options[name]

    if movie:
        options = options_list[0]
        imagedata_list = []
        min_limit = np.inf
        max_limit = -np.inf
        for infile, outdir in infiles_and_outdirs:
            (image_data, limits) = picmaker1(infile, '', options, logger=logger,
                                             return_limits=True)
            imagedata_list.append(image_data)
            min_limit = min(min_limit, limits[0])
            max_limit = max(max_limit, limits[1])

        options['limits'] = (min_limit, max_limit)
        options['percentiles'] = None

        for k, image_data in enumerate(imagedata_list):
            infile = infiles_and_outdirs[k][0]
            outdir = infiles_and_outdirs[k][1]
            outfile = get_outfile(infile, outdir=outdir, **options)
            picmaker1(infile, outfile, options, logger=logger, image_data=image_data)

    else:
        for infile, outdir in infiles_and_outdirs:
            image_data = None
            for options in options_list:
                outfile = get_outfile(infile, outdir=outdir, **options)
                image_data = picmaker1(infile, outfile, options, logger=logger,
                                       image_data=image_data)


def picmaker1(infile, outfile, options, *, logger=None, image_data=None,
              return_limits=False):
    """Write one picmaker image.

    Parameters:
        infile (str or pathlib.Path): Input data file path.
        outfile (str or pathlib.Path): Output file path.
        options (dict): Dictionary of all input parameters.
        logger (PdsLogger): Logger to use.
        image_data (:class:`ImageData`): ImageData object if `infile` was already read;
            None otherwise.
        return_limits (bool, optional): Return limits tuple along with image_data

    Returns:
        (:class:`ImageData` or ``(image_data, min_limit, max_limit)``: The ImageData
        object from ``infile``. If ``return_limits`` is True, also include the minimum and
        maximum limits obtained, and do not save a file.
    """

    # Read the image only if necessary
    if image_data is None:
        logger and logger.debug('Reading data file', infile)
        image_data = read_image_array(infile, **options)

    # Slice out the part we care about
    array, invalid_mask = slice_array(image_data.array, **options)

    # Fill zebra stripes
    if options.get('zebra', False):
        array = array.copy()
        fill_zebra_stripes(array, **options)

    # Assemble a mosaic if necessary; convert to RGB or grayscale arrays scaled 0-1
    mosaic = options.get('mosaic', False)
    if mosaic and array.ndim == 3 and hasattr(image_data, 'apply_mosaic'):
        # Get the scaling limits and apply the colormap to each band
        rgb_arrays = []
        min_limits = []
        max_limits = []
        for b in range(array.shape[0]):
            limits = get_limits(array[b], invalid_mask[b], **options)
            array_rgb = apply_colormap(array, limits,
                                       default_tint=image_data.default_tint, **options)
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
        array_rgb = apply_colormap(array, limits,
                                   default_tint=image_data.default_tint, **options)

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


__all__ = ['validate_options', 'get_versions', 'picmaker', 'picmaker1']

##########################################################################################
