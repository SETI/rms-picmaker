"""Shared test fixtures for picmaker tests."""

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
EXPECTED_DIR = FIXTURES_DIR / 'expected'


@pytest.fixture
def fixtures_dir() -> Path:
    """Absolute path to tests/fixtures/."""
    return FIXTURES_DIR


@pytest.fixture
def expected_dir() -> Path:
    """Absolute path to tests/fixtures/expected/."""
    return EXPECTED_DIR


@pytest.fixture
def tiny_array() -> NDArray[np.uint16]:
    """Deterministic 16x16 numpy array used by enhance / colormap unit tests."""
    return np.arange(256, dtype=np.uint16).reshape(16, 16)


@pytest.fixture
def basic_option_dict() -> dict[str, Any]:
    """A minimal ``option_dict`` shaped like the one
    :func:`picmaker.cli._normalize_and_validate` produces — every field
    that :func:`picmaker.pipeline.images_to_pics` and
    :func:`picmaker.pipeline.process_images` consume, with safe
    defaults. Returns a fresh dict on each call so tests can mutate
    without leaking state across the suite.
    """
    return {
        'replace': 'all',
        'proceed': False,
        'extension': 'jpg',
        'suffix': '',
        'strip': [],
        'quality': 75,
        'twobytes': False,
        'bands': (0, 1),
        'lines': None,
        'samples': None,
        'obj': None,
        'pointer': ['IMAGE'],
        'pds3_label_method': 'strict',
        'size': None,
        'scale': (100.0, 100.0),
        'crop': None,
        'frame': None,
        'pad': False,
        'pad_color': 'black',
        'frame_max': None,
        'wrap': False,
        'wrap_ratio': None,
        'overlap': (0.0, 0.0),
        'gap_size': 1,
        'gap_color': 'white',
        'hst': False,
        'valid': None,
        'limits': None,
        'percentiles': (0.0, 100.0),
        'trim': 0,
        'trim_zeros': False,
        'footprint': 0,
        'histogram': False,
        'colormap': None,
        'below_color': None,
        'above_color': None,
        'invalid_color': 'black',
        'gamma': 1.0,
        'tint': False,
        'display_upward': False,
        'display_downward': False,
        'rotate': 'none',
        'filter_name': 'none',
        'zebra': False,
    }
