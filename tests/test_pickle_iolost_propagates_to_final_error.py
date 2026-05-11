"""Documents the pre-PR3 pickle branch behavior at picmaker.py:1540-1541.

Currently the pickle branch contains `except IOError as e: raise e`, so calling
`read_one_image_array('/nonexistent/path', None)` raises the original
"No such file or directory" IOError without falling through to the cascade.

PR 3 commit 7 removes those two lines; after that, the call falls through
to numpy → VICAR → FITS → PIL and raises IOError('Unrecognized image file
format ...'). When PR 3 lands, flip the xfail off and remove the
`test_current_behavior` test.
"""

from __future__ import annotations

import pytest

from picmaker.picmaker import read_one_image_array


def test_current_behavior_pickle_raises_no_such_file_or_directory() -> None:
    # Pre-PR3 current state: open(fn, 'rb') raises FileNotFoundError, caught
    # by `except IOError as e: raise e` → propagates as-is.
    with pytest.raises((IOError, FileNotFoundError), match=r'No such file'):
        read_one_image_array('/nonexistent/path/should/not/exist.IMG', None)


@pytest.mark.xfail(
    strict=True,
    reason=(
        'Pre-PR3: the pickle branch propagates the original IOError. PR 3 '
        'commit 7 deletes `except IOError as e: raise e` so the cascade '
        'falls through to the final IOError("Unrecognized image file format").'
    ),
)
def test_future_behavior_falls_through_to_unrecognized_format_error() -> None:
    with pytest.raises(IOError, match=r'Unrecognized image file format'):
        read_one_image_array('/nonexistent/path/should/not/exist.IMG', None)
