##########################################################################################
# pipeline/sizing.py
##########################################################################################

import numpy as np
from PIL import Image


def get_size(array_rgb_shape, *, size=None, scale=(100., 100.), frame=None, wrap=False,
             wrap_ratio=None, overlaps=(0., 0.), gap_size=1, frame_max=None, **kwargs):
    """The output image size (width, height) and wrap properties based on the shape of the
    array.

    Parameters:
        array_rgb_shape (tuple[int, ...]): The 2-D or 3-D shape of the source numpy array.
            The index order is (lines, samples) or (lines, samples, channels).
        size (int or tuple[int, int], optional): A tuple of dimensions (width, height).
            Use a single value for a square image, or None to preserve the given array
            size.
        scale (float or tuple[float, float], optional): Scale factor as a percentage to
            apply. A scalar applies to both axes; pass two values (width, height) to scale
            the width and height independently. Note that the resulting size may still be
            constrained by `size`, `frame`, or `frame_max`.
        frame (int or tuple[int, int], optional): The firm outer limit on the (width,
            height) size of the output image. If the result of the above parameters
            exceeds the frame in either dimension, the image is scaled down proportionally
            to fit inside the frame. A single value implies a square frame; a tuple can be
            used to specify each dimension; None implies no frame constraint.
        wrap (bool, optional): True to consider wrapping the image to reduce distortion.
        wrap_ratio (float, optional): Wrap the sections of the image if the width/height
            or height/width ratio exceeds this value.
        overlaps (tuple[float, float], optional): (min, max) percentages of allowed
            overlap between the end of one wrapped section and the beginning of the next.
            For example, (5,10) means that between 5% and 10% of the last pixels in one
            section may overlap the first pixels of the next section.
        gap_size (int, optional): The size of the gap between wrap sections in pixels.
        frame_max (float, optional): Maximum percentage scale applied when `frame` is
            set and `wrap` is False.
        **kwargs: Additional input options, ignored here.

    Returns:
        tuple: `(unwrapped_size, wrapped_size, sections, wrap_axis)`:

        * `unwrapped_size` (tuple[int, int]): The (width, height) size of the PIL image
          before wrapping but after any re-scaling.
        * `wrapped_size` (tuple[int, int]): The (width, height) size of the PIL image
          after wrapping.
        * `sections` (int): The number of sections to wrap.
        * `wrap_axis` (int): 0 to wrap horizontally, 1 to wrap vertically.
    """

    # Normalize inputs
    if size is not None and not isinstance(size, (list, tuple)):
        size = (size, size)

    if scale is not None and not isinstance(scale, (list, tuple)):
        scale = (scale, scale)

    if frame is not None and not isinstance(frame, (list, tuple)):
        frame = (frame, frame)

    # Apply scale factor to shape
    array_size = [array_rgb_shape[1], array_rgb_shape[0]]   # [width, height]
    if scale is not None:
        array_size[0] *= scale[0]/100.
        array_size[1] *= scale[1]/100.

    # Determine the output size based on size or frame
    if size is not None:
        (unwrapped_size, quality,
         expand) = _get_size_for_size(array_size, size, 0, 1., 1.)
    elif frame is not None:
        (unwrapped_size, expanded_size, quality,
         expand) = _get_size_for_frame(array_size, frame, 0, 1., 1.)
        if frame_max and not wrap:
            wfactor = unwrapped_size[0] / array_size[0]
            hfactor = unwrapped_size[1] / array_size[1]
            ratio = frame_max/100. / max(wfactor, hfactor)
            if ratio < 1.:
                unwrapped_size[0] = int(unwrapped_size[0] * ratio)
                unwrapped_size[1] = int(unwrapped_size[1] * ratio)
    else:
        unwrapped_size = [int(array_size[0] + 0.5), int(array_size[1] + 0.5)]

        # Handle a limit on the wrap ratio
        if wrap_ratio:
            if unwrapped_size[0] > wrap_ratio * unwrapped_size[1]:
                for k in range(2, 101):
                    expand = 1. + overlaps[0]/100. * (k-1.)/k
                    wrapped_size = [int(unwrapped_size[0]/k * expand + 0.5),
                                    unwrapped_size[1] * k + gap_size * (k-1)]
                    if wrapped_size[0] <= wrap_ratio * wrapped_size[1]:
                        return (unwrapped_size, wrapped_size, k, 0)

            if unwrapped_size[1] > wrap_ratio * unwrapped_size[0]:
                for k in range(2, 101):
                    expand = 1. + overlaps[0]/100. * (k-1.)/k
                    wrapped_size = [unwrapped_size[0] * k + gap_size * (k-1),
                                    int(unwrapped_size[1]/k * expand + 0.5)]
                    if wrapped_size[1] <= wrap_ratio * wrapped_size[0]:
                        return (unwrapped_size, wrapped_size, k, 1)

    # Without the wrapping option, we're done
    if not wrap or ((size is None) and (frame is None)):
        return (unwrapped_size, unwrapped_size, 1, 0)

    best_quality = quality
    best_sections = 1
    best_axis = 0
    best_unwrapped = unwrapped_size
    best_wrapped = unwrapped_size
    best_overlap = 0.

    quality_1x1 = quality

    # Try horizontal, then vertical wrapping
    for axis in (0, 1):

        # Increment number of wrap sections until quality starts to drop
        for k in range(2, 101):

            tweak = (k-1.) / k
            expand_min = 1. + overlaps[0]/100. * tweak
            expand_max = 1. + overlaps[1]/100. * tweak

            # Adjust size and frame for axis, sections and gap
            if size is not None:

                # Calculate the number of pixels (w,h) available for the image if
                # we wrap it into k sections.
                temp_size = [size[0], size[1]]
                temp_size[axis] *= k
                temp_size[1-axis] -= (k-1) * gap_size
                temp_size[1-axis] //= k

                # Get the image size if it is forced to fit into this area
                (unwrapped_size, quality,
                 expand) = _get_size_for_size(array_size, temp_size, axis,
                                              expand_min, expand_max)
                test_overlap = (expand - 1.) / tweak * 100.

                wrapped_size = size

            else:
                temp_frame = [frame[0], frame[1]]
                temp_frame[axis] *= k
                temp_frame[1-axis] -= (k-1) * gap_size
                temp_frame[1-axis] //= k

                (unwrapped_size, expanded_size, quality,
                 expand) = _get_size_for_frame(array_size, temp_frame, axis,
                                               expand_min, expand_max)
                test_overlap = (expand - 1.) / tweak * 100.

                wrapped_size = [expanded_size[0], expanded_size[1]]
                wrapped_size[axis] = (wrapped_size[axis] + (k-1)) // k
                wrapped_size[1-axis] *= k
                wrapped_size[1-axis] += (k-1) * gap_size
                wrapped_size[0] = min(wrapped_size[0], frame[0])
                wrapped_size[1] = min(wrapped_size[1], frame[1])

            if quality < best_quality:
                break

            # If the improvement from 1x1 to 1x2 is marginal, stick with 1x1
            if frame is not None and k == 2 and quality < quality_1x1 * 1.1:
                continue

            best_quality = quality
            best_sections = k
            best_axis = axis
            best_unwrapped = unwrapped_size
            best_wrapped = wrapped_size
            best_overlap = test_overlap

    quality = best_quality
    sections = best_sections
    axis = best_axis
    unwrapped_size = best_unwrapped
    wrapped_size = best_wrapped
    test_overlap = best_overlap

    return (unwrapped_size, wrapped_size, sections, axis)


def _get_size_for_size(array_size, size, axis, expand_min, expand_max):
    """Calculate the size and quality when attempting to fit an image array into a pixel
    area.

    Parameters:
        array_size (tuple[int, int]): (width, height) of the image array.
        size (tuple[int, int]): (width, height) of the available pixels.
        axis (int): The axis being wrapped: 0 for width; 1 for height.
        expand_min (float): Minimum allowed expansion factor on the specified axis.
        expand_max (float): Maximum allowed expansion factor on the specified axis.

    Returns:
        tuple: `(unexpanded_size, quality, expand)`, where:

        * `unexpanded_size` (tuple[int, int]): The exact (width, height) size of the image
          to insert into the pixel area before expansion.
        * `quality` (float): Quality metric, which is maximized when the image has the
          least distortion.
        * `expand` (float): Expansion factor to use along the specified axis.
    """

    # Derive the (w,h) scale factors required to fit the image array into the
    # available size, neglecting expansion along the axis
    scale = [size[0] / float(array_size[0]),
             size[1] / float(array_size[1])]

    # Adjust the along-axis scale factor for minimum and maximum expansion
    scale_expmin = [scale[0], scale[1]]
    scale_expmin[axis] /= expand_min

    scale_expmax = [scale[0], scale[1]]
    scale_expmax[axis] /= expand_max

    # Derive distortion factors for minimum and maximum expansion
    # We take the log, so distortion == 0 for a 1:1 ratio of scale factors
    distortion_expmin = np.log(scale_expmin[1] / scale_expmin[0])
    distortion_expmax = np.log(scale_expmax[1] / scale_expmax[0])

    # Select the expansion factor that produces distortion closer to zero
    if abs(distortion_expmin) <= abs(distortion_expmax):
        expand = expand_min
        distortion = abs(distortion_expmin)
    else:
        expand = expand_max
        distortion = abs(distortion_expmax)

    # Choose an intermediate expansion factor if it can give us zero distortion
    if distortion_expmin * distortion_expmax < 0:
        expand = scale[axis] / scale[1-axis]
        distortion = 0.

    # Quality = 1 for zero distortion, smaller for larger distortion ratios
    quality = np.exp(-distortion)

    # Determine the size of the array to wrap
    unexpanded_size = [size[0], size[1]]
    unexpanded_size[axis] = int(unexpanded_size[axis]/expand + 0.5)

    return (unexpanded_size, quality, expand)


def _get_size_for_frame(array_size, frame, axis, expand_min, expand_max):
    """Calculate the size and quality when attempting to fit an image array into a given
    pixel frame.

    Parameters:
        array_size (tuple[int, int]): (width, height) of the image array.
        frame (tuple[int, int]): (width, height) of the available frame.
        axis (int): The axis being wrapped: 0 for width; 1 for height.
        expand_min (float): Minimum allowed expansion factor on the specified axis.
        expand_max (float): Maximum allowed expansion factor on the specified axis.

    Returns:
        tuple: `(unexpanded_size, expanded_size, quality, expand)`, where:

        * ``unexpanded_size`` (tuple[int, int]): The exact (width, height) size of the
          image to insert into the pixel frame before expansion.
        * ``expanded_size`` (tuple[int, int]): The exact (width, height)` size of the
          image after expansion.
        * `quality` (float): Quality metric, which is maximized when the image has the
          least distortion.
        * `expand` (float): Expansion factor to use along the specified axis.
    """

    # Determine optimal image size inside the frame, assuming minimal expansion
    array_size_expmin = [array_size[0], array_size[1]]
    array_size_expmin[axis] *= expand_min

    scalings = [frame[0] / float(array_size_expmin[0]),
                frame[1] / float(array_size_expmin[1])]

    scale = min(scalings[0], scalings[1])

    optimal_size_float = [scale * array_size_expmin[0],
                          scale * array_size_expmin[1]]

    optimal_size = [min(int(optimal_size_float[0] + 0.5), frame[0]),
                    min(int(optimal_size_float[1] + 0.5), frame[1])]

    # Quality is the fractional filling factor of the image when inserted into
    # the frame
    quality = optimal_size[0] * optimal_size[1] / float(frame[0] * frame[1])

    # Determine size of image before expansion
    unexpanded_size_float = [scale * array_size[0], scale * array_size[1]]
    unexpanded_size = [optimal_size[0], optimal_size[1]]
    unexpanded_size[axis] = int(unexpanded_size_float[axis] + 0.5)

    # Increase the expansion factor for better filling, if possible
    expanded_size = [optimal_size[0], optimal_size[1]]
    expanded_length = unexpanded_size_float[axis] * expand_max
    expanded_size[axis] = min(int(expanded_length + 0.5), frame[axis])

    expand = expanded_size[axis]/scale / float(array_size[axis])

    return (unexpanded_size, expanded_size, quality, expand)


def resize_pil_image(image, new_size):
    """Resize a PIL image or a list of three PIL images.

    Parameters:
        image (PIL.Image or list of three): A single PIL image or a list of three for
            16-bit RGB.
        new_size (tuple[int, int]): New (width, height) of the output.

    Returns:
        PIL.Image or list of three: The resized image or list of images.
    """

    # If the size is unchanged, just return. A list holds three images that
    # share one size, so check the first.
    current_size = image[0].size if isinstance(image, (list, tuple)) else image.size
    if current_size == new_size:
        return image

    # Handle one or three PIL image objects
    if isinstance(image, (list, tuple)):
        result = [_resize_one_image(i, new_size) for i in image]
    else:
        result = _resize_one_image(image, new_size)

    return result


def _resize_one_image(image, new_size):
    """Resize a single PIL image. Upscales with NEAREST, downscales with LANCZOS.

    Parameters:
        image (PIL.Image): A PIL image.
        new_size (tuple[int, int]): New (width, height) of the output.

    Returns:
        (PIL.Image): Resized image.
    """

    # Scale up if necessary using NEAREST
    if new_size[0] > image.size[0] or new_size[1] > image.size[1]:
        image = image.resize((max(new_size[0], image.size[0]),
                              max(new_size[1], image.size[1])), Image.NEAREST)

    # Scale down if necessary using ANTIALIAS (now LANCZOS)
    if new_size[0] < image.size[0] or new_size[1] < image.size[1]:
        image = image.resize(new_size, Image.LANCZOS)

    return image


__all__ = ['get_size', 'resize_pil_image']

##########################################################################################
