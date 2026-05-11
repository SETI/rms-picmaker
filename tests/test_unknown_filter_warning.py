"""Verify PR 3's print -> logger.warning conversion for unknown HST filters.

The HST tint dispatcher now lives in :mod:`picmaker.instruments.hst`, and
unknown filter names emit ``logger.warning('Unknown HST filter: ...')``
instead of the legacy ``print('******UNKNOWN FILTER: ...')`` line.
"""

from __future__ import annotations

import logging

import pytest

from picmaker.picmaker import tinted_colormap


def test_unknown_filter_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Calling :func:`tinted_colormap` with an unknown HST filter returns
    ``None`` and emits a single WARNING-level log record on the
    ``picmaker.instruments.hst`` logger whose message includes both the
    instrument id (``'WFC3'``) and the filter name.
    """
    with caplog.at_level(logging.WARNING, logger='picmaker.instruments.hst'):
        result = tinted_colormap(('HST', 'WFC3', 'UNKNOWN_FILTER_NAME'))
    assert result is None
    assert any('Unknown HST filter' in r.message for r in caplog.records)
    assert any('WFC3' in r.message for r in caplog.records)
    assert any('UNKNOWN_FILTER_NAME' in r.message for r in caplog.records)


def test_unknown_filter_does_not_print(capsys: pytest.CaptureFixture[str]) -> None:
    """Calling :func:`tinted_colormap` with an unknown HST filter must NOT
    write the legacy ``'UNKNOWN FILTER'`` string to stdout (the warning
    now goes through ``logger.warning``).
    """
    tinted_colormap(('HST', 'WFC3', 'UNKNOWN_FILTER_NAME'))
    captured = capsys.readouterr()
    assert 'UNKNOWN FILTER' not in captured.out
