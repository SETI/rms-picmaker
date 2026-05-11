"""PR 3 flipped the mutable defaults in `images_to_pics` and `get_outfile`.

These tests pin down the post-PR-3 state: ``strip=None`` (normalized
internally to ``[]``) and ``pointer=None`` (normalized to
``['IMAGE']``). The PR 2 xfail placeholders are gone; if a future
change re-introduces a mutable default the test fails immediately.
"""

from __future__ import annotations

import inspect

from picmaker.picmaker import get_outfile, images_to_pics


def _default(func, name: str):
    sig = inspect.signature(func)
    return sig.parameters[name].default


def test_images_to_pics_strip_default_is_not_mutable() -> None:
    assert _default(images_to_pics, 'strip') is None


def test_images_to_pics_pointer_default_is_not_mutable() -> None:
    assert _default(images_to_pics, 'pointer') is None


def test_get_outfile_strip_default_is_not_mutable() -> None:
    assert _default(get_outfile, 'strip') is None
