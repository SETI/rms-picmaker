"""Geometry helpers: slicing, cropping, rotation, sizing, wrapping, padding.

These functions take numpy arrays or PIL images and shape them — they
do not change pixel values (rotation/flips notwithstanding) or apply
colormaps.
"""

from typing import Any

import numpy as np
from PIL import Image

from picmaker.colornames import ColorNames
from picmaker.pil_utils import array_to_pil, pil_to_array


def circle_mask(diameter: float) -> Any:
    """Return a boolean disk mask of the given diameter.

    Parameters:
        diameter: The disk diameter in pixels.

    Returns:
        A 2-D boolean numpy array where ``True`` marks pixels inside the
        disk. The returned array is trimmed by one pixel on each side if
        the outer row is all-empty.
    """
    size = int(np.ceil(diameter))
    center = size / 2.0 - 0.5

    r = np.arange(size) - center
    r2 = r**2 + r[:, np.newaxis] ** 2
    mask = r2 <= diameter**2 / 4.0

    if np.sum(mask[0]) == 0:
        mask = mask[1:-1, 1:-1]

    return mask


def slice_array(
    array3d: Any,
    samples: Any = None,
    lines: Any = None,
    bands: Any = None,
    valid: Any = None,
    crop: Any = None,
) -> tuple[Any, Any]:
    """Return the requested slice of a 3-D array as a 2-D array.

    Parameters:
        array3d: 3-D image array indexed ``(bands, lines, samples)``.
        samples: Tuple ``(s0, s1)`` selecting the sample range, or
            ``None`` for all samples.
        lines: Tuple ``(l0, l1)`` selecting the line range, or ``None``
            for all lines.
        bands: Tuple ``(b0, b1)`` selecting the band range to average;
            ``None`` for all bands.
        valid: Tuple ``(vmin, vmax)`` of valid pixel values; pixels
            outside this range are masked. ``None`` keeps all pixels
            valid.
        crop: Numeric value to crop from the border of the image (e.g.
            ``0`` to crop zero borders). ``None`` disables cropping.

    Returns:
        ``(array2d, invalid_mask)``. ``array2d`` is the band-averaged
        2-D array; invalid pixels are excluded from the average.
        ``invalid_mask`` may be ``None`` if no pixels are masked.
    """
    slice3d = array3d
    if samples:
        slice3d = slice3d[:, :, samples[0] : samples[1]]
    if lines:
        slice3d = slice3d[:, lines[0] : lines[1], :]
    if bands:
        slice3d = slice3d[bands[0] : bands[1], :, :]

    masked = slice3d
    has_invalid_pixels = False

    nan_mask = np.isnan(masked)
    if np.any(nan_mask):
        masked = np.ma.masked_invalid(masked)
        masked.data[nan_mask] = 0.0
        has_invalid_pixels = True

    if valid:
        masked = np.ma.masked_outside(masked, valid[0], valid[1])
        has_invalid_pixels = True

    if crop is not None:
        masked = crop_array(masked, crop)

    if bands[1] - bands[0] > 1:
        array2d = np.ma.mean(masked, axis=0)
    else:
        array2d = masked[0, :, :].copy()

    invalid_mask = None
    if has_invalid_pixels:
        mask = np.ma.getmaskarray(masked)
        mask = masked.mask
        if np.any(mask):
            invalid_mask = mask[0, :, :]

    return (array2d, invalid_mask)


def crop_array(
    array: Any,
    value: float = 0.0,
    samples: bool = True,
    lines: bool = True,
) -> Any:
    """Crop constant-valued borders from a 2-D or 3-D image.

    Parameters:
        array: A 2-D image ``(lines, samples)`` or 3-D image
            ``(bands, lines, samples)``.
        value: Constant pixel value to trim from the border.
        samples: True to trim sample borders; False to leave them.
        lines: True to trim line borders; False to leave them.

    Returns:
        A view (or sliced copy) of the input with the constant border
        removed.
    """
    if np.ma.allequal(array, value):
        return array

    original_array = array
    if original_array.ndim == 2:
        array = array[np.newaxis, :, :]

    (_, nlines, nsamples) = array.shape

    lmin = 0
    lmax = nlines - 1
    if lines:
        while np.ma.allequal(array[:, lmin, :], value):
            lmin += 1
        while np.ma.allequal(array[:, lmax, :], value):
            lmax -= 1

    smin = 0
    smax = nsamples - 1
    if samples:
        while np.ma.allequal(array[:, :, smin], value):
            smin += 1
        while np.ma.allequal(array[:, :, smax], value):
            smax -= 1

    return original_array[..., lmin : lmax + 1, smin : smax + 1]


def rotate_array_rgb(
    arrayRGB: Any,  # noqa: N803 — preserved kwarg name
    display_upward: bool,
    rotation_name: str | None,
) -> Any:
    """Apply an orientation to an RGB array.

    Parameters:
        arrayRGB: An RGB array.
        display_upward: True to flip the image upward (top-of-image
            becomes top-of-display); False leaves it as is.
        rotation_name: One of ``'NONE'``, ``'FLIPLR'``, ``'FLIPTB'``,
            ``'ROT90'``, ``'ROT180'``, ``'ROT270'``. Case-insensitive.

    Returns:
        The rotated array.

    Raises:
        KeyError: If ``rotation_name`` is not one of the recognized
            choices.
    """
    if display_upward:
        arrayRGB = np.flipud(arrayRGB)

    if rotation_name:
        rotation_name = rotation_name.upper()

        if rotation_name == 'NONE':
            pass
        elif rotation_name == 'FLIPLR':
            arrayRGB = np.fliplr(arrayRGB)
        elif rotation_name == 'FLIPTB':
            arrayRGB = np.flipud(arrayRGB)
        elif rotation_name == 'ROT90':
            arrayRGB = np.rot90(arrayRGB, 1)
        elif rotation_name == 'ROT180':
            arrayRGB = np.rot90(arrayRGB, 2)
        elif rotation_name == 'ROT270':
            arrayRGB = np.rot90(arrayRGB, 3)
        else:
            raise KeyError(f'Unrecognized rotation method: {rotation_name}')

    return arrayRGB


def get_size(
    array_shape: Any,
    size: Any = None,
    scale: Any = (100.0, 100.0),
    frame: Any = None,
    wrap: bool = False,
    wrap_ratio: float | None = None,
    overlap: tuple[float, float] = (0.0, 0.0),
    gap_size: int = 1,
    frame_max: int | None = None,
) -> tuple[Any, Any, int, int]:
    """Compute the output image size and wrap properties.

    Parameters:
        array_shape: Shape of the source numpy array
            ``(lines, samples)`` or ``(lines, samples, bands)``.
        size: Target ``(width, height)``. A scalar means square. ``None``
            keeps the array size.
        scale: Percentage scale to apply. A scalar applies to both
            axes; pass a tuple to scale width/height independently.
        frame: Hard outer ``(width, height)`` constraint. ``None`` for
            no constraint.
        wrap: True to consider wrapping the image to reduce distortion.
        wrap_ratio: Wrap if the width:height (or height:width) ratio
            exceeds this value.
        overlap: ``(min%, max%)`` allowed overlap between wrap sections.
        gap_size: Pixels of gap between wrap sections.
        frame_max: Maximum percentage scale applied when frame is set
            and ``wrap`` is False.

    Returns:
        ``(unwrapped_size, wrapped_size, sections, wrap_axis)``.
    """
    if size is not None:
        if not isinstance(size, (list, tuple)):
            size = (size, size)

    if scale is not None:
        if not isinstance(scale, (list, tuple)):
            scale = (scale, scale)

    if frame is not None:
        if not isinstance(frame, (list, tuple)):
            frame = (frame, frame)

    array_size = [array_shape[1], array_shape[0]]
    if scale is not None:
        array_size[0] *= scale[0] / 100.0
        array_size[1] *= scale[1] / 100.0

    if size is not None:
        (unwrapped_size, quality, expand) = _get_size_for_size(
            array_size, size, 0, 1.0, 1.0
        )
    elif frame is not None:
        (unwrapped_size, expanded_size, quality, expand) = _get_size_for_frame(
            array_size, frame, 0, 1.0, 1.0
        )
        if frame_max and not wrap:
            wfactor = unwrapped_size[0] / array_size[0]
            hfactor = unwrapped_size[1] / array_size[1]
            ratio = frame_max / 100.0 / max(wfactor, hfactor)
            if ratio < 1.0:
                unwrapped_size[0] = int(unwrapped_size[0] * ratio)
                unwrapped_size[1] = int(unwrapped_size[1] * ratio)
    else:
        unwrapped_size = [int(array_size[0] + 0.5), int(array_size[1] + 0.5)]

        if wrap_ratio:
            if unwrapped_size[0] > wrap_ratio * unwrapped_size[1]:
                for k in range(2, 101):
                    expand = 1.0 + overlap[0] / 100.0 * (k - 1.0) / k
                    wrapped_size = [
                        int(unwrapped_size[0] / k * expand + 0.5),
                        unwrapped_size[1] * k + gap_size * (k - 1),
                    ]
                    if wrapped_size[0] <= wrap_ratio * wrapped_size[1]:
                        return (unwrapped_size, wrapped_size, k, 0)

            if unwrapped_size[1] > wrap_ratio * unwrapped_size[0]:
                for k in range(2, 101):
                    expand = 1.0 + overlap[0] / 100.0 * (k - 1.0) / k
                    wrapped_size = [
                        unwrapped_size[0] * k + gap_size * (k - 1),
                        int(unwrapped_size[1] / k * expand + 0.5),
                    ]
                    if wrapped_size[1] <= wrap_ratio * wrapped_size[0]:
                        return (unwrapped_size, wrapped_size, k, 1)

    if not wrap or ((size is None) and (frame is None)):
        return (unwrapped_size, unwrapped_size, 1, 0)

    best_quality = quality
    best_sections = 1
    best_axis = 0
    best_unwrapped = unwrapped_size
    best_wrapped = unwrapped_size

    quality_1x1 = quality

    for axis in (0, 1):
        for k in range(2, 101):
            tweak = (k - 1.0) / k
            expand_min = 1.0 + overlap[0] / 100.0 * tweak
            expand_max = 1.0 + overlap[1] / 100.0 * tweak

            if size is not None:
                temp_size = [size[0], size[1]]
                temp_size[axis] *= k
                temp_size[1 - axis] -= (k - 1) * gap_size
                temp_size[1 - axis] //= k

                (unwrapped_size, quality, expand) = _get_size_for_size(
                    array_size, temp_size, axis, expand_min, expand_max
                )
                wrapped_size = size

            else:
                temp_frame = [frame[0], frame[1]]
                temp_frame[axis] *= k
                temp_frame[1 - axis] -= (k - 1) * gap_size
                temp_frame[1 - axis] //= k

                (unwrapped_size, expanded_size, quality, expand) = _get_size_for_frame(
                    array_size, temp_frame, axis, expand_min, expand_max
                )

                wrapped_size = [expanded_size[0], expanded_size[1]]
                wrapped_size[axis] = (wrapped_size[axis] + (k - 1)) // k
                wrapped_size[1 - axis] *= k
                wrapped_size[1 - axis] += (k - 1) * gap_size
                wrapped_size[0] = min(wrapped_size[0], frame[0])
                wrapped_size[1] = min(wrapped_size[1], frame[1])

            if quality < best_quality:
                break

            if frame is not None and k == 2 and quality < quality_1x1 * 1.1:
                continue

            best_quality = quality
            best_sections = k
            best_axis = axis
            best_unwrapped = unwrapped_size
            best_wrapped = wrapped_size

    return (best_unwrapped, best_wrapped, best_sections, best_axis)


def _get_size_for_size(
    array_size: list[float],
    size: Any,
    axis: int,
    expand_min: float,
    expand_max: float,
) -> tuple[list[int], float, float]:
    """Fit an image array into an available pixel area."""
    scale = [size[0] / float(array_size[0]), size[1] / float(array_size[1])]

    scale_expmin = [scale[0], scale[1]]
    scale_expmin[axis] /= expand_min

    scale_expmax = [scale[0], scale[1]]
    scale_expmax[axis] /= expand_max

    distortion_expmin = np.log(scale_expmin[1] / scale_expmin[0])
    distortion_expmax = np.log(scale_expmax[1] / scale_expmax[0])

    if abs(distortion_expmin) <= abs(distortion_expmax):
        expand = expand_min
        distortion = abs(distortion_expmin)
    else:
        expand = expand_max
        distortion = abs(distortion_expmax)

    if distortion_expmin * distortion_expmax < 0:
        expand = scale[axis] / scale[1 - axis]
        distortion = 0.0

    quality = np.exp(-distortion)

    unexpanded_size = [size[0], size[1]]
    unexpanded_size[axis] = int(unexpanded_size[axis] / expand + 0.5)

    return (unexpanded_size, quality, expand)


def _get_size_for_frame(
    array_size: list[float],
    frame: Any,
    axis: int,
    expand_min: float,
    expand_max: float,
) -> tuple[list[int], list[int], float, float]:
    """Fit an image array into a pixel frame, computing the expansion."""
    array_size_expmin = [array_size[0], array_size[1]]
    array_size_expmin[axis] *= expand_min

    scalings = [
        frame[0] / float(array_size_expmin[0]),
        frame[1] / float(array_size_expmin[1]),
    ]

    scale = min(scalings[0], scalings[1])

    optimal_size_float = [scale * array_size_expmin[0], scale * array_size_expmin[1]]

    optimal_size = [
        min(int(optimal_size_float[0] + 0.5), frame[0]),
        min(int(optimal_size_float[1] + 0.5), frame[1]),
    ]

    quality = optimal_size[0] * optimal_size[1] / float(frame[0] * frame[1])

    unexpanded_size_float = [scale * array_size[0], scale * array_size[1]]
    unexpanded_size = [optimal_size[0], optimal_size[1]]
    unexpanded_size[axis] = int(unexpanded_size_float[axis] + 0.5)

    expanded_size = [optimal_size[0], optimal_size[1]]
    expanded_length = unexpanded_size_float[axis] * expand_max
    expanded_size[axis] = min(int(expanded_length + 0.5), frame[axis])

    expand = expanded_size[axis] / scale / float(array_size[axis])

    return (unexpanded_size, expanded_size, quality, expand)


def resize_image(image: Any, new_size: tuple[int, int]) -> Any:
    """Resize a PIL image or a list of three PIL images.

    Parameters:
        image: A single PIL image or a list/tuple of three images.
        new_size: ``(width, height)`` of the output.

    Returns:
        The resized image(s).
    """
    if image.size == new_size:
        return image

    if isinstance(image, (list, tuple)):
        result: Any = []
        for i in image:
            result.append(_resize_one_image(i, new_size))
    else:
        result = _resize_one_image(image, new_size)

    return result


def _resize_one_image(image: Any, new_size: tuple[int, int]) -> Any:
    """Resize a single PIL image. Upscales with NEAREST, downscales with LANCZOS."""
    if new_size[0] > image.size[0] or new_size[1] > image.size[1]:
        image = image.resize(
            (max(new_size[0], image.size[0]), max(new_size[1], image.size[1])),
            Image.Resampling.NEAREST,
        )

    if new_size[0] < image.size[0] or new_size[1] < image.size[1]:
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    return image


def wrap_image(
    image: Any,
    wrapped_size: Any,
    sections: int,
    wrap_axis: int,
    gap_size: int,
    gap_color: Any,
) -> Any:
    """Wrap a PIL image into ``sections`` sub-images separated by gaps.

    Parameters:
        image: A PIL image.
        wrapped_size: ``(width, height)`` of the final wrapped image.
        sections: Number of sections to wrap.
        wrap_axis: 0 for horizontal wrapping; 1 for vertical.
        gap_size: Width of gap in pixels between sections.
        gap_color: Gap color, either an X11 name or an ``(R, G, B)`` triple.

    Returns:
        A new PIL image of the requested size.
    """
    if gap_size > 0:
        if isinstance(gap_color, str):
            gap_color = list(ColorNames.lookup(gap_color))
    else:
        gap_color = [0, 0, 0]

    array = pil_to_array(image, rescale=False)
    array = np.atleast_3d(array)
    two_bytes = array.dtype.itemsize == 2

    if (
        array.shape[2] == 1
        and gap_size > 0
        and (gap_color[0] != gap_color[1] or gap_color[0] != gap_color[2])
    ):
        buffer = np.empty((wrapped_size[1], wrapped_size[0], 3), dtype=array.dtype)
    else:
        buffer = np.empty(
            (wrapped_size[1], wrapped_size[0], array.shape[2]), dtype=array.dtype
        )

    if two_bytes:
        gap_color[0] = int(gap_color[0] / 255.0 * 65535.9999)
        gap_color[1] = int(gap_color[1] / 255.0 * 65535.9999)
        gap_color[2] = int(gap_color[2] / 255.0 * 65535.9999)

    if buffer.shape[2] == 1:
        buffer[:, :, 0] = gap_color[0]
    else:
        buffer[:, :, 0] = gap_color[0]
        buffer[:, :, 1] = gap_color[1]
        buffer[:, :, 2] = gap_color[2]

    if wrap_axis == 0:
        di = wrapped_size[0]
        dj = (wrapped_size[1] + gap_size) // sections

        dl = dj - gap_size

        float_s0 = 0.5
        float_ds = (image.size[0] - wrapped_size[0]) / (sections - 1.0)

        j0 = int((wrapped_size[1] - dj * sections - gap_size) / 2.0 + 0.5)
        for _k in range(sections):
            s0 = int(float_s0)
            s1 = s0 + di
            j1 = j0 + dl

            buffer[j0:j1, :] = array[:, s0:s1]

            float_s0 += float_ds
            j0 += dj

    else:
        di = (wrapped_size[0] + gap_size) // sections
        dj = wrapped_size[1]

        ds = di - gap_size

        float_l0 = 0.5
        float_dl = (image.size[1] - wrapped_size[1]) / (sections - 1.0)

        i0 = int((wrapped_size[0] - di * sections - gap_size) / 2.0 + 0.5)
        for _k in range(sections):
            l0 = int(float_l0)
            l1 = l0 + dj
            i1 = i0 + ds

            buffer[:, i0:i1] = array[l0:l1, :]

            float_l0 += float_dl
            i0 += di

    return array_to_pil(buffer, two_bytes, rescale=False)


def pad_image(image: Any, frame: Any, pad_color: Any) -> Any:
    """Pad a PIL image to fill a target frame size.

    Parameters:
        image: A PIL image.
        frame: ``(width, height)`` target frame size, or ``None`` to
            skip padding.
        pad_color: Gap fill color (X11 name or ``(R, G, B)`` triple).

    Returns:
        A padded PIL image of the requested size, or the original if no
        padding is needed.
    """
    if frame is None:
        return image

    if image.width >= frame[0] and image.height >= frame[1]:
        return image

    if isinstance(pad_color, str):
        pad_color = list(ColorNames.lookup(pad_color))

    array = pil_to_array(image, rescale=False)
    array = np.atleast_3d(array)
    two_bytes = array.dtype.itemsize == 2

    width = max(image.width, frame[0])
    height = max(image.height, frame[1])

    if array.shape[2] == 1 and (
        pad_color[0] != pad_color[1] or pad_color[0] != pad_color[2]
    ):
        buffer = np.empty((height, width, 1), dtype=array.dtype)
    else:
        buffer = np.empty((height, width, array.shape[2]), dtype=array.dtype)

    if two_bytes:
        pad_color[0] = int(pad_color[0] / 255.0 * 65535.9999)
        pad_color[1] = int(pad_color[1] / 255.0 * 65535.9999)
        pad_color[2] = int(pad_color[2] / 255.0 * 65535.9999)

    if buffer.shape[2] == 1:
        buffer[:, :, 0] = pad_color[0]
    else:
        buffer[:, :, 0] = pad_color[0]
        buffer[:, :, 1] = pad_color[1]
        buffer[:, :, 2] = pad_color[2]

    l0 = (height - image.height) // 2
    s0 = (width - image.width) // 2

    l1 = l0 + image.height
    s1 = s0 + image.width

    buffer[l0:l1, s0:s1] = array[:, :]

    return array_to_pil(buffer, two_bytes, rescale=False)


__all__ = [
    '_get_size_for_frame',
    '_get_size_for_size',
    '_resize_one_image',
    'circle_mask',
    'crop_array',
    'get_size',
    'pad_image',
    'resize_image',
    'rotate_array_rgb',
    'slice_array',
    'wrap_image',
]
