##########################################################################################
# picmaker/main.py
##########################################################################################

# ruff: noqa: I001
import argparse
import sys
import warnings

from pdslogger import PdsLogger

from picmaker.control  import FileOverwriteWarning
from picmaker.options  import get_parser
from picmaker.picmaker import picmaker


def main():
    """Parse command-line arguments and run picmaker."""

    warnings.simplefilter('error')
    warnings.filterwarnings('default', category=DeprecationWarning)   # don't escalate
    warnings.filterwarnings('always', category=FileOverwriteWarning)  # don't escalate

    parser = get_parser()
    try:
        options = parser.parse_args()
    except argparse.ArgumentError:
        sys.excepthook(*sys.exc_info())
        sys.exit(1)

    logger = PdsLogger.get_logger('pds.picmaker', digits=3, lognames=False,
                                  indent=True, blanklines=False, level='debug')
    try:
        picmaker(logger=logger, _shift_origins=True, **options.__dict__)
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
