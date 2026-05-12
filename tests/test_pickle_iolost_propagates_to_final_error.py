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

from pathlib import Path

import pytest

from picmaker.picmaker import read_one_image_array


def test_falls_through_to_unrecognized_format_error(tmp_path: Path) -> None:
    # Use tmp_path so the non-existent path is OS-native absolute:
    # on Windows, a POSIX-style "/nonexistent/..." path is not absolute
    # and astropy's FITS reader inside the cascade rejects it with
    # "Local file URL is not absolute" before the cascade end.
    missing = tmp_path / 'does_not_exist.IMG'
    with pytest.raises(OSError, match=r'Unrecognized image file format'):
        read_one_image_array(str(missing), None)
