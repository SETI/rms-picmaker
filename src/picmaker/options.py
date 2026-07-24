##########################################################################################
# picmaker/options.py
##########################################################################################
"""Support for command-line options and function input parameters."""

# ruff: noqa: I001
import argparse

from picmaker._version    import __version__
from picmaker.colornames  import ColorNames
from picmaker.control     import REPLACE_CHOICES
from picmaker.instruments import DEFAULT_PDS3_METHOD, PDS3_METHODS
from picmaker.orientation import ROTATE_CHOICES
from picmaker.pil_utils   import PIL_EXTENSIONS
from picmaker.processing  import FILTER_CHOICES

_LOGGING_CHOICES = ['warning', 'info', 'debug', 'error']


def get_parser():
    parser = argparse.ArgumentParser(
        description='A converter from image data files to "browse" products in JPG, PNG, '
                    'or other formats.',
        epilog='All color options can be specified by a name (e.g., "blue") or by three '
               'RGB values in the range 0-255 inside parentheses (e.g., "(255,255,0)" '
               'for yellow).',
        usage='%(prog)s [options] file1 file2 ...',
        prog='picmaker',
        exit_on_error=False)
    parser.add_argument('--version', action='version',
                        version='%(prog)s version ' + __version__)
    parser.add_argument('files', nargs='*', help='Input files or directories')

    _control = parser.add_argument_group('Control options')
    _control.add_argument(
        '-r', '--recursive', action='store_true',
        help='Search recursively down each directory trees.')
    _control.add_argument(
        '--pattern', dest='patterns', type=str, nargs='+',
        help=r'One or more patterns describing file names to match, e.g., \*.IMG.')
    _control.add_argument(
        '--movie', action='store_true',
        help='Use the same enhancement limits for all images.')
    _control.add_argument(
        '--versions', type=str,
        help='Create multiple versions of each picture using different sets of options, '
             'specified one per line in the named input file.')
    _control.add_argument(
        '--replace', type=str, choices=REPLACE_CHOICES,
        help='What to do when a file already exists, one of "all" (overwrite silently), '
             '"none" (skip silently), "warning" (issue a warning), "error" (raise an '
             'exception and abort). Default is "all".')
    _control.add_argument(
        '--proceed', action='store_true',
        help='Continue processing subsequent files after an error. Ignored in --movie '
             'mode.')
    _control.add_argument(
        '--logging', type=str, choices=_LOGGING_CHOICES,
        help='Logging level; default is "info".')

    _input_ = parser.add_argument_group('Input options')
    _input_.add_argument(
        '-o', '--object', dest='obj', type=int,
        help='Numeric index (starting at 1) of the image object in the file to display;  '
             'the default is to use the first valid image object in the file.')
    _input_.add_argument(
        '--pointer', dest='pointers', type=str, default=None, nargs='+',
        help='One or more pointer strings identifying the image object in a PDS3 label '
             'or the HDU in a FITS file.')
    _input_.add_argument(
        '--pds3-method', type=str, choices=PDS3_METHODS,
        help='Pds3Label parsing strictness for PDS3 .LBL inputs; default is '
             f'"{DEFAULT_PDS3_METHOD}".')

    _preprocessing = parser.add_argument_group('Pre-processing options')
    _preprocessing.add_argument(
        '--zebra', action='store_true', default=None,
        help='Interpolate across zero-valued "zebra stripes" at the beginnings and ends '
             'of lines.')

    _slicing = parser.add_argument_group('Slicing options')
    _slicing.add_argument(
        '-b', '--band', type=int,
        help='Index of the band to appear in the output image, with indices starting at '
             '1; default is 1.')
    _slicing.add_argument(
        '--bands', type=int, nargs=2,
        help='A pair of indices indicating a range of bands to be coadded. Band indices '
             'start at 1 and are inclusive of the upper limit specified.')
    _slicing.add_argument(
        '--lines', type=int, nargs=2,
        help='A pair of line indices defining the image sub-region to include. Line '
             'values start at 1 and are inclusive of the upper limit specified.')
    _slicing.add_argument(
        '--samples', type=int, nargs=2,
        help='A pair of sample indices defining the image sub-region to include. Sample '
             'values start at 1 and are inclusive of the upper limit specified.')
    _slicing.add_argument(
        '--crop', type=float,
        help='Crop boundary regions that entirely contain the specified value.')

    _stretch = parser.add_argument_group('Stretch options')
    _stretch.add_argument(
        '-v', '--valid', type=float, nargs=2,
        help='Range of valid pixel values; pixels outside are ignored.')
    _stretch.add_argument(
        '-l', '--limits', type=float, nargs=2,
        help='Pair of pixel values that define the limits of the stretch.')
    _stretch.add_argument(
        '-p', '--percentiles', type=float, nargs=2,
        help='Pair of percentile values that operate within the image limits; default is '
             '"0 100".')
    _stretch.add_argument(
        '--trim', type=int,
        help='Number of pixels around the edge of the image to trim before computing the '
             'limits and percentiles.')
    _stretch.add_argument(
        '--trim-zeros', action='store_true', default=None,
        help='Ignore exterior rows/columns containing all zeros.')
    _stretch.add_argument(
        '--footprint', type=int,
        help='Diameter in pixels of a circular footprint for a median filter to apply to '
             'the image prior to calculating the limits and percentiles. This can be '
             'used to suppress noise spikes prior to determining the optimal scaling.')

    _enhancement = parser.add_argument_group('Enhancement options')
    _enhancement.add_argument(
        '-c', '--colormap', type=str, nargs='+',
        help='A colormap to apply to the image, defined via one or more colors. For '
             'example, "black blue white" defines an image in which the darkest pixels '
             'are black, the brightest pixels are white, and intermediate values contain '
             'varying shades of blue. If a single color is specified, it is assumed to '
             'be shorthand for the colormap "black <color> white".')
    _enhancement.add_argument(
        '--below', dest='below_color', type=str,
        help='Color for pixels whose values are less than the lower limit of the '
             'stretch. By default, this is the first color of the colormap.')
    _enhancement.add_argument(
        '--above', dest='above_color', type=str,
        help='Color for pixels whose values are greater than the upper limit. By '
             ' default, this is the last color of the colormap.')
    _enhancement.add_argument(
        '--invalid', dest='invalid_color', type=str, default=None,
        help='Color to use for invalid pixels and NaNs. Default is black.')
    _enhancement.add_argument(
        '-g', '--gamma', type=float,
        help='Gamma value to apply to the image. Values > 1 darken midtones; values < 1 '
             'brighten midtones. The gamma factor is applied before the colormap.')
    _enhancement.add_argument(
        '--tint', action='store_true', default=None,
        help='Use a default colormap for the image based on the instrument and the '
             'filter used.')
    _enhancement.add_argument(
        '--retint', type=float,
        help='A factor to apply to the filter wavelength before determining the tint '
             'color. This can be used to map IR or UV instruments into the visual range. '
             'The default is 1 for most instruments, but 0.4 for NICMOS and WFC3/IR, '
             'and 3 for ACS/SBC. WFPC2 does not apply a retint factor.')
    _enhancement.add_argument(
        '--histogram', action='store_true', default=None,
        help='Use a histogram contrast stretch. This takes advantage of the full dynamic '
             'range within the limits of the stretch.')

    _orientation = parser.add_argument_group('Orientation options')
    _orientation.add_argument(
        '-u', '--up', dest='display_upward', action='store_true',
        help='Display the image with line numbers increasing upward, overriding the '
             'default for the instrument.')
    _orientation.add_argument(
        '-d', '--down', dest='display_downward', action='store_true',
        help='Display the image with line numbers increasing downward, overriding the '
             'default for the instrument.')
    _orientation.add_argument(
        '--rotate', type=str, choices=ROTATE_CHOICES,
        help='Rotate or flip the image from its default orientation; default is "none".')

    _sizing = parser.add_argument_group('Sizing options')
    _sizing.add_argument(
        '--size', type=int, nargs=2,
        help='Width and height of the output image in pixels.')
    _sizing.add_argument(
        '--scale', type=float,
        help='Percentage by which to scale both the width and height of the image.')
    _sizing.add_argument(
        '--wscale', type=float,
        help='Percentage by which to scale the width of the image.')
    _sizing.add_argument(
        '--hscale', type=float,
        help='Percentage by which to scale the height of the image.')
    _sizing.add_argument(
        '--frame', type=int, nargs=2,
        help='Width and height of the frame within which the image must fit.')
    _sizing.add_argument(
        '--frame_max', type=int,
        help='Maximum percentage by which to scale the image to fit it inside the frame.')

    _layout = parser.add_argument_group('Layout options')
    _layout.add_argument(
        '--wrap', action='store_true',
        help='Wrap the sections of an image if it is extremely elongated.')
    _layout.add_argument(
        '--wrap-ratio', type=float,
        help='Wrap if one of the ratios width/height or height/width exceeds this value.')
    _layout.add_argument(
        '--overlap', type=float,
        help='Percentage of required overlap between wrapped sections of an elongated '
             'image. For example, if the value is 5, then the last 5%% of each strip in '
             'the image will be repeated at the beginning of the next strip.')
    _layout.add_argument(
        '--overlaps', type=float, nargs=2,
        help='Minimum and maximum percentages of tolerated overlap between wrapped '
             'sections of an elongated image when it is wrapped.')
    _layout.add_argument(
        '--gap-size', type=int,
        help='Width in pixels of the gap between strips of a wrapped image. '
             'Default is 1.')
    _layout.add_argument(
        '--gap-color', type=str,
        help='Color to use for the gap between sections of a wrapped image. Default is '
             'white.')
    _layout.add_argument(
        '--pad', action='store_true',
        help='Pad the image to match the full size of the frame.')
    _layout.add_argument(
        '--pad-color', type=str,
        help='The color to use when padding an image to fill a frame. Default is gray.')
    _layout.add_argument(
        '--mosaic', action='store_true',
        help='Invoke the instrument-specific method for constructing a mosaic of images '
             'for an instrument that has multiple detectors.')

    _processing = parser.add_argument_group('Post-processing options')
    _processing.add_argument(
        '--filter', type=str, choices=FILTER_CHOICES,
        help='Apply an image processing filter to the image; default is "none".')

    _output = parser.add_argument_group('Output options')
    _output.add_argument(
        '-x', '--extension', type=str, choices=PIL_EXTENSIONS,
        help='File name extension for the image produced; this also defines the output '
             'file format. The default is "jpg" for 8-bit output and "tiff" for 16-bit '
             'outputs.')
    _output.add_argument(
        '--directory', type=str,
        help='Directory in which to place converted files. If the recursive option is '
             'selected, this becomes the root of a tree that parallels the subdirectory '
             'structure of the source files.')
    _output.add_argument(
        '-s', '--suffix', type=str,
        help='A suffix to append to the end of each file name, prior to the file '
             'extension.')
    _output.add_argument(
        '--strip', type=str, nargs='+',
        help='One or more strings to strip from output filename if it is present.')
    _output.add_argument(
        '-q', '--quality', type=int,
        help='Output quality value for JPEG files (1-100).')
    _output.add_argument(
        '--16', dest='twobytes', action='store_true',
        help='Output a 16-bit tiff instead of an 8-bit picture.')

    return parser


# This is a table of (name, default, type1[, min1, max1[, type2[, min2, max2]]])
# If `type1` is int or float, the next two values are its limits (or None for no limits).
# If `type1` is a list, then min1 and max1 are the length requirements and the remainder
# of the tuple defines the requirements on the elements.
_OPTION_DEFAULTS = [
    # NAME              , DEFAULT   , TYPE1             , TYPE2
    # Control options; note that all options except "replace" are handled by picmaker()
    ('replace'          , 'all'     , REPLACE_CHOICES                       ),
    # Input options
    ('obj'              , None      , int, 1, None                          ),
    ('pointers'         , []        , list, 0, None     , str               ),
    ('pds3_method'      , DEFAULT_PDS3_METHOD, PDS3_METHODS                 ),
    # Control options
    ('zebra'            , False     , bool                                  ),
    # Slicing options
    ('band'             , None      , int, 1, None                          ),
    ('bands'            , None      , list, 2, 2        , int, 1, None      ),
    ('lines'            , None      , list, 2, 2        , int, 1, None      ),
    ('samples'          , None      , list, 2, 2        , int, 1, None      ),
    ('crop'             , None      , float, None, None                     ),
    # Stretch options
    ('valid'            , None      , list, 2, 2        , float, None, None ),
    ('limits'           , None      , list, 2, 2        , float, None, None ),
    ('percentiles'      , [0, 100  ], list, 2, 2        , float, 0, 100     ),
    ('trim'             , 0         , int, 0, None                          ),
    ('trim_zeros'       , False     , bool                                  ),
    ('footprint'        , 0         , int, 0, None                          ),
    # Enhancement options
    ('colormap'         , None      , list, 0, None     , 'color'           ),
    ('below_color'      , None      , 'color'                               ),
    ('above_color'      , None      , 'color'                               ),
    ('invalid_color'    , 'black'   , 'color'                               ),
    ('gamma'            , 1.        , float, 0, None                        ),
    ('tint'             , False     , bool                                  ),
    ('retint'           , 1.        , float, 0, None                        ),
    ('histogram'        , False     , bool                                  ),
    # Orientation options
    ('display_upward'   , None      , bool                                  ),
    ('display_downward' , None      , bool                                  ),
    ('rotate'           , None      , ROTATE_CHOICES                        ),
    # Sizing options
    ('size'             , None      , list, 2, 2        , int, 1, None      ),
    ('scale'            , None      , float, 0, None                        ),
    ('wscale'           , None      , float, 0, None                        ),
    ('hscale'           , None      , float, 0, None                        ),
    ('frame'            , None      , list, 2, 2        , int, 1, None      ),
    ('frame_max'        , None      , float, 0, None                        ),
    # Layout options
    ('wrap'             , None      , bool                                  ),
    ('wrap_ratio'       , None      , float, 0, None                        ),
    ('overlap'          , None      , float, 0, 100                         ),
    ('overlaps'         , None      , list, 2, 2        , float, 0, 100     ),
    ('gap_size'         , 1         , int, 0, None                          ),
    ('gap_color'        , 'white'   , 'color'                               ),
    ('pad'              , False     , bool                                  ),
    ('pad_color'        , 'gray'    , 'color'                               ),
    ('mosaic'           , False     , bool                                  ),
    # Post-processing options
    ('filter'           , 'none'    , FILTER_CHOICES                        ),
    # Output options
    ('extension'        , None      , PIL_EXTENSIONS                        ),
    ('suffix'           , ''        , str                                   ),
    ('strip'            , []        , list, 0, None     , str               ),
    ('quality'          , 75        , int, 0, 100                           ),
    ('twobytes'         , False     , bool                                  ),
]


def validate_options(options):
    """Validate all Picmaker options.

    Parameters:
        options (dict): Picmaker inputs.

    Returns:
        dict: Dictionary of all input options.

    Raises:
        KeyError: If a parameter is not in among its restricted set of choices.
        TypeError: If the type of a parameter is not correct.
        ValueError: If any parameter has an invalid or contradictory value.
    """

    def check_value(name, value, info):
        """Validate type and length or numeric range. Return the converted value."""
        if value is None:
            return None

        type_, *more = info
        if type_ is list:
            minlen, maxlen, *more = more
            if not isinstance(value, (list, tuple)) and minlen <= 1:
                value = [value]
            elif not isinstance(value, (list, tuple)):
                raise TypeError(f'Invalid type {type(value).__name__} for "{name}": '
                                f'{value!r}')
            if minlen is not None and len(value) < minlen:
                raise ValueError(f'Invalid "{name}"; minimum length is {minlen}')
            if maxlen is not None and len(value) > maxlen:
                raise ValueError(f'Invalid "{name}"; maximum length is {maxlen}')
            checked = []
            for subvalue in value:
                checked.append(check_value(name, subvalue, more))
            return checked

        elif type_ in (int, float):
            if not isinstance(value, int if type_ is int else (int, float)):
                raise TypeError(f'Invalid type {type(value).__name__} for "{name}"')
            minval, maxval = more
            if minval is not None and value < minval:
                raise ValueError(f'Invalid value {value!r} for "{name}"; '
                                 f'minimum is {minval!r}')
            if maxval is not None and value > maxval:
                raise ValueError(f'Invalid value {value!r} for "{name}"; '
                                 f'maximum is {maxval!r}')
            return float(value) if type_ is float else value

        elif type_ == 'color':
            if isinstance(value, (tuple, list)):
                return tuple(value)          # already resolved to an RGB triple
            return ColorNames.lookup(value)  # forward any exception

        elif isinstance(type_, (list, tuple)):
            if value not in type_:
                raise KeyError(f'Unrecognized "{name}" option: {value!r}')

        elif type_ is bool:
            return bool(value)

        elif not isinstance(value, type_):
            raise TypeError(f'Invalid type {type(value).__name__} for "{name}": '
                            f'{value!r}')

        return value

    # Fill in defaults, validate all values, forwarding an exception
    for info in _OPTION_DEFAULTS:
        name, default, *type_info = info
        value = options.get(name) or default
        options[name] = check_value(name, value, type_info)

    return options


def deconflict_options(options):
    """Handle alternative input options.

    * `band` is deleted in favor of `bands`, always with two values if not None.
    * `wscale` and `hscale` are deleted in favor of `scale`, always with two values if not
      None.
    * `overlap` is deleted in favor of `overlaps`, always with two values.
    * `display_downward` is deleted in favor of `display_upward`.
    * `extension` is filled in with valid extension, whose value depends on `twobytes`.

    This step must wait till after all sets of `versions` have been obtained.

    Parameters:
        options (dict): Picmaker inputs, already validated.

    Returns:
        dict: The `options` dictionary, updated in place.

    Raises:
        ValueError: If any parameter has an invalid or contradictory value.
    """

    # band vs. bands -> bands
    band = options['band']
    if band is not None:
        bands = options['bands']
        if not bands:
            options['bands'] = (band, band)
        else:
            raise ValueError('--band and --bands options are incompatible')
    del options['band']

    # scale vs. (wscale, hscale) -> scale, a pair of values (wscale, hscale)
    scale = options['scale']
    wscale = options['wscale']
    hscale = options['hscale']
    if scale is None:
        # A scalar --scale is normalized by get_size; here we only consolidate
        # per-axis --wscale / --hscale into a (width, height) pair.
        if wscale is not None or hscale is not None:
            options['scale'] = (wscale if wscale is not None else 100.,
                                hscale if hscale is not None else 100.)
    elif wscale is not None:
        raise ValueError('--scale and --wscale options are incompatible')
    elif hscale is not None:
        raise ValueError('--scale and --hscale options are incompatible')
    del options['wscale']
    del options['hscale']

    # overlap vs. overlaps -> overlaps as two values
    overlap = options['overlap']
    overlaps = options['overlaps']
    if overlap is not None and overlaps is not None:
        raise ValueError('--overlap and --overlaps options are incompatible')
    overlap = overlap or 0.
    if overlaps is None:
        options['overlaps'] = (overlap, overlap)
    del options['overlap']

    # display_upward vs. display_downward -> display_upward
    display_downward = options['display_downward']
    if display_downward is not None:
        if options['display_upward'] is None:
            options['display_upward'] = not display_downward
        else:
            raise ValueError('--up and --down options are incompatible')
    del options['display_downward']

    # frame vs. size
    if options['frame'] is not None and options['size'] is not None:
        raise ValueError('--frame and --size options are incompatible')

    # twobyte option and default extension
    extension = options['extension']
    if extension is None:
        if options['twobytes']:
            options['extension'] = 'tiff'
        else:
            options['extension'] = 'jpg'
    elif options['twobytes'] and extension.lower() not in {'tif', 'tiff'}:
        raise ValueError('Only tiffs can be written in 16-bit mode')

    return options


def get_versions(versions=None, *, files=None, **options):
    """Read the versions file and return a list of options dictionaries.

    The options are not validated or deconflicted.

    Parameters:
        versions (str or Path, optional): Path to a "versions" file with alternative sets
            of command-line options, one set per row.
        files (list, optional): Placeholder to ensure `options` does not still contain a
            list of files to process.
        **options: Additional picmaker input parameters.

    Returns:
        list[dict]: One or more dictionaries of alternative input parameters.

    Raises:
        argparse.ArgumentError: If an error occurs parsing a line of the versions file.
        OSError: If a versions file does not exist or cannot be read.
        ValueError: If the versions file refers to additional input files or another
            versions file.
    """

    if not versions:
        return [options]

    parser = get_parser()

    with open(versions, 'r') as f:  # forward any OSErrors
        lines = f.readlines()

    # Each version line layers its option overrides onto a fresh copy of the base options,
    # so the versions are independent. Input files are optional in the parser, so a line
    # specifying only options parses cleanly; the resolved file list comes from the base
    # options, not from each version.
    options_list = []
    for line in lines:
        new_args = line.split()
        if not new_args:  # ignore a blank line in the file
            continue

        # Parse the line starting from the original namespace
        namespace = argparse.Namespace(**options)
        alt_namespace = parser.parse_args(new_args, namespace=namespace)

        # Apply restrictions on the content of the versions file
        if alt_namespace.files:
            raise ValueError(f'Versions file {versions} cannot list new input files: "'
                             + ", ".join(alt_namespace.files) + '"')
        for name in ('directory', 'recursive', 'patterns', 'movie', 'versions',
                     'logging'):
            if getattr(alt_namespace, name):
                raise ValueError(f'Versions file {versions} cannot redefine --{name}')

        options_list.append(alt_namespace.__dict__)

    if not options_list:
        options_list = [options]

    return options_list


_ONE_BASED_PAIRS   = ('samples', 'lines', 'bands')
_ONE_BASED_SCALARS = ('obj', 'band')


def shift_to_zero_origin(options):
    """Convert 1-based CLI index options to picmaker's 0-based convention.

    The command line and version files present "--obj", "--band", "--bands", "--lines",
    and "--samples" as 1-based (their validated minimum is 1); picmaker works in 0-based
    indices.

    This function mutates and returns the `options` dict, shifting each index option
    present with a non-None value.
    """

    for name in _ONE_BASED_PAIRS:
        value = options.get(name)
        if value is not None:
            options[name] = (value[0] - 1, value[1])

    for name in _ONE_BASED_SCALARS:
        value = options.get(name)
        if value is not None:
            options[name] = value - 1

    return options


__all__ = ['deconflict_options', 'get_parser', 'get_versions',  'shift_to_zero_origin',
           'validate_options']

##########################################################################################
