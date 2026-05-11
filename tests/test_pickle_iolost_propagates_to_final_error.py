"""Pin down the post-PR-3 pickle-branch behavior.

PR 3 deleted the ``except IOError as e: raise e`` at the head of
``read_one_image_array``. As a result, a non-existent path no longer
short-circuits with the original ``FileNotFoundError``; it falls through
the entire format cascade and raises
``OSError('Unrecognized image file format: ...')``.

This is a deliberate user-observable behavior change documented in the
PR 3 description.
"""

from __future__ import annotations

import pytest

from picmaker.picmaker import read_one_image_array


def test_falls_through_to_unrecognized_format_error() -> None:
    with pytest.raises(OSError, match=r'Unrecognized image file format'):
        read_one_image_array('/nonexistent/path/should/not/exist.IMG', None)
