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
from picmaker.options     import (deconflict_options, get_versions, shift_to_zero_origin,
                                  validate_options)
from picmaker.orientation import rotate_rgb_array
from picmaker.pil_utils   import array_to_pil, write_pil
from picmaker.processing  import fill_zebra_stripes, filter_pil_image
from picmaker.sizing      import get_size, resize_pil_image
from picmaker.slicing     import slice_array
from picmaker.stretch     import get_limits


def picmaker(*, logger=None, _shift_origins=False, **options):
    r"""Convert one or more image data files into browse products.

    This function accepts the same options that the command line supports; any command
    line input produces the same results as this function with input
    ``**vars(get_parser().parse_args(argv))``. The exception is that the one-based,
    inclusive indexing in the command line, used for `obj`, `band`, `bands`, `lines`, and
    `samples`, is converted to zero-based, exclusive indexing in this function.

    All color may be given as an X11 name (e.g. "blue"), by an RGB tuple of three integers
    in the range 0-255, or by the string equivalent of an RGB tuple.

    Parameters:
        logger (Logger or PdsLogger, optional): Logger to use; None disables logging.
        _shift_origins (bool, optional): True to shift one-based indices to zero-based
            indices; used only for the command line input.

        files (list[str], optional): Input files or directories to convert.
        directory (str, optional): Directory to write outputs to. With `recursive` set,
            this is the root of a tree mirroring the source layout. The default is to
            write each output file to the input's own directory.
        recursive (bool, optional): Descend into input directories. Default is False.
        patterns (str or list[str], optional): One or more glob patterns that each file in
            an input directory mask match, e.g. "\*.IMG".
        movie (bool, optional): Share one set of enhancement limits across all images.
            This option is incompatible with `versions`. The default False.
        versions (str, optional): Path to a file whose non-blank lines each add a set of
            options, producing multiple output files for each input file.
        replace (str, optional): Behavior when the output exists: "all" (overwrite
            silently), "none" (skip), "warn", or "error". Default is "all".
        proceed (bool, optional): On a per-file error, log and continue rather than
            aborting. Ignored in `movie` mode. Default False.
        logging (str, optional): Verbosity of the logger, one of "debug", "info",
            "warning", or "error". The default is "info".
        obj (int, optional): Index of the image object to read, zero-based (unlike at the
            command line, where it is one-based. The default is to use the first image
            object in the file or among those selected by `pointers`.
        pointers (str or list[str], optional): One or more pointer strings identifying the
            image object in a PDS3 label or the HDU in a FITS file; these are tried in
            order.
        pds3_method (str, optional): Strictness for the PDS3 label reader. Options are
            "fast", "strict", "loose", or "compound". Default is "fast".
        zebra (bool, optional): Interpolate across zero-valued "zebra stripes" at the
            start and end of each line. Default is False.
        band (int, optional): Index of a single band to display in an image with multiple
            bands. Indexing is zero-based, unlike when it is used as a command line input.
            Incompatible with `bands`.
        bands (tuple[int, int], optional): Index of a range of bands to coadd to obtain
            the displayed image array. Indexing is zero-based, unlike when it is used as a
            command line input. Incompatible with `band`.
        lines (tuple[int, int], optional): Indices of the range of lines to include in the
            displayed image array. Indexing is zero-based, unlike when it is used as a
            command line input.
        samples (tuple[int, int], optional): Indices of the range of samples to include in
            the displayed image array. Indexing is zero-based, unlike when it is used as a
            command line input.
        crop (float, optional): Crop any boundary rows or columns whose pixels all equal
            this value.
        valid (tuple[float, float], optional): Numeric range of valid pixel values; pixels
            outside these limits are treated as invalid.
        limits (tuple[float, float], optional): Pixel values defining the stretch
            endpoints.
        percentiles (tuple[float, float], optional): Percentiles into the histogram of
            pixel values defining the stretch. The default is (0,100), but is ignored if
            `limits` is specified.
        trim (int, optional): The number of pixels to trim from each edge of the image
            before computing the stretch. Default is zero, but is ignored if `limits` is
            specified.
        trim_zeros (bool, optional): Ignore exterior rows and columns that are entirely
            zero before calculating a stretch. Default is False, but is ignored if
            `limits` is specified.
        footprint (int, optional): The diameter in pixels of a circular footprint by which
            to median-filter the image before computing the stretch. This can be used to
            suppress noise spikes that might otherwise corrupt the stretch. The default is
            0.
        colormap (str, tuple[int,int,int], or list[str, tuple[int,int,int]], optional):
            One or more color steps defining the colormap; a single color is shorthand for
            ["black", <color>, "white"].
        below_color (str or tuple[int,int,int], optional): Color to use for pixels below
            the lower limit of the stretch. The default is to use the first color in the
            `colormap`.
        above_color (str or tuple[int,int,int], optional): Color to use for pixels above
            the upper limit of the stretch. The default is to use the last color in the
            `colormap`.
        invalid_color (str or tuple[int,int,int], optional): Color to use for invalid
            pixels and NaNs. the default value is "black".
        gamma (float, optional): Gamma correction to apply to the image before the
            `colormap`. Values > 1 darken midtones; values < 1 brighten midtones. The
            default value is 1.
        tint (bool, optional): True to use the instrument/filter-based default colormap.
            Default is False.
        retint (float, optional): A factor to apply to the inferred filter wavelength for
            certain instrument filters before choosing the tint color. The default is
            0.4 for HST infrared instruments, 3 for HST UV instruments, and is ignored for
            other instruments.
        histogram (bool, optional): Use a flat-histogram stretch instead of a linear
            stretch. The default False.
        display_upward (bool, optional): Force line numbers to increase upward in the
            displayed image, overriding any instrument default.
        display_downward (bool, optional): Force line numbers to increase downward in the
            displayed image, overriding any instrument default.
        rotate (str, optional): Flip/rotate the image. Options are "none", "fliplr",
            "fliptb", "rot90", "rot180", or "rot270". Values are case-insensitive. The
            default is "none".
        size (tuple[int, int], optional): The output width and height in pixels. This
            option is incompatible with `frame`.
        scale (float, optional): Percentage by which to scale both axes.
        wscale (float, optional): Percentage by which to scale the image width only.
        hscale (float, optional): Percentage by which to scale the image height only.
        frame (tuple[int, int], optional): Width and height of a box the image
            must fit inside, preserving aspect ratio. Incompatible with `size`.
        frame_max (int, optional): Maximum percentage the image may be enlarged to fit
            into the frame.
        wrap (bool, optional): True to wrap a very elongated image into stacked sections.
            Default is False.
        wrap_ratio (float, optional): Wrap an image when the ratio of the longer to
            shorter dimension exceeds this value.
        overlap (float, optional): The percentage of overlap between the sections of a
            wrapped image. For example, if `overlap` is 5, then the last 5% of the pixels
            in each panel of the wrapped image will be repeated at the beginning of the
            next panel.
        overlaps (tuple[float, float], optional): Specify the `overlap` as a range of two
            percentages rather than as a single, fixed value.
        gap_size (int, optional): Width in pixels of the gap between wrapped sections. The
            sections. Default is 1.
        gap_color (str, optional): Color to use in the gap between wrapped sections. The
            default value is "white".
        pad (bool, optional): True to pad the output to the full size of the `frame` size.
            Default is False.
        pad_color (str, optional): Fill color used when padding. The default is "gray".
        mosaic (bool, optional): True to build an instrument-specific mosaic from a
            multi-detector exposure. This is implemented for HST WFPC2, producing a 2x2
            mosaic with PC1 at upper right (and not scaled relative to the others). It
            also stacks the two detectors in ACS/WFC and WFC3/UVIS images.
        filter (str, optional): An image filter to apply. Options are "none", "blur",
            "contour", "detail", "edge_enhance", "edge_enhance_more", "emboss",
            "find_edges", "smooth", "smooth_more", "sharpen", or one of "median_N",
            "minimum_N", or "maximum_N" where N is a window size of 3, 5, or 7 pixels.
            Default is "none".
        extension (str, optional): The extension of the output file name, which also
            defines the format of the output file. Options are "bmp", "dib", "gif", "jpg",
            "jpeg", "png", "tif", or "tiff", in lower- or upper-case. Default is "tiff"
            for `twobyte` images, "jpg" otherwise.
        suffix (str, optional): A suffix to be inserted before the extension in each
            output filename.
        strip (str or list[str], optional): One or more substrings to remove from the end
            of the filename stem before `suffix` is appended.
        quality (int, optional): The "quality" value to use for JPEG images, in the range
            1-100. The default is 75.
        twobytes (bool, optional): True to generate a 16-bit TIFF instead of an 8-bit
            image. Default is False.
    """

    if type(logger) is logging.Logger:
        logger = PdsLogger(logger)

    log_level = options.get('logging') or 'info'
    logger and logger.set_level(log_level)

    infiles_and_outdirs = get_filepaths(**options)
    if not infiles_and_outdirs:
        logger and logger.error('No input files identified')
        raise ValueError('No input files identified')

    movie = options.get('movie', False)
    proceed = options.get('proceed', False)
    versions = options.get('versions', None)

    # Remove fully-handled control options now
    for name in ('files', 'directory', 'recursive', 'patterns', 'movie', 'versions',
                 'logging'):
        options.pop(name)

    # Validate all remaining inputs
    try:
        if movie and versions:
            raise ValueError('--movie and --versions options are incompatible')
        options_list = get_versions(versions=versions, **options)
        for options in options_list:
            validate_options(options)
            deconflict_options(options)
            if _shift_origins:
                shift_to_zero_origin(options)
    except Exception as err:
        logger and logger.exception(err)
        raise

    # Functions below get their logger out of the options dict
    options['logger'] = logger

    # Process files...
    if movie:
        options = options_list[0]   # in `movie` mode there are never multiple versions
        entries = []                # (infile, outdir, image_data) for each readable file
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
                if not outfile:  # if replace='none' and the output file exists
                    continue
                picmaker1(infile, outfile, options, image_data=image_data)
            except Exception:
                if not proceed:
                    raise
                logger and logger.info('Proceeding after error')

    else:
        for infile, outdir in infiles_and_outdirs:
            image_data = None
            for options in options_list:
                try:
                    outfile = get_outfile(infile, outdir=outdir, **options)
                    if not outfile:  # replace='none' and the output already exists
                        continue
                    image_data = picmaker1(infile, outfile, options,
                                           image_data=image_data)
                except Exception:
                    if not proceed:
                        raise
                    logger and logger.info('Proceeding after error')


def picmaker1(infile, outfile, options, *, image_data=None, return_limits=False):
    """Write a single picmaker image.

    Parameters:
        infile (str or Path): Input data file path.
        outfile (str or Path): Output file path, ignored if `return_limits` is True.
        options (dict): A dictionary of all input parameters. See :meth:`picmaker` for
            details.
        image_data (ImageData): ImageData object if `infile` was already read; None
            otherwise.
        return_limits (bool, optional): Return limits tuple along with image_data

    Returns:
        ImageData or tuple[ImageData, tuple[float, float]]: The ImageData object from
        `infile`. If `return_limits` is True, also include the minimum and maximum limits
        obtained, and in this case do not write a file.
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
