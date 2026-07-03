Pipeline
========

This section covers the CLI-to-output-file path: a flowchart of the
major functions and a walk-through of each.

Flowchart
---------

The diagram below shows the path from a CLI invocation to a written
output file. Cross-references below link each box to its API entry;
the diagram itself uses bare names so it stays legible. The diagram is
rendered as inline SVG by Mermaid (client-side); use the browser's
zoom controls to read the labels at any size.

.. mermaid::
   :align: center

   flowchart TD
       A[picmaker CLI<br/>argv] --> B[main.main]
       B --> C[get_parser<br/>argparse]
       B --> D[validate_options]
       D --> E[get_versions<br/>validate --versions lines]
       B --> F[picmaker<br/>orchestrator]
       F --> DV[validate_options<br/>again, for library callers]
       F --> G[get_filepaths<br/>resolve files + outdirs]
       G --> MV{movie mode?}
       MV -->|yes| P1A[pass 1: picmaker1<br/>return_limits=True]
       P1A --> SH[shared limits =<br/>min/max across frames]
       SH --> GO
       MV -->|no| VER[get_versions<br/>option dict per version]
       VER --> GO[get_outfile<br/>skip if replace='none']
       GO --> P1[picmaker1<br/>infile, outfile]
       P1A -. reads each file .-> P1
       P1 --> RD[read_image_array<br/>if not cached]
       RD --> RO[_read_one_image_array<br/>format cascade]
       RO -->|suffix .lbl| NPI[detect_in_pds3<br/>per instrument]
       RO -->|VICAR open OK| NV[detect_in_vicar<br/>per instrument]
       RO -->|FITS open OK| NF[detect_in_fits<br/>per instrument]
       RO -->|otherwise| NG[detect_in_file<br/>per instrument]
       NPI --> Q[ImageData subclass<br/>array, default_upward, default_tint]
       NV --> Q
       NF --> Q
       NG --> Q
       Q --> SL[slice_array]
       SL --> ZB[fill_zebra_stripes<br/>optional]
       ZB --> MOS{mosaic AND ndim==3 AND<br/>image_data.apply_mosaic?}
       MOS -->|yes| GLB[get_limits per band]
       GLB --> ACB[apply_colormap per band]
       ACB --> AM[apply_mosaic<br/>panel assembly RGB]
       MOS -->|no| GL[get_limits]
       GL --> AC[apply_colormap]
       AM --> RR[rotate_rgb_array]
       AC --> RR
       RR --> GS[get_size]
       GS --> AP[array_to_pil]
       AP --> FI[filter_pil_image]
       FI --> RS[resize_pil_image]
       RS --> CC{sections > 1?}
       CC -->|yes| WR[wrap_pil_image]
       CC -->|no| SKW[skip wrap]
       WR --> PD[pad_pil_image]
       SKW --> PD
       PD --> WP[write_pil]
       WP --> M[Done]

Three short observations on the diagram:

* The ``movie=True`` branch runs :func:`~picmaker.picmaker.picmaker1`
  twice. The first pass reads each file and computes its limits with
  ``return_limits=True`` (no file is written); the orchestrator then
  sets ``options['limits']`` to the ``(min, max)`` across all frames
  and the second pass writes each frame with that shared stretch,
  reusing the already-read ``image_data``.
* The ``apply_mosaic`` branch fires only when ``--mosaic`` is set, the
  sliced array is still 3-D, and the resolved
  :class:`~picmaker.instruments.ImageData` subclass defines
  :func:`!apply_mosaic` (currently HST ACS/WFC two-panel and WFPC2
  quad-panel composites). In that branch the colormap is applied to
  each band *before* the panels are assembled; the standard path
  applies the colormap once to the band-merged array.
* Gamma is no longer a separate stage: it is one of the keyword
  arguments consumed inside
  :func:`~picmaker.enhancement.apply_colormap`.


Major functions
---------------

This subsection walks through the major library functions in pipeline
order. Cross-references resolve to the :doc:`/module` reference; each
public symbol is a clickable link to its full signature, docstring,
and source code (via :mod:`sphinx.ext.viewcode`).

CLI entry point
~~~~~~~~~~~~~~~

:func:`picmaker.main.main` is the function bound to the ``picmaker``
console script (``picmaker = "picmaker.main:main"``). It promotes all
warnings to errors, builds the argparse parser with
:func:`picmaker.parser.get_parser`, parses ``sys.argv``, normalizes
the result with :func:`picmaker.picmaker.validate_options`, shifts the
1-based ``--samples`` / ``--lines`` / ``--bands`` / ``--obj`` indices
to 0-based, and calls the orchestrator
:func:`picmaker.picmaker.picmaker` with the validated option dict as
``**kwargs``. There is no ``cli.py``; the two responsibilities are
split between :mod:`picmaker.parser` (parser construction) and
:mod:`picmaker.main` (wiring).

The library equivalent of "run the CLI from Python" is to call
:func:`picmaker.picmaker.picmaker` directly with keyword arguments; the
kwarg names match the CLI flags one-to-one, and the orchestrator runs
:func:`~picmaker.picmaker.validate_options` itself so callers do not
have to.

Option validation
~~~~~~~~~~~~~~~~~

:func:`picmaker.picmaker.validate_options` accepts either an argparse
:class:`argparse.Namespace` or a plain ``dict`` and returns a plain
``dict`` of normalized options. There is no ``PicmakerOptions`` class;
options are passed around as dictionaries and consumed by downstream
functions as ``**options`` / ``**kwargs``. The function runs every
mutex / value-validity check and collapses alternative spellings of the
same knob:

* ``--band`` collapses into ``bands = (band, band)``; supplying both
  ``--band`` and ``--bands`` is rejected.
* ``--scale`` is expanded to a ``(wscale, hscale)`` pair; ``--scale``
  together with ``--wscale`` or ``--hscale`` is rejected.
* ``--overlap`` collapses into ``overlaps = (overlap, overlap)``;
  ``--overlap`` together with an explicit ``--overlaps`` is rejected.
* ``--down`` collapses into ``display_upward = not display_downward``;
  ``--up`` together with ``--down`` is rejected.
* ``--frame`` together with ``--size`` is rejected.
* ``--twobytes`` requires a TIFF extension.
* ``--movie`` together with ``--versions`` is rejected.
* ``--obj`` together with ``--pointers`` is rejected.
* Every color name (the ``colormap`` list plus ``below_color``,
  ``above_color``, ``invalid_color``, ``gap_color``, ``pad_color``) is
  validated through :meth:`picmaker.colornames.ColorNames.lookup`.

When a ``--versions`` file is present, ``validate_options`` calls
:func:`picmaker.picmaker.get_versions`, which re-parses each line of
the file (layering its overrides onto a fresh copy of the base
namespace via :func:`picmaker.parser.get_parser`) and recursively
validates each resulting option dict. Recursive ``--versions`` files
are rejected via the ``_versions_validated`` guard.

The orchestrator
~~~~~~~~~~~~~~~~

:func:`picmaker.picmaker.picmaker` is the top-level driver. It:

1. Sets the logger level from the ``logging`` option and re-runs
   :func:`~picmaker.picmaker.validate_options` (so library callers who
   bypass the CLI are still validated).
2. Resolves the input files with :func:`picmaker.control.get_filepaths`,
   which walks any input directories (honoring ``--recursive`` and the
   ``--pattern`` globs) and returns a list of ``(infile, outdir)``
   tuples. An empty result raises ``ValueError``.
3. Deletes the options that are fully handled at this level (``files``,
   ``directory``, ``recursive``, ``patterns``, ``movie``, ``logging``,
   ``versions``) so the remaining dict is safe to forward as
   ``**options``.
4. Dispatches to one of two modes.

**Movie mode** (``--movie``) runs :func:`~picmaker.picmaker.picmaker1`
twice per file. The first pass calls
``picmaker1(infile, '', options, return_limits=True)`` to read the
array and compute its limits without writing; the returned
``image_data`` is cached. After the loop the orchestrator sets
``options['limits']`` to the overall ``(min, max)`` and
``options['percentiles'] = None`` so every frame shares one stretch,
then loops again calling :func:`picmaker.control.get_outfile` and
``picmaker1(infile, outfile, options, image_data=image_data)`` to write
each frame from the cached read.

**Per-version mode** (the default) calls
:func:`~picmaker.picmaker.get_versions` to expand ``--versions`` into a
list of option dicts (a single-element list when no versions file is
given). For each input file it loops over the versions, calling
:func:`picmaker.control.get_outfile` and then
:func:`~picmaker.picmaker.picmaker1`. The ``image_data`` returned by
one version is threaded into the next so the file is read from disk only
once.

Both modes honor ``--proceed``: an exception on one file is logged and
skipped instead of aborting the run.

Path planning
~~~~~~~~~~~~~

:func:`picmaker.control.get_filepaths` resolves the input arguments
into ``(infile, outdir)`` pairs. Bare files map to their own parent
directory (or to ``--directory`` when given); directories are expanded,
recursively when ``--recursive`` is set, with basenames filtered by the
``--pattern`` globs (dot-files are always skipped). When ``--directory``
is given, the output tree mirrors the input subdirectory structure
underneath it.

:func:`picmaker.control.get_outfile` derives the output file path for
one input. It applies ``--strip`` / ``--suffix`` / ``--extension`` and
honors four ``replace=`` policies (``'all'`` — silent overwrite;
``'none'`` — return ``''`` to signal the loop should skip; ``'warn'`` —
overwrite and warn; ``'error'`` — raise :class:`OSError`). It creates
the parent directory tree if it does not already exist.

Per-image pipeline
~~~~~~~~~~~~~~~~~~

:func:`picmaker.picmaker.picmaker1` processes one input file into one
output image, running the phases shown in the flowchart:

1. If no cached ``image_data`` was passed, read the array with
   :func:`picmaker.instruments.read_image_array` (see the reader cascade
   below).
2. Slice out the region of interest with
   :func:`picmaker.slicing.slice_array`, which returns the 2-D or 3-D
   array plus an optional invalid-pixel mask.
3. Optionally fill zebra stripes with
   :func:`picmaker.processing.fill_zebra_stripes` when ``--zebra`` is
   set.
4. Choose the colormap path:

   a. **Mosaic path** — when ``--mosaic`` is set, the sliced array is
      still 3-D, and the ``image_data`` object defines
      :func:`!apply_mosaic`: compute limits per band with
      :func:`picmaker.stretch.get_limits`, apply the colormap per band
      with :meth:`ImageData.apply_colormap
      <picmaker.instruments.ImageData.apply_colormap>`, take the
      combined ``(min, max)`` across bands, and (unless
      ``return_limits`` short-circuits) assemble the panels with the
      instrument's :func:`!apply_mosaic`.
   b. **Standard path** — otherwise compute one set of limits with
      :func:`picmaker.stretch.get_limits` and apply the colormap once
      with :meth:`ImageData.apply_colormap
      <picmaker.instruments.ImageData.apply_colormap>`.

   In either path, when ``return_limits=True`` the function returns
   ``(image_data, limits)`` before writing anything — this is how the
   movie first pass collects limits.
5. Apply the display orientation with
   :func:`picmaker.orientation.rotate_rgb_array`, passing the
   instrument's ``default_upward`` and any ``--up`` / ``--rotation``
   override.
6. Plan the output size with :func:`picmaker.sizing.get_size`, convert
   to a PIL image with :func:`picmaker.pil_utils.array_to_pil`, apply
   the PIL filter with :func:`picmaker.processing.filter_pil_image`,
   resize with :func:`picmaker.sizing.resize_pil_image`, wrap with
   :func:`picmaker.layout.wrap_pil_image` when ``sections > 1``, and pad
   with :func:`picmaker.layout.pad_pil_image`.
7. Write the file with :func:`picmaker.pil_utils.write_pil`, which
   dispatches 16-bit output to :func:`picmaker.tiff16.write_tiff16` and
   everything else to :meth:`PIL.Image.Image.save`.

The function returns the ``image_data`` object (so the caller can reuse
the read), or ``(image_data, limits)`` when ``return_limits=True``.

The reader cascade
~~~~~~~~~~~~~~~~~~

:func:`picmaker.instruments.read_image_array` is the entry point. Given
a single path it delegates to the private
:func:`!picmaker.instruments._read_one_image_array`; given a list of
paths it reads each one and stacks the arrays along the leading band
axis with :func:`numpy.vstack`, inheriting the ``default_upward`` and
``default_tint`` of the first file.

:func:`!picmaker.instruments._read_one_image_array` tries each format in
turn against every registered instrument. Instruments live in the
``_INSTRUMENTS`` list, kept sorted by class name by
:func:`picmaker.instruments._register_instrument`; the always-accepting
fallback :class:`!picmaker.instruments.zzz_generic.ZZZ_Generic` sorts
last so it is only reached when no real instrument claims the file. The
stages are:

1. **PDS3 label** — taken when the path's suffix is ``.lbl``. The label
   is parsed with :class:`pdsparser.Pds3Label` (using the
   ``pds3_method`` option), then each instrument's
   :func:`!detect_in_pds3(label, filepath, **kwargs)` is tried.
2. **VICAR** — if :meth:`vicar.VicarImage.from_file` succeeds, each
   instrument's :func:`!detect_in_vicar(vic, filepath, **kwargs)` is
   tried.
3. **FITS** — if :func:`astropy.io.fits.open` succeeds, each
   instrument's :func:`!detect_in_fits(hdulist, filepath, **kwargs)` is
   tried. The pixels are copied out of the memory-mapped HDU before the
   enclosing ``with`` closes the file.
4. **Other formats** — each instrument's
   :func:`!detect_in_file(filepath, **kwargs)` is tried. The generic
   fallback handles attached-label PDS3 files, pickle, ``.npy``, 16-bit
   TIFF, and any PIL-readable image here.

Each ``detect_*`` method returns an
:class:`~picmaker.instruments.ImageData` subclass instance on a match or
``None`` to pass to the next instrument. If every stage is exhausted the
cascade raises :class:`OSError`.

The image container
~~~~~~~~~~~~~~~~~~~

:class:`picmaker.instruments.ImageData` is the base class every
instrument subclasses. It is constructed as
``ImageData(array, default_upward, default_tint)`` and carries the raw
pixel array, the display-direction default, and the per-image default
tint color. Its :meth:`~picmaker.instruments.ImageData.apply_colormap`
method forwards to :func:`picmaker.enhancement.apply_colormap` with the
instrument's ``default_tint``; an instrument overrides it only for a
non-standard colormap policy. Instruments that assemble multi-detector
mosaics additionally define an :func:`!apply_mosaic` method, checked via
:func:`hasattr` in :func:`~picmaker.picmaker.picmaker1`.

:func:`picmaker.instruments.tint_by_nm` maps a wavelength in nanometers
to an RGB tint via a tabulated color ramp; the HST readers use it to
derive a default tint from filter-name digits.

Enhancement helpers
~~~~~~~~~~~~~~~~~~~

:func:`picmaker.stretch.get_limits` chooses the stretch range. It
supports several strategies that can be combined:

* Explicit ``limits=(lo, hi)`` — passed through unchanged.
* ``percentiles=(lo%, hi%)`` — uses :func:`numpy.histogram` over the
  valid pixels and linear interpolation to find the corresponding DN
  values.
* ``trim=N`` — drop ``N`` pixels from each edge before computing.
* ``trim_zeros`` — peel all-zero exterior rows and columns before
  computing.
* ``footprint=D`` — apply a circular median filter (footprint diameter
  ``D``) and tighten the limits to the filter output.

:func:`picmaker.enhancement.apply_colormap` maps a stretched array to an
RGB (or single-channel grayscale) array using either a named
hyphen-separated colormap, a list of ``(R, G, B)`` tuples, or the
instrument's ``default_tint`` when ``tint=True`` and no explicit
colormap is given. It also applies the ``gamma`` power-law correction
and the out-of-range / invalid-pixel highlight colors.

:func:`picmaker.processing.fill_zebra_stripes` cleans up leading- and
trailing-zero artifacts in compressed spacecraft images.

Geometry and layout helpers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:func:`picmaker.slicing.slice_array` takes the raw
``(bands, lines, samples)`` array (or a 2-D array) and returns the
band-selected / band-merged array plus an optional invalid-pixel mask.
It honors the ``samples``, ``lines``, ``bands``, ``valid``, and
``crop`` slice arguments.

:func:`picmaker.orientation.rotate_rgb_array` applies the
``--rotation`` choice and the ``--up`` / ``--down`` override on top of
the instrument's ``default_upward``.

:func:`picmaker.sizing.get_size` is the resize planner. It returns
``(unwrapped_size, wrapped_size, sections, wrap_axis)``; the caller uses
``unwrapped_size`` to resize and the remaining fields to wrap (when
``sections > 1``).

:func:`picmaker.sizing.resize_pil_image`,
:func:`picmaker.layout.wrap_pil_image`, and
:func:`picmaker.layout.pad_pil_image` execute the plan against a PIL
image.

PIL bridges
~~~~~~~~~~~

:func:`picmaker.pil_utils.array_to_pil`,
:func:`picmaker.pil_utils.pil_to_array`, and
:func:`picmaker.pil_utils.write_pil` are the numpy ↔ PIL bridges.
:func:`~picmaker.pil_utils.write_pil` dispatches 16-bit output through
:func:`picmaker.tiff16.write_tiff16` and the 8-bit path through
:meth:`PIL.Image.Image.save`. :func:`picmaker.processing.filter_pil_image`
applies one of the named PIL filter presets to a PIL image.
</content>
</invoke>
