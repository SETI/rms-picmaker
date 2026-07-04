"""Pin down the missing-file behavior of
:func:`picmaker.instruments.read_image_array`.

After the refactor, ``read_image_array`` checks for existence up front and
raises ``FileNotFoundError`` ("No such file or directory") before entering the
format cascade -- it no longer falls all the way through to the cascade-end
``unrecognized file format`` error. (``FileNotFoundError`` is a subclass of
``OSError``, so callers catching ``OSError`` still see it.)
"""

from pathlib import Path

import pytest

from picmaker.instruments import read_image_array


def test_missing_path_raises_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / 'does_not_exist.IMG'
    with pytest.raises(FileNotFoundError, match='No such file or directory'):
        read_image_array(str(missing))
