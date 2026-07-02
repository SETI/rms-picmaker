"""Regression guard: the default happy-path run must emit no warnings.

If a future change causes the pipeline to log a spurious ``WARNING``-level
record for a clean fixture, this test fails so CI catches the regression
rather than letting it slip past unnoticed.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from picmaker.parser import get_parser
from picmaker.picmaker import picmaker, validate_options


def test_default_run_emits_no_warnings(
    fixtures_dir: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger='picmaker'):
        options = validate_options(get_parser().parse_args([
            str(fixtures_dir / 'cassini_iss.vic'), '--directory', str(tmp_path),
        ]))
        picmaker(**options)
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
