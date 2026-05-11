"""Top-level orchestration: walk directories, process one image, drive a movie.

``process_images`` and ``images_to_pics`` are the CLI's main entry
points; everything else is plumbing.

The ``filter`` keyword is preserved as ``filter`` (not renamed) for
backward compatibility — the per-file ruff ignore for ``A002`` lives in
``pyproject.toml``.
"""


import logging
import os
import sys
import traceback
from typing import Any

import numpy as np
import pdsparser

from picmaker._filters import filter_image
from picmaker.color import tinted_colormap
from picmaker.enhance import (
    apply_colormap,
    apply_gamma,
    fill_zebra_stripes,
    get_limits,
)
from picmaker.geometry import (
    get_size,
    pad_image,
    resize_image,
    rotate_array_rgb,
    slice_array,
    wrap_image,
)
from picmaker.io import get_outfile, read_image_array
from picmaker.pil_utils import array_to_pil, write_pil

logger = logging.getLogger(__name__)


def find_common_path(directories: list[str]) -> str:
    """Return the longest path prefix shared by every directory in the list.

    Parameters:
        directories: A list of directory path strings.

    Returns:
        The longest common path prefix, trimmed at the last ``/``. An
        empty string if the directories share no useful prefix or the
        list is empty.
    """

    def longest_match(str1: str, str2: str) -> str:
        kmax = min(len(str1), len(str2))
        for k in range(kmax):
            if str1[k] != str2[k]:
                return str1[:k]
        return str1[:kmax]

    if len(directories) == 0:
        return ''
    if len(directories) == 1:
        return directories[0]

    longest = longest_match(directories[0], directories[1])
    for d in directories[2:]:
        longest = longest_match(longest, d)

    last_slash = longest.rfind('/')
    if last_slash < 1:
        return ''

    return longest[:last_slash]


def process_images(
    filenames: list[str],
    directory: str | None,
    movie: bool,
    option_dicts: list[dict[str, Any]],
    verbose: bool = False,
) -> None:
    """Process a list of images using a list of option dictionaries.

    In movie mode, all frames are converted with the same stretch
    derived from the median of the per-frame limits.

    Parameters:
        filenames: Files to process.
        directory: Output directory (created if missing). ``None`` to
            write next to the input.
        movie: Run as a movie (single shared stretch across frames).
        option_dicts: A list of ``option_dict`` dicts (one per
            ``--versions`` line).
        verbose: Print each file as it is processed.
    """
    if directory is not None and not os.path.exists(directory):
        os.makedirs(directory)

    results: Any
    if movie:
        assert all(d['proceed'] == option_dicts[0]['proceed'] for d in option_dicts)

        results = images_to_pics(
            filenames, directory, reuse=None, verbose=verbose, **option_dicts[0]
        )
        if results[:2] == (None, None):
            if option_dicts[0]['proceed']:
                return
            raise OSError('unable to process movie')

        movie_dict = option_dicts[0].copy()
        movie_dict['limits'] = results[:2]

        _ = images_to_pics(
            filenames, directory, reuse=None, verbose=verbose, **movie_dict
        )

    else:
        results = None  # persists across filenames, matching legacy behavior
        for filename in filenames:
            prev_obj: Any = -1
            prev_pointer: Any = None
            for k, option_dict in enumerate(option_dicts):
                if (
                    prev_obj == option_dict['obj']
                    and prev_pointer == option_dict['pointer']
                ):
                    reuse = results[-1]
                else:
                    reuse = None
                    prev_obj = option_dict['obj']
                    prev_pointer = option_dict['pointer']

                results = images_to_pics(
                    [filename],
                    directory,
                    reuse=reuse,
                    verbose=(verbose and k == 0),
                    **option_dict,
                )


def images_to_pics(
    filenames: list[str],
    directory: str | None = None,
    verbose: bool = False,
    *,
    replace: str = 'all',
    proceed: bool = False,
    extension: str | None = 'jpg',
    suffix: str = '',
    strip: Any = None,
    quality: int = 75,
    twobytes: bool = False,
    bands: Any = None,
    lines: Any = None,
    samples: Any = None,
    obj: Any = None,
    pointer: Any = None,
    size: Any = None,
    scale: Any = (100.0, 100.0),
    crop: Any = None,
    frame: Any = None,
    pad: bool = False,
    pad_color: Any = 'black',
    frame_max: int | None = None,
    wrap: bool = False,
    wrap_ratio: float | None = None,
    overlap: tuple[float, float] = (0.0, 0.0),
    gap_size: int = 1,
    gap_color: Any = 'white',
    hst: bool = False,
    valid: Any = None,
    limits: Any = None,
    percentiles: Any = None,
    trim: int = 0,
    trim_zeros: bool = False,
    footprint: int = 0,
    histogram: bool = False,
    colormap: Any = None,
    below_color: Any = None,
    above_color: Any = None,
    invalid_color: Any = None,
    gamma: float = 1.0,
    tint: bool = False,
    display_upward: bool = False,
    display_downward: bool = False,
    rotate: Any = None,
    filter: str = 'NONE',
    zebra: bool = False,
    reuse: Any = None,
) -> tuple[Any, Any, Any]:
    """Convert one or more image files to picture files.

    See module-level docs and CLI ``--help`` for the meaning of each
    keyword argument. ``filter`` shadows the builtin and is preserved
    for backward compatibility.

    Parameters:
        filenames: List of image file names to convert.
        directory: Output directory. ``None`` writes next to the input.
        verbose: Print each input filename as it is processed.

    Returns:
        ``(low, high, reuse)`` — the lower / upper limits of the
        stretch and the reuse tuple if the caller wants to call again
        without re-reading the file.
    """
    if strip is None:
        strip = []
    if pointer is None:
        pointer = ['IMAGE']

    if hst and bands is not None:
        raise ValueError('hst and bands options are incompatible')

    if frame is not None and size is not None:
        raise ValueError('frame and size options are incompatible')

    if frame is not None and wrap_ratio:
        raise ValueError('frame and wrap_ratio options are incompatible')

    if bands is None:
        bands = (0, 1)

    if extension is None:
        if twobytes:
            extension = 'tiff'
        else:
            extension = 'jpg'

    min_limits: list[Any] = []
    max_limits: list[Any] = []
    array3d: Any = None
    default_is_up = False
    filter_info: Any = None
    infile: str = ''

    for infile in filenames:
        if verbose:
            logger.info('%s', infile)

        try:
            outfile = get_outfile(infile, directory, strip, suffix, extension, replace)
            if outfile == '':
                continue

            if len(filenames) == 1 and reuse is not None:
                (array3d, default_is_up, filter_info, infile) = reuse

            else:
                filter_info = None
                upperfile = infile.upper()
                labelfile: Any = ''
                imagefile: Any = infile
                if upperfile.endswith('.LBL'):
                    labelfile = infile
                    labeldict = pdsparser.PdsLabel(infile).as_dict()

                    filter_info = None

                    if 'INSTRUMENT_HOST_ID' in labeldict:
                        inst_host = labeldict['INSTRUMENT_HOST_ID']
                    elif 'SPACECRAFT_ID' in labeldict:
                        inst_host = labeldict['SPACECRAFT_ID']
                    elif 'SPACECRAFT_NAME' in labeldict:
                        inst_host = labeldict['SPACECRAFT_NAME']
                    else:
                        inst_host = None

                    if inst_host is not None:
                        if 'INSTRUMENT_ID' in labeldict:
                            inst_id = labeldict['INSTRUMENT_ID']
                            if 'DETECTOR_ID' in labeldict:
                                detector_id = labeldict['DETECTOR_ID']
                                if isinstance(detector_id, str):
                                    inst_id += '/' + detector_id
                        elif 'INSTRUMENT_NAME' in labeldict:
                            inst_id = labeldict['INSTRUMENT_NAME']
                        else:
                            inst_id = None

                        if 'FILTER_NAME' in labeldict:
                            filter_name = labeldict['FILTER_NAME']
                        else:
                            filter_name = None

                        filter_info = (inst_host, inst_id, filter_name)

                    if isinstance(pointer, str):
                        pointer = [pointer]

                    pds_obj: Any = None
                    for pname in pointer:
                        pname = pname.upper()

                        if not pname.startswith('^'):
                            pname = '^' + pname

                        if pname in labeldict:
                            pds_obj = labeldict[pname]
                            if isinstance(pds_obj, tuple):
                                pds_obj = pds_obj[0]
                            break

                    if pds_obj is None:
                        raise KeyError(
                            f'PDS pointer {pointer[0].upper()} not found'
                        )

                    if isinstance(pds_obj, str):
                        pds_obj = [pds_obj]

                    if obj is None:
                        max_obj = len(pds_obj) - 1
                        imagefile = [
                            os.path.join(os.path.split(infile)[0], p)
                            for p in pds_obj
                        ]
                    elif isinstance(obj, int):
                        max_obj = obj
                        imagefile = os.path.join(
                            os.path.split(infile)[0], pds_obj[obj]
                        )
                    else:
                        max_obj = max(obj)
                        imagefile = [
                            os.path.join(os.path.split(infile)[0], pds_obj[o])
                            for o in obj
                        ]

                    if max_obj >= len(pds_obj):
                        raise IndexError(
                            f'index {max_obj + 1} for PDS pointer {pname[1:]} '
                            'out of range'
                        )

                (array3d, default_is_up, filter_info2) = read_image_array(
                    imagefile, labelfile, obj, hst
                )
                filter_info = filter_info or filter_info2

            if display_upward:
                this_display_upward = True
            elif display_downward:
                this_display_upward = False
            else:
                this_display_upward = default_is_up

            is_int = array3d.dtype.kind in ('i', 'u')

            if tint:
                colormap2 = tinted_colormap(filter_info)
                if colormap2 is not None:
                    colormap = colormap2

            if (
                hst
                and filter_info[0] == 'HST'
                and (filter_info[1] in ('ACS/WFC', 'WFPC2'))
            ):
                if default_is_up:
                    array3d = array3d[:, ::-1, :]

                this_display_upward = False

                arraysRGB: list[Any] = []
                for b in range(array3d.shape[0]):
                    (array2d, invalid_mask) = slice_array(
                        array3d, samples, lines, (b, b + 1), valid, crop
                    )

                    if zebra:
                        array2d = fill_zebra_stripes(array2d)

                    these_limits = get_limits(
                        array2d,
                        invalid_mask,
                        limits,
                        percentiles,
                        assume_int=is_int,
                        trim=trim,
                        trim_zeros=trim_zeros,
                        footprint=footprint,
                    )

                    arrayRGB = apply_colormap(
                        array2d,
                        these_limits,
                        histogram,
                        colormap,
                        invalid_mask,
                        below_color,
                        above_color,
                        invalid_color,
                    )

                    arraysRGB.append(arrayRGB)

                if filter_info[1] == 'WFPC2':
                    quadsRGB = np.zeros((4,) + arraysRGB[0].shape)

                    for b in range(array3d.shape[0]):
                        if isinstance(imagefile, str):
                            quadsRGB[b] = np.rot90(arraysRGB[b], b)
                        else:
                            testfile = imagefile[b].upper()
                            if 'PC1' in testfile:
                                quadsRGB[0] = arraysRGB[b]
                            elif 'WF2' in testfile:
                                quadsRGB[1] = np.rot90(arraysRGB[b], 1)
                            elif 'WF3' in testfile:
                                quadsRGB[2] = np.rot90(arraysRGB[b], 2)
                            elif 'WF4' in testfile:
                                quadsRGB[3] = np.rot90(arraysRGB[b], 3)
                            else:
                                quadsRGB[b] = np.rot90(arraysRGB[b], b)

                    (_, dl, ds, db) = quadsRGB.shape
                    arrayRGB = np.empty((2 * dl, 2 * ds, db))
                    arrayRGB[:dl, -ds:] = quadsRGB[0]
                    arrayRGB[:dl, :ds] = quadsRGB[1]
                    arrayRGB[-dl:, :ds] = quadsRGB[2]
                    arrayRGB[-dl:, -ds:] = quadsRGB[3]

                else:
                    if len(arraysRGB) > 1:
                        panelsRGB = np.zeros((2,) + arraysRGB[0].shape)

                        for b in range(2):
                            if isinstance(imagefile, str):
                                panelsRGB[1 - b] = arraysRGB[b]
                            else:
                                testfile = imagefile[b].upper()
                                if 'WFC1' in testfile:
                                    panelsRGB[0] = arraysRGB[b]
                                elif 'WFC2' in testfile:
                                    panelsRGB[1] = arraysRGB[b]
                                else:
                                    panelsRGB[b] = arraysRGB[b]

                        (dl, ds, db) = arraysRGB[0].shape
                        arrayRGB = np.zeros((2 * dl, ds, db))

                        arrayRGB[:dl] = panelsRGB[0]
                        arrayRGB[-dl:] = panelsRGB[1]

                    else:
                        arrayRGB = arraysRGB[0]

            else:
                (array2d, invalid_mask) = slice_array(
                    array3d, samples, lines, bands, valid, crop
                )

                if zebra:
                    array2d = fill_zebra_stripes(array2d)

                these_limits = get_limits(
                    array2d,
                    invalid_mask,
                    limits,
                    percentiles,
                    assume_int=is_int,
                    trim=trim,
                    trim_zeros=trim_zeros,
                    footprint=footprint,
                )

                min_limits.append(these_limits[0])
                max_limits.append(these_limits[1])

                arrayRGB = apply_colormap(
                    array2d,
                    these_limits,
                    histogram,
                    colormap,
                    invalid_mask,
                    below_color,
                    above_color,
                    invalid_color,
                )

            arrayRGB = rotate_array_rgb(arrayRGB, this_display_upward, rotate)

            arrayRGB = apply_gamma(arrayRGB, gamma)

            (unwrapped_size, wrapped_size, sections, wrap_axis) = get_size(
                arrayRGB.shape,
                size,
                scale,
                frame,
                wrap,
                wrap_ratio,
                overlap,
                gap_size,
                frame_max,
            )

            image = array_to_pil(arrayRGB, twobytes)

            image = filter_image(image, filter)

            image = resize_image(image, unwrapped_size)

            if sections > 1:
                image = wrap_image(
                    image,
                    wrapped_size,
                    sections,
                    wrap_axis,
                    gap_size,
                    gap_color,
                )

            if pad:
                image = pad_image(image, frame, pad_color)

            write_pil(image, outfile, quality)

        except Exception:
            if proceed:
                (etype, value, tb) = sys.exc_info()
                traceback.print_tb(tb)
                etype_name = etype.__name__ if etype is not None else 'Exception'
                logger.error('%s **** %s: %s', infile, etype_name, value)
            else:
                raise

    if min_limits == []:
        return (None, None, None)

    if array3d is None:
        return (np.median(min_limits), np.median(max_limits), None)

    return (
        np.median(min_limits),
        np.median(max_limits),
        (array3d, default_is_up, filter_info, infile),
    )


__all__ = ['find_common_path', 'images_to_pics', 'process_images']
