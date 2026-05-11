"""Shared test fixtures for picmaker tests."""

from pathlib import Path

import numpy as np
import pytest

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
EXPECTED_DIR = FIXTURES_DIR / 'expected'


@pytest.fixture
def fixtures_dir() -> Path:
    """Absolute path to tests/fixtures/."""
    return FIXTURES_DIR


@pytest.fixture
def expected_dir() -> Path:
    """Absolute path to tests/fixtures/expected/ (populated by PR 2 commit 6)."""
    return EXPECTED_DIR


@pytest.fixture
def tiny_array():
    """Deterministic 16x16 numpy array used by enhance / colormap unit tests."""
    return np.arange(256, dtype=np.uint16).reshape(16, 16)
