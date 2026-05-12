"""Regression guard: the default happy-path run must emit no warnings.

If a future change causes ``images_to_pics`` to log a spurious
``WARNING``-level record for a clean fixture, this test fails so CI
catches the regression rather than letting it slip past unnoticed.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest


def test_default_run_emits_no_warnings(
    fixtures_dir: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger='picmaker'):
        from picmaker import images_to_pics
        images_to_pics([str(fixtures_dir / 'cassini_iss.vic')], directory=str(tmp_path))
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
