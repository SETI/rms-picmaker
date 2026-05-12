# Test Suite Critique Report

**Generated:** 2026-05-11
**Scope:** every file under `tests/` (and `tests/conftest.py`, `tests/snapshots_index.py`, and `tests/fixture_recipes/`). 30 test modules, 1 conftest, 1 snapshots index, 18 fixture recipes. Pytest config: `[tool.pytest.ini_options]` in `pyproject.toml`.

## Executive summary

The suite is reasonably comprehensive for a library of this size: 30 test modules covering the public API, the I/O cascade, the per-instrument tint helpers, the geometry/enhancement pipeline, the CLI surface (both subprocess and in-process), and byte-identical snapshot tests against committed expected files. Fixtures are reproducible via dedicated recipe scripts under `tests/fixture_recipes/`. The suite uses `pytest-xdist -n auto`, `--strict-markers`, and `--strict-config`.

The main gaps are concentrated in:

- **`filterwarnings`** is not configured in `pyproject.toml`, so astropy/Pillow/numpy `DeprecationWarning`s emitted during the snapshot tests are silently swallowed — a new warning from a dependency would not fail CI.
- **Exception-message assertions** are good for `pytest.raises(..., match=...)` cases, but several tests assert only on type (`pytest.raises(KeyError)` then `assert ... in str(excinfo.value)` as separate statements — minor stylistic inconsistency, not a defect).
- **Module organization**: `tests/test_misc_branches.py` is 842 lines covering pil_utils + enhance + geometry + _filters + every instrument's fallthrough + tiff16 — it should be split into per-module files. Similarly `test_io_branches.py` (283 lines) mixes io.py edge cases with PDS3-label edge cases.
- **`from picmaker.picmaker import ...`** (the legacy alias) is the dominant import path across the suite, even though `from picmaker import ...` is the canonical public API. Per `test_api_compat.py` the alias is verified, but new tests should prefer the canonical path so a future deprecation of the alias doesn't trip them.
- **Snapshot management**: 63 expected files under `tests/fixtures/expected/` with no CI guardrail against silent regeneration. The skill flags this as the "snapshot drift" risk.
- **A documented bug remains as a passing test** (`test_pil_utils.py:28` `test_rescale_grayscale_returns_uint8_bug`) — per the project's testing rule §7 ("NEVER write a test that passes by ignoring an incorrect result"), this should be an `xfail(strict=True)` or the bug should be fixed.

**Coverage:** the project enforces `fail_under = 90` in `pyproject.toml [tool.coverage.report]`. CI runs `python -m pytest --cov=picmaker --cov-report=xml -n auto tests` and a follow-up `coverage report -m`, so the full suite is exercised. The `addopts` in `pyproject.toml` already include `--cov=picmaker`, so the threshold is checked. **Not verified in this critique**: whether the current test set actually clears 90% (the user did not request a coverage run; the inspection is static).

**Exception messages:** several tests use `pytest.raises(SomeError, match='substring')` correctly (e.g. `test_cli_unit.py`, `test_io_branches.py`). Where `pytest.raises(...) as excinfo` is used (`test_color.py:25`, `test_pds3_reader.py:69`), assertions on `str(excinfo.value)` correctly check the message. No tests use `pytest.raises(SomeError)` alone without verifying behavior beyond the type.

**High-priority fixes vs. nice-to-have:**

| Priority | Item | Status |
|----------|------|--------|
| High | Add `filterwarnings = ["error", ...]` to pytest config | **FIXED** — single targeted Pillow `getdata` ignore tracked in [#9](https://github.com/SETI/rms-picmaker/issues/9). |
| High | Convert `test_rescale_grayscale_returns_uint8_bug` to `xfail(strict=True)` | **FIXED** — renamed to `test_rescale_grayscale_returns_float_in_unit_range`; production bug tracked in [#10](https://github.com/SETI/rms-picmaker/issues/10). |
| Medium | Split `test_misc_branches.py` and `test_io_branches.py` | **FIXED** — split into nine focused files (`test_pil_utils_branches.py`, `test_enhance_branches.py`, `test_geometry_branches.py`, `test_filters_branches.py`, `test_instruments_branches.py`, `test_tiff16_branches.py`, `test_package_init.py`, `test_io_cascade.py`, `test_pds3_reader_branches.py`). |
| Medium | Remove `from __future__ import annotations` from test files | **FIXED** — removed from 24 files. |
| Medium | Move legacy `from picmaker.picmaker import X` to `from picmaker import X` | **FIXED** — migrated 17 files; `test_api_compat.py` keeps the legacy path intentionally (it's the BC-alias verifier); `test_enhance.py` takes the private `_percentile_lookup` from the leaf module. |
| Medium | Add a CI step to detect silent snapshot drift | **Open**. |
| Low | Parameterize repetitive test bodies | **Open**. |

### Status update (2026-05-11)

Final check status:

- pytest: **470 passed, 1 xfailed** (the strict-xfail for the `pil_utils` `rescale=True` bug — [#10](https://github.com/SETI/rms-picmaker/issues/10))
- ruff: **clean** (test files have no per-file ignores beyond `tests/test_*.py` = ["N806"])
- mypy strict: **clean** for all `src/` and `tests/`
- Sphinx `-W`: **clean**

Two GitHub issues were filed during the test-side fixes:

- [#9](https://github.com/SETI/rms-picmaker/issues/9) — Pillow `getdata` migration + `WriteTiff16` file-leak follow-up.
- [#10](https://github.com/SETI/rms-picmaker/issues/10) — `_one_pil_to_array` ignores `rescale=True` for `'L'` mode (production bug behind the new strict-xfail).

Notable side effects:

- Adding `filterwarnings = ["error"]` surfaced an unhandled `ResourceWarning` from `ReadTiff16` (bare `open()` leaked the handle when parsing raised mid-stream); both `ReadTiff16` and `WriteTiff16` are now wrapped in `with open(...) as f:`. The two strict-xfail palette tests in `test_tiff16.py` then started passing (the underlying `palette != None` bug was fixed in the same ruff `--unsafe-fixes` modernisation pass) and were un-`xfail`ed.
- Test renames: the legacy import path `from picmaker.picmaker import X` is now used only by `test_api_compat.py` (intentionally — that test verifies the BC alias is identity-equal to the canonical leaf-module symbol).
- Several `Existence-only asserts` were tightened: `test_io.py::test_instrument_detection` now asserts the exact shape `(1, 16, 16)`; `test_pipeline.py::test_default_options_writes_jpeg` now asserts `img.size == (16, 16)`; `test_io_extra.py::test_sixteen_bit_tiff` now asserts the precise shape `(8, 8)`.
- The `filter` → `filter_name` rename in `images_to_pics` propagated into `test_pipeline.py`, `test_pipeline_branches.py`, and `test_cli_unit.py` (the inline `option_dict` literals and `_normalize_and_validate` assertions).

---

## 1. Return values and assertions

- **Existence-only asserts. FIXED.**
  - `test_io.py:32` `assert array.ndim == 3` — now `assert array.shape == (1, 16, 16)`.
  - `test_pipeline.py:38-39` `assert img.size[0] > 0; assert img.size[1] > 0` — now `assert img.size == (16, 16)`.
  - `test_io_extra.py:31` `assert arr.shape == (8, 8) or arr.shape == (8, 8, 1)` — now `assert arr.shape == (8, 8)`.
- **Exact length / shape.** Most assertions are appropriately precise: `test_geometry.py::TestSliceArray` asserts both shapes and values; `test_io_branches.py` asserts exact `(1, 8, 8)` shapes; `test_pds3_reader.py` round-trips byte values.
- **Dynamic values.** Tests against file-byte output (`test_snapshots.py`) use byte-identical equality — that's the right choice for a deterministic pipeline; if the pipeline ever becomes non-deterministic (e.g. JPEG encoder version drift) this will fail loudly.

## 2. Success and failure conditions

**Per module, what's tested / what's missing:**

| Source module | Tests | Notable missing cases |
|---------------|-------|-----------------------|
| `cli.py` | `test_cli.py` (5 subprocess), `test_cli_unit.py` (33 in-process), `test_alt_strip_alias.py` (alias parity) | `--versions` with `#`-prefixed comment lines (user_guide.rst:825 documents these are skipped, but `cli.main:543-553` only skips blank lines — no test pins behavior). `--rectangle` parsing across negative or zero corners. `--bands` with `(LO, HI)` where `HI <= LO`. |
| `pipeline.py` | `test_pipeline.py` (12), `test_pipeline_branches.py` (28), `test_snapshots.py` (63 byte-identical), `test_frame_max.py` | `crop=value` with all-equal arrays (the `np.ma.allequal(array, value)` early-return at `geometry.py:128`). Recursive `--versions` interaction with `reuse=` in `process_images`. `images_to_pics` with `replace='warn'` where a `UserWarning` is asserted. |
| `io.py` | `test_io.py` (8 instruments + 4 malformed), `test_io_branches.py` (15), `test_io_extra.py` (10), `test_pds3_reader.py` (15) | `read_pds_labeled_image_array` with `^IMAGE` containing 4-tuple `(filename, offset, unit, "BYTES")`. The `unit == 'BYTES'` branch at `io.py:326` has no positive test. |
| `enhance.py` | `test_apply_gamma.py` (7), `test_enhance.py` (10), `test_zebra.py` (4), `test_misc_branches.py` (7 for get_limits + colormap) | `histogram=True` colormap path (`enhance.py:322-326`). Test exists in `test_pipeline_branches.py::test_extension_default_jpg` indirectly but no unit-level assertion that `rankdata` is being applied. |
| `geometry.py` | `test_geometry.py` (12), `test_geometry_extra.py` (15), `test_frame_max.py`, `test_misc_branches.py` (10 for get_size/wrap/pad) | `get_size` with `wrap=True, size=(W, H), wrap_ratio=R` simultaneously (the search-axes branch at `geometry.py:301-345`). `rotate_array_rgb` with `rotation_name=None` (no `if rotation_name:` test). |
| `color.py` / `_rgb.py` | `test_color.py` (10 ColorNames), `test_tinted_colormap.py` (12), `test_hst_filter_tuple_normalization.py` (5), `test_unknown_filter_warning.py` (2), `test_misc_branches.py` (~25 instrument branches) | `tinted_colormap` with `inst_host=None` returns `None` (covered by `test_misc_branches.py::test_instruments_lookup_returns_none_for_unknown`). The `filter_info is None` short-circuit (`color.py:34-35`) is covered by `test_tinted_colormap.py::test_none_filter_info`. Good. |
| `_filters.py` | `test_misc_branches.py` (3) | Every named filter (`BLUR`, `CONTOUR`, `DETAIL`, ..., `MAXIMUM_7`) — only `blur` and `none` are exercised. A parametrize over `FILTER_DICT.keys()` would cover all 20+ names. |
| `tiff16.py` | `test_tiff16.py` (6 plus 2 xfail), `test_misc_branches.py` (5 extra) | The `transpose=Image.Transpose.FLIP_LEFT_RIGHT` / `FLIP_TOP_BOTTOM` / `ROTATE_180` / `ROTATE_270` branches (only `ROTATE_90` is tested at `test_misc_branches.py:809-815`). The `my_assert(False)` path inside `ReadTiff16` (the `else: my_assert(False)` at `tiff16.py:311`). The currently-unraised `OSError("File format is not TIFF")` at `tiff16.py:281` — see the parent codebase critique; a TIFF version byte ≠ 42 is silently accepted today. |
| `pil_utils.py` | `test_pil_utils.py` (3), `test_misc_branches.py` (5 for 16-bit + list paths) | `pil_to_array` on an `RGBA` PIL image (only `'L'`, `'I'`, and `'RGB'` modes are tested; `RGBA` raises `OSError('Unsupported PIL image format')` per `pil_utils.py:121`). |
| `colornames.py` | `test_color.py` (10) | `ColorNames.lookup` with mixed-case underscored input (`'GHOST_WHITE'`); the strip-and-lowercase path is tested for `'ghost white'` but not the underscore variant. |
| `instruments/cassini.py` | `test_misc_branches.py` (`test_cassini_tint_chain_each_branch` — 13 parametrize cases), `test_tinted_colormap.py` (5) | The `CASSINI` host predicate is tested for `'CASSINI ORBITER'` and rejected for `'HUBBLE'`. (Good.) |
| `instruments/galileo.py` | `test_misc_branches.py` (galileo predicates + KeyError swallow) | Detect path 2 (`LAB01[:7] == 'GLL/SSI'`, `LAB03.partition('FILTER=')`) — `galileo_ssi_b.vic` exists but no unit test calls `galileo.detect_vicar` directly on it; only `test_io.py::test_instrument_detection` covers it through `read_one_image_array`. A direct unit test would localize failure. |
| `instruments/voyager.py` | `test_misc_branches.py` (predicates + KeyError swallow), `test_tinted_colormap.py` | The `LAB02[:3] == 'VGR'` happy path is exercised through `read_one_image_array`. |
| `instruments/hst.py` | `test_misc_branches.py` (~12 branches), `test_hst_filter_tuple_normalization.py` (5), `test_unknown_filter_warning.py` (2) | The `wavelength` digit-extraction loop's `wavelength < 1600` cap (test names this at `test_hst_filter_tuple_normalization.py:42-45` but the cap interaction is a side-effect; would benefit from a dedicated parametrized test for filter names whose digit string exceeds the cap). |
| `instruments/nh.py` | `test_misc_branches.py` (predicates + missing-header branches) | Good coverage. |

**Edge cases not covered anywhere:**

- Empty input list to `images_to_pics([])` returns `(None, None, None)` — pinned at `test_pipeline_branches.py:556-559`. Good.
- `process_images` with `directory=None` (write next to input) — not tested. All `process_images`/`images_to_pics` calls in the suite pass an explicit `directory=str(tmp_path)`.
- Reading a file whose name is a `Path` (not a `str`) — public API claims `str | os.PathLike[str]` but every test passes `str(...)`. The cascade does `filename_str = str(filename)` at `io.py:96`, so a Path *should* work, but it's not pinned.

## 3. Consistency

- **Naming:** Mixed. Most tests use `test_<function>_<scenario>` (e.g. `test_get_limits_trim_zeros_recovers_when_all_zero`). Several use the older `test_<scenario>` (e.g. `test_grayscale_round_trip`, `test_two_horizontal_sections`). Both styles read OK individually but the suite reads slightly inconsistently.
- **Structure (Arrange-Act-Assert):** Generally clean. A few tests interleave setup and asserts (e.g. `test_io_branches.py::test_pds3_prefix_bytes_misaligned_raises:187-205` has 12 lines of label-text setup inside the test body — fine, but a `_write_pds3_lbl_with(field, value, tmp_path)` factory would dedupe with `test_pds3_suffix_bytes_misaligned_raises`).
- **Fixtures:** Same concepts (`fixtures_dir`, `expected_dir`, `tiny_array`) are reused via `conftest.py`. Good. But `test_pipeline.py:80-99`, `test_pipeline_branches.py:223-269`, and `tests/test_snapshots.py` all build option dicts inline; a `basic_option_dict` fixture in `conftest.py` would dedupe.
- **Assertion style:** mostly one logical assert per concept. Multi-assert tests are uncommon and reasonable when present (`test_versions_override.py:50-66` checks two state values from a sequence of two CLI runs).
- **`from __future__ import annotations` usage:** **FIXED** — removed from all 24 affected test files.
- **Import paths:** **FIXED** — legacy `from picmaker.picmaker import X` migrated to `from picmaker import X` in 17 files; only `test_api_compat.py` keeps the legacy path (intentionally — that's the BC verifier).

## 4. Completeness

**Coverage map:** Section 2 summarizes per-module coverage. The two notable gaps are `_filters.py` (only 2 of 20+ named filters exercised) and the `transpose=` branches of `WriteTiff16`/`ReadTiff16` (4 of 5 untested).

**Docstring vs. tests gaps:**

- `picmaker.io.read_one_image_array`'s docstring documents the try-cascade order (pickle → numpy → VICAR → FITS → PIL → PDS3). `test_io_branches.py::test_cascade_falls_through_to_pil` and `test_cascade_falls_through_to_pds3` cover the last two steps. The pickle / numpy / VICAR / FITS positive cases are covered by `test_io.py::test_instrument_detection`. Good.
- `picmaker.io.get_outfile`'s docstring documents four `replace` policies (`all`, `none`, `warn`, `error`). All four are tested in `test_paths.py::TestGetOutfile` — could be parameterized.
- `picmaker.pipeline.images_to_pics`'s docstring promises `(low, high, reuse)` return. The `reuse` element's contract is exercised by `test_pipeline_branches.py::test_process_images_reuse_path` but the docstring doesn't describe the structure of the reuse tuple `(array3d, default_is_up, filter_info, infile)` — so the test would need to be updated if that structure ever changes, and it can't be regression-checked without reading the implementation.
- `picmaker.color.tinted_colormap`'s docstring describes the CL1/CL2/CLEAR/N/A normalization. `test_hst_filter_tuple_normalization.py` covers it.
- `picmaker.geometry.get_size`'s docstring documents four input modes (`size=...`, `frame=...`, default, `wrap=True`). The first three are tested in `test_geometry.py::TestGetSize` and `test_misc_branches.py`. The combined `wrap=True + size=... + wrap_ratio=...` mode is not pinned.

## 5. Redundancy

- **Duplicate coverage of `images_to_pics` defaults.** `test_pipeline.py::test_default_options_writes_jpeg` parametrizes over `ALL_FIXTURES` and asserts `.jpg` exists. `test_snapshots.py::test_byte_identical_snapshot` parametrizes over the same fixtures × `default` slug and asserts byte-identical output. The first is a strict subset of the second. **Suggestion:** keep the snapshot tests; collapse `test_default_options_writes_jpeg` into a single `test_smoke_writes_output_for_every_fixture` that runs with `extension='jpg'` only (no per-fixture parametrize) — or delete it as fully subsumed.
- **Overlapping HST mosaic tests.** `test_pipeline.py::test_hst_acs_branch_executes` and `test_pipeline_branches.py::test_hst_acs_mosaic_writes_output` both call `images_to_pics(..., hst=True)` on the same fixture and assert the JPG exists. **Suggestion:** keep one; the second is more idiomatic (`replace='all'` explicit) and lives next to the other mosaic tests.
- **`test_pipeline.py::test_movie_option_writes_outputs:80-106`** has a 17-line inline `option_dict`. The almost-identical `_basic_option_dict()` factory exists in `test_pipeline_branches.py:223-269`. **Suggestion:** lift `_basic_option_dict()` into `conftest.py` as a fixture; `test_pipeline.py` consumes it.
- **`test_pipeline.py:34, 47, 59, 109` + `test_pipeline_branches.py::test_extension_default_jpg`** all assert the existence of `cassini_iss.jpg` in `tmp_path` after calling `images_to_pics`. Different option combos, OK to keep distinct, but the assertion pattern repeats. A small `_assert_picture_written(tmp_path, stem, ext='jpg')` helper would clarify intent.
- **`test_io_extra.py::test_sixteen_bit_tiff` and `test_io_extra.py::test_sixteen_bit_tiff_rescale`** both call `read_array(..., rescale=False/True)` and assert on shape/range. **Suggestion:** parametrize.
- **`test_geometry_extra.py::TestCircleMask::test_diameter_1, ..._3, ..._5, ..._8, ..._9`** — five tests for the same function with different inputs. **Suggestion:** parametrize.
- **`test_misc_branches.py::test_rotate_array_rgb_rot90, ..._rot270`** — both assert the shape preserves. Parametrize.

## 6. Parallel execution

- **`addopts = ["-n", "auto", ...]`** runs tests in parallel by default. The `run-all-checks.sh` script also passes `--dist loadscope` so each test module pins to one worker.
- **Module-level mutable state.** None observed in `tests/`. `tests/snapshots_index.py` is read-only data. `conftest.py` defines three function-scoped fixtures that return immutable / fresh values.
- **Shared resources.**
  - Tests use `tmp_path` (pytest's per-test tmpdir) for all output paths. Good.
  - Snapshot fixtures live under `tests/fixtures/expected/` (read-only). Good.
  - `test_pipeline_branches.py::test_replace_none_skips_existing:90-103` and other tests write into `tmp_path` only — no cross-test interference.
- **Order dependence.** None observed. `test_versions_override.py::test_main_replace_none_overrides_versions_replace_all:39-66` runs two CLI subprocess invocations in sequence inside one test, but both targets are inside the same `tmp_path` (isolated from other tests).
- **`subprocess.run` calls.** `test_cli.py`, `test_alt_strip_alias.py`, `test_overlap_vs_overlaps.py`, `test_versions_override.py` all `subprocess.run(['picmaker', ...])`. Subprocess invocations don't share state with the parent test process; safe under xdist. Cost: each subprocess test pays the picmaker startup cost (~50-100ms). With `-n auto` parallelism the cost is masked.

## 7. Mocking and dependency isolation

- **External services / network.** None. The suite is fully offline.
- **Time-sensitive logic.** None observed. No `datetime.now()`, no `time.time()` dependencies in production code path. `test_versions_override.py::test_main_replace_none_overrides_versions_replace_all` reads `out_file.stat().st_mtime_ns` — this is fragile under fast filesystems (mtime granularity can be 1ms or coarser, so two writes within the same ms have the same mtime). **Risk:** spurious pass on systems with coarse mtime if the file *should* have been rewritten but the test passes anyway. **Suggestion:** assert on file *contents* (`out_file.read_bytes() == ...`) or `st_size`, not `mtime_ns`.
- **`pytest.MonkeyPatch` usage.** Used in `test_cli_unit.py::test_main_*` to swap `sys.argv` and (in one case) `picmaker.cli._build_parser` to a `kb()` that raises `KeyboardInterrupt`. Used appropriately — narrow scope, restored after test.
- **`mock.patch` usage.** Not used. The suite tests through the public surface and via fixture files, not via in-process mocking of dependencies.
- **Mock return values.** N/A (no mocks).
- **Patch target location.** N/A.
- **Real I/O.** Tests write to `tmp_path` and read from `tests/fixtures/`. Both are isolated from system state.

## 8. Security and input validation

- **Input validation tests.** `test_cli_unit.py` exercises every documented mutex (hst+band, scale+wscale, frame+size, overlap+overlaps, up+down, 16+filter, ...). Each validation rule has at least one negative test asserting `ValueError` with a substring match. Good.
- **`ColorNames.lookup` malicious-input tests.** `test_color.py::TestNegativeLookups` covers unknown name, empty string, hex code, non-string. Missing: a test that an `eval`-injection payload like `'(1,2,3)\n+\nimport os; os.system("ls")'` is rejected. The `RGB_PATTERN` regex blocks it (the multiline second statement fails the `match.end() == len(name)` check), but a regression test would pin the security boundary explicitly. See `CODEBASE_CRITIQUE.md` §7 for the underlying concern.
- **Path traversal.** None tested. `io.get_outfile` joins `outdir` and a stripped input filename. A malicious filename like `'../../etc/passwd'` would currently produce a path outside `outdir`. The threat model for picmaker is "user runs it on their own files" so this is acceptable, but a positive test that `get_outfile(infile='/tmp/../etc/passwd', outdir='/tmp/safe', ...)` lands inside `/tmp/safe` would document the contract.
- **PDS3 label injection.** Not tested. The PDS3 reader uses `pdsparser`, which is presumed safe. A malformed label that triggers `pdsparser.ParseException` is tested (`test_pds3_reader.py::test_unparseable_file_returns_none`).
- **Pickle untrust.** Not tested. The README documents that pickle inputs must be trusted. A `test_pickle_executes_arbitrary_code_warning` documenting the contract would be useful but is currently out of scope.

## 9. Parameterization and data-driven tests

**Already parameterized:**

- `test_alt_strip_alias.py::test_both_spellings_parse` over `ALIAS_PAIRS`.
- `test_apply_gamma.py::TestBoundaryValues::test_zero_and_one_are_fixed_points` iterates `for gamma in (0.4, 1.0, 2.2, 3.0)` inside the test body — **should be parametrized**, not a loop.
- `test_geometry.py::TestRotateArrayRgb::test_named_rotations_run` parametrizes over the 5 named rotations.
- `test_io.py::test_instrument_detection` and `test_malformed_falls_through_cascade` parametrize over fixtures.
- `test_misc_branches.py::test_cassini_tint_chain_each_branch` parametrizes over 13 filter names.
- `test_pipeline.py::test_default_options_writes_jpeg` parametrizes over `ALL_FIXTURES`.
- `test_snapshots.py::test_byte_identical_snapshot` parametrizes over 63 `SNAPSHOTS` entries.

**Should be parametrized:**

- `test_geometry_extra.py::TestCircleMask` (5 tests) — collapse into one parametrize over `(diameter, expected_shape, expected_center_value)`.
- `test_paths.py::TestGetOutfile::test_replace_*` (4 tests) — parametrize over `(replace_policy, expected_result_or_exception)`.
- `test_misc_branches.py::test_rotate_array_rgb_rot90 / _rot270` plus the FLIPLR / FLIPTB / ROT180 cases — parametrize.
- `test_apply_gamma.py::test_zero_and_one_are_fixed_points` — gamma values should be parametrize cases.
- `test_io_extra.py::test_sixteen_bit_tiff` / `test_sixteen_bit_tiff_rescale` — parametrize over rescale boolean.

**Boundary values not tested:**

- `--quality` boundary (1 vs. 0 vs. 100 vs. 101). The CLI declares `--quality N` without a range check; behavior at the extremes is undefined.
- `--gamma 0.0` (should yield `array**0 = 1.0` everywhere, i.e. white image). Documented? Not tested.
- `--percentiles 100 0` (sorted to `(0, 100)` by `_normalize_and_validate`). Tested for `(95, 5)` in `test_cli_unit.py`. Good.
- `--bands 0 0` (empty range). The CLI converts to half-open, so `bands=(0, 0)` is invalid. Not tested.

## 10. Async (if applicable)

Not applicable. The library and tests are entirely synchronous.

## 11. Output and contract

- **Return shape assertions.** Most tests assert exact array shapes (e.g. `(1, 16, 16)`, `(8, 8, 3)`). `test_io.py::test_instrument_detection:32` asserts only `array.ndim == 3` — could be tightened (each fixture is a known size).
- **Exception type + message assertions.** Used consistently. Every `pytest.raises(SomeError, match='substring')` is paired with a message check. The exceptions tested are:
  - `ValueError` for CLI mutex violations and pipeline contract violations.
  - `KeyError` for missing pointers and unknown rotations.
  - `IndexError` for out-of-range obj indices.
  - `TypeError` for invalid `obj` types and `ColorNames.lookup` non-string.
  - `OSError` / `IOError` for unrecognized formats, missing files, replace=error.
  - `UserWarning` for `replace=warn` (via `pytest.warns(UserWarning, match='File overwritten')`).
- **Exception message contents.** `test_color.py::TestNegativeLookups::test_unknown_name_raises:24-27`:
  ```python
  with pytest.raises(KeyError) as excinfo:
      ColorNames.lookup('not_a_real_color')
  assert 'not_a_real_color' in str(excinfo.value)
  ```
  Good pattern. Several other tests use the inline `match=` form, which is equivalent and slightly tighter. Both styles coexist in the suite without conflict.

## 12. Error handling

- Different error conditions are distinguished by type. E.g. `test_pds3_reader.py` exercises `KeyError` (missing pointer), `IndexError` (out-of-range obj), `TypeError` (invalid obj type), `ValueError` (PREFIX_BYTES misalignment) — four separate tests with separate exception types.
- The `pytest.raises(IOError, match='...')` style is used. Note: `IOError is OSError` in Python 3 — both names work. The suite uses `IOError` in older tests and `OSError` in newer ones. Cosmetic only.
- **Exception message assertions** are checked in every relevant test. Examples:
  - `test_pipeline_branches.py::test_pds3_label_missing_pointer_raises:506` `match=r'PDS pointer .* not found'`.
  - `test_pds3_reader.py::test_attached_obj_unknown_name_raises:69` `match='Object MISSING not found'`.
  - `test_io_branches.py::test_pds3_prefix_bytes_misaligned_raises:204` `match='PREFIX_BYTES'`.

## 13. State and workflow

- **State transitions.** No state machine in the library; not applicable.
- **Idempotency.** `images_to_pics` is idempotent for `replace='all'` (re-running produces the same output). The `test_versions_override.py` test runs picmaker twice and asserts the second run is a no-op with `replace='none'`. Good idempotency coverage.
- **Side effects.** File-write side effects are universally tested via `Path.exists()` plus content/bytes equality (`test_overlap_vs_overlaps.py:60`: `assert f1.read_bytes() == f2.read_bytes()`). Logging side effects are tested with `caplog` (see §21 below).

## 14. Test data and fixtures

- **Realistic data.** Fixtures are synthetic 16×16 numpy zeros wrapped in VICAR/FITS labels. Real PDS3/VICAR/FITS files would be much larger and could expose performance issues, but for correctness testing the synthetic fixtures are fine.
- **Cleanup.** All tests write to `tmp_path` (auto-cleaned by pytest). No leakage observed.
- **Fixture scope.** All conftest fixtures are function-scoped (the default). `fixtures_dir` and `expected_dir` return immutable `Path` objects, so a `session` scope would be a valid optimization, but the savings (~1µs per test) aren't worth the conceptual cost.
- **Conftest hierarchy.** Single `tests/conftest.py` at the test root with 3 fixtures. No sub-directory conftests. Good — the rule of thumb "fixtures live in the conftest.py closest to where they're used" is satisfied trivially because all fixtures are used widely.
- **Autouse fixtures.** None. Good.
- **Fixture visibility.** `fixtures_dir`, `expected_dir`, `tiny_array` are all used by multiple test modules. Good.
- **Fixture depth.** Maximum is 1 (no fixture depends on another fixture). Good — easy to trace.
- **Inline setup that could be a fixture.** The PDS3 label-text heredocs in `test_pipeline_branches.py:400-413, 442-444, 462-466` and `test_io_branches.py:191-202, 213-224` could be a `pds3_lbl_factory` fixture that takes keyword args. As-is, ~6 tests each rewrite a similar label.
- **Snapshot fixtures.** 63 files under `tests/fixtures/expected/` plus 16 binary fixture files under `tests/fixtures/`. All regenerable via `tests/fixture_recipes/regenerate_all.py` and `tests/fixture_recipes/generate_snapshots.py`. The regeneration scripts are well-documented and idempotent.
- **`.baseline-flags.txt`** (583 bytes, 60 flags) and `.baseline-help.txt` (12,165 bytes) are committed snapshots of CLI behavior. `.baseline-help.txt` appears to be the *legacy `optparse`* help text (`--directory=DIRECTORY`, `--gap-size=GAP_SIZE`) — but `cli.py` uses `argparse` (which produces `--directory DIRECTORY`). The test `test_help_flag_set_matches_baseline:41-50` uses only the flag names (regex `r'--[a-z_-]+'`), so the `optparse`-style argument syntax in the baseline doesn't matter to that test — but the file is misleading and a reader would assume it's the current help output. **Suggestion:** either regenerate `.baseline-help.txt` from the current `picmaker --help` or rename it to `.baseline-flags-source.txt` to clarify it's only used for the flag-extraction regex.

## 15. Flakiness indicators

- **Time-based assertions.** One concern: `test_versions_override.py:57, 66` `out_file.stat().st_mtime_ns == first_mtime`. See §7 for details. Risk is low (the second run uses `replace='none'`, which should skip the write entirely, so the mtime check pins behavior correctly), but mtime granularity makes the test fragile on some filesystems.
- **Order dependence.** None observed.
- **External dependencies.** None.
- **Random data.** None observed. Fixtures use `np.arange` / `np.zeros` (deterministic).
- **Subprocess invocations** could be slow under load. With `pytest-xdist -n auto` and a JIT-warm `picmaker` entry point, observed test time is small.
- **JPEG / TIFF encoder determinism.** Snapshot tests rely on Pillow producing byte-identical JPEG output across runs. Pillow's `libjpeg-turbo` is deterministic for a given input + quality setting, but a Pillow version bump could change the output. **Risk:** snapshot drift on CI when Pillow is upgraded. **Suggestion:** pin `pillow>=12.2.0` (already done at `pyproject.toml:14`); the lower bound is fine, but a `<13` upper bound for safety would prevent silent snapshot breakage from a Pillow major rev.

## 16. Regression and documentation

- **Bug references.** Several tests reference PR numbers in docstrings (`test_pickle_iolost_propagates_to_final_error.py:1-12` "PR 3 deleted ..."; `test_pil_utils.py:28-32` "Pre-PR3 bug at picmaker.py:3029-3034"). Per project rule §7 ("NEVER include line numbers, verbose rationale, or modification history in test comments"), these are violations. **Suggestion:** trim to one-line summaries; rely on `git blame` for the historical detail. The "PR 3 deleted ..." pattern is especially fragile because once PR 3 is ancient history, the test name `test_pickle_iolost_propagates_to_final_error` and the docstring "PR 3 deleted the IOError" become opaque.
- **Spec alignment.** `docs/user_guide.rst` documents the public CLI surface. `test_cli.py::test_user_guide_documents_every_cli_flag` actively checks that every flag in `--help` appears in the guide. Excellent doc-drift detection. (One of the strongest tests in the suite.)
- **Deprecation warnings.** No deprecated APIs in the package today, so no `pytest.warns(DeprecationWarning)` tests. As deprecations are introduced (e.g. if `from picmaker.picmaker import` is deprecated in a future release), corresponding tests should land.
- **`filterwarnings` configuration.** **FIXED.** `pyproject.toml [tool.pytest.ini_options]` now has `filterwarnings = ["error", "ignore:Image.Image.getdata is deprecated:DeprecationWarning"]`. The single ignore is targeted at the Pillow 12 deprecation and is tracked for removal in [#9](https://github.com/SETI/rms-picmaker/issues/9). Per the skill §16: "Without it, new warnings go unnoticed." Astropy emits `VerifyWarning`, `AstropyDeprecationWarning`, and `AstropyUserWarning` regularly; Pillow emits `DeprecationWarning` for renamed `Image.FLIP_*` aliases. **Suggestion:** add:
  ```toml
  [tool.pytest.ini_options]
  filterwarnings = [
      "error",
      "ignore::DeprecationWarning:astropy.*",  # if needed
  ]
  ```
- **Warning noise.** The `test_warning_elevation.py::test_corrupt_fits_falls_through_via_warning_elevation` test exercises the FITS-branch `warnings.filterwarnings('error')`. Good. The corrupt-FITS fixture only triggers astropy warnings inside that try block, so no warnings leak out of the test.

## 17. Other good practices

- **Clarity.** Test names are descriptive. Docstrings (where present) summarize intent. A few outliers:
  - `test_pickle_iolost_propagates_to_final_error.py` — cryptic file name. "iolost" doesn't appear elsewhere. **Suggestion:** rename to `test_missing_file_propagates_to_unrecognized_format.py`.
  - `test_io_extra.py`, `test_io_branches.py`, `test_misc_branches.py`, `test_geometry_extra.py`, `test_pipeline_branches.py` — five "extra" / "branches" modules whose names tell you nothing about their content. **Suggestion:** rename to reflect what they cover (e.g. `test_io_edge_cases.py`, `test_pds3_reader_branches.py`).
- **Speed.** Subprocess-based tests (`test_cli.py`, `test_versions_override.py`, etc.) are inherently slow (~50-100ms each). With ~15 such tests and `-n auto`, total cost is acceptable. No `@pytest.mark.slow` marker exists; per `pyproject.toml:65` `markers = []`. If subprocess tests grow further, adding a `slow` mark would help dev-loop ergonomics (`pytest -m "not slow"`).
- **Assertion messages.** Most asserts don't include a message. A few do (e.g. `test_pipeline_branches.py:284` `assert (out_dir / 'cassini_iss.jpg').exists(), f'expected cassini_iss.jpg under {out_dir}'`). Inconsistent but acceptable.
- **Single responsibility.** Most tests verify one behavior. The compound tests in `test_versions_override.py:39-66` and `test_io_extra.py::TestWritePil::test_round_trip_quality_setting:51-60` (which writes at two quality levels and asserts both file sizes plus a relation between them) bundle two checks; this is reasonable when the relation is the point of the test.
- **Arrange-Act-Assert.** Generally followed. The PDS3-label tests blend setup and act because the setup *is* part of the act (writing the file).
- **Test logic minimal.** No complex control flow in tests. Some `for` loops (e.g. `test_apply_gamma.py:33-37`) should be `parametrize`, but the loops are simple and the assertions are clear.

## 18. Code coverage

- **Target.** `pyproject.toml [tool.coverage.report] fail_under = 90`. Codecov targets 90% project and patch coverage (`codecov.yml`).
- **Scope.** `[tool.coverage.run] source = ["picmaker"]; omit = ["tests/*", "_version.py", "*/picmaker.py"]`. The omit correctly excludes the BC shim and the auto-generated version file.
- **Measurement.** `pytest.ini_options.addopts = ["-n", "auto", "--cov=picmaker", "--strict-markers", "--strict-config"]`. The full suite is measured by default; CI runs the same command (`python -m pytest --cov=picmaker --cov-report=xml -n auto tests`). The 90% threshold is enforced via `fail_under` in pyproject.
- **Report.** Not run as part of this static critique. The user did not request a coverage run. Based on the test inventory in §2, the modules most likely to be under-covered are:
  - `_filters.py` (only 2 of 20+ filters tested).
  - `tiff16.py` (transpose branches, palette branches all `xfail`).
  - `colornames.py` (the regex/eval/strip branches are partially covered; the trailing-space-after-RGB branch may not be hit).
  - `pipeline.py` HST WFPC2 quad-mosaic geometry (`pipeline.py:407-431`) — exercised via the snapshot tests, so probably covered.

## 19. Pytest markers

- **Marker registration.** `pyproject.toml:65` `markers = []`. The suite uses only built-in marks (`@pytest.mark.parametrize`, `@pytest.mark.xfail`). `--strict-markers` is enabled, so a typo'd mark would fail collection. Good.
- **`--strict-markers`.** Present in `addopts`. Good.
- **`xfail` audit.** **RESOLVED.** The ruff `--unsafe-fixes` pass on `tiff16.py` converted `palette != None` → `palette is not None` (fixing the underlying bug). Both strict-xfail tests then XPASSed; the markers were removed and the tests now pass normally. The only remaining strict-xfail is `test_pil_utils.py::test_rescale_grayscale_returns_float_in_unit_range` (the `pil_utils` `rescale=True` bug tracked in [#10](https://github.com/SETI/rms-picmaker/issues/10)). `test_tiff16.py:50-57, 76-83` — two `xfail(strict=True, reason="...")` tests with detailed reasons referencing the `palette != None` bug. **Verify these xfails still xfail.** If the underlying bug has been fixed (which it appears to have been — the codebase critique didn't flag `palette != None` as broken), the xfails will fail because the strict-xfail tests now pass. **Action required:** run the suite and either un-`xfail` (if the bug is fixed) or leave (if it's not). Looking at `tiff16.py:101` `has_palette = (palette != None)` — the bug persists (this *does* compare a numpy array to None and would raise on a non-None palette). So the xfails are still correctly xfailing.
- **`skip`/`skipif` audit.** None observed.
- **Categorization marks.** None. See §17 — consider adding `slow` for subprocess tests.

## 20. Test boundary

- **Private imports.**
  - `test_cli_unit.py` imports `from picmaker.cli import _build_parser, _normalize_and_validate, _separate_files_and_dirs, main`. Three private leaf helpers. The trade-off is targeted unit testing vs. coupling to internals. The unit tests provide much better failure locator than the subprocess `test_cli.py` tests, so this is a justified violation of the "test through the public surface" rule.
  - `test_misc_branches.py:32` imports `from picmaker.pil_utils import _one_pil_to_array`. One private helper. Same justification.
  - `test_api_compat.py:57` `assert legacy._percentile_lookup is enhance._percentile_lookup` — the BC contract explicitly includes private names, so the test must reach them. Fine.
- **Public API coverage.** `picmaker.__all__` contains 35 names. `test_misc_branches.py::test_package_imports_resolve:832-842` checks a sample of the public surface is callable. `test_api_compat.py::test_package_level_imports_match_leaf_modules:147-159` iterates the full `__all__` and asserts identity with the BC alias. Combined, the public API is well-pinned.
- **Over-mocking.** None — the suite doesn't mock.

## 21. Logging assertions

- **`caplog` usage.** `test_pipeline_branches.py::test_verbose_emits_log:121-133`, `test_pipeline_branches.py::test_proceed_swallows_errors:141-160`, `test_unknown_filter_warning.py::test_unknown_filter_logs_warning:17-28`. Three places, all targeted, all assert on both message presence and (in the unknown-filter case) message content. Good.
- **Log level verification.** `test_unknown_filter_warning.py:23` uses `caplog.at_level(logging.WARNING, logger='picmaker.instruments.hst')` — verifies the warning is emitted at WARNING level on the right logger. Excellent.
- **Absence of logging.** `test_unknown_filter_warning.py::test_unknown_filter_does_not_print:31-38` asserts the legacy `print()` output is **not** present in stdout — pinning the migration from `print` to `logger.warning`. Good negative test.
- **Missing.** No test asserts the absence of warnings in the "happy path". E.g. running `images_to_pics` on a clean Cassini fixture should not emit any warnings or errors. A `with caplog.at_level(logging.WARNING): images_to_pics([fixture], ...); assert not caplog.records` test would catch silent regressions.

## 22. Pytest configuration

- **Config file discovery.** `pyproject.toml` contains `[tool.pytest.ini_options]`. No competing `pytest.ini`, `pytest.toml`, `tox.ini`, or `setup.cfg`. Single source of truth. Good.
- **`testpaths`.** `testpaths = ["tests"]` — present. Good.
- **`python_files` / `python_classes` / `python_functions`.** Not overridden; standard `test_*.py` discovery. Good.
- **Plugin inventory.** Installed via dev extras: `pytest-cov`, `pytest-xdist`. No `pytest-randomly` (which would catch order dependencies — but the suite has none). No `pytest-mock` (which the suite doesn't use). No `pytest-benchmark` (which would help once performance work begins).
- **`addopts`.** `["-n", "auto", "--cov=picmaker", "--strict-markers", "--strict-config"]`. Reasonable defaults. **Missing:** `-W error::DeprecationWarning` or `filterwarnings = ["error"]`. **Missing:** `-q` (quiet) to reduce noise; subjective.
- **Ignored duplicate configs.** Single config file (pyproject). No duplicates.

## 23. Snapshot and golden-file testing

- **Complex output.** `test_snapshots.py` parametrizes 63 (fixture × combo × ext) triples and asserts byte-identical equality against committed snapshots in `tests/fixtures/expected/`. The snapshots index (`tests/snapshots_index.py`) is auto-generated by `tests/fixture_recipes/generate_snapshots.py`.
- **Golden file management.**
  - Snapshots are committed (visible in `tests/fixtures/expected/`).
  - Regeneration is via `python tests/fixture_recipes/generate_snapshots.py`. The script regenerates `snapshots_index.py` to keep test parametrize in sync.
  - **Missing CI guardrail:** there is no CI step that runs the regenerator and asserts no diff. A maintainer could regenerate locally to silence a real bug. **Suggestion:** add a CI step:
    ```yaml
    - name: Snapshot freshness check
      run: |
        python tests/fixture_recipes/generate_snapshots.py
        git diff --exit-code tests/fixtures/expected/ tests/snapshots_index.py
    ```
- **Over-use.** 63 snapshots, but each pins a distinct (fixture, option-combo) pair that exercises a real pipeline path. The combo list (`default`, `gamma2`, `pct5_95`, `colormap_red_blue`, `tint`, `rot90`, `frame_128_pad`, `frame_max_50`, `twobytes_tiff`) covers the major enhancement and geometry knobs. Reasonable coverage; not "approve and forget."
- **Stale snapshot risk.** Pillow / libjpeg-turbo upgrades can change byte output. The runtime deps pin `pillow>=12.2.0` without an upper bound. **Suggestion:** add `pillow<13` (or whatever the current major is) as an upper bound for the lifetime of these snapshots, then regenerate on a Pillow major rev.

---

## Prompt for an AI agent to fix tests

**Note (2026-05-11):** Items 1, 2, 3, 5, and 6 of the prompt below have been applied. Items 4 (parametrize repetitive bodies), 7 (rename `test_pickle_iolost_propagates_to_final_error.py`), 8 (mtime → bytes safety net in `test_versions_override.py`), 9 (absence-of-warnings test), and 10 (CI snapshot-freshness check) remain open and constitute the residual work this prompt now describes.

You are improving a Python library's pytest test suite. Read this critique top to bottom; address the items below **without modifying production code** (`src/picmaker/`), without changing any test's existing passing behavior, and without changing the byte-identical snapshot files under `tests/fixtures/expected/`. Preserve all xfail / skip semantics. Apply the project's testing rules from `.cursor/rules/python_best_practices.mdc` (Section 7) for every new or modified test.

### Required actions

1. **Configuration: add `filterwarnings`.** **DONE** (with one targeted Pillow `getdata` ignore tracked in [#9](https://github.com/SETI/rms-picmaker/issues/9)). Update `[tool.pytest.ini_options]` in `pyproject.toml` to:
   ```toml
   filterwarnings = ["error"]
   ```
   Then run the suite. For any test that legitimately emits a warning (e.g. astropy `VerifyWarning` inside corrupt-FITS tests), add a per-test `@pytest.mark.filterwarnings("ignore:...")` or a `with warnings.catch_warnings(): warnings.simplefilter('ignore')` — do NOT broaden the global filter.

2. **Fix `test_pil_utils.py::TestRoundTrip::test_rescale_grayscale_returns_uint8_bug`.** **DONE** (renamed to `test_rescale_grayscale_returns_float_in_unit_range`, marked `xfail(strict=True)`; production bug tracked in [#10](https://github.com/SETI/rms-picmaker/issues/10)). This test currently *passes* by asserting the buggy behavior (`assert back.max() == 255  # not 1.0`). Convert it to:
   ```python
   @pytest.mark.xfail(strict=True, reason="rescale=True is ignored for 'L' mode PIL images; see _one_pil_to_array")
   def test_rescale_grayscale_returns_float_in_unit_range(self) -> None:
       arr = np.arange(64, dtype=np.float64).reshape(8, 8)
       img = array_to_pil(arr, rescale=True)
       back = pil_to_array(img, rescale=True)
       assert back.dtype == np.float64
       assert back.max() <= 1.0
   ```
   So the bug becomes a recorded expected-failure with strict enforcement (the test will fail if the bug is silently fixed without updating the xfail).

3. **Split monolithic test files.** **DONE** (all nine target files created; the original `test_misc_branches.py` and `test_io_branches.py` were removed). Move tests out of `tests/test_misc_branches.py` into:
   - `tests/test_pil_utils_branches.py` — the `array_to_pil` / `pil_to_array` / `_one_pil_to_array` / `write_pil` tests (lines 39-110).
   - `tests/test_enhance_branches.py` — the `get_limits` / `apply_colormap` / `apply_gamma` branch tests (lines 113-241).
   - `tests/test_geometry_branches.py` — the `get_size` / `wrap_image` / `pad_image` / `slice_array` / `crop_array` / `rotate_array_rgb` tests (lines 244-506).
   - `tests/test_filters_branches.py` — the `_filters.filter_image` tests (lines 511-525).
   - `tests/test_instruments_branches.py` — every per-instrument fall-through and predicate test (lines 528-761).
   - `tests/test_tiff16_branches.py` — the `tiff16` palette/transpose/byteorder tests (lines 770-824).
   Then split `tests/test_io_branches.py` into `tests/test_io_cascade.py` (the reader-cascade tests) and `tests/test_pds3_reader_branches.py` (the PREFIX_BYTES/SUFFIX_BYTES misalignment tests and `read_pds_labeled_image_array` edge cases). Preserve every existing test's behavior — do not change docstrings or assertions during the move.

4. **Parametrize repetitive tests.** **Open** — not done in this round. Convert these tests to `@pytest.mark.parametrize`:
   - `tests/test_apply_gamma.py::TestBoundaryValues::test_zero_and_one_are_fixed_points` — split the inline loop into 4 parametrize cases over `gamma`.
   - `tests/test_geometry_extra.py::TestCircleMask` (5 tests) — one parametrize over `(diameter, expected_shape, center_pixel_value)`.
   - `tests/test_paths.py::TestGetOutfile::test_replace_*` (4 tests) — one parametrize over `(replace_policy, expected_outcome)`.
   - `tests/test_io_extra.py::TestReadArray::test_sixteen_bit_tiff` / `test_sixteen_bit_tiff_rescale` — parametrize over `rescale: bool`.

5. **Remove `from __future__ import annotations` from every test file.** **DONE** (24 files updated). The project targets Python 3.11+ and the import is unnecessary. Run `ruff check --select=UP010 --fix tests/` if available, or remove the lines manually.

6. **Migrate test imports from `picmaker.picmaker` to `picmaker`.** **DONE** (17 files updated; `test_api_compat.py` keeps the legacy path intentionally; `test_enhance.py` takes the private `_percentile_lookup` from `picmaker.enhance`). Any new test should import `from picmaker import X`. For existing tests, only update imports that don't intentionally exercise the BC alias path (`test_api_compat.py` is the BC-verifier and stays as-is). Examples to update: `test_apply_gamma.py`, `test_enhance.py`, `test_frame_max.py`, `test_geometry.py`, `test_geometry_extra.py`, `test_hst_filter_tuple_normalization.py`, `test_io.py`, `test_io_extra.py`, `test_mutable_defaults.py`, `test_paths.py`, `test_pickle_iolost_propagates_to_final_error.py`, `test_pil_utils.py`, `test_pipeline.py`, `test_snapshots.py`, `test_tinted_colormap.py`, `test_unknown_filter_warning.py`, `test_warning_elevation.py`, `test_zebra.py`.

7. **Rename cryptic test files.** **Open**. Rename `tests/test_pickle_iolost_propagates_to_final_error.py` to `tests/test_missing_file_propagates_to_cascade_end.py`. Move the test docstring's "PR 3 deleted..." historical commentary to the commit message and replace it with a one-line summary: "A non-existent path falls through every reader and surfaces as the cascade-end `Unrecognized image file format` error."

8. **Add a flaky-time-stamp safety net.** **Open**. In `tests/test_versions_override.py::test_main_replace_none_overrides_versions_replace_all`, replace the `out_file.stat().st_mtime_ns` comparison with a content comparison: save `first_bytes = out_file.read_bytes()` before the second run; after the second run, assert `out_file.read_bytes() == first_bytes`. (The mtime check is fragile on coarse-mtime filesystems.)

9. **Add absence-of-warnings test.** **Open**. Create `tests/test_happy_path_no_warnings.py` containing:
   ```python
   def test_default_run_emits_no_warnings(fixtures_dir, tmp_path, caplog):
       import logging
       with caplog.at_level(logging.WARNING, logger='picmaker'):
           from picmaker import images_to_pics
           images_to_pics([str(fixtures_dir / 'cassini_iss.vic')], directory=str(tmp_path))
       assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
   ```
   so a future regression that emits a spurious warning fails CI.

10. **Add CI snapshot-freshness check.** **Open**. Add to `.github/workflows/run-tests.yml` (in the `test` job, after the pytest step):
    ```yaml
    - name: Snapshot freshness check
      if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.13'
      run: |
        python tests/fixture_recipes/generate_snapshots.py
        git diff --exit-code tests/fixtures/expected/ tests/snapshots_index.py
    ```
    This detects silent snapshot drift (regenerated locally without commit).

### Coverage requirement

After all changes, run the **entire test suite** with coverage and ensure the existing 90% threshold (`fail_under = 90` in `pyproject.toml`) still passes:

```
python -m pytest --cov=picmaker --cov-report=term-missing --cov-fail-under=90 -n auto tests
```

The split into smaller test files must not decrease coverage. Any module that drops below 90% after splitting should get an additional targeted test to restore the threshold.

### Exception-message assertion requirement

Every new or modified test that uses `pytest.raises(SomeError)` MUST verify the message content via either:

- `pytest.raises(SomeError, match='substring')`, or
- `with pytest.raises(SomeError) as exc_info:` then `assert 'substring' in str(exc_info.value)`.

Do not write tests that only assert on exception type.

### Out-of-scope (do NOT do)

- Do not modify production code under `src/picmaker/`.
- Do not regenerate the snapshot files under `tests/fixtures/expected/`.
- Do not delete or weaken the strict-xfail tests in `tests/test_tiff16.py`.
- Do not introduce mocking; the suite is fully integration-oriented and that's a feature.
- Do not add `pytest-randomly` or other order-randomization plugins (the suite assumes ordering is OK; randomization would surface unrelated issues without finding new bugs).

### Done when

- `python -m pytest -n auto tests --cov=picmaker --cov-fail-under=90` passes locally.
- `ruff check tests` passes.
- No new warnings appear during the test run (the new `filterwarnings = ["error"]` plus the absence-of-warnings test catches this).
- The CI snapshot-freshness step passes (i.e., the snapshots in the repo match what the generator produces).
