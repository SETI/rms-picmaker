"""Unit tests for :mod:`picmaker.control` (get_outfile, get_filepaths)."""

import warnings
from pathlib import Path

import pytest

from picmaker.control import get_filepaths, get_outfile


class TestGetOutfile:
    def test_replace_all_overwrites_silently(self, tmp_path: Path) -> None:
        infile = tmp_path / 'image.IMG'
        infile.write_bytes(b'')
        out_existing = tmp_path / 'image.jpg'
        out_existing.write_bytes(b'')

        result = get_outfile(str(infile), outdir=str(tmp_path), replace='all')
        assert result == out_existing

    def test_replace_none_returns_none_when_exists(self, tmp_path: Path) -> None:
        infile = tmp_path / 'image.IMG'
        infile.write_bytes(b'')
        out_existing = tmp_path / 'image.jpg'
        out_existing.write_bytes(b'')

        assert get_outfile(str(infile), outdir=str(tmp_path), replace='none') is None

    def test_replace_warn_warns_and_returns_path(self, tmp_path: Path) -> None:
        infile = tmp_path / 'image.IMG'
        infile.write_bytes(b'')
        out_existing = tmp_path / 'image.jpg'
        out_existing.write_bytes(b'')

        with pytest.warns(UserWarning, match='File overwritten'):
            result = get_outfile(str(infile), outdir=str(tmp_path), replace='warn')
        assert result == out_existing

    def test_replace_error_raises_when_exists(self, tmp_path: Path) -> None:
        infile = tmp_path / 'image.IMG'
        infile.write_bytes(b'')
        out_existing = tmp_path / 'image.jpg'
        out_existing.write_bytes(b'')

        with pytest.raises(OSError, match='File already exists'):
            get_outfile(str(infile), outdir=str(tmp_path), replace='error')

    def test_strip_substring(self, tmp_path: Path) -> None:
        infile = tmp_path / 'cm_image.IMG'
        infile.write_bytes(b'')
        result = get_outfile(
            str(infile), outdir=str(tmp_path), strip='cm_', extension='png'
        )
        assert result == tmp_path / 'image.png'

    def test_suffix_appended(self, tmp_path: Path) -> None:
        infile = tmp_path / 'image.IMG'
        result = get_outfile(
            str(infile), outdir=str(tmp_path), suffix='_v1', extension='png'
        )
        assert result == tmp_path / 'image_v1.png'

    def test_extension_swapped(self, tmp_path: Path) -> None:
        infile = tmp_path / 'image.IMG'
        result = get_outfile(str(infile), outdir=str(tmp_path), extension='tif')
        assert result == tmp_path / 'image.tif'

    def test_strip_none_then_no_replace(self, tmp_path: Path) -> None:
        # strip=None is falsy, so the stem is left untouched; no warnings.
        infile = tmp_path / 'image.IMG'
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            result = get_outfile(
                str(infile), outdir=str(tmp_path), strip=None, extension='jpg'
            )
        assert result == tmp_path / 'image.jpg'


class TestGetFilepaths:
    """Directory-discovery coverage that ``test_cli_unit`` only exercises
    end-to-end through ``main()``."""

    def test_directory_pattern_filters_and_overrides_outdir(
        self, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """A glob pattern keeps matching files and skips the rest, and an
        explicit ``directory`` becomes the output dir."""
        import shutil

        src = tmp_path / 'src'
        src.mkdir()
        shutil.copy(fixtures_dir / 'cassini_iss.vic', src / 'cassini_iss.vic')
        (src / 'README.txt').write_text('not an image')

        out = tmp_path / 'out'
        result = get_filepaths([str(src)], directory=str(out), patterns=['*.vic'])
        assert result == [(src / 'cassini_iss.vic', out)]

    def test_recursive_mirrors_subdir_tree(
        self, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """Recursive discovery walks subdirs and mirrors their tail path
        under the output directory."""
        import shutil

        src = tmp_path / 'src'
        nested = src / 'nested'
        nested.mkdir(parents=True)
        shutil.copy(fixtures_dir / 'cassini_iss.vic', src / 'top.vic')
        shutil.copy(fixtures_dir / 'cassini_iss.vic', nested / 'deep.vic')

        out = tmp_path / 'out'
        result = get_filepaths(
            [str(src)], directory=str(out), recursive=True, patterns=['*.vic']
        )
        assert set(result) == {
            (src / 'top.vic', out),
            (nested / 'deep.vic', out / 'nested'),
        }

    def test_directory_dotfiles_excluded(
        self, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """Hidden (dot-prefixed) basenames never match a pattern."""
        import shutil

        src = tmp_path / 'src'
        src.mkdir()
        shutil.copy(fixtures_dir / 'cassini_iss.vic', src / 'visible.vic')
        shutil.copy(fixtures_dir / 'cassini_iss.vic', src / '.hidden.vic')

        result = get_filepaths([str(src)], patterns=['*.vic'])
        assert [p.name for p, _ in result] == ['visible.vic']

    def test_directory_default_outdir_is_the_directory(
        self, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """Without a ``directory`` override, a directory input's outputs
        default to that same directory."""
        import shutil

        src = tmp_path / 'src'
        src.mkdir()
        shutil.copy(fixtures_dir / 'cassini_iss.vic', src / 'cassini_iss.vic')

        result = get_filepaths([str(src)], patterns=['*.vic'])
        assert result == [(src / 'cassini_iss.vic', src)]

    def test_empty_directory_string_behaves_like_default(
        self, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        """An empty-string ``directory`` — the value the CLI defaults resolve
        to when no ``--directory`` is given — is treated as unset: a directory
        input's outputs go beside their inputs, rather than raising TypeError."""
        import shutil

        src = tmp_path / 'src'
        src.mkdir()
        shutil.copy(fixtures_dir / 'cassini_iss.vic', src / 'cassini_iss.vic')

        result = get_filepaths([str(src)], directory='', patterns=['*.vic'])
        assert result == [(src / 'cassini_iss.vic', src)]
