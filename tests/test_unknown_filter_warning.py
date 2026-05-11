"""Currently `tinted_colormap` `print()`s 'UNKNOWN FILTER' (picmaker.py:2358).

PR 3 commit 8 converts that to `logger.warning(...)`. This test captures
both the current print-to-stdout behavior AND the future logging behavior so
the same file gates both states. The `caplog`-based assertions are xfail
until PR 3 lands.
"""

from __future__ import annotations

import logging

import pytest

from picmaker.picmaker import tinted_colormap


def test_unknown_filter_prints_to_stdout(capsys: pytest.CaptureFixture) -> None:
    # Pre-PR3: print(...) to stdout. We assert the message text.
    result = tinted_colormap(('HST', 'WFC3', 'UNKNOWN_FILTER_NAME'))
    assert result is None
    captured = capsys.readouterr()
    assert '******UNKNOWN FILTER:' in captured.out
    assert 'WFC3' in captured.out
    assert 'UNKNOWN_FILTER_NAME' in captured.out


@pytest.mark.xfail(
    strict=True,
    reason='Pre-PR3: tinted_colormap uses print(), not logger.warning().',
)
def test_unknown_filter_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger='picmaker.picmaker'):
        tinted_colormap(('HST', 'WFC3', 'UNKNOWN_FILTER_NAME'))
    assert any('UNKNOWN FILTER' in r.message for r in caplog.records)
