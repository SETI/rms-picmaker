"""End-to-end pipeline tests via images_to_pics on every fixture.

The byte-identical snapshot tests live in test_snapshots.py — this file just
asserts that the pipeline produces an output file with sensible properties
for each option combination, and that the HST-specific branches at
picmaker.py:1656 + 1667 (ACS/WFC and WFPC2) execute without error.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from picmaker.picmaker import images_to_pics


ALL_FIXTURES = [
    'cassini_iss.vic',
    'voyager_iss.vic',
    'galileo_ssi_a.vic',
    'galileo_ssi_b.vic',
    'hst_wfc3.fits',
    'hst_acs.fits',
    'hst_wfpc2.fits',
    'nh_mvic.fits',
]


@pytest.mark.parametrize('fixture', ALL_FIXTURES)
def test_default_options_writes_jpeg(
    fixture: str, fixtures_dir: Path, tmp_path: Path
) -> None:
    images_to_pics([str(fixtures_dir / fixture)], directory=str(tmp_path))
    expected = tmp_path / (Path(fixture).stem + '.jpg')
    assert expected.exists()
    with Image.open(expected) as img:
        assert img.size[0] > 0
        assert img.size[1] > 0


@pytest.mark.parametrize('fixture', ALL_FIXTURES)
def test_gamma_two(fixture: str, fixtures_dir: Path, tmp_path: Path) -> None:
    images_to_pics(
        [str(fixtures_dir / fixture)], directory=str(tmp_path), gamma=2.0
    )
    assert (tmp_path / (Path(fixture).stem + '.jpg')).exists()


@pytest.mark.parametrize('fixture', ALL_FIXTURES)
def test_percentile_stretch(
    fixture: str, fixtures_dir: Path, tmp_path: Path
) -> None:
    images_to_pics(
        [str(fixtures_dir / fixture)],
        directory=str(tmp_path),
        percentiles=(5.0, 95.0),
    )
    assert (tmp_path / (Path(fixture).stem + '.jpg')).exists()


def test_tint_option(fixtures_dir: Path, tmp_path: Path) -> None:
    images_to_pics(
        [str(fixtures_dir / 'cassini_iss.vic')],
        directory=str(tmp_path),
        tint=True,
    )
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_rotate_rot90(fixtures_dir: Path, tmp_path: Path) -> None:
    images_to_pics(
        [str(fixtures_dir / 'cassini_iss.vic')],
        directory=str(tmp_path),
        rotate='rot90',
    )
    assert (tmp_path / 'cassini_iss.jpg').exists()


def test_movie_option_writes_outputs(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    # Movie mode runs the pipeline twice; both passes write to the same dir.
    from picmaker.picmaker import process_images

    option_dict = {
        'replace': 'all', 'proceed': False, 'extension': 'jpg', 'suffix': '',
        'strip': [], 'quality': 75, 'twobytes': False, 'bands': None,
        'lines': None, 'samples': None, 'obj': None, 'pointer': ['IMAGE'],
        'size': None, 'scale': (100., 100.), 'crop': None, 'frame': None,
        'pad': False, 'pad_color': 'black', 'frame_max': None, 'wrap': False,
        'wrap_ratio': None, 'overlap': (0., 0.), 'gap_size': 1,
        'gap_color': 'white', 'hst': False, 'valid': None, 'limits': None,
        'percentiles': None, 'trim': 0, 'trim_zeros': False, 'footprint': 0,
        'histogram': False, 'colormap': None, 'below_color': None,
        'above_color': None, 'invalid_color': None, 'gamma': 1.0,
        'tint': False, 'display_upward': False, 'display_downward': False,
        'rotate': None, 'filter': 'NONE', 'zebra': False,
    }
    process_images(
        [str(fixtures_dir / 'cassini_iss.vic')],
        directory=str(tmp_path),
        movie=True,
        option_dicts=[option_dict],
    )
    assert (tmp_path / 'cassini_iss.jpg').exists()


@pytest.mark.parametrize('fixture', ALL_FIXTURES)
def test_sixteen_bit_tiff_extension(
    fixture: str, fixtures_dir: Path, tmp_path: Path
) -> None:
    images_to_pics(
        [str(fixtures_dir / fixture)],
        directory=str(tmp_path),
        extension='tiff',
        twobytes=True,
    )
    assert (tmp_path / (Path(fixture).stem + '.tiff')).exists()


def test_hst_acs_branch_executes(fixtures_dir: Path, tmp_path: Path) -> None:
    # Exercises the inst_id == 'ACS/WFC' branch at picmaker.py:1656.
    images_to_pics(
        [str(fixtures_dir / 'hst_acs.fits')],
        directory=str(tmp_path),
        hst=True,
    )
    assert (tmp_path / 'hst_acs.jpg').exists()


def test_hst_wfpc2_branch_executes(fixtures_dir: Path, tmp_path: Path) -> None:
    # Exercises the WFPC2 stacking branch at picmaker.py:1667.
    images_to_pics(
        [str(fixtures_dir / 'hst_wfpc2.fits')],
        directory=str(tmp_path),
        hst=True,
    )
    assert (tmp_path / 'hst_wfpc2.jpg').exists()
