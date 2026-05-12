Module-by-module description
============================

Each leaf module under :mod:`picmaker` has one responsibility. The
prose below summarizes that responsibility and links to the API
reference for each public symbol.

:mod:`picmaker` (``src/picmaker/__init__.py``)
----------------------------------------------

Top-level package. Re-exports the public API surface from the leaf
modules, defines :data:`__all__`, and resolves :data:`__version__`
from ``importlib.metadata`` (with a fallback to the
``setuptools_scm``-generated ``_version.py`` when the package is run
from a source checkout that has not been installed).

:mod:`picmaker.picmaker` (``src/picmaker/picmaker.py``)
-------------------------------------------------------

Backward-compatibility shim. Re-exports every public name plus
several BC-only aliases (``ColorNames``, ``ReadTiff16``,
``WriteTiff16``, ``VicarError``, ``VicarImage``, and the legacy
``GALILEO_SSI_DICT`` / ``GALILEO_SSI_NAMES`` / ``NH_MVIC_DICT`` /
``VOYAGER_ISS_DICT`` aliases). New code should import from the
canonical leaf modules instead; the shim exists so callers of the
pre-PR-3 1.x API keep working.

:mod:`picmaker.cli` (``src/picmaker/cli.py``)
---------------------------------------------

The argparse-based command-line entry point. :func:`picmaker.cli.main`
parses ``sys.argv``, dispatches to :func:`picmaker.pipeline.process_images`,
and converts ``--versions FILE`` into a list of normalized option
dicts. The private helpers :func:`!_build_parser`,
:func:`!_separate_files_and_dirs`, and :func:`!_normalize_and_validate`
each handle one phase of CLI processing and are unit-tested directly
in :file:`tests/test_cli_unit.py`.

:mod:`picmaker.pipeline` (``src/picmaker/pipeline.py``)
-------------------------------------------------------

The orchestration layer. :func:`picmaker.pipeline.process_images`
walks the input list (with optional ``--movie`` mode that shares a
stretch across frames) and dispatches each file to
:func:`picmaker.pipeline.images_to_pics`, which runs the per-image
pipeline. :func:`picmaker.pipeline.find_common_path` is a small
directory-walking helper used to derive the output tree's root when
``--recursive`` is set.

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

:mod:`picmaker.io` (``src/picmaker/io.py``)
-------------------------------------------

The file-reader cascade and output-path helpers. The cascade lives in
:func:`picmaker.io.read_one_image_array` and tries each known format
in turn (pickle → numpy ``.npy`` → VICAR → FITS → PIL → PDS3-label);
the first match returns a :class:`~picmaker.io.ReadResult`
:class:`typing.NamedTuple` of ``(array3d, default_is_up, filter_info)``.
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

Per-mission detectors and tint chains. Each module under this
subpackage exposes the same four-function protocol described in
:doc:`adding_an_instrument`.
:func:`picmaker.instruments.lookup` picks the right instrument module
given a host string;
:data:`~picmaker.instruments.VICAR_INSTRUMENTS` and
:data:`~picmaker.instruments.FITS_INSTRUMENTS` are the per-format
dispatch lists that :func:`picmaker.io.read_one_image_array` iterates.
