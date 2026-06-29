##########################################################################################
# picmaker/cli.py
##########################################################################################

import argparse
import sys

from picmaker.control     import REPLACE_CHOICES
from picmaker.instruments import PDS3_METHODS, DEFAULT_PDS3_METHOD
from picmaker.orientation import ROTATE_CHOICES
from picmaker.pil_utils   import PIL_EXTENSIONS
from picmaker.processing  import FILTER_CHOICES


PARSER = argparse.ArgumentParser(
    description='A converter from image data files to "browse" products in JPG, PNG, '
                'or other formats.',
    epilog='All color options can be specified by a name (e.g., "blue") or by three '
           'RGB values in the range 0-255 inside parentheses (e.g., "(255,255,0)" '
           'for yellow).',
    usage='%(prog)s [options] file1 file2 ...',
    prog='picmaker')
PARSER.add_argument('--version', action='version', version='%(prog)s 1.0')
PARSER.add_argument('files', nargs='+', help='input files or directories')

_control = PARSER.add_argument_group('control options')
_control.add_argument(
    '--directory', type=str, default=None,
    help='directory in which to place converted files. If the recursive option is '
         'selected, this becomes the root of a tree which parallels subdirectory '
         'structure of the source files.')
_control.add_argument(
    '-r', '--recursive', action='store_true', default=False,
    help='search recursively down each directory trees.')
_control.add_argument(
    '--pattern', dest='patterns', type=str, default=[], nargs='+',
    help='one or more patterns describing file names to match, e.g., *.IMG.')
_control.add_argument(
    '--movie', action='store_true', default=False,
    help='use the same enhancement limits for all images.')
_control.add_argument(
    '--versions', type=str, default=None,
    help='create multiple versions of each picture using different sets of options, '
         'specified one per line in the named input file.')
_control.add_argument(
    '--replace', type=str, default='all', choices=REPLACE_CHOICES,
    help='what to do when a file already exists, one of "all" (overwrite silently), '
         '"none" (skip silently), "warn" (issue a warning), "error" (raise an '
         'exception and abort).')
_control.add_argument(
    '--proceed', action='store_true', default=False,
    help='continue processing subsequent files after an error.')
_control.add_argument(
    '--logging', type=str, default='info',
    choices=['warning', 'info', 'debug', 'error'],
    help='logging level, one of "warning", "info", "debug", or "error". Default is '
         '"info".')

_input_ = PARSER.add_argument_group('input options')
_input_.add_argument(
    '-o', '--object', dest='obj', type=int, default=None,
    help='numeric index of the object in the file to display; default is the first valid '
         'image object in the file.')
_input_.add_argument(
    '--pds3-pointer',dest='pds3_pointers', type=str, default=[], nargs='+',
    help='one or more pointer strings identifying the image object in a PDS3 label.')
_input_.add_argument(
    '--pds3-method', dest='pds3_method', type=str, default=DEFAULT_PDS3_METHOD,
    choices=PDS3_METHODS,
    help='pdsparser.Pds3Label parsing strictness for PDS3 .LBL inputs: '
         '"fast" (default), "strict", "loose", or "compound".')

_output = PARSER.add_argument_group('output options')
_output.add_argument(
    '-x', '--extension', default=None, choices=PIL_EXTENSIONS,
    help='file name extension for image produced; default is "jpg"')
_output.add_argument(
    '-s', '--suffix', type=str, default='',
    help='a suffix to append to the end of each file name, prior to the file extension.')
_output.add_argument(
    '--strip', type=str, nargs='+', default=[],
    help='one or more strings to strip from output filename if it is present.')
_output.add_argument(
    '-q', '--quality', type=int, default=75,
    help='output quality value for JPEG files (1-100).')
_output.add_argument(
    '--16', dest='twobytes', action='store_true', default=False,
    help='output a 16-bit tiff instead of an 8-bit picture.')

_slicing = PARSER.add_argument_group('slicing options')
_slicing.add_argument(
    '-b', '--band', type=int, default=None,
    help='index of the band to appear in the output image, with indices starting at 1; '
         'default is 1.')
_slicing.add_argument(
    '--bands', type=int, nargs=2, default=None,
    help='a pair of indices indicating a range of bands to be coadded. Band indices '
         'start at 1 and are inclusive of the upper limit specified.')
_slicing.add_argument(
    '--lines', type=int, nargs=2, default=None,
    help='a pair of line indices defining the image sub-region to include. Sample values '
         'start at 1 and are inclusive of the upper limit specified.')
_slicing.add_argument(
    '--samples', type=int, nargs=2, default=None,
    help='a pair of sample indices defining the image sub-region to include. Sample '
         'values start at 1 and are inclusive of the upper limit specified.')
_slicing.add_argument(
    '--crop', type=float, default=None,
    help='crop boundary regions entirely containing the specified value.')

_scaling = PARSER.add_argument_group('scaling options')
_scaling.add_argument(
    '-v', '--valid', type=float, nargs=2, default=None,
    help='range of valid pixel values; pixels outside are ignored.')
_scaling.add_argument(
    '-l', '--limits', type=float, nargs=2, default=None,
    help='pair of pixel values that define the limits of the histogram.')
_scaling.add_argument(
    '-p', '--percentiles', type=float, nargs=2, default=(0.0, 100.0),
    help='pair of percentile values that define the limits of the histogram.')
_scaling.add_argument(
    '--trim', type=int, default=0,
    help='number of pixels around the edge of the image to trim before computing a '
         'histogram.')
_scaling.add_argument(
    '--trim-zeros', dest='trim_zeros',
    action='store_true', default=False,
    help='ignore exterior rows/columns containing all zeros.')
_scaling.add_argument(
    '--footprint', type=int, default=0,
    help='diameter in pixels of a circular footprint for a median filter to apply to the '
         'image prior to calculating the extreme values and percentages. This can be '
         'used to suppress noise spikes prior to determining the optimal scaling.')

_enhancement = PARSER.add_argument_group('enhancement options')
_enhancement.add_argument(
    '-c', '--colormap', type=str, default=[], nargs='+',
    help='a colormap to apply to the image, defined via one or more colors. For example, '
         '"black blue white" defines an image in which the darkest pixels are black, the '
         'brightest pixels are white, and intermediate values contain varying shades of '
         'blue. If a single color is specified, it is assumed tobe shorthand for the '
         'colormap "black <color> white".')
_enhancement.add_argument(
    '--below', dest='below_color', type=str, default=None,
    help='color for pixels whose values are less than the lower limit. By default, the '
         'first color of the colormap is used.')
_enhancement.add_argument(
    '--above', dest='above_color', type=str, default=None,
    help='color for pixels whose values are greater than the upper limit. By default, '
         'the last color of the colormap is used.')
_enhancement.add_argument(
    '--invalid', dest='invalid_color', type=str, default='black',
    help='color to use for invalid pixels and NaNs. Default is black.')
_enhancement.add_argument(
    '-g', '--gamma', type=float, default=1.0,
    help='gamma value to apply to the image. Values > 1 darken midtones; values < 1 '
         'brighten midtones. The gamma factor is applied before the colormap.')
_enhancement.add_argument(
    '--tint', action='store_true', default=False,
    help='use a default colormap for the image based on the instrument and the filter '
         'used.')
_enhancement.add_argument(
    '--histogram', action='store_true', default=False,
    help='use a histogram contrast stretch. This takes advantage of the full dynamic '
         'range from black to white.')

_orientation = PARSER.add_argument_group('orientation options')
_orientation.add_argument(
    '-u', '--up', dest='display_upward', action='store_true', default=False,
    help='display the image with line numbers increasing upward, overriding the default '
         'for the instrument.')
_orientation.add_argument(
    '-d', '--down', dest='display_downward', action='store_true', default=False,
    help='display the image with line numbers increasing downward, overriding the '
         'default for the instrument.')
_orientation.add_argument(
    '--rotate', default=None, choices=ROTATE_CHOICES,
    help='rotate or flip the image from its default orientation.')

_sizing = PARSER.add_argument_group('sizing options')
_sizing.add_argument(
    '--size', type=int, nargs=2, default=None,
    help='width and height of the output image in pixels.')
_sizing.add_argument(
    '--scale', type=float, default=None,
    help='percentage by which to scale both the width and height of the image.')
_sizing.add_argument(
    '--wscale', type=float, default=None,
    help='percentage by which to scale the width of the image.')
_sizing.add_argument(
    '--hscale', type=float, default=None,
    help='percentage by which to scale the height of the image.')
_sizing.add_argument(
    '--frame', type=int, nargs=2, default=None,
    help='width and height of the frame within which the image must fit.')
_sizing.add_argument(
    '--frame_max', type=int, default=None,
    help='maximum percentage by which to scale the image to fit it inside the frame.')

_layout = PARSER.add_argument_group('layout options')
_layout.add_argument(
    '--wrap', action='store_true', default=False,
    help='wrap the sections of an image if it is extremely elongated.')
_layout.add_argument(
    '--wrap-ratio', type=float, default=None,
    help='wrap if width:height or height:width ratio exceeds this value.')
_layout.add_argument(
    '--overlap', type=float, default=None,
    help='percentage of required overlap between wrapped sections of an elongated image. '
         'For example, if the value is 5, then the last 5% of each strip in the image '
         'will be repeated at the beginning of the next strip.')
_layout.add_argument(
    '--overlaps', type=float, nargs=2, default=None,
    help='minimum and maximum percentages of tolerated overlap between wrapped sections '
         'of an elongated image when it is wrapped.')
_layout.add_argument(
    '--gap-size', dest='gap_size', type=int, default=1,
    help='width in pixels of the gap between strips of a wrapped image.')
_layout.add_argument(
    '--gap-color', dest='gap_color', type=str, default='white',
    help='color to use for the gap between sections of a wrapped image. Default is '
         'white.')
_layout.add_argument(
    '--pad', action='store_true', default=False,
    help='pad the image to match the full size of the frame.')
_layout.add_argument(
    '--pad-color', dest='pad_color', type=str, default='gray',
    help='the color to use when padding an image to fill a frame. Default is gray.')
_layout.add_argument(
    '--mosaic', action='store_true', default=False,
    help='invoke the instrument-specific method for constructing a mosaic of images for '
         'an instrument that has multiple detectors.')

_processing = PARSER.add_argument_group('processing options')
_processing.add_argument(
    '-f', '--filter', default=None, choices=FILTER_CHOICES,
    help='apply an image processing filter to the image. Options are '
         + f'{", ".join(FILTER_CHOICES[:-1])} and {FILTER_CHOICES[-1]}.')
_processing.add_argument(
    '--zebra', action='store_true', default=False,
    help='interpolate across zero-valued "zebra stripes" at the beginnings and ends of '
         'lines.')


def main():
    """Parse command-line arguments and run picmaker."""

    # Imported here to avoid a circular import: picmaker.picmaker imports PARSER from this
    # module at load time.
    from picmaker.picmaker import picmaker, validate_options

    options = PARSER.parse_args()   # could raise SystemExit
    kwargs = validate_options(options)

    # Shift the indexing origin to zero for values from the command line
    for name in ('samples', 'lines', 'bands'):
        pair = kwargs.get(name, None)
        if pair is not None:
            kwargs[name] = (pair[0]-1, pair[1])

    try:
        picmaker(**kwargs)
    except KeyboardInterrupt:
        print('*** KeyboardInterrupt ***')
        sys.exit(2)
    except Exception:
        sys.excepthook(*sys.exc_info())
        sys.exit(1)


__all__ = ['main']

##########################################################################################
