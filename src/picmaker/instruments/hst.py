"""HST detection and wavelength-based tint."""

import logging
import os
import warnings
from typing import Any

import astropy.io.fits as pyfits
import numpy as np
from numpy.typing import NDArray

from picmaker._rgb import BFUNC, GFUNC, RFUNC, RGB_BY_NM
from picmaker._types import FilterInfo, ObjectSelector, ReadResult
from picmaker.enhance import _band_to_rgb
from picmaker.instruments import _shared
from picmaker.options import PicmakerOptions

_MOSAIC_INSTRUMENTS = ('ACS/WFC', 'WFPC2')

logger = logging.getLogger(__name__)


def _detect_fits(hdulist: Any) -> tuple[str, str, Any] | None:
    """Extract HST metadata from an open ``astropy.io.fits`` HDU list.

    The ``TELESCOP`` keyword identifies the host, ``INSTRUME`` (with an
    optional ``DETECTOR`` suffix) identifies the instrument, and the
    filter name comes from one of ``FILTER``, ``FILTER1``/``FILTER2``
    (HST/ACS), or ``FILTNAM1``/``FILTNAM2`` (HST/WFPC2).

    Parameters:
        hdulist: An ``astropy.io.fits`` HDU list.

    Returns:
        ``(inst_host, inst_id, filter_name)`` where ``filter_name`` may
        be a string or a 2-tuple of strings, or ``None`` if the file is
        not an HST FITS image.
    """
    try:
        inst_host = hdulist[0].header['TELESCOP']
    except KeyError:
        return None
    try:
        inst_id = hdulist[0].header['INSTRUME']
        if 'DETECTOR' in hdulist[0].header:
            inst_id += '/' + hdulist[0].header['DETECTOR']
    except KeyError:
        return None

    filter_name: Any = None
    try:
        filter_name = hdulist[0].header['FILTER'].upper().strip()
    except KeyError:
        pass
    try:
        filter_name = (hdulist[0].header['FILTER1'], hdulist[0].header['FILTER2'])
    except KeyError:
        pass
    try:
        filter_name = (hdulist[0].header['FILTNAM1'], hdulist[0].header['FILTNAM2'])
    except KeyError:
        pass

    return (inst_host, inst_id, filter_name)


def _extract_hst_array(
    hdulist: Any,
    inst_id: str,
    obj: ObjectSelector,
    use_mosaic: bool,
) -> NDArray[Any]:
    """Extract the image array from an HST FITS hdulist.

    Handles the ACS/WFC and WFPC2 mosaic cases when ``use_mosaic`` is
    true and ``obj`` is ``None``; all other cases delegate to
    :func:`~picmaker.instruments._shared.extract_fits_array`.

    Parameters:
        hdulist: An open ``astropy.io.fits`` HDU list.
        inst_id: Instrument id string (e.g. ``'ACS/WFC'``, ``'WFPC2'``).
        obj: Object selector; mosaic logic only applies when ``None``.
        use_mosaic: True to stitch multi-CCD mosaics.

    Returns:
        3-D numpy array ``(bands, lines, samples)``.
    """
    array3d: NDArray[Any]

    if use_mosaic and obj is None:
        if inst_id == 'ACS/WFC':
            array = hdulist[1].data
            try:
                array2 = hdulist[4].data
                shape = (2, *array.shape)
                array3d = np.empty(shape)
                array3d[0] = array
                array3d[1] = array2
            except IndexError:
                array3d = array
            if array3d.ndim == 2:
                array3d = array3d.reshape((1, *array3d.shape))
            return array3d

        if inst_id == 'WFPC2':
            array3d_list: list[Any] = []
            for hdu in hdulist:
                candidate = hdu.data
                if not isinstance(candidate, np.ndarray):
                    continue
                if candidate.ndim not in (2, 3):
                    continue
                array3d_list.append(candidate)
            return np.array(array3d_list)

    return _shared.extract_fits_array(hdulist, obj)


def read_file(
    filename: str | os.PathLike[str],
    obj: ObjectSelector = None,
    **kwargs: Any,
) -> ReadResult | None:
    """Try to detect and read an HST FITS image.

    Checks the FITS magic bytes, opens the file, identifies it as HST
    via the ``TELESCOP`` header keyword, and extracts the data array.
    When ``mosaic=True`` (passed via ``kwargs``) and the instrument is
    ``ACS/WFC`` or ``WFPC2``, the multi-CCD mosaic is assembled from
    multiple HDUs.

    Parameters:
        filename: Path to the candidate file.
        obj: HDU index, name, or list/tuple of indices to stack.
        **kwargs: Instrument-specific options. Recognises ``mosaic``
            (bool, default ``False``): when ``True``, assemble the
            ACS/WFC or WFPC2 mosaic.

    Returns:
        :class:`~picmaker._types.ReadResult` on success, ``None`` if
        the file is not recognized as an HST FITS image.
    """
    hst: bool = kwargs.get('mosaic', False)
    if not _shared.is_fits_file(filename):
        return None
    try:
        with warnings.catch_warnings(), pyfits.open(str(filename)) as hdulist:
            warnings.filterwarnings('error')
            _fitsobj = hdulist[0]  # IndexError / KeyError if not valid FITS
            filter_info = _detect_fits(hdulist)
            if filter_info is None:
                return None
            inst_id = filter_info[1]
            array3d = _extract_hst_array(hdulist, inst_id, obj, hst)
            return ReadResult(array3d, True, filter_info)
    except (UserWarning, OSError):
        return None


def _wfpc2_mosaic(arrays_rgb: list[Any], imagefile: Any) -> Any:
    """Assemble WFPC2's four detectors (PC1, WF2, WF3, WF4) into a 2x2 mosaic.

    When ``imagefile`` is a list of per-detector file paths, the band order is
    inferred from substrings (``PC1``, ``WF2``, ``WF3``, ``WF4``) in each
    filename. When ``imagefile`` is a single string (e.g. a multi-extension FITS
    file), bands are placed in ``b``-order with a ``b``-step ``np.rot90``
    rotation. Each non-PC1 detector is rotated to share the PC1's pixel
    orientation.

    Parameters:
        arrays_rgb: Per-band RGB arrays (length 4), each ``(lines, samples, 3)``.
        imagefile: Either a single string or a list of strings.

    Returns:
        The assembled 2x2 mosaic, shape ``(2 * lines, 2 * samples, 3)``.
    """
    quads_rgb = np.zeros((4, *arrays_rgb[0].shape))
    for b in range(len(arrays_rgb)):
        if isinstance(imagefile, str):
            quads_rgb[b] = np.rot90(arrays_rgb[b], b)
        else:
            testfile = imagefile[b].upper()
            if 'PC1' in testfile:
                quads_rgb[0] = arrays_rgb[b]
            elif 'WF2' in testfile:
                quads_rgb[1] = np.rot90(arrays_rgb[b], 1)
            elif 'WF3' in testfile:
                quads_rgb[2] = np.rot90(arrays_rgb[b], 2)
            elif 'WF4' in testfile:
                quads_rgb[3] = np.rot90(arrays_rgb[b], 3)
            else:
                quads_rgb[b] = np.rot90(arrays_rgb[b], b)

    (_, dl, ds, db) = quads_rgb.shape
    mosaic = np.empty((2 * dl, 2 * ds, db))
    mosaic[:dl, -ds:] = quads_rgb[0]
    mosaic[:dl, :ds] = quads_rgb[1]
    mosaic[-dl:, :ds] = quads_rgb[2]
    mosaic[-dl:, -ds:] = quads_rgb[3]
    return mosaic


def _acs_panel_mosaic(arrays_rgb: list[Any], imagefile: Any) -> Any:
    """Assemble ACS/WFC's two detectors (WFC1 above, WFC2 below).

    When ``imagefile`` is a list of per-detector file paths, the panel order is
    inferred from substrings (``WFC1``, ``WFC2``) in each filename. When
    ``imagefile`` is a single string, band 0 is placed below and band 1 above
    (matching the legacy ``1 - b`` indexing).

    Parameters:
        arrays_rgb: Per-band RGB arrays (length 2), each ``(lines, samples, 3)``.
        imagefile: Either a single string or a list of strings.

    Returns:
        The assembled panel mosaic, shape ``(2 * lines, samples, 3)``.
    """
    panels_rgb = np.zeros((2, *arrays_rgb[0].shape))
    for b in range(2):
        if isinstance(imagefile, str):
            panels_rgb[1 - b] = arrays_rgb[b]
        else:
            testfile = imagefile[b].upper()
            if 'WFC1' in testfile:
                panels_rgb[0] = arrays_rgb[b]
            elif 'WFC2' in testfile:
                panels_rgb[1] = arrays_rgb[b]
            else:
                panels_rgb[b] = arrays_rgb[b]

    (dl, ds, db) = arrays_rgb[0].shape
    mosaic = np.zeros((2 * dl, ds, db))
    mosaic[:dl] = panels_rgb[0]
    mosaic[-dl:] = panels_rgb[1]
    return mosaic


def apply_mosaic(
    array3d: NDArray[Any],
    filter_info: FilterInfo,
    options: PicmakerOptions,
    *,
    default_is_up: bool = False,
    colormap: Any = None,
    imagefile: Any = None,
) -> NDArray[Any] | None:
    """Assemble the ACS/WFC or WFPC2 multi-detector mosaic when ``--mosaic`` is set.

    Called by the pipeline only when ``--mosaic`` is specified. Returns ``None``
    for non-mosaic HST instruments, letting the standard single-band colormap
    pipeline handle them.

    Parameters:
        array3d: ``(bands, lines, samples)`` stack from :func:`read_file`.
        filter_info: ``(host, instrument, filter)`` triple; only
            ``filter_info[1]`` (``'ACS/WFC'`` or ``'WFPC2'``) is used.
        options: Pipeline options dataclass.
        default_is_up: When ``True`` the array is flipped vertically before
            mosaicking so panels assemble in the correct spatial order.
        colormap: Pre-resolved colormap (post-tint override from the pipeline).
        imagefile: Source file path or list of paths — used to identify
            per-detector files by name substring.

    Returns:
        Assembled ``(lines, samples, 3)`` uint8-range RGB array, or ``None``
        when the instrument is not an ACS/WFC or WFPC2 mosaic target.
    """
    if filter_info is None or filter_info[1] not in _MOSAIC_INSTRUMENTS:
        return None

    inst_id: str = filter_info[1]

    if default_is_up:
        array3d = array3d[:, ::-1, :]

    is_int = array3d.dtype.kind in ('i', 'u')
    arrays_rgb: list[NDArray[Any]] = []
    for b in range(array3d.shape[0]):
        array_rgb, _ = _band_to_rgb(
            array3d, (b, b + 1), options=options, is_int=is_int, colormap=colormap,
        )
        arrays_rgb.append(array_rgb)

    if inst_id == 'WFPC2':
        return np.asarray(_wfpc2_mosaic(arrays_rgb, imagefile))
    if len(arrays_rgb) > 1:
        return np.asarray(_acs_panel_mosaic(arrays_rgb, imagefile))
    return arrays_rgb[0]


def matches(inst_host: str, inst_id: str) -> bool:
    """Host-level predicate: accept any host that mentions HUBBLE or HST.

    Parameters:
        inst_host: Instrument host string (e.g. ``'HST'`` or ``'HUBBLE
            SPACE TELESCOPE'``).
        inst_id: Instrument id.

    Returns:
        ``True`` if either substring appears in ``inst_host``.
    """
    return 'HUBBLE' in inst_host or 'HST' in inst_host


def tint_for(inst_id: str, filter_name: Any) -> list[tuple[int, int, int]] | None:
    """Return the full ``[black, tint, white]`` colormap for an HST filter.

    The tint color comes from inferring a wavelength out of the numeric
    characters in ``filter_name`` (e.g. ``'F606W'`` → 606 nm) and looking
    that wavelength up in :data:`picmaker._rgb.RGB_BY_NM` via the
    :data:`picmaker._rgb.RFUNC` / :data:`picmaker._rgb.GFUNC` /
    :data:`picmaker._rgb.BFUNC` splines. Each detector family has its
    own correction:

    * NICMOS scales the inferred number by 3.5 (its filter names encode
      tens of nm rather than nm).
    * WFC3/IR and ACS/SBC also scale by 3.5 when the inferred number is
      below 200.
    * WFPC2 quad-filters ``FQUV*`` and ``FQCH4*`` are pinned to 300 nm
      and 900 nm respectively.
    * NICMOS polarisers ``POL0S`` / ``POL0L`` are pinned to 110 nm and
      220 nm before the NICMOS x3.5 scaling.

    Broadband filters ``F350LP``, ``F606W``, and ``LONG_PASS`` short-
    circuit to a plain ``[black, white]`` colormap.

    Parameters:
        inst_id: Instrument id, possibly with detector suffix (e.g.
            ``'WFC3/IR'``).
        filter_name: HST filter name; passed through as-is from
            :func:`_detect_fits`.

    Returns:
        ``[(0, 0, 0), (r, g, b), (255, 255, 255)]`` for a successfully
        inferred wavelength, ``[(0, 0, 0), (255, 255, 255)]`` for the
        broadband short-circuits, or ``None`` when no wavelength can be
        inferred (a WARNING is logged).
    """
    if filter_name in ('F350LP', 'F606W', 'LONG_PASS'):
        return [(0, 0, 0), (255, 255, 255)]

    wavelength: float = 0
    for c in filter_name:
        if '0' <= c <= '9' and wavelength < 1600:
            wavelength = 10 * wavelength + int(c)

    # Detector-specific wavelength scaling. The elif chain is kept as
    # three separate branches (rather than `or`-combined) so future
    # per-detector adjustments don't change the others' precedence.
    if 'NIC' in inst_id:  # noqa: SIM114
        wavelength *= 3.5
    elif ('WFC3' in inst_id or 'IR' in inst_id) and wavelength < 200:  # noqa: SIM114
        wavelength *= 3.5
    elif ('ACS' in inst_id or 'SBC' in inst_id) and wavelength < 200:
        wavelength *= 3.5
    elif filter_name.startswith('FQUV'):
        wavelength = 300
    elif filter_name.startswith('FQCH4'):
        wavelength = 900
    elif filter_name == 'POL0S':
        wavelength = 110 * 3.5
    elif filter_name == 'POL0L':
        wavelength = 220 * 3.5

    if wavelength == 0:
        logger.warning('Unknown HST filter: %s %s', inst_id, filter_name)
        return None

    wavelength = max(wavelength, RGB_BY_NM[0, 0])
    wavelength = min(wavelength, RGB_BY_NM[-1, 0])

    r = int(RFUNC(wavelength))
    g = int(GFUNC(wavelength))
    b = int(BFUNC(wavelength))
    return [(0, 0, 0), (r, g, b), (255, 255, 255)]


__all__ = ['apply_mosaic', 'matches', 'read_file', 'tint_for']
