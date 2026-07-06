# picmaker — critique (2026-07-04)

Assessment of the current `src/picmaker/` on branch `mark-2026-06`. No code was modified;
this is assessment only. Findings marked **[verified]** were confirmed by reading the cited
source; the rest are reviewer-reported and plausible but not independently re-checked.

## Top line

This is a healthy, mature package — a completely different picture from the 2026-06-28
critique of the broken rewrite. Everything imports and runs, the 556-test suite passes,
coverage is 96.86 %, and the architecture is sound: `__init_subclass__` auto-registration
is clean, the parse → validate → deconflict → get_versions option contract is coherent,
and `tiff16.py` / `orientation.py` / `colornames.py` are genuinely solid.

What remains is a handful of real correctness bugs hiding in untested corners, a cluster of
inconsistent `None`/`KeyError` guards across otherwise-parallel HST readers, and some
copy-paste that a couple of shared helpers would remove. None of it blocks normal use;
most of it bites only on option combinations or data types the test suite doesn't exercise.

## Status (updated 2026-07-06)

Sections **A**, **B**, **C**, **D**, all five **E** items, and all of **H** (the H1–H5
nits) are resolved (560 tests pass, coverage 96.79 %; ruff, mypy, bandit, vulture clean);
each is annotated inline below. The **E** fixes came as part of a broader option-pipeline
refactor (see note below). In **G**, the test-quality and tooling items are addressed
(snapshot flake, weak branch tests, worthless rot90 snapshots, NICMOS pixel assertion,
`run-all-checks.sh` divergence); G5 (committed binary bulk) is in progress — 99 MB → 64 MB
so far, with the remaining targets identified below. Two deliberate carve-outs: the Galileo
`IndexError` is accepted as unreachable, and the duplication in **F** is disregarded by the
maintainer. **The only work left is the tail of G5** (further data shrink/replacement).

**Refactor note.** E3–E5 were fixed by restructuring the pipeline rather than by patching
in place: `validate_options` is now a pure per-dict validator; `picmaker` performs the
movie/versions mutex check, then `get_versions` (once), then per-version
validate → deconflict → shift; `get_versions` returns raw dicts and rejects any
control-option redefinition (which is how recursive `--versions` is now caught); and the
parser runs with `exit_on_error=False` (so `main()` catches `ArgumentError`). User-facing
error/log messages were also capitalized consistently, and `--replace` uses the value
`"warning"` with a dedicated `FileOverwriteWarning`. The test suite was migrated to all of
these contracts.

---

## A. Correctness bugs (verified against source) — ✅ all resolved

1. **`--rotate` is a silent no-op in the real pipeline.** [verified] ✅ **FIXED**
   The `rotate_rgb_array` parameter was renamed `rotation`→`rotate` so the pipeline key now
   binds; `tests/test_orientation.py` was updated to the `rotate=` kwarg (and the new
   `unrecognized rotate` message); snapshots were regenerated. The regeneration confirmed
   the diagnosis: all seven `--rot90` fixtures had been byte-identical to their `--default`
   baselines, and only `hst_wfpc2--rot90.jpg` (the one non-symmetric pattern) actually
   changed — the other six 16×16 gradients are rotation-symmetric.
   `picmaker1` calls `rotate_rgb_array(array_rgb, default_upward=..., **options)`
   (`picmaker.py:309`). The options dict carries the key `rotate` (parser `dest`,
   `options.py:175`/`316`), but the function's parameter is `rotation`
   (`orientation.py:11`), and the function has `**kwargs`. So `rotate=...` is absorbed and
   discarded, `rotation` stays `None`, and `if not rotation: return array_rgb`
   (`orientation.py:43`) returns unrotated. Nothing anywhere remaps `rotate`→`rotation`.
   A documented, user-visible feature does nothing. Worse, the `rot90` snapshot fixture
   (`tests/snapshots_index.py` → `{'rotate':'rot90'}`) was generated with this bug, so it
   is actually un-rotated and self-consistently "passes." **Fix:** rename the parameter to
   `rotate`, or translate the key in `deconflict_options`, and regenerate that snapshot.

2. **VAX single-precision reals are decoded as doubles.** [verified] ✅ **FIXED**
   `_pds3_support.py:289` guarded `if sample_bytes == 32:` to select `from_vax32`, but
   `sample_bytes = sample_bits // 8` (`:155`), so a 32-bit VAX float has
   `sample_bytes == 4`, never 32 — the `from_vax32` branch was unreachable and every VAX
   real fell through to `from_vax64`. Now tests `sample_bytes == 4`.

3. **Four error messages print literal `{…}` instead of the value.** [verified] ✅ **FIXED**
   The missing `f` prefixes on `instruments/__init__.py:127/129/179` (`{filepath}`) and
   `options.py:439` (`{versions}`) are now all `f`-strings.

4. **`--pattern`/`patterns` escapes the defaults-table validation.** [verified] ✅ **FIXED**
   The parser defines `--pattern` with `dest='patterns'` (`options.py:38`) but
   `_OPTION_DEFAULTS` keyed it as `'pattern'`; the defaults entry is now `'patterns'`, so
   the real value is validated and no phantom key is injected.

5. **Latent crash on 16-bit wrap/pad.** [verified] ✅ **FIXED**
   `wrap_pil_image` defaulted `gap_color='white'` → `ColorNames.lookup(...)` returns a
   *tuple*, then the two-byte path did item assignment `gap_color[0] = ...` → `TypeError`
   on any 16-bit image; `pad_pil_image` had the identical pattern. Both now rebuild a new
   tuple instead of mutating in place. (Still untested — the `--16` + `--wrap`/`--pad`
   combo has no test; see G.)

---

## B. Inconsistent guards across the HST readers (reviewer-reported) — ✅ resolved

All four items below are fixed: `hst_wfc3`/`hst_acs` now use `hdu.header.get('EXTNAME')`,
`hst_wfc3` added an `if digits:` grism guard, `hst_wfpc`/`hst_wfpc2` filter `None` out of
`lambda_nms` before `np.mean`, and `nh_lorri`/`nh_mvic` forward `**kwargs`. The Galileo
`IndexError` is accepted as unreachable (annotated in source). Original findings:

- **`get_hst_filter_digits(...)` can return `None`, and several readers use the result
  unguarded.** `hst_wfc3.py:70-76` does `digits * (retint or 1)` with no None-check (a
  grism such as `G280` that isn't matched by `_IS_UNDIAGNOSTIC` → `TypeError`);
  `hst_wfpc.py:57-59` and `hst_wfpc2.py:61-64` call `np.mean(lambda_nms)` where the list may
  contain `None`. Contrast `hst_foc.py:54`, which explicitly drops `None` — that is the
  pattern the others should follow.
- **`hdu.header['EXTNAME']` used as a hard index** in `hst_acs.py:74` and `hst_wfc3.py:61`
  raises `KeyError` on any extension HDU lacking `EXTNAME`, whereas `hst_wfc3.py:84` uses
  the safer `.get('CCDCHIP')`. Pick one style.
- **`detect_in_pds3` doesn't forward `**kwargs`** in `nh_lorri.py:40` and `nh_mvic.py:46`,
  so `obj`/`pointers` are silently ignored there, unlike Cassini/Voyager/Galileo.
- **`galileo_ssi.py:74` indexes `_FILTER_NAMES[...]`** with a VICAR filter index and will
  `IndexError` (past the detection guard) on an out-of-range value instead of degrading to
  no tint.

---

## C. Edge-case crashes in image processing (reviewer-reported)

- **`stretch.py:63`**: with `footprint` set and the antimask all-False, `np.min(array[...])`
  ran on an empty array (`ValueError`) *before* the fully-masked guard that returns
  `(0., 1.)`. ✅ **FIXED** — the empty check now runs ahead of the footprint block and
  `unmasked` is recomputed after filtering.
- **`processing.py:108`**: `fill_zebra_stripes` initialized `lprev = 1` and indexed
  `array2d[lprev]`, so a single-line image → `IndexError`. ✅ **FIXED** — an early
  `if lines <= 2: return array` guard.
- **`enhancement.py`**: no direct NaN handling in the non-histogram path; a NaN not covered
  by `invalid_mask` flows through to the output (`:94,104` comparisons are False for NaN,
  `np.clip` preserves NaN). ✅ **RESOLVED** — the coupling is now documented: the
  `apply_colormap` docstring states `invalid_mask` must include "all NaNs in `array`", so
  the caller's obligation to sanitize NaN is explicit rather than implicit.

---

## D. Mutation / aliasing hazards (reviewer-reported) — ✅ resolved

The package documents that a source array is shared across output "versions"
(`processing.py:85-88`), which makes in-place writes on shared arrays risky:

- **`slicing.py` `_crop_array` mutated the caller's array.** When `valid` + `crop` are set
  on an integer (or NaN-free float) array, no copy was taken and `array[mask] = crop`
  wrote into the original. ✅ **FIXED** — the pre-mutation is removed; the crop bounds are
  still computed correctly because masked pixels are excluded via `other_value &= ~mask`.
- **`pil_utils.py` `array_to_pil` did in-place `*=`** on the `np.atleast_3d(...)` view,
  corrupting a float 0–1 caller array. ✅ **FIXED** — now `array = array * 65535.9999` /
  `array = array * 255.99999`, which allocates a new array rather than mutating the view.

---

## E. Option-pipeline robustness (reviewer-reported) — ✅ all resolved (via refactor)

- **`--replace warn` is broken under `main()`.** `main()` sets
  `warnings.simplefilter('error')` (`main.py:19`), so `get_outfile`'s `warnings.warn(...)`
  for `replace=='warn'` was promoted to an exception instead of warn-and-overwrite.
  ✅ **FIXED** — the overwrite path now emits a dedicated `FileOverwriteWarning`, and
  `main()` exempts that category from the warnings-as-errors escalation
  (`warnings.filterwarnings('always', category=FileOverwriteWarning)`), so `--replace
  "warning"` warns-and-overwrites instead of aborting. (The `replace` value was renamed
  `warn`→`warning` across the parser, choices, and docstring.) Covered by
  `test_control.py::…test_replace_warning_overwrites_under_main_warning_config`.
- **Version-file options use a different index origin.** `main()` shifted
  `obj/band/bands/lines/samples` from 1-based to 0-based on the base kwargs only, so
  `--versions` lines were never shifted and the same option meant different things on the
  command line vs in a versions file. ✅ **FIXED** — the shift is now factored into
  `options.shift_to_zero_origin` and applied *once, after validation, uniformly to every
  resolved dict* (base and each version) inside `picmaker`, gated by a `_shift_origins`
  flag that `main()` sets and that defaults off (so programmatic 0-based callers are
  untouched). Because nothing is re-validated in 0-based form, this also fixed a latent
  bug where a base `--obj 1` combined with `--versions` silently lost the first object.
  Pinned by `test_versions.py::test_versions_index_options_match_cli_origin`.
- **Self-referential versions files recurse unbounded.** The old `!=` guard only caught a
  *different* nested file, so a versions line pointing at the same file re-entered
  `get_versions` forever. ✅ **FIXED** — `get_versions` now rejects *any* control-option
  redefinition in a version line, including `--versions` itself
  (`Versions file … cannot redefine --versions`), so same-file and different-file nesting
  are both refused. Pinned by `test_options_spec.py::test_recursive_versions_rejected`.
- **The versions file is parsed twice** — once to validate and once for real. ✅ **FIXED**
  — the throwaway validation-time expansion is gone; `picmaker` calls `get_versions` once,
  before any file is processed, and validates each expanded version in the same pass.
- **Non-recursive directory scans are unsorted** while the recursive path sorts. ✅ **FIXED**
  — the non-recursive branch now uses `sorted(child.name for child in filepath.iterdir())`,
  matching the recursive walk, so directory scans are deterministic across platforms.

---

## F. Duplication worth factoring out (reviewer-reported) — ⏭️ disregarded by maintainer

_Deliberately not pursued; recorded for reference only._

- The ACS and WFC3 mosaic-assembly blocks (`hst_acs.py:90-110` vs `hst_wfc3.py:82-102`) and
  their `apply_mosaic` methods are near-verbatim copies; likewise the two WFPC readers'
  `detect_in_fits`/`apply_mosaic`. A shared HST mosaic helper would remove all four.
- The science-data regex `r'.*_[cd]0f...'` is duplicated in `hst_foc.py`, `hst_wfpc.py`,
  and `hst_wfpc2.py`; it belongs in `_hst_support.py` with the other shared HST helpers.
- The proceed-try/except/`logger.info('Proceeding after error')` block is repeated three
  times in `picmaker.py` (`:205-210`, `:220-228`, `:235-244`).
- `wrap_pil_image`/`pad_pil_image` share near-identical buffer/color/pre-fill logic
  (`layout.py:41-62` vs `:133-155`).

---

## G. Testing & project hygiene (reviewer-reported)

Testing is above average for a scientific-imaging library — a byte-identical snapshot layer
over smoke/pipeline tests over unit/spec tests, documented regression tests, strong
negative-detection coverage, and round-trip checks. Weaknesses:

- **Byte-identical JPEG/TIFF snapshots vs floating dependency lower bounds was a flake risk.**
  56 JPEG + 7 TIFF byte-for-byte comparisons ran on all 6 CI cells, but every dep is pinned
  only `>=` (`pyproject.toml:11-21`, e.g. `pillow>=12.2.0`); a future libjpeg/Pillow revision
  could change output bytes and turn every comparison red with no code change. ✅ **ADDRESSED**
  — `tests/test_snapshots.py` now compares *decoded pixels* (via `tests.assert_snapshot_matches`)
  instead of file bytes: PNG/TIFF must match exactly, while JPEG must stay within tight
  thresholds on both the largest-absolute and RMS per-pixel difference
  (`SNAPSHOT_JPEG_MAX_TOL = 5`, `SNAPSHOT_JPEG_RMS_TOL = 0.5` DN). A failure reports both
  measured metrics against their thresholds plus guidance, so a tester can tell benign
  encoder drift from a real regression. (The single-cell `git diff` freshness check is
  unchanged — a separate determinism check, not the cross-cell flake.)
- **~19 of 56 test files assert only `.exists()`.** The `--zebra`/`--wrap`/`--pad`/`--up`/
  `--down`/`--tint`-no-info tests in `test_pipeline_branches.py` were no-crash guards, not
  correctness checks — they'd pass on visibly wrong pixels. (This is also why the 16-bit
  layout crash in A.5 slipped through.) ✅ **ADDRESSED** — these are now pixel-level tests
  (rendered losslessly to PNG via a `_render` helper): `--up`/`--down` assert a vertical
  mirror with the bright band at opposite edges; `--pad` asserts a uniform pad border
  around centered content; `--zebra` asserts a crafted edge zero-stripe is actually filled;
  `--wrap` asserts an elongated strip reflows taller-and-narrower; `--tint`-no-info asserts
  byte-identical output to the untinted render.
- **The `--rot90` snapshots were near-worthless — and this is why the A.1 bug hid.** All
  seven `--rot90` fixtures were byte-identical to their `--default` baselines, so the
  snapshot layer never actually exercised rotation. ✅ **ADDRESSED** —
  `test_pipeline_branches.py::test_rotate_actually_rotates` renders a quadrant-distinct
  8×8 array and asserts the output equals `np.rot90` of the unrotated render (for `rot90`
  and `rot180`), which fails outright if `--rotate` is a no-op.
- **Marquee real-data render (NICMOS) asserted geometry only**, never pixels — the real
  render path had no pixel-level assertion. ✅ **ADDRESSED** —
  `test_hst_nicmos_read.py::test_nicmos_tinted_render_applies_red_tint` renders the real
  FITS to PNG and asserts the F187N red tint is genuinely applied (G channel tracks B, the
  image is colored not grayscale, and it has real structure) — reproducible without the
  unbundled reference JPEGs.
- **Binary test data committed under `test_files/`** — permanent git-history blobs (the
  16×16 synthetic `tests/fixtures/` are the better model). The bulk is a handful of
  full-frame products the tests only need enough of to exercise a reader/pipeline; candidates
  for **shrinkage** (block-average the image HDUs via `support/shrink_fits.py`) or
  **replacement** (swap for small synthetic/fewer samples). 🔄 **In progress — 99 MB → 64 MB:**

  | Rank | File(s) | Size | Consuming test | Action | Status / note |
  |---|---|---|---|---|---|
  | 1 | `nh_mvic/mc0_..._sci.fit` | 33 MB→**560 KB** | `test_nh_mvic_previews.py` | shrink | ✅ **done** — block-averaged ×8 to 85×628; the detached `.lbl`'s record pointers, `LINES`/`LINE_SAMPLES` and `FILE_RECORDS` recomputed from the shrunk FITS, and the 4 reference previews regenerated |
  | 2 | `hst_wfc3/*_small.fits` (drz/flt/raw) | **17 MB** | `test_hst_wfc3_read.py` | shrink | still ~850² — see "why still big" below; re-shrinkable ~100× |
  | 3 | `hst_acs/*_small.fits` (drz/flt/raw) | **17 MB** | `test_hst_acs_read.py` | shrink | same structure as WFC3 |
  | 4 | `cassini_iss_fmovie/subdir{1,2}/*.IMG` | 13 MB→**11 MB** | `test_cassini_iss_fmovie_movie.py` | replace | 🔄 2 unscaled originals removed (the 6 scaled `_xNN` ramp frames drive the test); the rest could be replaced with tiny synthetic frames |
  | 5 | `nh_lorri/lor_..._sci.fit` | **10 MB** | `test_nh_lorri_previews.py` | shrink | pure 1024×1024 ×3 → factor-8/16 to ~64–128 px |
  | 6 | `hst_wfpc2/u2tf0504t_c{0,1}f.fits` | **3.9 MB** | `test_hst_wfpc2_read.py` | shrink | 4×400×400 detector cube → shrink the 400² planes |

  **Why the HST `_small.fits` are still big** — the "_small" pass only reduced the *linear*
  dimensions partway (to ~850², or 410×819 for the two-chip `flt`), not to the 16–100 px
  synthetic scale, and each file keeps *every* 32-bit plane the pipeline reads past:
  a `drz` is three ~850² planes (SCI + WHT + CTX ≈ 2.9 MB each = 8.7 MB; the `HDRTAB` is
  only ~15 KB); an `flt` is two chips × {SCI, ERR, DQ} ≈ 6.7 MB plus four ~0.11 MB `HDRLET`
  blobs. Further block-averaging those planes ~8–10× (and/or dropping the ancillary
  WHT/CTX/DQ/HDRLET HDUs the reader doesn't consult — SCI, and ERR for the mosaic-detection
  `'ERR' in hdulist` check, are the only ones needed) would cut each to a few hundred KB.

  Lower priority (each < ~1 MB, ~4 MB combined): `hst_nicmos` (1.1 MB), `hst_foc` (1.0 MB),
  `galileo_ssi` (0.8 MB), `voyager_iss` RAW+CLEANED (1.4 MB) — shrinkable but small wins.

  Caveat: shrinking an input changes the rendered output, so each shrink also requires
  regenerating that test's committed reference previews (`assert_preview_matches`) and
  updating any hard-coded expected shapes. Best remaining ROI is **#5** (pure single-image
  file) and **#2/#3** (drop ancillary planes + re-shrink).
- **Local `run-all-checks.sh` diverged from CI:** it hardcoded `venv/` (aborting if absent)
  and defaulted bandit/vulture *off* while CI runs them, so a green local run could fail CI.
  ✅ **FIXED** — an `activate_venv` helper sources `$VENV/bin/activate` if present and
  otherwise falls back to the active Python environment (no more abort); `ENABLE_BANDIT` /
  `ENABLE_VULTURE` now default *on* to match CI (`ruff format` stays off, as CI intends).
  Also fixed the two nits: removed the stray `# TODO ... parallelism` (`pyproject.toml`) and
  corrected the copy-paste `--cov=psfmodel` comment to `--cov=picmaker`. Verified: the
  script runs all checks green with no `venv/` present.
- `fail_under = 95` vs actual 96.86 % is a thin ~1.9-pt margin. Config hygiene is otherwise
  above average (well-commented `filterwarnings`, justified ruff/bandit ignores).

---

## H. Smaller items / nits

- **H1** — `_pds3_support.py` read the private `label._filepath`; an upstream rename would
  silently redirect detached-file resolution to `Path('.')`. ✅ **FIXED** —
  `read_pds3_image_array` now takes the label's `filepath` explicitly (threaded from the
  `detect_in_pds3`/`detect_in_file` callers), so no private attribute is consulted. Filed
  [SETI/rms-pdsparser#20](https://github.com/SETI/rms-pdsparser/issues/20) requesting a
  public `filepath` property upstream.
- **H2** (`instruments/__init__.py`), three parts: multi-file stacking keeps only
  `results[0]`'s tint/orientation (`:100-105`); the ZZZ-sorts-last contract is load-bearing
  but was undocumented (`:28`); the `detect_in_file` loop was wrapped in a bare
  `except Exception: pass`, masking real reader errors as "unrecognized file format."
  ✅ **ADDRESSED** — H2a/H2b documented with comments (the "first frame wins" stacking
  behavior and the ZZZ-last sort invariant); H2c's blanket catch removed, so a reader's
  genuine error now propagates instead of being masked.
- **H3** — `zzz_generic.py` (the 16-bit TIFF branch): if `read_tiff16` raised,
  `array`/`palette` were left unbound and the `palette is not None` check then raised —
  which H2c turned from a masked "unrecognized file format" into a raw `UnboundLocalError`.
  ✅ **FIXED** — the palette-check and `return` moved into an `else:` clause, so a failed
  `read_tiff16` falls through to the PIL handler and, if that also fails, to the clean
  "unrecognized file format" error. Pinned by
  `test_instruments_cascade.py::test_corrupt_tiff_falls_through_to_unrecognized`.
- **H4** — `sizing.py` `get_size`: `best_overlap`/`test_overlap` and the post-loop
  `quality = best_quality` were computed/tracked but never returned (dead bookkeeping).
  ✅ **FIXED** — the six dead lines removed; `best_quality`/`quality_1x1` and the in-loop
  `quality` (all load-bearing for the wrap-search) are kept, so there's no behavior change
  (vulture clean, suite green). The larger "decompose the wrap-search loop" refactor is
  deliberately deferred.
- **H5** — assorted one-liners. ✅ **FIXED**: `pil_utils.py` reshape now uses `image[0]`
  instead of the leaked loop variable `c`; `is_science_hdu` returns a plain boolean
  (single `return ... == 'SCI'`); the `hst_wfpc.py` docstring says "WFPC" not "WFPC2"; the
  unused `pdsparser`/`pyfits` `# noqa` imports are removed from `nh_lorri`/`nh_mvic`; and
  `control.py`'s deprecated `logger.warn` was already replaced with `logger.warning` during
  the `--replace "warning"` work. All behavior-preserving; ruff/mypy/bandit/vulture clean.

---

## What's solid (don't touch)

`tiff16.py` (read path mirrors write field-by-field with validation and proper file
handling), `orientation.py` (clean, well-documented — modulo the aliasing note),
`colornames.py` (correct data + lookup), the `__init_subclass__` registration design, the
`_pds3_support.py` reader (careful and well-commented, apart from the VAX branch), and the
overall option-pipeline contract. The falsy-check (`if not x`) and `x or default` idioms are
used deliberately throughout and are **not** flagged here.
