"""Command-line entry point for picmaker.

The :func:`main` function builds an :mod:`argparse` parser covering
every option documented in ``picmaker --help`` and dispatches to
:func:`picmaker.pipeline.process_images`. Each long flag also has an
underscore alias (``--alt_strip`` for ``--alt-strip``, etc.) so older
scripts that use the underscore spelling keep working.

Error handling follows three layers:

* :class:`SystemExit` raised by argparse's own usage errors propagates
  through unchanged.
* Mutex / value-validity checks raise :class:`ValueError`; the outer
  ``except Exception`` wrapper prints the traceback via
  :func:`sys.excepthook` (so any plugin / IDE / profiler hook attached
  to ``sys.excepthook`` still fires) and exits with code 1.
* :exc:`KeyboardInterrupt` prints ``*** KeyboardInterrupt ***`` and
  exits with code 2.

The ``filter`` argparse dest deliberately shadows the builtin so the
``option_dict`` it builds passes straight through to
:func:`picmaker.pipeline.images_to_pics`. The per-file ``A002`` ruff
ignore lives in ``pyproject.toml``.
"""


import argparse
import fnmatch
import logging
import os
import shlex
import sys
from typing import Any

from picmaker.options import PDS3_LABEL_METHODS, PicmakerOptions
from picmaker.pipeline import find_common_path, process_images

logger = logging.getLogger(__name__)

_EXTENSION_CHOICES = [
    'BMP', 'bmp', 'DIB', 'dib',
    'GIF', 'gif',
    'JPG', 'jpg', 'JPEG', 'jpeg',
    'PNG', 'png',
    'TIF', 'tif', 'TIFF', 'tiff',
]

_ROTATE_CHOICES = [
    'NONE', 'none',
    'FLIPLR', 'fliplr',
    'FLIPTB', 'fliptb',
    'ROT90', 'rot90',
    'ROT180', 'rot180',
    'ROT270', 'rot270',
]

_FILTER_CHOICES = [
    'NONE', 'none',
    'BLUR', 'blur',
    'CONTOUR', 'contour',
    'DETAIL', 'detail',
    'EDGE_ENHANCE', 'edge_enhance',
    'EDGE_ENHANCE_MORE', 'edge_enhance_more',
    'EMBOSS', 'emboss',
    'FIND_EDGES', 'find_edges',
    'SMOOTH', 'smooth',
    'SMOOTH_MORE', 'smooth_more',
    'SHARPEN', 'sharpen',
    'MEDIAN_3', 'median_3',
    'MEDIAN_5', 'median_5',
    'MEDIAN_7', 'median_7',
    'MINIMUM_3', 'minimum_3',
    'MINIMUM_5', 'minimum_5',
    'MINIMUM_7', 'minimum_7',
    'MAXIMUM_3', 'maximum_3',
    'MAXIMUM_5', 'maximum_5',
    'MAXIMUM_7', 'maximum_7',
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage='%(prog)s [options] file1 file2 ...',
        prog='picmaker',
    )
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('files', nargs='*', help='input files or directories')

    control = parser.add_argument_group('control options')
    control.add_argument(
        '--directory', dest='directory', type=str, default=None,
        help='directory in which to place converted files. If the recursive '
             'option is selected, this becomes the root of a tree which '
             'parallels that of the source files.',
    )
    control.add_argument(
        '-r', '--recursive', dest='recursive', action='store_true', default=False,
        help='search recursively down directory trees.',
    )
    control.add_argument(
        '--pattern', dest='pattern', type=str, default='*',
        help='pattern describing file names to match, e.g., *.IMG.',
    )
    control.add_argument(
        '--movie', dest='movie', action='store_true', default=False,
        help='use the same enhancement limits for all images.',
    )
    control.add_argument(
        '--versions', dest='versions', type=str, default=None,
        help='create multiple versions of the picture using different sets of '
             'options, specified one per line in the named input file.',
    )
    control.add_argument(
        '--verbose', dest='verbose', type=int, default=0,
        help='1 to print out the name of each directory in a recursive search; '
             '2 to print out each file path.',
    )
    control.add_argument(
        '--replace', dest='replace', type=str, default='all',
        help='what to do when a file already exists ("all", "none", "warn", '
             '"error").',
    )
    control.add_argument(
        '--proceed', dest='proceed', action='store_true', default=False,
        help='continue processing subsequent files after an error.',
    )

    output = parser.add_argument_group('output options')
    output.add_argument(
        '-x', '--extension', dest='extension', default=None,
        choices=_EXTENSION_CHOICES,
        help='file name extension for image produced.',
    )
    output.add_argument(
        '-s', '--suffix', dest='suffix', type=str, default='',
        help='a suffix to append to the end of each file name, prior to the '
             'file extension.',
    )
    output.add_argument(
        '--strip', dest='strip', type=str, default='',
        help='a string to strip from output filename if it is present.',
    )
    output.add_argument(
        '--alt-strip', '--alt_strip', dest='alt_strip', type=str, default=None,
        help='an additional string to strip from output filename if it is present.',
    )
    output.add_argument(
        '-q', '--quality', dest='quality', type=int, default=75,
        help='output quality value for JPEG files (1-100).',
    )
    output.add_argument(
        '--16', dest='twobytes', action='store_true', default=False,
        help='output a 16-bit tiff instead of an 8-bit picture.',
    )

    selection = parser.add_argument_group('selection options')
    selection.add_argument(
        '-b', '--band', dest='band', type=int, default=None,
        help='index of the band to appear in the output image; default 1.',
    )
    selection.add_argument(
        '--bands', dest='bands', type=int, nargs=2, default=None,
        help='pair of indices indicating a range of bands to be averaged.',
    )
    selection.add_argument(
        '--rectangle', dest='rectangle', type=int, nargs=4, default=None,
        help='corner coordinates of a rectangular sub-region '
             '(sample1, line1, sample2, line2).',
    )
    selection.add_argument(
        '-o', '--object', dest='obj', type=int, default=None,
        help='numeric index of the object in the file to display; default is '
             'the first valid image object in the file.',
    )
    selection.add_argument(
        '--pointer', dest='pointer', type=str, default='IMAGE',
        help='the PDS pointer identifying the image object.',
    )
    selection.add_argument(
        '--alt-pointer', '--alt_pointer', dest='alt_pointer',
        type=str, default=None,
        help='alternative PDS pointer used when the first pointer is not found.',
    )
    selection.add_argument(
        '--pds3-label-method', '--pds3_label_method',
        dest='pds3_label_method',
        type=str, default='strict',
        choices=list(PDS3_LABEL_METHODS),
        help='pdsparser.PdsLabel parsing strictness for PDS3 .LBL inputs: '
             '"strict" (default), "loose", "compound", or "fast".',
    )

    sizing = parser.add_argument_group('sizing options')
    sizing.add_argument(
        '--size', dest='size', type=int, nargs=2, default=None,
        help='width and height of the output image in pixels.',
    )
    sizing.add_argument(
        '--scale', dest='scale', type=float, default=None,
        help='percentage by which to scale the size of the image.',
    )
    sizing.add_argument(
        '--wscale', dest='wscale', type=float, default=None,
        help='percentage by which to scale the width of the image.',
    )
    sizing.add_argument(
        '--hscale', dest='hscale', type=float, default=None,
        help='percentage by which to scale the height of the image.',
    )
    sizing.add_argument(
        '--crop', dest='crop', type=float, default=None,
        help='crop boundary regions entirely containing the specified value.',
    )
    sizing.add_argument(
        '--frame', dest='frame', type=int, nargs=2, default=None,
        help='width and height of the frame within which the image must fit.',
    )
    sizing.add_argument(
        '--pad', dest='pad', action='store_true', default=False,
        help='pad the image to match the full size of the frame.',
    )
    sizing.add_argument(
        '--pad-color', dest='pad_color', type=str, default='black',
        help='the color to use when padding an image to fill a frame.',
    )
    sizing.add_argument(
        '--frame_max', dest='frame_max', type=int, default=None,
        help='maximum percentage by which to scale the image to fit it inside '
             'the frame.',
    )

    layout = parser.add_argument_group('layout options')
    layout.add_argument(
        '--wrap', dest='wrap', action='store_true', default=False,
        help='wrap the sections of an image if it is extremely elongated.',
    )
    layout.add_argument(
        '--wrap-ratio', dest='wrap_ratio', type=float, default=None,
        help='wrap if width:height or height:width ratio exceeds this value.',
    )
    layout.add_argument(
        '--overlap', dest='overlap', type=float, default=None,
        help='percentage of overlap between wrapped sections.',
    )
    layout.add_argument(
        '--overlaps', dest='overlaps', type=float, nargs=2, default=None,
        help='range of percentages of overlaps between wrapped sections.',
    )
    layout.add_argument(
        '--gap-size', '--gapsize', dest='gap_size', type=int, default=1,
        help='width of the gap in pixels between sections of a wrapped image.',
    )
    layout.add_argument(
        '--gap-color', '--gapcolor', dest='gap_color', type=str, default='white',
        help='color of the gap between sections of a wrapped image.',
    )
    layout.add_argument(
        '--hst', dest='hst', action='store_true', default=False,
        help='construct a mosaic using all the detectors of an HST image.',
    )

    scaling = parser.add_argument_group('scaling options')
    scaling.add_argument(
        '-v', '--valid', dest='valid', type=float, nargs=2, default=None,
        help='range of valid pixel values; pixels outside are ignored.',
    )
    scaling.add_argument(
        '-l', '--limits', dest='limits', type=float, nargs=2, default=None,
        help='pair of pixel values that define the limits of the histogram.',
    )
    scaling.add_argument(
        '-p', '--percentiles', dest='percentiles', type=float, nargs=2,
        default=(0.0, 100.0),
        help='pair of percentile values that define the limits of the histogram.',
    )
    scaling.add_argument(
        '--trim', dest='trim', type=int, default=0,
        help='number of pixels around the edge of the image to trim before '
             'computing a histogram.',
    )
    scaling.add_argument(
        '--trim-zeros', '--trimzeros', dest='trim_zeros',
        action='store_true', default=False,
        help='ignore exterior rows/columns containing all zeros.',
    )
    scaling.add_argument(
        '--footprint', dest='footprint', type=int, default=0,
        help='diameter in pixels of a circular footprint for a median filter.',
    )
    scaling.add_argument(
        '--histogram', dest='histogram', action='store_true', default=False,
        help='use a histogram stretch.',
    )

    enhancement = parser.add_argument_group('enhancement options')
    enhancement.add_argument(
        '-c', '--colormap', dest='colormap', type=str, default=None,
        help='colormap to apply (e.g., "black-white" or "black-blue-white").',
    )
    enhancement.add_argument(
        '--below', dest='below_color', type=str, default=None,
        help='color for pixel values below the lower limit.',
    )
    enhancement.add_argument(
        '--above', dest='above_color', type=str, default=None,
        help='color for pixel values above the upper limit.',
    )
    enhancement.add_argument(
        '--invalid', dest='invalid_color', type=str, default='black',
        help='color for invalid pixel values and NaNs.',
    )
    enhancement.add_argument(
        '-g', '--gamma', dest='gamma', type=float, default=1.0,
        help='gamma value to apply to grayscale.',
    )
    enhancement.add_argument(
        '--tint', dest='tint', action='store_true', default=False,
        help="override the colormap based on the image's filter name.",
    )

    orientation = parser.add_argument_group('orientation options')
    orientation.add_argument(
        '-u', '--up', dest='display_upward', action='store_true', default=False,
        help='display the image with line numbers increasing upward.',
    )
    orientation.add_argument(
        '-d', '--down', dest='display_downward', action='store_true', default=False,
        help='display the image with line numbers increasing downward.',
    )
    orientation.add_argument(
        '--rotate', dest='rotate', default='none', choices=_ROTATE_CHOICES,
        help='rotate or flip the image from its default orientation.',
    )

    processing = parser.add_argument_group('processing options')
    processing.add_argument(
        '-f', '--filter', dest='filter_name', default='none', choices=_FILTER_CHOICES,
        help='name of image processing filter to apply.',
    )
    processing.add_argument(
        '--zebra', dest='zebra', action='store_true', default=False,
        help='interpolate across black zebra stripes at the beginnings and '
             'ends of lines.',
    )

    return parser


def _separate_files_and_dirs(args: list[str]) -> tuple[list[str], list[str]]:
    """Split positional arguments into existing files vs. directories.

    Trailing slashes on directory paths are stripped; anything that is
    not an existing file is treated as a directory.
    """
    filenames: list[str] = []
    directories: list[str] = []
    for f in args:
        if os.path.isfile(f):
            filenames.append(f)
        else:
            if f.endswith('/'):
                f = f[:-1]
            directories.append(f)
    return filenames, directories


def _normalize_and_validate(
    options: argparse.Namespace, replace: str, proceed: bool
) -> dict[str, Any]:
    """Run mutex checks, normalize parameter shapes, and build the option_dict.

    Parameters:
        options: Parsed argparse Namespace.
        replace: The validated ``--replace`` value (``'all'`` / ``'none'``
            / ``'warn'`` / ``'error'``).
        proceed: The validated ``--proceed`` flag.

    Returns:
        The ``option_dict`` consumed by ``images_to_pics``. Validation
        failures raise :class:`ValueError`.
    """
    if options.hst and (options.band is not None or options.bands is not None):
        raise ValueError('hst and band options are incompatible')
    if (
        options.band is not None
        and options.bands is not None
        and (
            options.band != options.bands[0]
            or options.band != options.bands[1]
        )
    ):
        raise ValueError('band and bands options are incompatible')

    if options.hst and options.movie:
        raise ValueError('hst and movie options are incompatible')

    if options.scale is not None and options.wscale is not None:
        raise ValueError('scale and wscale options are incompatible')

    if options.scale is not None and options.hscale is not None:
        raise ValueError('scale and hscale options are incompatible')

    if options.overlap is not None and options.overlaps is not None:
        raise ValueError('overlap and overlaps options are incompatible')

    # The frame/size, up/down, and twobytes-mode checks moved into
    # PicmakerOptions.validate() (called at the bottom of this function);
    # keeping them inline here would duplicate the post-normalization
    # invariants the dataclass owns.

    if not options.hst:
        if options.band is None:
            options.band = 0
        if options.bands is None:
            options.bands = (options.band, options.band + 1)

    if options.rectangle is None:
        samples: Any = None
        lines: Any = None
    else:
        samples = sorted([options.rectangle[0] - 1, options.rectangle[2]])
        lines = sorted([options.rectangle[1] - 1, options.rectangle[3]])

    if options.scale is None:
        options.scale = 100.0
    if options.wscale is None:
        options.wscale = options.scale
    if options.hscale is None:
        options.hscale = options.scale

    options.scale = (options.wscale, options.hscale)

    if options.valid is not None:
        options.valid = tuple(sorted(options.valid))
    if options.limits is not None:
        options.limits = tuple(sorted(options.limits))
    if options.percentiles is not None:
        options.percentiles = tuple(sorted(options.percentiles))

    if options.alt_pointer is not None:
        options.pointer = [options.pointer, options.alt_pointer]
    if options.alt_strip is not None:
        options.strip = [options.strip, options.alt_strip]

    if options.overlaps is None:
        if options.overlap is None:
            options.overlaps = (0.0, 0.0)
        else:
            options.overlaps = (options.overlap, options.overlap)

    option_dict: dict[str, Any] = {
        # control parameters
        'replace': replace,
        'proceed': proceed,
        # output options
        'extension': options.extension,
        'suffix': options.suffix,
        'strip': options.strip,
        'quality': options.quality,
        'twobytes': options.twobytes,
        # selection options
        'bands': options.bands,
        'lines': lines,
        'samples': samples,
        'obj': options.obj,
        'pointer': options.pointer,
        'pds3_label_method': options.pds3_label_method,
        # sizing options
        'size': options.size,
        'scale': options.scale,
        'crop': options.crop,
        'frame': options.frame,
        'pad': options.pad,
        'pad_color': options.pad_color,
        'frame_max': options.frame_max,
        # layout options
        'wrap': options.wrap,
        'wrap_ratio': options.wrap_ratio,
        'overlap': options.overlaps,
        'gap_size': options.gap_size,
        'gap_color': options.gap_color,
        'hst': options.hst,
        # scaling options
        'valid': options.valid,
        'limits': options.limits,
        'percentiles': options.percentiles,
        'trim': options.trim,
        'trim_zeros': options.trim_zeros,
        'footprint': options.footprint,
        'histogram': options.histogram,
        # enhancement options
        'colormap': options.colormap,
        'below_color': options.below_color,
        'above_color': options.above_color,
        'invalid_color': options.invalid_color,
        'gamma': options.gamma,
        'tint': options.tint,
        # orientation options
        'display_upward': options.display_upward,
        'display_downward': options.display_downward,
        'rotate': options.rotate.lower(),
        # special processing options
        'filter_name': options.filter_name.lower(),
        'zebra': options.zebra,
    }
    # Single source of truth for post-normalization mutex / value-validity
    # checks. The CLI runs this here so failures surface immediately
    # (before any I/O); pipeline.images_to_pics runs the same check on
    # its own so library callers that bypass the CLI get the same guarantee.
    PicmakerOptions(**option_dict).validate()
    return option_dict


def _collect_option_dicts(
    parser: argparse.ArgumentParser,
    options: argparse.Namespace,
    *,
    replace: str,
    proceed: bool,
) -> list[dict[str, Any]]:
    """Build the list of normalized ``option_dict`` dicts that drive the pipeline.

    When ``options.versions`` is ``None`` a single-element list is
    returned containing the normalization of ``options`` itself. When
    it is a file path, each non-blank line is tokenised with
    :func:`shlex.split` (so quoted values with embedded whitespace are
    preserved) and re-parsed as additional CLI args appended to
    ``sys.argv[1:]``; each merged namespace is normalized via
    :func:`!_normalize_and_validate`. The main CLI's ``--replace`` and
    ``--proceed`` always win over per-line values.

    Parameters:
        parser: The argparse parser, reused so per-line merges share
            the canonical option defaults.
        options: Parsed namespace from the main CLI argv.
        replace: The validated ``--replace`` value, propagated to every
            versions-line namespace.
        proceed: The validated ``--proceed`` flag, propagated to every
            versions-line namespace.

    Returns:
        One normalized ``option_dict`` per versions-file line (or a
        single-element list when ``--versions`` was not given). Each
        dict is the keyword-argument shape consumed by
        :func:`picmaker.pipeline.images_to_pics`.
    """
    if options.versions is None:
        return [_normalize_and_validate(options, replace, proceed)]

    namespaces: list[argparse.Namespace] = []
    with open(options.versions, encoding='utf-8') as f:
        version_lines = f.readlines()
    for line in version_lines:
        # ``shlex.split`` (not ``str.split``) so quoted values with
        # embedded whitespace round-trip through argparse the same way
        # they would on the shell command line.
        new_args = shlex.split(line)
        if len(new_args) == 0:
            continue
        merged = parser.parse_args(sys.argv[1:] + new_args)
        # Versions-file lines do not override the main CLI's --replace
        # / --proceed values; force the merged namespace back to the
        # main-CLI values before normalization.
        merged.replace = replace
        merged.proceed = proceed
        namespaces.append(merged)

    return [_normalize_and_validate(ns, replace, proceed) for ns in namespaces]


def _process_directory(
    dirpath: str,
    *,
    recursive: bool,
    pattern: str,
    directory: str | None,
    lcommon: int,
    movie: bool,
    option_dicts: list[dict[str, Any]],
    verbose: int,
) -> None:
    """Process every file under ``dirpath`` that matches ``pattern``.

    Walks the tree with :func:`os.walk` when ``recursive`` is set,
    otherwise reads ``dirpath`` non-recursively. When ``directory`` is
    set, the output tree under it parallels the source tree using the
    ``lcommon`` prefix length computed by the caller from
    :func:`picmaker.pipeline.find_common_path`.

    Parameters:
        dirpath: Source directory.
        recursive: Recurse into subdirectories.
        pattern: :mod:`fnmatch`-style filename pattern.
        directory: Output directory root, or ``None`` to write next to
            the source files.
        lcommon: Length of the common source-prefix, or ``-1`` when
            there is no useful prefix (means: output directly under
            ``directory``).
        movie: Run the per-directory dispatch in movie mode.
        option_dicts: List of normalized option dicts (one per
            ``--versions`` line).
        verbose: Per-CLI verbosity level. ``>=1`` logs each visited
            directory; ``>1`` is propagated as
            :func:`~picmaker.pipeline.process_images`' ``verbose`` flag.
    """
    if recursive:
        for this_dir, _subdirs, files_in_dir in os.walk(dirpath):
            f_filtered = fnmatch.filter(files_in_dir, pattern)
            if len(f_filtered) == 0:
                continue
            if verbose:
                logger.info('%s', this_dir)
            filepaths = [os.path.join(this_dir, f) for f in f_filtered]
            out_dir = (
                None
                if directory is None
                else os.path.join(directory, this_dir[lcommon + 1 :])
            )
            process_images(
                filepaths, out_dir, movie, option_dicts,
                verbose=(verbose > 1),
            )
        return

    if verbose:
        logger.info('%s', dirpath)
    files_in_dir = os.listdir(dirpath)
    f_filtered = fnmatch.filter(files_in_dir, pattern)
    # ``os.listdir`` returns both files and subdirectories; the
    # recursive branch above relies on ``os.walk`` to separate them, so
    # this branch must filter out subdirectories whose name happens to
    # match ``pattern`` (otherwise they'd flow into ``process_images``
    # as if they were files).
    filepaths = [
        os.path.join(dirpath, f)
        for f in f_filtered
        if os.path.isfile(os.path.join(dirpath, f))
    ]
    if len(filepaths) == 0:
        return
    out_dir = (
        None
        if directory is None
        else os.path.join(directory, dirpath[lcommon + 1 :])
    )
    process_images(
        filepaths, out_dir, movie, option_dicts, verbose=(verbose > 1),
    )


def main() -> None:
    """Picmaker CLI entry point.

    Argparse usage errors raise :class:`SystemExit` (passed through).
    Validation errors raise :class:`ValueError`; the outer
    ``except Exception`` wrapper prints them via
    :func:`sys.excepthook` and exits with code 1.
    """
    try:
        parser = _build_parser()
        options = parser.parse_args()

        if options.movie and options.versions is not None:
            raise ValueError('movie and versions options are incompatible')

        directory = options.directory
        if directory is not None and directory.endswith('/'):
            directory = directory[:-1]

        if options.verbose not in (0, 1, 2):
            raise ValueError(f'unrecognized verbose option: {options.verbose}')

        if options.replace not in ('all', 'none', 'warn', 'error'):
            raise ValueError(f'unrecognized replace option: "{options.replace}"')

        replace = options.replace
        proceed = options.proceed
        verbose = options.verbose
        movie = options.movie
        pattern = options.pattern
        recursive = options.recursive

        filenames, directories = _separate_files_and_dirs(options.files)
        option_dicts = _collect_option_dicts(
            parser, options, replace=replace, proceed=proceed,
        )

        filtered = fnmatch.filter(filenames, pattern)
        if filtered:
            process_images(
                filtered, directory, movie, option_dicts, verbose=(verbose > 1)
            )

        common_prefix = find_common_path(directories)
        if filenames:
            common_prefix = os.path.split(common_prefix)[0]
        lcommon = len(common_prefix) if common_prefix else -1

        for dirpath in directories:
            _process_directory(
                dirpath,
                recursive=recursive,
                pattern=pattern,
                directory=directory,
                lcommon=lcommon,
                movie=movie,
                option_dicts=option_dicts,
                verbose=verbose,
            )

    except KeyboardInterrupt:
        print('*** KeyboardInterrupt ***')
        sys.exit(2)
    except SystemExit:
        raise
    except Exception:
        sys.excepthook(*sys.exc_info())
        sys.exit(1)


__all__ = ['main']
