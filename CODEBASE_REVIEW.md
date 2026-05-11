# Codebase analysis: `rms-picmaker`

## Summary

`rms-picmaker` is a single-developer scientific tool (PDS3 / VICAR / FITS → JPEG/TIFF) that has been **wrapped in a modern packaging shell (PEP 621 `pyproject.toml`, src layout, Sphinx, ReadTheDocs, RTD, CI workflows, `.cursor/rules/*`) without modernizing the code itself**. The runtime code in `src/picmaker/` is essentially the 2009–2023 legacy CLI: one 3,493-line `picmaker.py` god module, plus two pre-PEP-8 utility files. The project's own rule set (`.cursor/rules/python_best_practices.mdc`, `dependency_management.mdc`) is violated almost everywhere in the source.

**Top three priorities:**

1. **There are zero tests and CI runs nothing.** `tests/` is an empty directory; `.github/workflows/run-tests.yml` has every meaningful step commented out and only triggers on `workflow_dispatch`. `fail_under = 90` plus no tests means the toolchain is fictional.
2. **Split `picmaker.py` (3,493 lines) into a proper package** with `__init__.py`, `__all__`, `py.typed`, and modules per concern (CLI, IO/readers, enhancement, geometry, color, write-out). Migrate the CLI from deprecated `optparse` to `argparse`.
3. **Make CI actually enforce the standards already declared** (ruff, mypy, pytest, Sphinx `-W`, pymarkdown) and align the Python-version matrix with `requires-python = ">=3.10"`.

---

## 1. Structure and layout

- **Finding (Critical):** `src/picmaker/` has no `__init__.py`. **Evidence:** `ls src/picmaker/` shows only `colornames.py`, `picmaker.py`, `tiff16.py`, `_version.py`; `[tool.setuptools.package-data] "picmaker" = ["py.typed"]` references a marker that does not exist. **Impact:** users have to write `from picmaker.picmaker import ...`; there is no public API surface (`__all__`), no module docstring, no `__version__` re-export, and no `py.typed`, so downstream users get no type information. **Suggestion:** add `src/picmaker/__init__.py` that re-exports the documented public API (`images_to_pics`, `process_images`, `read_image_array`, `array_to_pil`, etc.), declares `__all__`, and exposes `__version__` via `importlib.metadata`. Add a real empty `py.typed` file.
- **Finding (High):** `picmaker.py` is 3,493 lines — explicitly forbidden by `.cursor/rules/python_best_practices.mdc` §2 ("ALWAYS keep modules under 1000 lines"). Function `images_to_pics` alone spans roughly lines 893–1485 (~590 lines) with **53 parameters**. **Suggestion:** decompose into a package (e.g. `picmaker/cli.py`, `picmaker/io.py`, `picmaker/labels.py`, `picmaker/enhance.py` (stretch / gamma / histogram / colormap), `picmaker/geometry.py` (slice / crop / wrap / pad / rotate / resize), `picmaker/pil_utils.py`, `picmaker/color.py`, `picmaker/tiff16.py`, `picmaker/_filters.py`). Replace `images_to_pics`' giant kwargs surface with a dataclass (the RORO pattern from rule §2).
- **Finding (High):** `tiff16.py` does test code at import time. **Evidence:** `src/picmaker/tiff16.py:478–681` defines `test()`, `gray_test()`, `rgb_test()`, `palette_test()`, and module-level `from vicar import *` / `from optparse import OptionParser` / `ROTATE_DICT = {...}`. None of this should ship with the library. **Suggestion:** move the test driver into `tests/test_tiff16.py`, remove the `from vicar import *`, and delete the test/driver functions from the library module.
- **Finding (Medium):** Inconsistent shebangs and module headers across `src/picmaker/`. **Evidence:** `picmaker.py:1` `#!/usr/bin/env python3`, `tiff16.py:1` `#!/usr/bin/python3`, `colornames.py:1` `#!/usr/bin/python`. Library modules generally should not have shebangs at all; the executable entry is `[project.scripts] picmaker = "picmaker.picmaker:main"`. **Suggestion:** drop shebangs from every file under `src/picmaker/`.
- **Finding (Low):** Repository contains a `legacy/` directory in the working tree (per the initial `git status`) and a `.coverage` binary at the root. **Suggestion:** confirm `legacy/` is intentional and gitignored / clearly marked; keep `.coverage` untracked (the gitignore already covers it).

## 2. Best practices alignment

These map directly against `.cursor/rules/python_best_practices.mdc`.

- **Finding (High):** Multi-import on one line and unsorted imports (rule §2). **Evidence:** `picmaker.py:16` `import os, sys, fnmatch`, mixed std/third-party/local order across lines 16–33. **Suggestion:** split per import, group std / third-party / local, sort alphabetically (ruff `I` will fix this automatically).
- **Finding (High):** Wildcard import in a library module (rule §2). **Evidence:** `tiff16.py:22` `from struct import *`, `tiff16.py:478` `from vicar import *`. **Suggestion:** import explicit names (`from struct import pack, unpack`); remove vicar wildcard with the test code.
- **Finding (High):** Mutable default arguments (forbidden by ruff `B006` which is enabled in `pyproject.toml [tool.ruff.lint].select`). **Evidence:** `picmaker.py:895` `strip=[]`, `pointer=['IMAGE']`; `picmaker.py:896` and `picmaker.py:3423` `strip=[]`. **Suggestion:** use `strip=None` / `pointer=None` and normalize inside the function.
- **Finding (High):** Shadows the `filter` builtin as a parameter name (rule §1, ruff `A`). **Evidence:** `picmaker.py:906` `filter='NONE'` in `images_to_pics`. **Suggestion:** rename to `filter_` or `filter_name` (the latter is already used internally — `filter_image(image, filter_name)`).
- **Finding (High):** `print()` for diagnostic output and `sys.exit()` from library code (rule §2: no `print()` in library code; `sys.exit()` only in CLI entry points). **Evidence:** 42 `print(` matches in `picmaker.py`; `sys.exit(1)` at line 789 and `sys.exit(2)` at line 793 are inside `main()` but additional `print` calls appear deep inside library functions (e.g. `tiff16.py:558` `print("Unrecognized mode")`). **Suggestion:** introduce `logger = logging.getLogger(__name__)`, replace diagnostic `print` with `logger.info/warning/debug`, and keep user-facing messages only in `main()`.
- **Finding (High):** Exception swallowing and traceback loss (rule §2: smallest granularity, use `raise ... from`). **Evidence:** `picmaker.py:1540–1543`:

```python
    except IOError as e:    # Problem reading file
        raise e
    except Exception:       # Not a pickle file
        pass
```

  The `raise e` reraises but resets the traceback context for diagnostics, and `except Exception: pass` masks bugs. Similar patterns repeat at `picmaker.py:1565`, `1574`, `1582`, `1590`. **Suggestion:** delete the `except IOError as e: raise e` (it's a no-op that loses context — just remove the clause); narrow the second except to the specific exception types raised by `pickle.UnpicklingError` / `EOFError`.

- **Finding (Medium):** `raise IOError("File already exists: " + outfile)` and similar throughout (`picmaker.py:1729`, `3033`, `3373`, `3409`, `3483`). **Evidence:** `IOError` is an alias for `OSError`. `"File overwritten"` in line 3485 uses `warnings.warn`, but `read_pil` does `return IOError(...)` at line 3373 (a bug — it returns an exception instance instead of raising it). **Suggestion:** define a `PicmakerError(Exception)` base, plus specific subclasses (`UnsupportedFormatError`, `LabelParseError`); fix the `return IOError(...)` bug; use f-strings for messages.
- **Finding (Medium):** Function shape violates the "≤3 positional args, keyword-only after `*`" rule. **Evidence:** `images_to_pics(filenames, directory=None, verbose=False, *, …)` is fine, but `read_one_image_array(filename, labelfile, obj=None, hst=False)`, `slice_array(...)`, `crop_array(...)`, `get_limits(...)`, `get_outfile(infile, outdir=None, strip=[], suffix="", extension="jpg", replace='all')` etc. all have many positional args. **Suggestion:** insert `*` after the first 1–3 logical positional arguments per rule §2.
- **Finding (Medium):** Deprecated CLI library. **Evidence:** `picmaker.py:19` `from optparse import OptionParser`; `optparse` has been **deprecated since Python 3.2** ("The optparse module is deprecated and will not be developed further; development will continue with the argparse module"). The project targets 3.10–3.13. **Suggestion:** migrate `main()` to `argparse` (also fixes rule §2: don't `getattr(options, 'foo')`; argparse namespaces support direct attribute access).
- **Finding (Medium):** `os.path` string manipulation throughout instead of `pathlib.Path` (rule §2: prefer `pathlib`). **Evidence:** `os.path.split`, `os.path.exists`, `os.path.splitext`, `os.path.join`, `os.makedirs` are used pervasively. **Suggestion:** standardize on `pathlib.Path` for new code; accept `str | os.PathLike` in public API.
- **Finding (Medium):** `open()` without `encoding=` for text files (rule §2). The binary opens (`open(..., 'rb')`) are fine; check that any text reads (e.g. when reading label files in `pdsparser`) specify UTF-8 at the call site.
- **Finding (Medium):** Banner comments and 2-space / 1-space indentation. **Evidence:** `picmaker.py:42–793` uses 2-space indent inside `main()`, while other functions use 4-space. Lines like `picmaker.py:1617–1620` use 2-space indent inside a `try:` block. **Suggestion:** run `ruff format` once across the codebase.
- **Finding (Low):** `if __name__ == "__main__": main()` on a single line (`picmaker.py:3493`) — minor, but `ruff format` will fix.

## 3. Types and static checks

- **Finding (High):** No type annotations anywhere in `src/picmaker/`. **Evidence:** none of the 30+ `def` signatures have parameter or return annotations; `[tool.mypy].strict = true` is configured but mypy is **not** installed (`# "mypy>=1.0"` is commented out in `dev` extras), and CI never runs it. **Suggestion:** install mypy in `dev`, annotate the public API first (`images_to_pics`, `read_image_array`, `array_to_pil`, `apply_colormap`, `get_outfile`, ...), then internal helpers; commit `py.typed`. Numpy ≥ 1.20 has stubs, so `npt.NDArray[np.float64]` annotations are straightforward.
- **Finding (Medium):** Ruff is configured strictly (`A`, `B`, `N`, `PT`, `RUF`, `UP`, ...) but never run; current code violates many of those rules (mutable defaults, builtin shadowing, `optparse` (UP), bare two-arg `IOError`, etc.). **Suggestion:** baseline with `ruff check --fix`, then `ruff format`, then enable both as required CI steps.
- **Finding (Medium):** Docstrings inconsistent with rule §6 (Google style with `Parameters:`, 90-char wrap). **Evidence:** most public functions use ad-hoc `Input:` / `Inputs:` / `Return:` blocks (e.g. `picmaker.py:1502`, `3307`, `3387`, `3425`). Sphinx/Napoleon won't render these as parameters. **Suggestion:** convert to Google style (`Parameters:` / `Returns:` / `Raises:`); napoleon is already enabled in `docs/conf.py`.

## 4. Testing

- **Finding (Critical):** `tests/` is **empty**. **Evidence:** `ls tests/` returns no files; `addopts = ["-n", "auto", "--cov=src", ...]` with `fail_under = 90` means any run that actually tries to enforce the threshold will hard-fail. **Suggestion:** add a `tests/conftest.py` and start with smoke + golden-image tests for the simpler pure functions (`get_outfile`, `find_common_path`, `circle_mask`, `apply_gamma`, `array_to_pil`, `pil_to_array`, `slice_array`, `crop_array`, the colormap dict). Then add integration tests over a small bundled FITS/VICAR/PDS3 fixture.
- **Finding (High):** Test driver code is mixed into the library (`tiff16.py:488–681`). **Suggestion:** move to `tests/test_tiff16.py` and re-shape as `pytest` functions.
- **Finding (Medium):** Pytest config combines `pythonpath = ["src"]` *and* an installed editable package. Either alone is fine; both is redundant and surprising — and the package-name mismatch (`--cov=src` vs `[tool.coverage.run].source = ["picmaker"]`) is fragile. **Suggestion:** since you install editable, drop `pythonpath`. Change `addopts` to use `--cov=picmaker` (package name) so coverage is consistent with `[tool.coverage.run].source`.

## 5. Performance and resource use

- **Finding (Medium):** `apply_colormap` / `_percentile_lookup` / `get_limits` use unbounded Python-level loops over per-pixel arrays where vectorized numpy would be substantially faster (functions are 100+ lines each). **Suggestion:** profile against representative inputs once tests exist; vectorize hot loops with `np.searchsorted`, `np.clip`, or `np.histogram` instead of Python iteration.
- **Finding (Low):** `read_one_image_array` repeatedly opens the file with multiple library probes (Pickle → numpy → VICAR → FITS) using broad `except`s, including reading `f.read(9)` after several failed loads. **Suggestion:** sniff the magic bytes once and dispatch.

## 6. Maintainability and extensibility

- **Finding (Critical):** README is unwritten. **Evidence:** `README.md` "Features" section is `TODO`; "Getting Started" is `TODO`; `pyproject.toml` has `description = "TODO"` and `keywords = ["TODO"]`. **Suggestion:** populate description/keywords; document a one-liner usage example for the CLI and the library.
- **Finding (High):** Sphinx docs render the public API via a single `automodule:: picmaker` (`docs/module.rst`), but `picmaker` has no `__init__.py` to export anything; the readers will likely have to do `picmaker.picmaker`. **Suggestion:** with the `__init__.py` proposed in §1, `:members:` will pick up the curated public API.
- **Finding (High):** Tight coupling between CLI parsing and library functions. **Evidence:** `images_to_pics` takes 53 keyword arguments that exactly mirror CLI flags (`limits=`, `percentiles=`, `colormap=`, `tint=`, `display_upward=`, `display_downward=`, `rotate=`, `filter=`, ...). **Suggestion:** introduce a `PicmakerOptions` dataclass; have the CLI build one and pass it; library callers can construct the dataclass directly.
- **Finding (Medium):** A `proceed` local variable in `main()` is read inside `process_images` (`picmaker.py:858`) but never passed or declared global — it works only because `process_images` shadows nothing and Python looks up `proceed` in enclosing scope at run time of the import-level call. **Evidence:** `picmaker.py:507` `proceed = options.proceed` (inside `main`); `picmaker.py:858` `if proceed: return` (inside `process_images`). This is a latent NameError waiting to happen if `process_images` is called from anywhere except `main()` after `proceed` has been bound. **Suggestion:** pass `proceed` as a parameter.

## 7. Security and robustness

- **Finding (Low):** No use of `subprocess`, `eval`, `exec`, `shell=True`, or secrets in source. Inputs come from CLI flags and on-disk files; FITS is opened via `astropy` with `warnings.filterwarnings('error')` to detect non-FITS — that's defensive.
- **Finding (Low):** `os.makedirs(parent)` (`picmaker.py:3316`) races with concurrent runs. **Suggestion:** `Path(parent).mkdir(parents=True, exist_ok=True)`.
- **Finding (Low):** `pickle.load(f)` on attacker-supplied paths (`picmaker.py:1535`). For an astronomy CLI the threat model is internal, but worth a one-line README note that pickle inputs must be trusted.

## 8. Dependencies and tooling

- **Finding (Critical):** CI is dead. **Evidence:** `.github/workflows/run-tests.yml` runs only on `workflow_dispatch`; the lint job stops at "Install dependencies"; the test matrix is entirely commented out; lint / mypy / Sphinx / pymarkdown steps are commented out. **Suggestion:** re-enable `pull_request: branches: [main]` and `push: branches: [main]`; un-comment the steps; matrix `python-version: ['3.10', '3.11', '3.12', '3.13']` to match `requires-python`.
- **Finding (High):** CI Python version mismatch. **Evidence:** `pyproject.toml` `requires-python = ">=3.10"` and `[tool.ruff] target-version = "py310"`; current lint job pins **only** 3.13; `publish_to_pypi.yml` builds on 3.12. **Suggestion:** test the full 3.10–3.13 matrix; build sdist/wheel on the lowest supported Python (3.10) or use `actions/setup-python` with `python-version-file` to keep one source of truth.
- **Finding (High):** Dev extras are missing tools the rules require. **Evidence:** `mypy`, `bandit`, `vulture` are all commented out in `[project.optional-dependencies].dev`, but `python_best_practices.mdc` §5 requires mypy. `pip-audit` is not in dev or in CI despite `dependency_management.mdc` §5 mandating it. **Suggestion:** add `mypy>=1.0` (required by rules) and `pip-audit`; add bandit/vulture as opt-in only if you actually intend to run them.
- **Finding (Medium):** Publish workflow uses a long-lived API token. **Evidence:** `publish_to_pypi.yml:37` `password: ${{ secrets.PYPI_API_TOKEN }}`. **Suggestion:** switch to PyPI Trusted Publishers (OIDC) — drop the secret and add `permissions: id-token: write`.
- **Finding (Low):** Stale and silent CLI tools. **Evidence:** `scripts/run-all-checks.sh` advertises bandit/vulture/mypy gating, but the dev extras don't install them, so the script is a no-op for those checks. **Suggestion:** keep the script honest — either install the tools or remove the flags.

## 9. Technical debt and risk

- **Finding (High):** Codebase predates the project rules; every rule under `python_best_practices.mdc` §1–§8 has at least one violation. **Suggestion:** treat the first reformat / ruff-fix / type-annotate pass as a single mechanical commit, separate from semantic refactors, to keep history reviewable.
- **Finding (Medium):** Deprecated APIs. `optparse` (since 3.2). `from struct import *`. `array.astype("float")` (string dtype is fine but `np.float64` is the preferred idiom). `np.dstack` returns; OK. `Image.FLIP_LEFT_RIGHT` etc. were renamed under `Image.Transpose` in Pillow 9.1 (the old names still work via deprecated aliases but emit `DeprecationWarning`). **Suggestion:** use `Image.Transpose.FLIP_LEFT_RIGHT` etc.
- **Finding (Medium):** `IOError("File overwritten: " + outfile)` in `get_outfile` (`picmaker.py:3485`) is a `warnings.warn` of an `IOError` string — fine, but inconsistent with the explicit `replace == 'warn'` semantics; the warning category should be a `UserWarning`/custom subclass.
- **Finding (Low):** No `__version__` accessible at the package level; `_version.py` is generated by setuptools-scm but never imported in `__init__.py` (because there is no `__init__.py`).

## 10. Packaging and distribution

- **Finding (High):** Metadata stubs. **Evidence:** `pyproject.toml` `description = "TODO"`, `keywords = ["TODO"]`. **Suggestion:** fill in before the next release; pyroma (already in dev extras) flags these.
- **Finding (High):** `py.typed` declared in `package-data` but the file does not exist on disk; users get **no** type hints downstream. **Suggestion:** `touch src/picmaker/py.typed`. (Becomes meaningful only once annotations exist.)
- **Finding (Medium):** Version on PyPI is `0.1.devN` because there is no Git tag matching `setuptools_scm`'s expectations; OK for pre-release, but the README badges link to PyPI versions that don't exist yet. **Suggestion:** tag `v0.1.0` once tests and README land.
- **Finding (Low):** `dependencies` lacks minimum versions (rule `dependency_management.mdc` §3: declare minimums). **Suggestion:** add e.g. `numpy>=1.23`, `pillow>=9.1` (needed for `Image.Transpose`), `astropy>=5`, `scipy>=1.10`, `rms-vicar>=1.2`.

---

## Recommended priorities

1. **Make CI real and enforce the rule set.** Un-comment `run-tests.yml`, add the 3.10–3.13 matrix, install `mypy` + `pip-audit`, run `ruff check`, `ruff format --check`, `mypy`, `pytest`, `sphinx-build -W`, `pymarkdown`. This is the single change that prevents further drift while the rest of the work happens.
2. **Add `src/picmaker/__init__.py`, `py.typed`, a curated `__all__`, and a working README.** Cheap, immediately fixes user-facing breakage of docs and imports, and unblocks adding type annotations.
3. **Write the first tests** for the small pure functions (`get_outfile`, `find_common_path`, `circle_mask`, `apply_gamma`, `array_to_pil` / `pil_to_array`, `slice_array`, `crop_array`) and the `tiff16` round-trip. Move the existing `tiff16.test()` driver into `tests/`. Get coverage > 0 % before turning `fail_under = 90` into a non-lie.
4. **Mechanical hygiene pass:** `ruff check --fix` + `ruff format`. This will fix the mutable defaults, multi-imports, builtin shadowing (`filter=` → `filter_name=`), and the `B`/`SIM`/`C4` issues automatically. Commit separately.
5. **Migrate CLI from `optparse` to `argparse`.** Encapsulate library options in a `PicmakerOptions` dataclass so the CLI just builds and passes that dataclass.
6. **Split `picmaker.py` into a package** (cli, io, labels, enhance, geometry, pil_utils, color, _filters). This unlocks meaningful unit testing and type annotation.
7. **Replace `print()` with `logging`** in library functions; keep CLI-level `print()` only in `main()`.
8. **Add `mypy>=1.0` and annotate the public API.** With `py.typed` and `strict = true`, downstream typed users will benefit.
9. **Tighten publishing:** switch `publish_to_pypi.yml` to Trusted Publishers (OIDC). Add minimum versions to runtime dependencies.

**Areas not reviewed in depth:** the math in `get_limits` / `_percentile_lookup` / `apply_colormap` (correctness; only structural critique above), the FITS/PDS label-handling branches, and behavior of `tinted_colormap` with empty filter info. Those should be revisited once tests provide a safety net.
