"""Verify the kebab-case ↔ snake_case CLI flag aliases produce identical outputs.

Flag aliases covered: --alt-strip / --alt_strip, --gap-size / --gapsize,
--gap-color / --gapcolor, --alt-pointer / --alt_pointer, --trim-zeros /
--trimzeros. Each pair is asserted by checking the `.baseline-flags.txt`
contents (cheap) and by spot-checking that `picmaker --foo` parses without
error (sub-process invocation).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ALIAS_PAIRS = [
    ('--alt-strip', '--alt_strip'),
    ('--alt-pointer', '--alt_pointer'),
    ('--gap-size', '--gapsize'),
    ('--gap-color', '--gapcolor'),
    ('--trim-zeros', '--trimzeros'),
]


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['picmaker', *args], capture_output=True, text=True, check=False
    )


def test_baseline_flags_contains_both_spellings() -> None:
    baseline = (
        Path(__file__).parent / 'fixtures' / '.baseline-flags.txt'
    ).read_text().splitlines()
    for kebab, snake in ALIAS_PAIRS:
        assert kebab in baseline, kebab
        assert snake in baseline, snake


@pytest.mark.parametrize(('kebab', 'snake'), ALIAS_PAIRS)
def test_both_spellings_parse(
    kebab: str, snake: str, fixtures_dir: Path, tmp_path: Path
) -> None:
    fixture = str(fixtures_dir / 'cassini_iss.vic')
    out1 = tmp_path / 'out_kebab'
    out2 = tmp_path / 'out_snake'
    out1.mkdir()
    out2.mkdir()

    # Pick a benign value so the flag is accepted by every option.
    value = 'red' if 'color' in kebab else '1' if 'size' in kebab else 'JUNK'
    # --trim-zeros and --trimzeros are store_true; no value needed.
    if 'trim-zeros' in kebab or 'trimzeros' in kebab:
        r1 = _run(kebab, '--directory', str(out1), fixture)
        r2 = _run(snake, '--directory', str(out2), fixture)
    else:
        r1 = _run(f'{kebab}={value}', '--directory', str(out1), fixture)
        r2 = _run(f'{snake}={value}', '--directory', str(out2), fixture)

    assert r1.returncode == 0, r1.stderr
    assert r2.returncode == 0, r2.stderr
    # Both produced an output file with the same name AND identical bytes.
    files1 = sorted(p.name for p in out1.iterdir())
    files2 = sorted(p.name for p in out2.iterdir())
    assert files1 == files2 == ['cassini_iss.jpg']
    assert (out1 / files1[0]).read_bytes() == (out2 / files2[0]).read_bytes()
