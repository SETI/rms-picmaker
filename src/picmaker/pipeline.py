"""Top-level orchestration: walk directories, process one image, drive a movie.

:func:`process_images` and :func:`images_to_pics` are the CLI's main
entry points; everything else in this module is plumbing.
"""


import logging
import os
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
from picmaker.options import PicmakerOptions
from picmaker.pil_utils import array_to_pil, write_pil

logger = logging.getLogger(__name__)


def find_common_path(directories: list[str]) -> str:
    """Return the longest directory prefix shared by every directory in the list.

    Uses :func:`os.path.commonpath` so the result honors the current
    platform's separator (``/`` on POSIX, ``\\`` on Windows).

    Parameters:
        directories: A list of directory path strings.

    Returns:
        The longest common directory path. An empty string if the list
        is empty or the directories share no common ancestor (e.g. paths
        on different drives on Windows, or a mix of absolute and
        relative paths).
    """
    if len(directories) == 0:
        return ''
    if len(directories) == 1:
        return directories[0]

    try:
        result = os.path.commonpath(directories)
    except ValueError:
        # commonpath raises ValueError when the inputs share no common
        # prefix (e.g. mix of absolute / relative, different Windows
        # drives). Preserve the legacy "no common ancestor" return.
        return ''

    # Treat root-only common paths ('/' on POSIX, '\\' on Windows, or a
    # bare drive root like 'C:\\') as "no useful prefix" so the legacy
    # behavior is preserved (the old implementation rejected commons
    # that had no slash at position >= 1). os.path.splitdrive separates
    # the drive anchor from the rest so we can detect drive-only roots
    # on Windows in addition to the platform separator.
    _drive, rest = os.path.splitdrive(result)
    if not rest or rest == os.sep:
        return ''
    return result


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
        # Validate input shape before indexing option_dicts[0]. An empty
        # option_dicts in movie mode is a programming error from the
        # caller; raising up-front is clearer than the IndexError that
        # the next line would otherwise produce.
        if not option_dicts:
            raise ValueError('movie mode requires at least one option_dict')
        # Use ValueError (not `assert`) so the check survives `python -O`,
        # which strips assertions and would otherwise let an inconsistent
        # `proceed` slip through movie mode silently.
        if any(
            d['proceed'] != option_dicts[0]['proceed'] for d in option_dicts
        ):
            raise ValueError(
                'movie mode requires all option_dicts to share the same '
                "'proceed' value"
            )

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
        # `results` is declared outside the per-filename loop so the
        # reuse-detection check below can fall through to the previous
        # filename's output when obj/pointer match.
        results = None
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
    filter_name: str = 'NONE',
    zebra: bool = False,
    reuse: Any = None,
) -> tuple[Any, Any, Any]:
    """Convert one or more image files to picture files.

    See ``picmaker --help`` for the meaning of each keyword argument.
    The CLI's ``--filter`` flag binds to the ``filter_name`` keyword on
    this function (the rename in 2026-05 dropped the legacy
    builtin-shadowing ``filter`` kwarg).

    Parameters:
        filenames: List of image file names to convert.
        directory: Output directory. ``None`` writes next to the input.
        verbose: Print each input filename as it is processed.

    Returns:
        ``(low, high, reuse)`` — the lower / upper limits of the
        stretch and the reuse tuple if the caller wants to call again
        without re-reading the file.
    """
    # Single source of truth for mutex / value-validity checks: build a
    # PicmakerOptions and let its `validate()` method raise on any
    # cross-field conflict. The CLI does this earlier via
    # _normalize_and_validate; library callers get the same checks here.
    PicmakerOptions(
        replace=replace, proceed=proceed, extension=extension,
        suffix=suffix, strip=strip, quality=quality, twobytes=twobytes,
        bands=bands, lines=lines, samples=samples, obj=obj, pointer=pointer,
        size=size, scale=scale, crop=crop, frame=frame, pad=pad,
        pad_color=pad_color, frame_max=frame_max, wrap=wrap,
        wrap_ratio=wrap_ratio, overlap=overlap, gap_size=gap_size,
        gap_color=gap_color, hst=hst, valid=valid, limits=limits,
        percentiles=percentiles, trim=trim, trim_zeros=trim_zeros,
        footprint=footprint, histogram=histogram, colormap=colormap,
        below_color=below_color, above_color=above_color,
        invalid_color=invalid_color, gamma=gamma, tint=tint,
        display_upward=display_upward, display_downward=display_downward,
        rotate=rotate, filter_name=filter_name, zebra=zebra,
    ).validate()

    if strip is None:
        strip = []
    if pointer is None:
        pointer = ['IMAGE']

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

                        # Local PDS3-label "FILTER_NAME" value; do NOT
                        # shadow the function parameter ``filter_name``
                        # (the PIL filter name to apply downstream).
                        if 'FILTER_NAME' in labeldict:
                            pds_filter_name = labeldict['FILTER_NAME']
                        else:
                            pds_filter_name = None

                        filter_info = (inst_host, inst_id, pds_filter_name)

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

            image = filter_image(image, filter_name)

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
                # `logger.exception` logs the type, message, AND the full
                # traceback in one call through the configured handler, so
                # output ordering stays deterministic under `pytest -n auto`
                # and `caplog` captures it cleanly.
                logger.exception('%s', infile)
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
