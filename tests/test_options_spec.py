"""Spec tests for :mod:`picmaker.options`, derived from the docstrings.

``validate_options`` documents that it fills defaults and validates every value,
raising ``KeyError`` for an off-list choice, ``TypeError`` for a value of the
wrong type, and ``ValueError`` for an invalid or contradictory value. These
tests exercise those documented contracts as a black box.
"""

from pathlib import Path
from typing import Any

import pytest

from picmaker.options import (
    deconflict_options,
    get_parser,
    get_versions,
    validate_options,
)


def _validated(**overrides: Any) -> dict[str, Any]:
    result: dict[str, Any] = validate_options(dict(overrides))
    return result


# --- documented Raises -----------------------------------------------------


def test_off_list_choice_raises_keyerror() -> None:
    """A value outside a choice list is rejected (``--extension`` choices)."""
    with pytest.raises(KeyError, match='Unrecognized'):
        _validated(extension='xyz')


def test_non_list_for_paired_option_raises_typeerror() -> None:
    """A scalar where a pair is required (``bands``) is a type error."""
    with pytest.raises(TypeError):
        _validated(bands=5)


def test_wrong_scalar_type_raises_typeerror() -> None:
    """A non-integer ``band`` is a type error."""
    with pytest.raises(TypeError):
        _validated(band='x')


def test_wrong_string_type_raises_typeerror() -> None:
    """A non-string where a string is required (``suffix``)."""
    with pytest.raises(TypeError):
        _validated(suffix=123)


def test_pair_too_short_raises_valueerror() -> None:
    """A ``bands`` pair with too few values is invalid."""
    with pytest.raises(ValueError):
        _validated(bands=[1])


def test_pair_too_long_raises_valueerror() -> None:
    """A ``bands`` list with too many values is invalid."""
    with pytest.raises(ValueError):
        _validated(bands=[1, 2, 3])


def test_below_minimum_raises_valueerror() -> None:
    """A ``band`` index below the documented minimum is invalid."""
    with pytest.raises(ValueError):
        _validated(band=-1)


def test_above_maximum_raises_valueerror() -> None:
    """A ``quality`` above 100 is invalid."""
    with pytest.raises(ValueError):
        _validated(quality=200)


def test_element_out_of_range_raises_valueerror() -> None:
    """An out-of-range element inside a pair is invalid."""
    with pytest.raises(ValueError):
        _validated(bands=[0, 3])       # band indices start at 1


def test_recursive_versions_rejected(tmp_path: Path) -> None:
    """A versions file may not itself request another versions file."""
    inner = tmp_path / 'inner.txt'
    inner.write_text('--gamma 2\n')
    outer = tmp_path / 'outer.txt'
    outer.write_text(f'--versions {inner}\n')
    with pytest.raises(ValueError, match='cannot redefine --versions'):
        get_versions(versions=str(outer))


# --- documented defaulting -------------------------------------------------


def test_defaults_are_filled() -> None:
    """Unspecified options come back with their documented defaults."""
    out = _validated()
    assert out['replace'] == 'all'
    assert out['gamma'] == 1.0
    assert list(out['percentiles']) == [0.0, 100.0]
    assert out['quality'] == 75
    assert out['invalid_color'] == (0, 0, 0)        # "black" resolved to RGB


def test_deconflict_defaults_extension_to_jpg() -> None:
    """With no ``--16`` and no extension, the output defaults to jpg."""
    out = deconflict_options(validate_options(
        vars(get_parser().parse_args(['in.vic']))))
    assert out['extension'] == 'jpg'


def test_deconflict_defaults_16bit_to_tiff() -> None:
    """``--16`` with no explicit extension defaults to tiff."""
    out = deconflict_options(validate_options(
        vars(get_parser().parse_args(['in.vic', '--16']))))
    assert out['extension'] == 'tiff'


def test_mask_flag_maps_to_mask_ranges() -> None:
    """``--mask MIN MAX`` is stored as a list of float pairs in ``mask_ranges``, and
    each repeat of the flag adds another range."""
    args = get_parser().parse_args(['x.img', '--mask', '0', '0'])
    assert args.mask_ranges == [[0.0, 0.0]]
    args = get_parser().parse_args(['x.img', '--mask', '0', '0', '--mask', '4095', '1e9'])
    assert args.mask_ranges == [[0.0, 0.0], [4095.0, 1e9]]
    assert _validated()['mask_ranges'] is None


def test_mask_ranges_validation() -> None:
    """``mask_ranges`` is a list of pairs; a bare pair is shorthand for one range."""
    assert _validated(mask_ranges=[[0, 0], [5, 6]])['mask_ranges'] == [[0., 0.], [5., 6.]]
    assert _validated(mask_ranges=(0, 0))['mask_ranges'] == [[0., 0.]]
    with pytest.raises(ValueError):
        _validated(mask_ranges=[[0]])
    with pytest.raises(ValueError):
        _validated(mask_ranges=[[0, 1, 2]])
    with pytest.raises(TypeError):
        _validated(mask_ranges=[0, 1, 2])


def test_versions_line_adds_mask_ranges(tmp_path: Path) -> None:
    """A ``--mask`` in a versions line adds to the base ranges without altering the
    base options used by the other lines."""
    versions = tmp_path / 'versions.txt'
    versions.write_text('--mask 9 9\n--gamma 2\n')
    base = vars(get_parser().parse_args(['x.img', '--mask', '0', '0']))
    base.pop('versions')
    first, second = get_versions(versions, **base)
    assert first['mask_ranges'] == [[0.0, 0.0], [9.0, 9.0]]
    assert second['mask_ranges'] == [[0.0, 0.0]]
