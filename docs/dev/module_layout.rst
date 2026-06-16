Module-by-module description
============================

Each leaf module under :mod:`picmaker` has one responsibility. The
summary below describes that responsibility and links to the API
reference for each public symbol.

:mod:`picmaker` (``src/picmaker/__init__.py``)
----------------------------------------------

Top-level package. Re-exports the public API surface from the leaf
modules, defines :data:`__all__`, and resolves :data:`__version__`
from ``importlib.metadata`` (with a fallback to the
``setuptools_scm``-generated ``_version.py`` when the package is run
from a source checkout that has not been installed). New code
should import from here (``from picmaker import images_to_pics``)
rather than from the individual leaf modules.

:mod:`picmaker.cli` (``src/picmaker/cli.py``)
---------------------------------------------

The argparse-based command-line entry point. :func:`picmaker.cli.main`
parses ``sys.argv``, dispatches to :func:`picmaker.pipeline.process_images`,
and converts ``--versions FILE`` into a list of normalized option
dicts. Each CLI phase lives in its own private helper:
:func:`!_build_parser` (argparse setup),
:func:`!_separate_files_and_dirs` (positional-arg classification),
:func:`!_normalize_and_validate` (mutex / value-validity checks),
:func:`!_collect_option_dicts` (``--versions`` re-parse loop), and
:func:`!_process_directory` (per-directory walk). They are
unit-tested directly in :file:`tests/test_cli_unit.py` and
:file:`tests/test_cli_helpers.py`.

:mod:`picmaker.pipeline` (``src/picmaker/pipeline.py``)
-------------------------------------------------------

The orchestration layer. :func:`picmaker.pipeline.process_images`
walks the input list (with optional ``--movie`` mode that shares a
stretch across frames) and dispatches each file to
:func:`picmaker.pipeline.images_to_pics`. The per-image work is split
across three module-private helpers:
:func:`!_pds3_resolve_pointer` (PDS3 ``.LBL`` pointer resolution),
:func:`!_hst_mosaic_rgb` (HST ACS/WFC and WFPC2 mosaic assembly,
with :func:`!_hst_wfpc2_mosaic` and :func:`!_hst_acs_panel_mosaic` as
geometry sub-helpers), and :func:`!_process_one_image` (the per-file
read → slice → colormap → write chain). Each helper has direct
unit-test coverage in :file:`tests/test_pipeline_helpers.py`.
:func:`picmaker.pipeline.find_common_path` is a small directory-walking
helper used to derive the output tree's root when ``--recursive`` is
set.

:mod:`picmaker.options` (``src/picmaker/options.py``)
-----------------------------------------------------

:class:`~picmaker.options.PicmakerOptions` is the dataclass that owns
all post-normalization mutex / value-validity invariants. Both
:func:`!picmaker.cli._normalize_and_validate` (early, at CLI parse
time) and :func:`picmaker.pipeline.images_to_pics` (late, at library
call time) build a :class:`~picmaker.options.PicmakerOptions` from
their kwargs and call
:meth:`~picmaker.options.PicmakerOptions.validate` so the invariants
live in exactly one place.

:mod:`picmaker._types` (``src/picmaker/_types.py``)
---------------------------------------------------

Shared type definitions imported by both :mod:`picmaker.io` and the
instrument sub-modules. Lives here (rather than in :mod:`picmaker.io`)
to break the import cycle that would arise if instrument modules
imported from :mod:`picmaker.io` while :mod:`picmaker.io` imports from
:mod:`picmaker.instruments`. Defines :class:`~picmaker._types.ReadResult`
(a :class:`typing.NamedTuple` of ``(array3d, default_is_up,
filter_info)``), :data:`~picmaker._types.FilterInfo` (the
``(inst_host, inst_id, filter_name)`` triple or ``None``), and
:data:`~picmaker._types.ObjectSelector` (the ``obj=`` parameter type
accepted by file readers).

:mod:`picmaker.io` (``src/picmaker/io.py``)
-------------------------------------------

The file-reader cascade and output-path helpers. The cascade lives in
:func:`picmaker.io.read_one_image_array` and tries each known format in
turn: pickle → numpy ``.npy`` → per-instrument readers →
generic VICAR fallback → generic FITS fallback → PIL → PDS3-label.
The per-instrument step iterates :data:`picmaker.instruments.ALL_INSTRUMENTS`
and calls each instrument's :func:`!read_file`; the first non-``None``
result wins.  The generic VICAR and FITS fallbacks handle files from
unrecognized instruments.  The first match returns a
:class:`~picmaker._types.ReadResult`.
:func:`~picmaker.io.read_image_array` is the multi-file variant that
stacks the per-file results along the band axis.
:func:`~picmaker.io.read_pds_labeled_image_array` is the PDS3 label
parser.
:func:`~picmaker.io.get_outfile` builds the output path, honoring
the ``replace=`` policy.

The module's name shadows the stdlib ``io``; use absolute imports
(``from picmaker.io import …``) and never write ``import io`` inside
the ``picmaker`` package. A rename to ``picmaker.readers`` is tracked
in `issue #14 <https://github.com/SETI/rms-picmaker/issues/14>`__.

:mod:`picmaker.enhance` (``src/picmaker/enhance.py``)
-----------------------------------------------------

Intensity-space operations. :func:`~picmaker.enhance.get_limits`
chooses the stretch endpoints from the array, optional masks, and the
``--limits`` / ``--percentiles`` / ``--trim`` / ``--footprint``
options. :func:`~picmaker.enhance.apply_colormap` maps a 2-D array to
RGB through a named or per-instrument tint.
:func:`~picmaker.enhance.apply_gamma` is the final power-law
correction. :func:`~picmaker.enhance.fill_zebra_stripes` is the
optional pre-stretch cleanup for legacy spacecraft compression
artifacts.

:mod:`picmaker.geometry` (``src/picmaker/geometry.py``)
-------------------------------------------------------

Shape-space operations. :func:`~picmaker.geometry.slice_array` selects
the sample / line / band range from the raw 3-D input.
:func:`~picmaker.geometry.crop_array` strips constant-valued borders.
:func:`~picmaker.geometry.rotate_array_rgb` applies the requested
flip / rotation. :func:`~picmaker.geometry.get_size` is the resize
planner that consumes ``--size`` / ``--scale`` / ``--frame`` /
``--wrap-ratio`` and returns the final dimensions plus wrap geometry.
:func:`~picmaker.geometry.resize_image`,
:func:`~picmaker.geometry.wrap_image`, and
:func:`~picmaker.geometry.pad_image` execute the plan against a PIL
image. :func:`~picmaker.geometry.circle_mask` is a small helper used
by the median-filter footprint option in :mod:`~picmaker.enhance`.

:mod:`picmaker.color` (``src/picmaker/color.py``)
-------------------------------------------------

Mission-agnostic tint dispatch. :func:`~picmaker.color.tinted_colormap`
takes the ``filter_info`` triple from the reader cascade, normalizes
the HST ``CL1`` / ``CL2`` / ``CLEAR*`` / ``N/A`` quirks, then
delegates to the per-instrument modules in
:mod:`picmaker.instruments`. The wavelength-to-RGB lookup tables
(:data:`picmaker._rgb.RGB_BY_NM`, :data:`picmaker._rgb.RFUNC`,
:data:`picmaker._rgb.GFUNC`, :data:`picmaker._rgb.BFUNC`) are
re-exported here for convenience but live in :mod:`picmaker._rgb`.

:mod:`picmaker.pil_utils` (``src/picmaker/pil_utils.py``)
---------------------------------------------------------

The bridge between numpy arrays and PIL images.
:func:`~picmaker.pil_utils.array_to_pil` converts an
``(lines, samples, bands)`` array into a PIL image (or a list of three
PIL images for 16-bit RGB). :func:`~picmaker.pil_utils.pil_to_array`
is the inverse. :func:`~picmaker.pil_utils.write_pil` writes a PIL
image to disk and routes 16-bit output through
:func:`picmaker.tiff16.WriteTiff16`.

:mod:`picmaker._filters` (``src/picmaker/_filters.py``)
-------------------------------------------------------

A thin dispatch around PIL's :mod:`PIL.ImageFilter` presets.
:data:`picmaker._filters.FILTER_DICT` maps the case-folded filter
name to the ``ImageFilter`` instance;
:func:`~picmaker._filters.filter_image` applies one to a PIL image
(or raises :class:`ValueError` for the 16-bit-RGB-as-list path,
which is not supported).

:mod:`picmaker._rgb` (``src/picmaker/_rgb.py``)
-----------------------------------------------

The wavelength → RGB table that the HST tint inferer uses. Private to
the package; re-exported via :mod:`picmaker.color`.

:mod:`picmaker.tiff16` (``src/picmaker/tiff16.py``)
---------------------------------------------------

Hand-rolled 16-bit TIFF reader and writer. Used because Pillow's
16-bit support is uneven across grayscale / RGB / palette modes.
:func:`~picmaker.tiff16.WriteTiff16` and
:func:`~picmaker.tiff16.ReadTiff16` keep their PascalCase names for
backward compatibility (the one remaining per-file ruff ignore for
this module is the ``N802`` allow).

:mod:`picmaker.colornames` (``src/picmaker/colornames.py``)
-----------------------------------------------------------

The X11 color-name table (~800 entries) plus a normalizing lookup
helper. Used by the ``--pad-color`` / ``--gap-color`` / colormap
options.

:mod:`picmaker.instruments` (``src/picmaker/instruments/``)
-----------------------------------------------------------

Per-mission file readers and tint chains. Each module under this
subpackage exposes the three-function protocol (``read_file``,
``matches``, ``tint_for``) plus an optional ``apply_tint`` described in
:doc:`adding_an_instrument`.  Each instrument owns its own format
detection and array extraction inside :func:`!read_file`.
:func:`picmaker.instruments.lookup` picks the right instrument module
given a host string; :data:`~picmaker.instruments.ALL_INSTRUMENTS` is
the ordered dispatch list that :func:`picmaker.io.read_one_image_array`
iterates.

:mod:`picmaker.instruments._shared` (``src/picmaker/instruments/_shared.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Shared format-level utilities for use by instrument modules.
:func:`~picmaker.instruments._shared.try_open_vicar` wraps
:meth:`vicar.VicarImage.from_file` and returns ``None`` on failure.
:func:`~picmaker.instruments._shared.is_fits_file` sniffs the FITS
magic bytes.
:func:`~picmaker.instruments._shared.extract_fits_array` extracts a 3-D
array from an open FITS HDU list.  These helpers live here rather than
in :mod:`picmaker.io` to avoid circular imports.
