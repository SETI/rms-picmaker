"""Tests for the real ``PdsLogger`` wiring through ``picmaker`` and ``main``.

These exercise the actual logging paths (rather than the ``logger=None``
short-circuit covered by the other suites) by attaching a capturing handler
to a real :class:`pdslogger.PdsLogger` and asserting on the emitted records.
"""

import logging
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from pdslogger import PdsLogger

from picmaker.parser import get_parser
from picmaker.picmaker import picmaker, validate_options

CapturedLogger = tuple[PdsLogger, list[logging.LogRecord]]


class _ListHandler(logging.Handler):
    """A stdlib handler that just collects the records it is given."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def captured_logger(request: pytest.FixtureRequest) -> Iterator[CapturedLogger]:
    """A real PdsLogger (uniquely named per test) plus its captured records."""
    handler = _ListHandler()
    logger = PdsLogger.get_logger(f'pds.picmaker.test.{request.node.name}', level='debug')
    logger.add_handler(handler)
    try:
        yield logger, handler.records
    finally:
        logger.remove_handler(handler)


def _messages(records: list[logging.LogRecord], level: str | None = None) -> list[str]:
    return [r.getMessage() for r in records if level is None or r.levelname == level]


def _run(logger: PdsLogger, *argv: str) -> None:
    """Build a complete options dict the CLI way and run the pipeline."""
    options = validate_options(get_parser().parse_args(list(argv)), logger=logger)
    options['logger'] = logger
    picmaker(**options)


def test_no_input_files_logs_error(captured_logger: CapturedLogger) -> None:
    """An empty input set logs an ERROR before raising."""
    logger, records = captured_logger
    with pytest.raises(ValueError, match='no input files identified'):
        _run(logger)
    assert any('no input files identified' in m for m in _messages(records, 'ERROR'))


def test_validation_error_is_logged(captured_logger: CapturedLogger) -> None:
    """A validation conflict is logged (as an exception) before raising."""
    logger, records = captured_logger
    with pytest.raises(ValueError, match='--band and --bands'):
        validate_options(
            get_parser().parse_args(['x.vic', '--band', '2', '--bands', '0', '1']),
            logger=logger,
        )
    # logger.exception() records the error at CRITICAL level.
    assert any('--band and --bands' in m for m in _messages(records))
    assert any(r.levelname == 'CRITICAL' for r in records)


def test_proceed_after_error_logs_info(
    captured_logger: CapturedLogger, fixtures_dir: Path, tmp_path: Path
) -> None:
    """``--proceed`` logs an INFO record and keeps processing later files."""
    logger, records = captured_logger
    bad = tmp_path / 'bad.vic'
    bad.write_bytes(b'not a vicar file')
    out = tmp_path / 'out'
    _run(logger, str(bad), str(fixtures_dir / 'cassini_iss.vic'),
         '--directory', str(out), '--proceed')
    assert (out / 'cassini_iss.jpg').exists()
    assert any('Proceeding after error' in m for m in _messages(records, 'INFO'))


def test_successful_run_logs_writing(
    captured_logger: CapturedLogger, fixtures_dir: Path, tmp_path: Path
) -> None:
    """A normal run logs the output file it writes."""
    logger, records = captured_logger
    _run(logger, str(fixtures_dir / 'cassini_iss.vic'), '--directory', str(tmp_path))
    assert (tmp_path / 'cassini_iss.jpg').exists()
    assert any('cassini_iss.jpg' in m for m in _messages(records))


def test_main_creates_logger_and_logs_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``main()`` builds its own ``pds.picmaker`` logger; a no-input run exits 1
    and the error is logged through it."""
    from picmaker.main import main

    handler = _ListHandler()
    # main() calls PdsLogger.get_logger('pds.picmaker', ...); attach to that name
    # so the handler survives into the logger main() resolves.
    logger = PdsLogger.get_logger('pds.picmaker', level='debug')
    logger.add_handler(handler)
    monkeypatch.setattr(sys, 'argv', ['picmaker'])
    try:
        with pytest.raises(SystemExit) as excinfo:
            main()
    finally:
        logger.remove_handler(handler)
    assert excinfo.value.code == 1
    messages = [r.getMessage() for r in handler.records]
    assert any('no input files identified' in m for m in messages)
