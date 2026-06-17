"""Top-level orchestration: walk directories, process one image, drive a movie.

:func:`process_images` and :func:`images_to_pics` are the CLI's main
entry points; the module-private helper :func:`!_process_one_image`
handles one phase of the per-image
pipeline so that :func:`images_to_pics` reads as a flat loop.
"""


import logging
import os
from typing import Any, cast

import numpy as np
import pdsparser

from picmaker import instruments
from picmaker._filters import filter_image
from picmaker.color import tinted_colormap
from picmaker.enhance import (
    _band_to_rgb,
    apply_gamma,
)
from picmaker.geometry import (
    get_size,
    pad_image,
    resize_image,
    rotate_array_rgb,
    wrap_image,
)
from picmaker.io import get_outfile, read_image_array
from picmaker.options import READ_FILE_KWARGS, PicmakerOptions
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


def _pds3_resolve_pointer(
    infile: str,
    pointer: Any,
    obj: Any,
    *,
    pds3_label_method: str = 'fast',
) -> tuple[Any, tuple[Any, Any, Any] | None, pdsparser.PdsLabel]:
    """Parse a PDS3 ``.LBL`` and resolve its image-object pointer.

    The pointer name list is tried in order; the first one present in
    the label wins. When the pointer resolves to multiple objects, the
    ``obj`` argument selects which (an integer selects one, a sequence
    selects several, ``None`` selects all).

    Parameters:
        infile: Path to a PDS3 ``.LBL`` detached-label file.
        pointer: Pointer name (e.g. ``'IMAGE'``) or list of pointer
            names to try in order. A leading ``^`` is optional.
        obj: ``None`` (all objects), an ``int`` (one object), or a
            sequence of ``int`` (several objects).
        pds3_label_method: Forwarded to :class:`pdsparser.PdsLabel` as
            its ``method=`` argument (``'strict'``, ``'loose'``,
            ``'compound'``, or ``'fast'``).

    Returns:
        ``(imagefile, filter_info, label)`` — ``imagefile`` is either a
        single path (``obj`` was an int) or a list of paths;
        ``filter_info`` is the ``(host, instrument, filter)`` triple
        extracted from the label, or ``None`` when no instrument
        metadata is present; ``label`` is the parsed
        :class:`pdsparser.PdsLabel` object (to avoid re-parsing in the
        caller).

    Raises:
        KeyError: When none of the pointer names is present in the
            label.
        IndexError: When ``obj`` selects an index past the end of the
            resolved pointer list.
    """
    label = pdsparser.PdsLabel(infile, method=pds3_label_method)
    labeldict = label.as_dict()

    if 'INSTRUMENT_HOST_ID' in labeldict:
        inst_host = labeldict['INSTRUMENT_HOST_ID']
    elif 'SPACECRAFT_ID' in labeldict:
        inst_host = labeldict['SPACECRAFT_ID']
    elif 'SPACECRAFT_NAME' in labeldict:
        inst_host = labeldict['SPACECRAFT_NAME']
    else:
        inst_host = None

    filter_info: tuple[Any, Any, Any] | None = None
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

        pds_filter_name = labeldict.get('FILTER_NAME')
        filter_info = (inst_host, inst_id, pds_filter_name)

    if isinstance(pointer, str):
        pointer = [pointer]

    pds_obj: Any = None
    pname: str = ''
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
        raise KeyError(f'PDS pointer {pointer[0].upper()} not found')

    if isinstance(pds_obj, str):
        pds_obj = [pds_obj]

    # Validate the upper bound BEFORE indexing into ``pds_obj`` so the
    # informative IndexError (which names the pointer) fires instead of
    # Python's bare ``list index out of range``.
    if obj is None:
        max_obj = len(pds_obj) - 1
    elif isinstance(obj, int):
        max_obj = obj
    else:
        max_obj = max(obj)

    if max_obj >= len(pds_obj):
        raise IndexError(
            f'index {max_obj + 1} for PDS pointer {pname[1:]} out of range'
        )

    parent = os.path.split(infile)[0]
    if obj is None:
        imagefile: Any = [os.path.join(parent, p) for p in pds_obj]
    elif isinstance(obj, int):
        imagefile = os.path.join(parent, pds_obj[obj])
    else:
        imagefile = [os.path.join(parent, pds_obj[o]) for o in obj]

    return imagefile, filter_info, label



def _process_one_image(
    infile: str,
    options: PicmakerOptions,
    reuse: tuple[Any, Any, Any, str] | None,
    *,
    directory: str | None,
) -> tuple[tuple[Any, Any], tuple[Any, Any, Any, str]] | None:
    """Run the per-image pipeline on one input file.

    Encapsulates the loop body of :func:`images_to_pics`: it builds the output path, optionally
    reuses a prior read, decides between the HST mosaic branch and the single-detector branch,
    applies the orientation / gamma / size / wrap / pad chain, and writes the result.

    Parameters:
        infile: Input file path.
        options: Validated and post-normalized
            :class:`~picmaker.options.PicmakerOptions`. The caller is
            responsible for filling in defaults that the legacy
            :func:`~picmaker.pipeline.images_to_pics` kwarg interface
            used to set inline (``strip`` defaults to ``[]``,
            ``pointer`` to ``['IMAGE']``, ``bands`` to ``(0, 1)``,
            ``extension`` to ``'jpg'`` / ``'tiff'``).
        reuse: A 4-tuple ``(array3d, default_is_up, filter_info,
            infile)`` from a previous call, or ``None`` to read from
            disk.
        directory: Output directory, or ``None`` to write next to the
            input.

    Returns:
        ``None`` when ``get_outfile`` returned ``''`` (the ``replace='none'`` skip path). Otherwise
        ``((min_limit, max_limit), reuse_tuple)`` where ``min_limit`` / ``max_limit`` are the
        stretch endpoints (or ``None`` in the HST mosaic branch, which computes per-detector
        stretches internally) and ``reuse_tuple`` is the read-result tuple the caller persists
        for a possible later reuse.
    """
    # ``images_to_pics`` backfills ``options.extension`` to ``'jpg'`` or
    # ``'tiff'`` before calling this helper. The cast narrows the
    # ``str | None`` field for mypy without introducing an ``assert``
    # that ``python -O`` would strip.
    extension = cast(str, options.extension)
    outfile = get_outfile(
        infile, directory, options.strip, options.suffix,
        extension, options.replace,
    )
    if outfile == '':
        return None

    if reuse is not None:
        (array3d, default_is_up, filter_info, infile) = reuse
        imagefile: Any = infile
    else:
        imagefile = infile
        (array3d, default_is_up, filter_info) = read_image_array(
            infile, options.obj,
            **{k: getattr(options, k) for k in READ_FILE_KWARGS},
        )

    if options.display_upward:
        this_display_upward = True
    elif options.display_downward:
        this_display_upward = False
    else:
        this_display_upward = default_is_up

    is_int = array3d.dtype.kind in ('i', 'u')
    limits_pair: tuple[Any, Any] = (None, None)

    # Resolve colormap; tint override applies to both mosaic and standard paths.
    colormap = options.colormap
    if options.tint and filter_info is not None:
        tint_override = tinted_colormap(filter_info)
        if tint_override is not None:
            colormap = tint_override

    # Per-instrument hooks — when non-None the instrument owns orientation;
    # pipeline sets this_display_upward = False to avoid a double flip.
    # apply_tint: custom colorization, gated on --tint.
    # apply_mosaic: array assembly (e.g. multi-detector panels), gated on --mosaic.
    _custom_rgb = None
    if filter_info is not None:
        _inst = instruments.lookup(filter_info[0], filter_info[1])
        if _inst is not None:
            if options.tint and hasattr(_inst, 'apply_tint'):
                _custom_rgb = _inst.apply_tint(array3d, filter_info, options)
            if _custom_rgb is None and options.mosaic and hasattr(_inst, 'apply_mosaic'):
                _custom_rgb = _inst.apply_mosaic(
                    array3d, filter_info, options,
                    default_is_up=default_is_up,
                    colormap=colormap,
                    imagefile=imagefile,
                )

    if _custom_rgb is not None:
        array_rgb = _custom_rgb
        this_display_upward = False
    else:
        array_rgb, these_limits = _band_to_rgb(
            array3d, options.bands,
            options=options, is_int=is_int, colormap=colormap,
        )
        limits_pair = (these_limits[0], these_limits[1])

    array_rgb = rotate_array_rgb(array_rgb, this_display_upward, options.rotate)
    array_rgb = apply_gamma(array_rgb, options.gamma)

    (unwrapped_size, wrapped_size, sections, wrap_axis) = get_size(
        array_rgb.shape, options.size, options.scale, options.frame,
        options.wrap, options.wrap_ratio, options.overlap,
        options.gap_size, options.frame_max,
    )

    image = array_to_pil(array_rgb, options.twobytes)
    image = filter_image(image, options.filter_name)
    image = resize_image(image, unwrapped_size)

    if sections > 1:
        image = wrap_image(
            image, wrapped_size, sections, wrap_axis,
            options.gap_size, options.gap_color,
        )

    if options.pad:
        image = pad_image(image, options.frame, options.pad_color)

    write_pil(image, outfile, options.quality)

    return limits_pair, (array3d, default_is_up, filter_info, infile)


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
    pds3_label_method: str = 'fast',
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
    mosaic: bool = False,
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
    options = PicmakerOptions(
        replace=replace, proceed=proceed, extension=extension,
        suffix=suffix, strip=strip, quality=quality, twobytes=twobytes,
        bands=bands, lines=lines, samples=samples, obj=obj, pointer=pointer,
        pds3_label_method=pds3_label_method,
        size=size, scale=scale, crop=crop, frame=frame, pad=pad,
        pad_color=pad_color, frame_max=frame_max, wrap=wrap,
        wrap_ratio=wrap_ratio, overlap=overlap, gap_size=gap_size,
        gap_color=gap_color, mosaic=mosaic, valid=valid, limits=limits,
        percentiles=percentiles, trim=trim, trim_zeros=trim_zeros,
        footprint=footprint, histogram=histogram, colormap=colormap,
        below_color=below_color, above_color=above_color,
        invalid_color=invalid_color, gamma=gamma, tint=tint,
        display_upward=display_upward, display_downward=display_downward,
        rotate=rotate, filter_name=filter_name, zebra=zebra,
    )
    options.validate()

    # Backfill the legacy "set inline if None" defaults that the kwarg
    # interface used to apply before the loop. PicmakerOptions stores
    # them as-given so library callers that bypass the kwarg interface
    # still get a consistent shape.
    if options.strip is None:
        options.strip = []
    if options.pointer is None:
        options.pointer = ['IMAGE']
    if options.bands is None:
        options.bands = (0, 1)
    if options.extension is None:
        options.extension = 'tiff' if options.twobytes else 'jpg'

    min_limits: list[Any] = []
    max_limits: list[Any] = []
    last_reuse_tuple: tuple[Any, Any, Any, str] | None = None

    # The caller's ``reuse`` short-circuit is only valid for a one-file
    # batch (the function returns at most one ``reuse`` tuple). Clamp it
    # to ``None`` for multi-file batches so the helper signature stays
    # honest.
    effective_reuse = reuse if len(filenames) == 1 else None

    for infile in filenames:
        if verbose:
            logger.info('%s', infile)

        try:
            result = _process_one_image(
                infile, options, effective_reuse, directory=directory,
            )
        except Exception:
            if proceed:
                # `logger.exception` logs the type, message, AND the full
                # traceback in one call through the configured handler, so
                # output ordering stays deterministic under `pytest -n auto`
                # and `caplog` captures it cleanly.
                logger.exception('%s', infile)
                continue
            raise
        finally:
            # The caller-supplied reuse only applies to the first
            # iteration (and only when ``len(filenames) == 1``); clear
            # it unconditionally so the helper sees ``None`` on any
            # subsequent iteration.
            effective_reuse = None

        if result is None:
            continue
        limits_pair, reuse_tuple = result
        if limits_pair[0] is not None:
            min_limits.append(limits_pair[0])
            max_limits.append(limits_pair[1])
        last_reuse_tuple = reuse_tuple

    if len(min_limits) == 0:
        # HST-mosaic mode never appends to min_limits / max_limits (it
        # uses per-detector stretches), so an HST-only batch ends here
        # with no reuse — preserves the legacy return shape that movie
        # mode and process_images depend on.
        return (None, None, None)

    return (np.median(min_limits), np.median(max_limits), last_reuse_tuple)


__all__ = ['find_common_path', 'images_to_pics', 'process_images']
