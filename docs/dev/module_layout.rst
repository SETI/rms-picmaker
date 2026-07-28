Module-by-module description
============================

Each leaf module under :mod:`picmaker` has one responsibility. The
summary below describes that responsibility and links to the API
reference for each public symbol.

:mod:`picmaker` (``src/picmaker/__init__.py``)
----------------------------------------------

Top-level package. Re-exports the public API surface from the leaf
modules (see :data:`__all__`) and resolves :data:`__version__` from
``importlib.metadata`` (with a fallback to the
``setuptools_scm``-generated ``_version.py`` when the package is run
from a source checkout that has not been installed). Private modules
(those whose names begin with an underscore), the per-instrument
:class:`~picmaker.instruments.ImageData` subclasses, and ALL-CAPS
module constants are intentionally not re-exported. New code should
import from here (``from picmaker import picmaker``) rather than from
the individual leaf modules.

:mod:`picmaker.picmaker` (``src/picmaker/picmaker.py``)
-------------------------------------------------------

The library entry point and orchestration layer.
:func:`picmaker.picmaker.validate_options` converts an argparse
``Namespace`` (or a plain dict) into the normalized ``options`` dict
used throughout the package, enforcing the mutex / value-validity
rules (``--band`` vs. ``--bands``, ``--scale`` vs.
``--wscale``/``--hscale``, ``--up`` vs. ``--down``, ``--frame`` vs.
``--size``, ``--movie`` vs. ``--versions``, color-name validation,
etc.). Options are plain dicts; there is no options dataclass.
:func:`picmaker.picmaker.get_versions` reads a ``--versions`` file and
returns one option dict per version line, layering each line's
overrides onto a copy of the base options.
:func:`picmaker.picmaker.picmaker` is the top-level driver: it
validates options, resolves the input files via
:func:`picmaker.control.get_filepaths`, and calls
:func:`picmaker.picmaker.picmaker1` for each file (once per version, or
once per frame with a shared stretch in ``--movie`` mode).
:func:`picmaker.picmaker.picmaker1` performs the per-image work: read
→ slice → optional zebra fill → stretch limits → colormap (or mosaic)
→ rotate → size → convert to PIL → filter → resize → wrap → pad →
write.

:mod:`picmaker.main` (``src/picmaker/main.py``)
-----------------------------------------------

The console-script entry point (``picmaker = "picmaker.main:main"`` in
``pyproject.toml``). :func:`picmaker.main.main` builds the parser from
:func:`picmaker.options.get_parser`, parses ``sys.argv``, runs the
options through :func:`picmaker.picmaker.validate_options`, shifts the
one-based ``--samples`` / ``--lines`` / ``--bands`` / ``--obj``
command-line indices to zero-based, and calls
:func:`picmaker.picmaker.picmaker`. Warnings are promoted to errors
here (``warnings.simplefilter('error')``), except for
``DeprecationWarning``, which is reported without escalating.

:mod:`picmaker.options` (``src/picmaker/options.py``)
-----------------------------------------------------

The argparse definition. :func:`picmaker.options.get_parser` builds and
returns the :class:`argparse.ArgumentParser` for every ``picmaker``
command-line flag. It is used both by :mod:`picmaker.main` (to parse
``sys.argv``) and by :func:`picmaker.picmaker.get_versions` (to
re-parse each line of a ``--versions`` file).

:mod:`picmaker.control` (``src/picmaker/control.py``)
-----------------------------------------------------

File-selection and output-path helpers.
:func:`picmaker.control.get_filepaths` expands the positional files,
``--directory``, ``--recursive``, and ``--patterns`` options into the
ordered list of ``(infile, outdir)`` pairs to process.
:func:`picmaker.control.get_outfile` derives the output path for one
input file, honoring the ``--replace`` policy
(:data:`picmaker.control.REPLACE_CHOICES`).

:mod:`picmaker.slicing` (``src/picmaker/slicing.py``)
-----------------------------------------------------

Shape-space selection. :func:`picmaker.slicing.slice_array` extracts
the requested sample / line / band sub-range from the raw 3-D input
array and returns it together with an optional invalid-pixel mask.

:mod:`picmaker.stretch` (``src/picmaker/stretch.py``)
-----------------------------------------------------

:func:`picmaker.stretch.get_limits` chooses the stretch endpoints from
the array, the optional invalid mask, and the ``--limits`` /
``--percentiles`` / ``--trim`` / ``--footprint`` options.

:mod:`picmaker.enhancement` (``src/picmaker/enhancement.py``)
-------------------------------------------------------------

Intensity-to-color mapping. :func:`picmaker.enhancement.apply_colormap`
maps a stretched grayscale array (up to three bands) to a 3-D RGB or
grayscale array scaled zero to one, using a named colormap or the
reader's ``default_tint``. This is the default implementation that
each :class:`~picmaker.instruments.ImageData` subclass calls (and may
override).

:mod:`picmaker.orientation` (``src/picmaker/orientation.py``)
-------------------------------------------------------------

:func:`picmaker.orientation.rotate_rgb_array` applies the requested
flip / rotation to the RGB array, taking the reader's
``default_upward`` hint and the ``--up`` / ``--down`` / ``--rotate``
options (:data:`picmaker.orientation.ROTATE_CHOICES`) into account.

:mod:`picmaker.sizing` (``src/picmaker/sizing.py``)
---------------------------------------------------

Resize planning and execution. :func:`picmaker.sizing.get_size`
consumes the array shape plus ``--size`` / ``--scale`` / ``--frame`` /
``--wrap-ratio`` and returns the unwrapped size, wrapped size, section
count, and wrap axis. :func:`picmaker.sizing.resize_pil_image` resizes
a PIL image (or a list of three 16-bit RGB images) to the planned size.

:mod:`picmaker.layout` (``src/picmaker/layout.py``)
---------------------------------------------------

Post-resize page layout. :func:`picmaker.layout.wrap_pil_image` splits
a tall or wide image into ``sections`` panels separated by gaps, and
:func:`picmaker.layout.pad_pil_image` pads an image out to fill a
requested ``--frame`` size.

:mod:`picmaker.pil_utils` (``src/picmaker/pil_utils.py``)
---------------------------------------------------------

The bridge between numpy arrays and PIL images.
:func:`picmaker.pil_utils.array_to_pil` converts an
``(lines, samples, bands)`` array into a PIL image (or a list of three
PIL images for 16-bit RGB). :func:`picmaker.pil_utils.pil_to_array`
is the inverse. :func:`picmaker.pil_utils.write_pil` writes a PIL image
to disk, routing 16-bit output through
:func:`picmaker.tiff16.write_tiff16`.
:data:`picmaker.pil_utils.PIL_EXTENSIONS` is the set of recognized
output extensions used by :func:`picmaker.picmaker.validate_options`.

:mod:`picmaker.preprocessing` (``src/picmaker/preprocessing.py``)
-----------------------------------------------------------------

Optional array cleanup applied before the limits and colormap are
computed. :func:`picmaker.preprocessing.fill_zebra_stripes` is the
pre-stretch cleanup for legacy spacecraft compression artifacts.

:mod:`picmaker.postprocessing` (``src/picmaker/postprocessing.py``)
-------------------------------------------------------------------

Optional PIL-image processing applied after the stretch.
:func:`picmaker.postprocessing.filter_pil_image` applies a named
:mod:`PIL.ImageFilter` preset
(:data:`picmaker.postprocessing.FILTER_CHOICES`) to a PIL image.
:func:`picmaker.postprocessing.adjust_pil_image` applies the Pillow
:mod:`PIL.ImageEnhance` adjustments selected by ``--brighten``,
``--contrast``, ``--saturation``, and ``--sharpen``.

:mod:`picmaker.tiff16` (``src/picmaker/tiff16.py``)
---------------------------------------------------

Hand-rolled 16-bit TIFF reader and writer. Used because Pillow's
16-bit support is uneven across grayscale / RGB / palette modes.
:func:`picmaker.tiff16.write_tiff16` and
:func:`picmaker.tiff16.read_tiff16`.

:mod:`picmaker.colornames` (``src/picmaker/colornames.py``)
-----------------------------------------------------------

The X11 color-name table plus a normalizing lookup helper,
:class:`picmaker.colornames.ColorNames`. Used by the colormap,
``--pad-color``, ``--gap-color``, and related color options.

:mod:`picmaker.instruments` (``src/picmaker/instruments/``)
-----------------------------------------------------------

Per-mission file readers and tint chains. The package ``__init__``
defines the reader cascade and the plug-in machinery:

* :class:`picmaker.instruments.ImageData` is the base class every
  instrument reader subclasses. An instance carries the pixel
  ``array``, a ``default_upward`` orientation hint, and a
  ``default_tint`` RGB color; its :meth:`~picmaker.instruments.ImageData.apply_colormap`
  method delegates to :func:`picmaker.enhancement.apply_colormap` and
  may be overridden per instrument.
* :func:`picmaker.instruments.read_image_array` is the public reader.
  For a single path it runs the cascade; for a list of paths it stacks
  the per-file arrays along the band axis. The private
  ``_read_one_image_array`` tries each format in turn — PDS3 ``.LBL``
  label, then VICAR, then FITS, then any other file format — and, for
  each, offers the file to every registered instrument's
  ``detect_in_pds3`` / ``detect_in_vicar`` / ``detect_in_fits`` /
  ``detect_in_file`` static method until one returns an
  :class:`~picmaker.instruments.ImageData`.
* :func:`picmaker.instruments._register_instrument` adds an
  :class:`~picmaker.instruments.ImageData` subclass to the dispatch
  list. Every non-underscore module in the subpackage is imported at
  package load so it can register itself, so a new instrument is picked
  up simply by dropping a module into the package.
* :func:`picmaker.instruments.tint_by_nm` maps a wavelength in nm to an
  RGB tint via a private wavelength → RGB lookup table. Each reader's
  ``default_tint`` is typically computed from its filter's central
  wavelength through this function; there is no separate colormap
  module.

The support modules hold format-level helpers shared by the readers:

:mod:`picmaker.instruments._fits_support` (``_fits_support.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Shared FITS tools: ``hdu_is_image``, ``get_fits_image_hdus``,
``get_fits_image_hdu``, and ``get_fits_array`` for locating and
extracting image arrays from an open FITS HDU list.

:mod:`picmaker.instruments._hst_support` (``_hst_support.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Shared HST tools: ``get_hst_filter_digits`` (parse the numeric
wavelength out of an HST filter name) and ``is_science_hdu``.

:mod:`picmaker.instruments._pds3_support` (``_pds3_support.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Shared PDS3 tools: ``read_pds3_image_array`` (plus ``PDS3_METHODS`` /
``DEFAULT_PDS3_METHOD``) for reading the image object out of a PDS3
label.

Per-instrument reader modules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each of the following modules defines exactly one
:class:`~picmaker.instruments.ImageData` subclass and registers it:

* ``cassini_iss.py`` — Cassini ISS (PDS3 and VICAR).
* ``voyager_iss.py`` — Voyager ISS (PDS3 and VICAR).
* ``galileo_ssi.py`` — Galileo SSI (PDS3 and VICAR).
* ``hst_acs.py`` — HST ACS (FITS).
* ``hst_wfc3.py`` — HST WFC3 (FITS).
* ``hst_wfpc2.py`` — HST WFPC2 (FITS, with optional four-detector
  mosaic assembly).
* ``hst_nicmos.py`` — HST NICMOS (FITS).
* ``nh_lorri.py`` — New Horizons LORRI (PDS3 and FITS).
* ``nh_mvic.py`` — New Horizons MVIC (PDS3 and FITS).
* ``zzz_generic.py`` — the generic fallback reader (PDS3, VICAR, FITS,
  and other raster formats). Named with a ``zzz`` prefix so it sorts
  last in the dispatch order and only matches when no instrument-
  specific reader claims the file.

See :doc:`adding_an_instrument` for the full reader protocol.
