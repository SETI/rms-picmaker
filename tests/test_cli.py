"""Subprocess smoke tests for the `picmaker` CLI entry-point.

These tests verify the user-facing behavior end-to-end (sys.argv parsing,
exit codes, --versions semantics, baseline help text). They're necessarily
slow (one subprocess per test); each test is small to keep total time low.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    """Invoke the installed ``picmaker`` CLI with ``args`` and capture output.

    Parameters:
        *args: Positional CLI arguments forwarded verbatim.

    Returns:
        The :class:`subprocess.CompletedProcess` with text stdout/stderr.
    """
    return subprocess.run(
        ['picmaker', *args], capture_output=True, text=True, check=False
    )


def test_help_exits_zero_and_lists_flags() -> None:
    """``picmaker --help`` exits 0 and includes the usage banner plus the
    representative flags ``--directory``, ``--versions``, and ``--gamma``.
    """
    proc = _run('--help')
    assert proc.returncode == 0
    output = proc.stdout + proc.stderr
    assert 'usage: picmaker' in output.lower()
    for flag in ('--directory', '--versions', '--gamma'):
        assert flag in output


def test_help_flag_set_matches_baseline() -> None:
    """The set of flags surfaced in ``--help`` matches the PR 1 baseline
    in ``tests/fixtures/.baseline-flags.txt`` exactly.
    """
    proc = _run('--help')
    assert proc.returncode == 0
    import re
    flags = sorted(set(re.findall(r'--[a-z_-]+', proc.stdout + proc.stderr)))
    baseline_path = Path(__file__).parent / 'fixtures' / '.baseline-flags.txt'
    baseline = sorted(baseline_path.read_text().splitlines())
    assert flags == baseline


def test_user_guide_documents_every_cli_flag() -> None:
    """Every long flag in ``--help`` is mentioned in ``docs/user_guide.rst``
    so doc drift is caught by CI. Excludes ``--help`` and ``--version``
    which are documented implicitly by the argparse banner.
    """
    import re
    baseline_path = Path(__file__).parent / 'fixtures' / '.baseline-flags.txt'
    baseline = set(baseline_path.read_text().splitlines())

    # The guide's narrative covers --help / --version in the Overview and
    # 4. Command-line reference text rather than as table entries.
    implicit = {'--help', '--version'}
    expected = baseline - implicit

    guide_path = Path(__file__).parent.parent / 'docs' / 'user_guide.rst'
    guide = guide_path.read_text()
    guide_flags = set(re.findall(r'--[a-z0-9_-]+', guide))

    missing = expected - guide_flags
    assert not missing, (
        f'docs/user_guide.rst is missing CLI flags: {sorted(missing)}. '
        'Add them to the relevant table in section 4 (Command-line reference).'
    )


def test_no_args_succeeds() -> None:
    """Running ``picmaker`` with no positional arguments exits 0 (no-op)."""
    proc = _run()
    assert proc.returncode == 0


def test_nonexistent_file_exits_nonzero() -> None:
    """A missing input path produces a non-zero exit and surfaces
    ``FileNotFoundError`` / ``No such file`` via ``sys.excepthook``.
    """
    proc = _run('/nonexistent/path/should/not/exist.IMG')
    assert proc.returncode != 0
    assert 'No such file' in proc.stderr or 'FileNotFoundError' in proc.stderr


def test_versions_produces_two_output_files(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """``--versions FILE`` re-parses the CLI for each non-blank line in the
    file; a two-line ``two_versions.txt`` produces two output files
    (``_v1.jpg`` and ``_v2.tif``) for one input fixture.
    """
    proc = _run(
        '--versions', str(fixtures_dir / 'two_versions.txt'),
        '--directory', str(tmp_path),
        '--replace=all',
        str(fixtures_dir / 'cassini_iss.vic'),
    )
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / 'cassini_iss_v1.jpg').exists()
    assert (tmp_path / 'cassini_iss_v2.tif').exists()
