# picmaker rewrite — critique (2026-06-28)

Assessment of the reorganized/rewritten `src/picmaker/` against `OLD/picmaker.py` and
the revised `.cursor/rules/python_best_practices.mdc`. No code was modified; this is
assessment only.

## Top line

The package in its current state **cannot be imported or run at all**. Nine modules fail
to even parse, and several more would raise on import. Beyond the syntax breakage there is
a systemic architectural mismatch (wrong package name in every instrument import,
`super()` misused as a constructor, an `ImageData` contract that nobody actually honors)
plus a long tail of logic inversions in option-validation and pipeline glue.

---

## A. Showstoppers — code does not parse / import

Found by compiling every file individually (`python -m py_compile`):

| File | Problem |
|---|---|
| `cli.py:83` | `--strip` arg: a positional string follows keyword args (missing `help=`) → SyntaxError |
| `pil_utils.py:117-119,125` | `_one_pil_to_array(r, rescale=rescale))` — stray trailing `)` (×4) → SyntaxError |
| `scaling.py:11` | `footprint=0. **kwargs` — **missing comma**. Parses as `0.0 ** kwargs`, a default-value expression evaluated at import → `NameError` on module load |
| `instruments/_hst_support.py:333` | `'(' was never closed` |
| `instruments/hst_acs.py:6`, `hst_nicmos.py:6`, `nh_lorri.py:7`, `nh_mvic.py:7` | `from astropy.io.fits as pyfits` — invalid syntax (should be `import astropy.io.fits as pyfits`) |
| `instruments/hst_wfpc2.py:82` | unmatched `)` |
| `instruments/zzz_generic.py:16` | `class ZZZ_Generic(ImageData)` — missing the `:` |

`cli.py` additionally has a half-merged `get_versions` (lines 247-273): no signature body,
references `options`/`replace`/`proceed`/`sys` that don't exist, a dangling `else`, and
`main()` line 282 `pair = kwargs.get(name, None):` has a stray trailing colon. This whole
function looks pasted from `OLD/picmaker.py` and never finished — and it duplicates the
*working* `get_versions` already in `picmaker.py`.

Until these are fixed, nothing downstream can be exercised, including the test suite.

---

## B. Cross-cutting architectural defects

Consistent across many files, so design-level rather than typos:

1. **Wrong package name in every instrument import.** The package is
   `picmaker/instruments/` (plural), but code imports `from picmaker.instrument import ...`
   (singular) — in `picmaker.py:14` and in *every* instrument module (`nh_lorri.py:9-10`,
   `zzz_generic.py:11-12`, etc.). Every one is an `ImportError`.

2. **`super(...)` used as a constructor.** Ten call sites do
   `return super(array, _DEFAULT_UPWARD, tint)` (e.g. `cassini_iss.py:41`,
   `voyager_iss.py:55`, `hst_*`, `nh_mvic.py:47`). `super()` is not a factory — in a
   `@staticmethod` there is no implicit class/instance, and even in a method this returns a
   proxy, not an `ImageData`. Should be `cls(...)` / `ImageData(...)`.

3. **`ImageData` contract is inconsistent three ways:**
   - `read_image_array` (`instruments/__init__.py:53`) reads `results[0].default_is_up`,
     but the class attribute is `default_upward` (`__init__.py:31`) → `AttributeError`.
     Docstrings (`:42`, `:64`) also advertise the old `default_is_up` tuple name.
   - `read_image_array:50-51` indexes results as tuples (`r[0]`) **and** accesses
     `.default_is_up` as attributes on the same objects — readers can't be both.
   - Instrument subclasses inherit `ImageData` but `detect_in_*` are `@staticmethod`s that
     try to "construct via super" — the subclass relationship is never used to build.

4. **`picmaker.py` requires an `apply_mosaic` method and `default_tint`/`default_upward`
   attributes** (`:230`, `:238`, `:256`) that `ImageData` doesn't define. `apply_mosaic`
   exists nowhere. Mosaic mode will `AttributeError`.

5. **Duplicate, competing implementations.** `read_pds3_image_array` is defined both in
   `instruments/__init__.py:123` and `instruments/_pds3_support.py:15`; `get_fits_array`
   in both `instruments/__init__.py:409` and `instruments/__fits_support.py:7`. Instruments
   import them from yet a third path (`picmaker.instrument._pds3_support`). DRY violation
   (rules §2) that guarantees drift.

---

## C. Logic bugs (would fail even after A and B are fixed)

**`picmaker.py`**
- `validate_options` scale logic is **inverted** (`:64-71`): supplying `--wscale` alone
  (valid) raises, while `--scale` + `--wscale` together (the real conflict) passes. Same
  inversion for overlap (`:79-84`); it never derives `overlaps` from a scalar `overlap`.
- Movie mode is dead (`:169-185`): `imagedata_list = []` is never appended to, so the
  enumerate loop writes zero files.
- `picmaker1` converts the **wrong array to PIL**: `image = array_to_pil(array, ...)`
  (`:263`) uses the raw sliced array, not the colormapped/rotated `array_rgb`. All
  colormap+gamma+rotate work is discarded.
- Mosaic branch (`:237`) calls `apply_colormap(array, ...)` on the full cube instead of
  `array[b]`.
- 16-bit output (`twobytes`) is never threaded into `array_to_pil`/`write_pil` here.
- `picmaker()` has no docstring (rules §6).

**`control.py`**
- `get_filepaths:65-66, 71-72`: `info.append(a, b)` — `list.append` takes one argument →
  `TypeError`. Must be `info.append((a, b))`.
- `:54` missing `f` prefix on the f-string; same in `instruments/__init__.py:72-74`.
- `get_outfile:109` `replace = replace or '_all_'` → falsy `replace` becomes `'_all_'`,
  which fails the `REPLACE_CHOICES` check and raises. Should be `'all'`.
- `__all__ = [REPLACE_CHOICES, ...]` (`:140`) puts a list object into `__all__`; entries
  must be strings. Same in `pil_utils.py:200` and `orientation.py:55` (function object).

**`slicing.py`**
- `:50` `bands.shape[0]` — `bands` is the user's `(b0,b1)` option/`None`, no `.shape`.
- `:72` `sum0.maximum(sum0, 1)` — ndarrays have no `.maximum`; want `np.maximum(...)`.
- `_crop_array:103` references undefined `other_values` (var is `other_value`) → NameError.
- `:61` mutates caller's array in place before any copy; in-place policy inconsistent with
  `processing.fill_zebra_stripes` (which copies).

**`scaling.py`** (beyond the import-time NameError)
- `:38,40` `array.isnan()` — want `np.isnan(array)`. Parameter is named `array2d` (`:10`)
  but the body uses `array` → NameError regardless.
- `:97` `np.percentile(percentiles[:2])` — missing the data argument.

**`enhancement.py`**
- `:116` `for b in bands:` — `bands` is an int count, not iterable; want `range(bands)`.
- `:132` `scaled = np.array(scaled)` references `scaled` before assignment.
- `:134` `scaled[full_mask] = 0.` runs even when `full_mask is None`.
- `:90,97` `colormap[0]`/`colormap[-1]` assume `colormap is not None`.
- `:161,168-169` index `rgb_array[b]` with a channel index, but channel is the last axis of
  `(line, sample, channel)` — channel/line axes conflated.

**`orientation.py`**
- `rotate_array` flips on the absolute `display_upward` flag (`:32`) with no reference to
  `default_upward`, so the instrument default is ignored.

**`sizing.py` / `layout.py`**
- Both call `ColorNames.lookup(...)` (`layout.py:32,126`) without importing `ColorNames` →
  NameError.
- Banner comments say `# pipeline/layout.py` / `# pipeline/sizing.py` — wrong path.
- `write_pil` (`pil_utils.py:167`) `outfile.parent(parents=True, exist_ok=True)` —
  `.parent` is a property, method is `.mkdir(...)`. Every write crashes.
- `pil_utils._one_pil_to_array:145-150` `return` precedes the rescale block in the `'L'`
  branch; grayscale rescale is dead code.

---

## D. Standards violations vs. revised rules

- **Line length 90** (rules §1) vs files still at 100; project `CLAUDE.md` still says 100 —
  the two disagree, pick one.
- **No builtin shadowing** (Ruff `A`): `processing.py:36` `filter=None` shadows builtin.
- **Mutable default args** (`B006`): `control.py:13,80` `patterns=[]`, `strip=[]`.
- **Explicit checks over exceptions** (§1): instruments use broad `try/except KeyError` for
  normal flow; `_read_one_image_array` / `zzz_generic.detect_in_file` swallow with bare
  `except Exception: pass`.
- **Logging, not print** (§2): `cli.py:291` uses `print(...)`.
- **Docstrings** (§6) missing/stale/typo'd ("uf any", "whihch", "operational", "tobe",
  `array2d` vs `array`, "(line, sample, channel)" vs actual `(band,line,sample)`).
- **`py.typed`** deleted despite rules §3; `__all__` lists contain non-strings.
- **Imports** (§2): `cli.py:13` imports from `picmaker.procesing` (typo).

---

## E. Smaller notes

- `instruments/__init__.py:149` `'IMAGE' in value.get('OBJECT')` — `.get` may be `None`
  (raises), and substring match false-positives on `IMAGE_HISTOGRAM`.
- `instruments/__init__.py:377` VAX path checks `sample_bytes == 32` but `sample_bytes` is
  bytes (4/8), not bits — branch never selects `from_vax32`.
- `get_fits_array:435` for `obj>0` a data-less IMAGE HDU returns `hdu.data` which may be
  `None`.
- `tiff16.py` (453 lines) and `colornames.py` (825 lines) reviewed only at interface level;
  the two largest modules deserve their own pass once the package imports.

---

## Suggested order of attack

1. **Make it parse** — fix the 9 syntax errors + `scaling.py` missing comma (Section A).
2. **Make it import** — `instrument`→`instruments` everywhere, delete the duplicate
   `read_pds3_image_array`/`get_fits_array`, converge the `ImageData` contract
   (`default_is_up`/`default_upward`, tuple-vs-object) (Section B).
3. **Fix `super()`→`ImageData(...)`** across all instruments (B2).
4. **Then** the logic inversions in `validate_options`, the `array`/`array_rgb` mixup in
   `picmaker1`, and dead movie mode (Section C) — needs tests, which can't run until 1-3.
5. Lint/style sweep against the new 90-col rule set (Section D).
