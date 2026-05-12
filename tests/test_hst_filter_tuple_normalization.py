"""HST filter-tuple CL1/CL2/N/A/CLEAR* normalization (picmaker.py:2314-2327)."""

from picmaker import tinted_colormap


def test_cl1_grn_normalizes_to_grn() -> None:
    # ('CL1', 'GRN') → 'GRN' → green wavelength inference.
    result = tinted_colormap(('HST', 'WFC3', ('CL1', 'GRN')))
    # GRN is not a 3-digit wavelength → wavelength stays 0 → returns None
    # (the function prints the unknown-filter warning).
    assert result is None


def test_cl1_cl2_normalizes_to_clear() -> None:
    # ('CL1', 'CL2') → both normalize to 'CLEAR' → black/white grayscale.
    result = tinted_colormap(('HST', 'WFC3', ('CL1', 'CL2')))
    assert result == [(0, 0, 0), (255, 255, 255)]


def test_na_filter_paired_with_real_filter() -> None:
    # ('N/A', 'F606W') → 'F606W' → special-case grayscale at line 2334.
    result = tinted_colormap(('HST', 'WFC3', ('N/A', 'F606W')))
    assert result == [(0, 0, 0), (255, 255, 255)]


def test_clear5_paired_with_filter_normalizes_via_startswith() -> None:
    # 'CLEAR5'.startswith('CLEAR') → 'CLEAR'; with 'F555W' as partner, the
    # remaining filter wins → wavelength inference of F555W.
    result = tinted_colormap(('HST', 'WFC3', ('CLEAR5', 'F555W')))
    assert result is not None
    assert len(result) == 3


def test_both_real_filters_concatenated() -> None:
    # Neither side is CLEAR/CL1/CL2/N/A → 'F555W+F606W' constructed and run
    # through the wavelength-inference path. The digit-extraction loop
    # concatenates "555" and "606" into 555606, then caps at wavelength<1600
    # so each digit pushes past the cap; the loop ends at 555 (the largest
    # value reached before the cap takes effect). 555 nm is green; with
    # WFC3/UVIS no NIR rescale applies, so the inferred tint is what
    # RFUNC/GFUNC/BFUNC return at 555 nm.
    result = tinted_colormap(('HST', 'WFC3', ('F555W', 'F606W')))
    assert result == [(0, 0, 0), (255, 60, 60), (255, 255, 255)]
