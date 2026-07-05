"""Subprocess smoke tests for the `picmaker` CLI entry-point.

These tests verify the user-facing behavior end-to-end (sys.argv parsing,
exit codes, --versions semantics, baseline help text). They're necessarily
slow (one subprocess per test); each test is small to keep total time low.
"""

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
    """The set of flags surfaced in ``--help`` matches the baseline in
    ``tests/fixtures/.baseline-flags.txt`` exactly.
    """
    proc = _run('--help')
    assert proc.returncode == 0
    import re
    # Include digits in the character class so flags like ``--16`` and
    # ``--pds3-method`` are captured whole, not truncated.
    flags = sorted(set(re.findall(r'--[a-z0-9_-]+', proc.stdout + proc.stderr)))
    baseline_path = Path(__file__).parent / 'fixtures' / '.baseline-flags.txt'
    baseline = sorted(baseline_path.read_text().splitlines())
    assert flags == baseline


def test_user_guide_documents_every_cli_flag() -> None:
    """Section 4 of ``docs/user_guide.rst`` auto-generates its option list
    from ``get_parser`` via the ``sphinx-argparse`` directive, so every flag
    is documented by construction. Guard that the directive stays wired to
    the real parser rather than assert on a hand-maintained flag list.
    """
    guide_path = Path(__file__).parent.parent / 'docs' / 'user_guide.rst'
    guide = guide_path.read_text()

    assert '.. argparse::' in guide, (
        'docs/user_guide.rst no longer auto-generates the command-line '
        'reference; restore the sphinx-argparse directive in section 4.'
    )
    assert ':module: picmaker.options' in guide
    assert ':func: get_parser' in guide


def test_no_args_errors() -> None:
    """Running ``picmaker`` with no positional arguments exits non-zero and
    reports that no input files were identified."""
    proc = _run()
    assert proc.returncode != 0
    assert 'No input files identified' in proc.stderr


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
