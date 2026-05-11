"""find_common_path and get_outfile unit tests."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from picmaker.picmaker import find_common_path, get_outfile


class TestFindCommonPath:
    def test_empty(self) -> None:
        assert find_common_path([]) == ''

    def test_single(self) -> None:
        assert find_common_path(['/foo/bar']) == '/foo/bar'

    def test_two_with_no_common_prefix(self) -> None:
        # No shared parent: longest common prefix '' (no slash at position >= 1)
        assert find_common_path(['/a/b', '/c/d']) == ''

    def test_two_sharing_foo_bar(self) -> None:
        assert find_common_path(['/foo/bar/x', '/foo/bar/y']) == '/foo/bar'

    def test_three_sharing_two_levels(self) -> None:
        result = find_common_path(['/foo/bar/x', '/foo/bar/y', '/foo/bar/zzz'])
        assert result == '/foo/bar'


class TestGetOutfile:
    def test_replace_all_overwrites_silently(self, tmp_path: Path) -> None:
        infile = tmp_path / 'image.IMG'
        infile.write_bytes(b'')
        out_existing = tmp_path / 'image.jpg'
        out_existing.write_bytes(b'')

        result = get_outfile(str(infile), outdir=str(tmp_path), replace='all')
        assert result == str(out_existing)

    def test_replace_none_returns_empty_when_exists(self, tmp_path: Path) -> None:
        infile = tmp_path / 'image.IMG'
        infile.write_bytes(b'')
        out_existing = tmp_path / 'image.jpg'
        out_existing.write_bytes(b'')

        assert get_outfile(str(infile), outdir=str(tmp_path), replace='none') == ''

    def test_replace_warn_warns_and_returns_path(self, tmp_path: Path) -> None:
        infile = tmp_path / 'image.IMG'
        infile.write_bytes(b'')
        out_existing = tmp_path / 'image.jpg'
        out_existing.write_bytes(b'')

        with pytest.warns(UserWarning, match='File overwritten'):
            result = get_outfile(str(infile), outdir=str(tmp_path), replace='warn')
        assert result == str(out_existing)

    def test_replace_error_raises_when_exists(self, tmp_path: Path) -> None:
        infile = tmp_path / 'image.IMG'
        infile.write_bytes(b'')
        out_existing = tmp_path / 'image.jpg'
        out_existing.write_bytes(b'')

        with pytest.raises(IOError, match='File already exists'):
            get_outfile(str(infile), outdir=str(tmp_path), replace='error')

    def test_strip_substring(self, tmp_path: Path) -> None:
        infile = tmp_path / 'cm_image.IMG'
        infile.write_bytes(b'')
        result = get_outfile(
            str(infile), outdir=str(tmp_path), strip='cm_', extension='png'
        )
        assert result == str(tmp_path / 'image.png')

    def test_suffix_appended(self, tmp_path: Path) -> None:
        infile = tmp_path / 'image.IMG'
        result = get_outfile(
            str(infile), outdir=str(tmp_path), suffix='_v1', extension='png'
        )
        assert result == str(tmp_path / 'image_v1.png')

    def test_extension_swapped(self, tmp_path: Path) -> None:
        infile = tmp_path / 'image.IMG'
        result = get_outfile(str(infile), outdir=str(tmp_path), extension='tif')
        assert result == str(tmp_path / 'image.tif')

    def test_strip_none_then_no_replace(self, tmp_path: Path) -> None:
        # strip=None is converted to [''] internally; verifies the public
        # behavior even though the default value is the mutable [] list (which
        # PR 3 will replace with None).
        infile = tmp_path / 'image.IMG'
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            result = get_outfile(
                str(infile), outdir=str(tmp_path), strip=None, extension='jpg'
            )
        assert result == str(tmp_path / 'image.jpg')
