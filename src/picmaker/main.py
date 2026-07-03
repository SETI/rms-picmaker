##########################################################################################
# picmaker/main.py
##########################################################################################

# ruff: noqa: I001
import sys
import warnings

from pdslogger import PdsLogger

from picmaker.options import get_parser, validate_options
from picmaker.picmaker import picmaker



def main():
    """Parse command-line arguments and run picmaker."""

    warnings.simplefilter('error')

    parser = get_parser()
    options = parser.parse_args()   # could raise SystemExit

    logger = PdsLogger.get_logger('pds.picmaker', digits=3, lognames=False, indent=True,
                                  blanklines=False, level='debug')
    kwargs = validate_options(options, logger=logger)
    kwargs['logger'] = logger

    # Shift the indexing origin to zero for values from the command line
    for name in ('samples', 'lines', 'bands'):
        value = kwargs.get(name, None)
        if value is not None:
            kwargs[name] = (value[0] - 1, value[1])
    for name in ('obj',):
        value = kwargs.get(name, None)
        if value is not None:
            kwargs[name] = value - 1

    try:
        picmaker(**kwargs)
    except KeyboardInterrupt:
        print('*** KeyboardInterrupt ***')
        sys.exit(2)
    except Exception:
        sys.excepthook(*sys.exc_info())
        sys.exit(1)


__all__ = ['main']

if __name__ == '__main__':
    main()

##########################################################################################
