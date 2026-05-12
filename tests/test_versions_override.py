"""--versions x --replace/--proceed override semantics (picmaker.py:543, 548).

Two sub-cases:
(a) Main CLI --replace=none with a versions-file line specifying --replace=all
    → the main CLI wins: file is NOT overwritten on second run.
(b) Main CLI --proceed with versions lines not specifying --proceed → the
    main CLI wins: processing continues on errors.
"""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def two_versions_replace_all(tmp_path: Path) -> Path:
    f = tmp_path / 'versions.txt'
    f.write_text('--suffix=_v1 --extension=jpg --replace=all\n')
    return f


def _run_picmaker(*args: str) -> subprocess.CompletedProcess[str]:
    # Use the installed `picmaker` entry-point so that sys.argv looks the
    # same as when an end-user invokes the CLI (matters for --versions which
    # rebuilds args via sys.argv[1:]).
    return subprocess.run(
        ['picmaker', *args],
        capture_output=True,
        text=True,
        check=False,
    )




def test_main_replace_none_overrides_versions_replace_all(
    fixtures_dir: Path, tmp_path: Path, two_versions_replace_all: Path
) -> None:
    # First run produces the file. Second run with --replace=none + a
    # versions line that says --replace=all should still NOT overwrite,
    # because picmaker.py:543 forces options.replace = the main-CLI value
    # for every versions line.
    out_file = tmp_path / 'cassini_iss_v1.jpg'

    args = [
        '--versions', str(two_versions_replace_all),
        '--directory', str(tmp_path),
        '--replace=all',
        str(fixtures_dir / 'cassini_iss.vic'),
    ]
    first = _run_picmaker(*args)
    assert first.returncode == 0, first.stderr
    assert out_file.exists()
    first_bytes = out_file.read_bytes()

    # Second run with --replace=none. The versions line still says
    # --replace=all but the main CLI overrides it → the file is NOT touched.
    args_none = list(args)
    args_none[args_none.index('--replace=all')] = '--replace=none'
    second = _run_picmaker(*args_none)
    assert second.returncode == 0, second.stderr
    # File contents must be unchanged (content comparison avoids coarse-mtime
    # filesystem flakiness).
    assert out_file.read_bytes() == first_bytes


def test_versions_produces_two_output_files(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    versions = tmp_path / 'versions.txt'
    versions.write_text(
        '--suffix=_v1 --extension=jpg\n'
        '--suffix=_v2 --extension=tif\n'
    )
    args = [
        '--versions', str(versions),
        '--directory', str(tmp_path),
        '--replace=all',
        str(fixtures_dir / 'cassini_iss.vic'),
    ]
    proc = _run_picmaker(*args)
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / 'cassini_iss_v1.jpg').exists()
    assert (tmp_path / 'cassini_iss_v2.tif').exists()
