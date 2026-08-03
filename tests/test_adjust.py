"""Cover the Pillow ImageEnhance adjustments.

``adjust_pil_image`` wraps the four ``PIL.ImageEnhance`` classes behind the
``--brighten``, ``--contrast``, ``--saturation``, and ``--sharpen`` options.
Each takes a factor where 1 is neutral, 0 is the degenerate case, and larger
values exaggerate the property.
"""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageFilter

from picmaker.options import get_parser, validate_options
from picmaker.postprocessing import ADJUST_OPTIONS, adjust_pil_image
from tests import generate_previews

DATA_DIR = Path(__file__).parent.parent / 'test_files' / 'juno_junocam'
MAP = DATA_DIR / 'JNCR_2023136_51P00000_V01_shrunk.LBL'   # a color (RGB) product


def _colorful() -> Image.Image:
    """A small RGB image with saturated color and a bright/dark split, so every
    adjustment has something to act on."""
    array = np.zeros((8, 8, 3), dtype='u1')
    array[:4] = (200, 60, 30)
    array[4:] = (40, 90, 180)
    return Image.fromarray(array, 'RGB')


def _saturation(image: Image.Image) -> float:
    """Mean per-pixel spread between the largest and smallest channel."""
    array = np.asarray(image, dtype=float)
    return float(np.mean(array.max(axis=2) - array.min(axis=2)))


# --- no-op paths ---------------------------------------------------------------------

def test_no_options_returns_input_unchanged() -> None:
    """With nothing set the input object is handed straight back, so the common
    case costs no image work at all."""
    image = _colorful()
    assert adjust_pil_image(image) is image
    assert adjust_pil_image(image, filter='blur', quality=75) is image


@pytest.mark.parametrize('option', ADJUST_OPTIONS)
def test_none_is_skipped(option: str) -> None:
    """An option explicitly set to None is skipped, not treated as a factor."""
    image = _colorful()
    assert adjust_pil_image(image, **{option: None}) is image


@pytest.mark.parametrize('option', ADJUST_OPTIONS)
def test_factor_one_is_neutral(option: str) -> None:
    """A factor of 1 leaves the pixels alone. The image is still rebuilt, so this
    checks values rather than identity."""
    image = _colorful()
    result = adjust_pil_image(image, **{option: 1.0})
    np.testing.assert_array_equal(np.asarray(result), np.asarray(image))


# --- each adjustment does its own thing ----------------------------------------------

def test_color_zero_is_grayscale() -> None:
    """``saturation=0`` desaturates completely: every pixel's channels become
    equal. This is the headline use of a zero factor."""
    result = adjust_pil_image(_colorful(), saturation=0.0)
    assert _saturation(result) == 0.0


def test_color_above_one_saturates() -> None:
    """A factor above 1 pushes the channels further apart."""
    image = _colorful()
    result = adjust_pil_image(image, saturation=2.0)
    assert _saturation(result) > _saturation(image)


def test_brightness_scales_toward_black() -> None:
    """Brightness scales pixel values linearly, to black at 0."""
    image = _colorful()
    base = float(np.asarray(image, dtype=float).mean())

    assert float(np.asarray(adjust_pil_image(image, brighten=0.0)).mean()) == 0
    assert float(np.asarray(adjust_pil_image(image,
                                              brighten=0.5)).mean()) < base
    assert float(np.asarray(adjust_pil_image(image,
                                              brighten=1.5)).mean()) > base


def test_contrast_zero_is_flat_gray() -> None:
    """Contrast at 0 collapses the image to its mean, so every pixel is identical."""
    result = np.asarray(adjust_pil_image(_colorful(), contrast=0.0))
    assert len(np.unique(result.reshape(-1, 3), axis=0)) == 1


def test_contrast_above_one_widens_the_range() -> None:
    """A factor above 1 spreads values away from the mean."""
    image = _colorful()
    base = float(np.asarray(image, dtype=float).std())
    result = adjust_pil_image(image, contrast=2.0)
    assert float(np.asarray(result, dtype=float).std()) > base


def test_sharpness_blurs_and_sharpens() -> None:
    """Sharpness at 0 blurs and above 1 sharpens, measured as the spread of pixel
    values around a soft edge. The edge has to be soft and unsaturated: a hard
    0/255 square is already maximally sharp, and sharpening it only overshoots
    into the clipping range, leaving the spread unchanged."""
    array = np.zeros((16, 16), dtype='u1')
    array[6:10, 6:10] = 200
    image = Image.fromarray(array, 'L')
    for _ in range(3):
        image = image.filter(ImageFilter.SMOOTH)
    base = np.asarray(image, dtype=float).std()

    blurred = np.asarray(adjust_pil_image(image, sharpen=0.0), dtype=float)
    sharpened = np.asarray(adjust_pil_image(image, sharpen=3.0), dtype=float)

    assert blurred.std() < base
    assert sharpened.std() > base


def test_grayscale_image_survives_every_option() -> None:
    """A grayscale product takes all four options without error; color saturation
    is simply a no-op on a single-channel image."""
    image = Image.fromarray(np.arange(64, dtype='u1').reshape(8, 8), 'L')
    result = adjust_pil_image(image, brighten=1.2, contrast=1.2,
                               saturation=0.0, sharpen=2.0)
    assert result.mode == 'L'
    assert result.size == image.size


# --- combining, ordering, and the 2-byte guard ---------------------------------------

def test_all_four_apply_in_documented_order() -> None:
    """Given several factors, the adjustments run brighten, contrast, saturation,
    then sharpen. These do not commute, so the combined result must equal applying
    them one at a time in that order -- and must differ from the reverse order."""
    image = _colorful()
    factors = {'brighten': 1.4, 'contrast': 1.3, 'saturation': 0.6, 'sharpen': 2.0}

    combined = adjust_pil_image(image, **factors)

    stepwise = image
    for option in ('brighten', 'contrast', 'saturation', 'sharpen'):
        stepwise = adjust_pil_image(stepwise, **{option: factors[option]})
    np.testing.assert_array_equal(np.asarray(combined), np.asarray(stepwise))

    reversed_ = image
    for option in reversed(list(factors)):
        reversed_ = adjust_pil_image(reversed_, **{option: factors[option]})
    assert not np.array_equal(np.asarray(combined), np.asarray(reversed_))


def test_two_byte_image_raises() -> None:
    """A 16-bit image reaches this step as a list of PIL images, which
    ImageEnhance cannot take."""
    with pytest.raises(ValueError, match='2-byte'):
        adjust_pil_image([], contrast=1.5)


def test_two_byte_image_passes_when_nothing_is_requested() -> None:
    """The guard runs only if an adjustment was actually asked for, so a 16-bit
    image is untouched rather than rejected -- matching ``filter_pil_image``."""
    assert adjust_pil_image([]) == []


# --- option plumbing -----------------------------------------------------------------

@pytest.mark.parametrize('option', ADJUST_OPTIONS)
def test_command_line_option_parses(option: str) -> None:
    """Each option is exposed on the command line as ``--<name>``."""
    flag = '--' + option
    parsed = vars(get_parser().parse_args(['dummy.img', flag, '1.75']))
    assert parsed[option] == 1.75


@pytest.mark.parametrize('option', ADJUST_OPTIONS)
def test_zero_survives_validation(option: str) -> None:
    """A factor of 0 must reach the pipeline. Validation fills in the default for a
    falsy value, which would otherwise turn a deliberate 0 into "unset"."""
    assert validate_options({option: 0})[option] == 0.0
    assert validate_options({option: 2.5})[option] == 2.5
    assert validate_options({})[option] is None


@pytest.mark.parametrize('option', ADJUST_OPTIONS)
def test_negative_factor_rejected(option: str) -> None:
    """Factors are non-negative."""
    with pytest.raises(ValueError, match='minimum'):
        validate_options({option: -1.0})


@pytest.mark.parametrize(('option', 'default'),
                         [('quality', 75), ('gamma', 1.), ('retint', 1.)])
def test_other_options_keep_falsy_fallback(option: str, default: float) -> None:
    """Outside _ZERO_IS_MEANINGFUL, a falsy value still falls back to the default."""
    assert validate_options({option: 0})[option] == default


@pytest.mark.parametrize(('option', 'zero', 'unset'),
                         [('crop', 0., None), ('gap_size', 0, 1), ('overlap', 0., None)])
def test_zero_is_meaningful_beyond_the_adjustments(option: str, zero: float,
                                                   unset: float | None) -> None:
    """Zero is a real request for these too, not an omission: crop away the
    zero-valued border, no gap between strips, no required overlap. Each used to
    collapse to its default -- ``--crop 0``, the example in that option's own help
    text, silently did nothing at all. Omitting the option still gives the default."""
    assert validate_options({option: zero})[option] == zero
    assert validate_options({})[option] == unset


# --- end to end ----------------------------------------------------------------------

def test_cli_saturation_zero_renders_grayscale(tmp_path: Path) -> None:
    """Driven through the whole pipeline, ``--saturation 0`` desaturates a real
    color product while leaving its size and brightness alone."""
    generate_previews(MAP, tmp_path, extra_args=('--extension=jpg', '--suffix=_base'))
    generate_previews(MAP, tmp_path, extra_args=('--extension=jpg', '--suffix=_gray',
                                                 '--saturation', '0'))

    stem = MAP.stem
    with Image.open(tmp_path / f'{stem}_base.jpg') as base_image:
        base = np.asarray(base_image, dtype=float)
        base_saturation = _saturation(base_image)
    with Image.open(tmp_path / f'{stem}_gray.jpg') as gray_image:
        gray = np.asarray(gray_image, dtype=float)
        gray_saturation = _saturation(gray_image)

    assert base_saturation > 1.0                    # the source really is in color
    assert gray_saturation < 0.5                    # JPEG chroma leaves a little
    assert gray.shape == base.shape
    assert abs(gray.mean() - base.mean()) < 1.0     # desaturation preserves brightness


def test_cli_brighten_brightens(tmp_path: Path) -> None:
    """``--brighten`` above 1 raises the mean level of a rendered image."""
    generate_previews(MAP, tmp_path, extra_args=('--extension=jpg', '--suffix=_base'))
    generate_previews(MAP, tmp_path, extra_args=('--extension=jpg', '--suffix=_bright',
                                                 '--brighten', '2'))

    stem = MAP.stem
    with Image.open(tmp_path / f'{stem}_base.jpg') as image:
        base = np.asarray(image, dtype=float).mean()
    with Image.open(tmp_path / f'{stem}_bright.jpg') as image:
        brightened = np.asarray(image, dtype=float).mean()

    assert brightened > 1.8 * base
