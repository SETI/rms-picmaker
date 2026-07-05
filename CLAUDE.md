# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`rms-picmaker` (`import picmaker`) converts PDS3/VICAR/FITS astronomy images to JPEG/TIFF/PNG. Python ≥ 3.12, src-layout (`src/picmaker/`).

## Commands

**Dev install:**
```sh
pip install -e ".[dev]"
```

**Run tests:**
```sh
pytest                   # parallel by default (-n auto --cov=picmaker)
pytest -k 'test_name'    # run a single test
```

**Lint:**
```sh
ruff check src tests
MYPYPATH=src mypy tests   # src/picmaker is intentionally untyped and excluded from mypy
bandit -c pyproject.toml -r src -q
vulture src
```

**All checks at once:**
```sh
./scripts/run-all-checks.sh          # parallel
./scripts/run-all-checks.sh -s       # sequential
./scripts/run-all-checks.sh --pytest # just pytest
```

**Regenerate test snapshots** (run when image pipeline output changes):
```sh
python tests/fixture_recipes/generate_snapshots.py
```
After regenerating, verify no unexpected diff: `git diff --exit-code tests/fixtures/expected/ tests/snapshots_index.py`

## Style

- Line length: **90** (not the ruff default of 88)
- Quotes: **single**
- **Do not run `ruff format`** — it is intentionally not enforced; existing style inconsistencies are left as-is
- mypy runs in strict mode; `MYPYPATH=src` is required
- Bandit B301/B403 (pickle) and B110 (try/except/pass) are intentionally skipped — pickle usage is documented and by design, and the try/except/pass is the format-reader cascade's "not this format, move on" control flow

## Testing Quirks

- `tests/snapshots_index.py` is **auto-generated** — never edit it by hand; regenerate via `generate_snapshots.py`
- `tests/fixture_recipes/*_recipe.py` are snapshot-generator scripts, not pytest test files — pytest does not collect them
- Warnings are treated as errors; three specific deprecation warnings are exempted (Pillow 12 `getdata`, astropy `XDG_CONFIG_HOME`, and `datetime.utcfromtimestamp` from the boto3 import chain)
- Coverage minimum is 95%
- Snapshot freshness is checked in CI only on ubuntu-latest + Python 3.13
