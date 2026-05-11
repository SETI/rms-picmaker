"""Subprocess smoke tests for the `picmaker` CLI entry-point.

These tests verify the user-facing behavior end-to-end (sys.argv parsing,
exit codes, --versions semantics, baseline help text). They're necessarily
slow (one subprocess per test); each test is small to keep total time low.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['picmaker', *args], capture_output=True, text=True, check=False
    )


def test_help_exits_zero_and_lists_flags() -> None:
    proc = _run('--help')
    assert proc.returncode == 0
    # argparse emits a lowercase "usage:" line; optparse used "Usage:" — accept either.
    output = proc.stdout + proc.stderr
    assert 'usage: picmaker' in output.lower()
    # Sanity: a few representative flags are present.
    for flag in ('--directory', '--versions', '--gamma'):
        assert flag in output


def test_help_flag_set_matches_baseline() -> None:
    proc = _run('--help')
    assert proc.returncode == 0
    # Extract flags via the same regex pattern PR 1 baselined with.
    import re
    flags = sorted(set(re.findall(r'--[a-z_-]+', proc.stdout + proc.stderr)))
    baseline_path = Path(__file__).parent / 'fixtures' / '.baseline-flags.txt'
    baseline = sorted(baseline_path.read_text().splitlines())
    assert flags == baseline


def test_no_args_succeeds() -> None:
    # With no files to process, picmaker still exits cleanly (no work to do).
    proc = _run()
    assert proc.returncode == 0


def test_nonexistent_file_exits_nonzero() -> None:
    proc = _run('/nonexistent/path/should/not/exist.IMG')
    assert proc.returncode != 0
    # sys.excepthook prints the traceback to stderr.
    assert 'No such file' in proc.stderr or 'FileNotFoundError' in proc.stderr


def test_versions_produces_two_output_files(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    proc = _run(
        '--versions', str(fixtures_dir / 'two_versions.txt'),
        '--directory', str(tmp_path),
        '--replace=all',
        str(fixtures_dir / 'cassini_iss.vic'),
    )
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / 'cassini_iss_v1.jpg').exists()
    assert (tmp_path / 'cassini_iss_v2.tif').exists()
