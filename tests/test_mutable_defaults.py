"""Documents the mutable-default bugs in `images_to_pics` and `get_outfile`.

These tests use `xfail(strict=True)` so they FAIL when PR 3 fixes the
defaults: `strip=[]` and `pointer=['IMAGE']` should become `None`. When the
fix lands, flip xfail off and the tests will assert the defaults are `None`.
"""

from __future__ import annotations

import inspect

import pytest

from picmaker.picmaker import get_outfile, images_to_pics


def _default(func, name: str):
    sig = inspect.signature(func)
    return sig.parameters[name].default


@pytest.mark.xfail(
    strict=True,
    reason='Pre-PR3: images_to_pics(strip=[]) — mutable default still in place.',
)
def test_images_to_pics_strip_default_is_not_mutable() -> None:
    assert _default(images_to_pics, 'strip') is None


@pytest.mark.xfail(
    strict=True,
    reason='Pre-PR3: images_to_pics(pointer=["IMAGE"]) — mutable default.',
)
def test_images_to_pics_pointer_default_is_not_mutable() -> None:
    assert _default(images_to_pics, 'pointer') is None


@pytest.mark.xfail(
    strict=True,
    reason='Pre-PR3: get_outfile(strip=[]) — mutable default still in place.',
)
def test_get_outfile_strip_default_is_not_mutable() -> None:
    assert _default(get_outfile, 'strip') is None


def test_current_strip_defaults_are_empty_list() -> None:
    # Documents the present state so PR 3's flip is loud.
    assert _default(images_to_pics, 'strip') == []
    assert _default(get_outfile, 'strip') == []


def test_current_pointer_default_is_image_list() -> None:
    assert _default(images_to_pics, 'pointer') == ['IMAGE']
