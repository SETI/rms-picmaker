"""Singular --overlap vs plural --overlaps reconciliation (picmaker.py:650-654).

`--overlap 0.1` is promoted to the (0.1, 0.1) tuple that `--overlaps 0.1 0.1`
produces directly. Both should yield byte-identical output files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['picmaker', *args], capture_output=True, text=True, check=False
    )


def test_overlap_and_overlaps_byte_identical(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    fixture = str(fixtures_dir / 'cassini_iss.vic')
    out_singular = tmp_path / 'singular'
    out_plural = tmp_path / 'plural'
    out_singular.mkdir()
    out_plural.mkdir()

    r1 = _run(
        '--overlap=0.1',
        '--wrap', '--frame=32', '32',
        '--directory', str(out_singular),
        fixture,
    )
    r2 = _run(
        '--overlaps', '0.1', '0.1',
        '--wrap', '--frame=32', '32',
        '--directory', str(out_plural),
        fixture,
    )
    assert r1.returncode == 0, r1.stderr
    assert r2.returncode == 0, r2.stderr
    f1 = out_singular / 'cassini_iss.jpg'
    f2 = out_plural / 'cassini_iss.jpg'
    assert f1.exists() and f2.exists()
    assert f1.read_bytes() == f2.read_bytes()
