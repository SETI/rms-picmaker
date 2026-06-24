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
       A[picmaker CLI<br/>argv] --> B[cli.main]
       B --> C[_build_parser<br/>argparse]
       B --> D[_separate_files_and_dirs]
       B --> CO[_collect_option_dicts]
       CO --> E[_normalize_and_validate<br/>per --versions line]
       E --> F[PicmakerOptions.validate]
       B --> PD[_process_directory<br/>per dirpath, recursive or not]
       F --> G[process_images<br/>per directory]
       PD --> G
       G -->|movie=True| H[images_to_pics<br/>pass 1: collect limits]
       H --> I[images_to_pics<br/>pass 2: shared stretch]
       G -->|movie=False| J[images_to_pics<br/>per file]
       I --> K[_process_one_image]
       J --> K
       K --> L[get_outfile]
       L -->|skip if replace='none'| M[Done]
       L --> N[read_image_array]
       N --> O[read_one_image_array<br/>format cascade]
       O -->|.LBL / Pds3Label| NPI[instrument cascade<br/>PDS3-aware read_file]
       NPI -->|unrecognized label| NPF[read_pds3_image_array<br/>generic PDS3 fallback]
       O -->|other paths| P[pickle / numpy]
       P --> PI[instrument cascade<br/>read_file per ALL_INSTRUMENTS]
       PI --> PF[generic VICAR fallback]
       PF --> PG[generic FITS fallback]
       PG --> PH[PIL / 16-bit TIFF<br/>PDS3 auto-detect]
       PH --> Q[ReadResult<br/>array3d, default_is_up, filter_info]
       NPI --> Q
       NPF --> Q
       PI --> Q
       PF --> Q
       PG --> Q
       Q --> TINT{tint=True AND<br/>instrument has apply_tint?}
       TINT -->|yes| ATC[apply_tint<br/>custom RGB]
       TINT -->|no| MOS{mosaic=True AND<br/>instrument has apply_mosaic?}
       MOS -->|yes| AMC[apply_mosaic<br/>panel assembly RGB]
       MOS -->|no| T[slice_array]
       T --> U[fill_zebra_stripes<br/>optional]
       U --> V[get_limits]
       V --> W[apply_colormap]
       ATC --> X[rotate_array_rgb]
       AMC --> X
       W --> X
       X --> Y[apply_gamma]
       Y --> Z[get_size + array_to_pil]
       Z --> AA[filter_image]
       AA --> BB[resize_image]
       BB --> CC{sections > 1?}
       CC -->|yes| DD[wrap_image]
       CC -->|no| EE[skip wrap]
       DD --> FF{pad?}
       EE --> FF
       FF -->|yes| GG[pad_image]
       FF -->|no| HH[skip pad]
       GG --> II[write_pil]
       HH --> II
       II --> M

Three short observations on the diagram:

* The ``movie=True`` branch runs :func:`~picmaker.pipeline.images_to_pics`
  twice. The first pass computes the per-frame limits, the second
  pass uses the median of those limits so every frame shares one
  stretch.
* The ``apply_tint`` branch fires only when ``--tint`` is set and the
  instrument module defines :func:`!apply_tint`; it produces the final
  RGB array directly, bypassing :func:`~picmaker.enhance.apply_colormap`.
* The ``apply_mosaic`` branch fires only when ``--mosaic`` is set and
  the instrument module defines :func:`!apply_mosaic`; it handles
  multi-detector panel assembly (currently HST ACS/WFC two-panel and
  WFPC2 quad-panel composites).  Array extraction is split: the raw
  per-detector data is gathered by :func:`picmaker.instruments.hst.read_file`
  via its private :func:`!_extract_hst_array` helper, and
  :func:`!apply_mosaic` handles panel layout and colormap application.
* Both instrument hooks are checked after the ``apply_tint`` gate so
  that ``apply_tint`` takes priority when both are defined; the standard
  ``_band_to_rgb`` path runs when neither hook fires.


Major functions
---------------

This subsection walks through the major library functions in pipeline
order. Cross-references resolve to the :doc:`/module` reference; each
public symbol is a clickable link to its full signature, docstring,
and source code (via :mod:`sphinx.ext.viewcode`).

CLI entry point
~~~~~~~~~~~~~~~

:func:`picmaker.cli.main` is the function bound to the ``picmaker``
console script. It builds the argparse parser, splits ``args.files``
into files and directories with
:func:`!picmaker.cli._separate_files_and_dirs`, and delegates the two
remaining phases to two private helpers:
:func:`!picmaker.cli._collect_option_dicts` (the ``--versions FILE``
re-parse loop, returning one normalized option_dict per line) and
:func:`!picmaker.cli._process_directory` (the per-directory walk in
recursive or non-recursive mode). Each helper is unit-tested directly
in :file:`tests/test_cli_helpers.py`.

The library equivalent of "run the CLI from Python" is to import
:func:`picmaker.pipeline.images_to_pics` directly; the kwarg names
match the CLI flags one-to-one. The CLI does no I/O of its own —
every file operation flows through :mod:`picmaker.io`.

Option validation
~~~~~~~~~~~~~~~~~

:class:`picmaker.options.PicmakerOptions` is a frozen-by-convention
dataclass that holds the ~45 post-normalization knobs that drive the
pipeline. Its :meth:`~picmaker.options.PicmakerOptions.validate`
method runs every mutex / value-validity check that does not depend
on raw argparse fields:

* ``mosaic`` + ``bands`` is rejected (mosaic mode consumes every
  detector panel).
* ``frame`` + ``size`` is rejected (both specify output dimensions).
* ``frame`` + ``wrap_ratio`` is rejected (incompatible layout
  decisions).
* ``display_upward`` + ``display_downward`` is rejected.
* ``twobytes`` requires a TIFF extension and rejects any
  ``filter_name`` other than ``'NONE'``.
* ``pds3_label_method`` must be one of the values in
  :data:`~picmaker.options.PDS3_LABEL_METHODS`
  (``'strict'``, ``'loose'``, ``'compound'``, ``'fast'``); the value is
  forwarded as :class:`pdsparser.Pds3Label`'s ``method=`` argument when
  a PDS3 ``.LBL`` is parsed.

The CLI's :func:`!picmaker.cli._normalize_and_validate` does a few
more checks that are CLI-specific (band/bands mismatch,
``--scale`` + ``--wscale``, ``--overlap`` + ``--overlaps``,
``--movie`` + ``--versions``) because those operate on raw flags that
get collapsed before the dataclass is built. Adding a new mutex rule
that applies to both surfaces should go in
:meth:`~picmaker.options.PicmakerOptions.validate`.

The reader cascade
~~~~~~~~~~~~~~~~~~

:func:`picmaker.io.read_one_image_array` is the single-file reader.
It returns a :class:`~picmaker._types.ReadResult` triple on the first
format match and has two top-level branches depending on the input type.

**PDS3 label branch** — taken when *filename* is a
:class:`pdsparser.Pds3Label` object, or a path whose extension is
``.LBL`` / ``.lbl`` (auto-parsed at the top of the function).  The
cascade within this branch is:

1. **Per-instrument readers (PDS3-aware)** — iterates
   :data:`picmaker.instruments.ALL_INSTRUMENTS` and calls each
   instrument's :func:`!read_file` with the label object, ``obj``, and
   ``**kwargs``.  Instruments that support PDS3 (Cassini ISS, Voyager
   ISS, Galileo SSI, NH LORRI) detect the label's metadata and extract
   the data file; unrecognised instruments return ``None`` safely.
2. **Generic PDS3 fallback** —
   :func:`~picmaker.instruments._shared.read_pds3_image_array`, for
   labels not matched by any instrument.  Resolves the ``^IMAGE``
   pointer and reads via VICAR or FITS.  Returns ``filter_info=None``.

**Non-label cascade** — taken for all other paths.  Stages are tried in
order; each catches its specific exception type so an unrecognized file
falls through to the next:

1. **pickle** — :func:`pickle.load`, catches any exception.
2. **numpy** — :func:`numpy.load`, catches :class:`OSError` /
   :class:`ValueError`.
3. **per-instrument readers** — iterates
   :data:`picmaker.instruments.ALL_INSTRUMENTS` and calls each
   instrument's :func:`!read_file` as
   ``instrument.read_file(filename, obj, **kwargs)``.  The ``kwargs``
   dict is assembled in :func:`picmaker.pipeline._process_one_image`
   from the :class:`~picmaker.options.PicmakerOptions` fields named in
   :data:`picmaker.options.READ_FILE_KWARGS` (currently ``mosaic`` and
   ``pds3_label_method``).  Each instrument handles its own format
   detection (VICAR magic, FITS magic, file-extension heuristic, etc.)
   and returns :class:`~picmaker._types.ReadResult` on success or
   ``None`` to pass to the next instrument.  Shared format utilities
   live in :mod:`picmaker.instruments._shared`.
4. **generic VICAR fallback** — :meth:`vicar.VicarImage.from_file` with
   ``strict=False``, for VICAR files from instruments not yet in
   :data:`~picmaker.instruments.ALL_INSTRUMENTS`.  Returns
   ``filter_info=None``.
5. **generic FITS fallback** — sniffs the first 9 bytes for
   ``b'SIMPLE  ='`` before calling :func:`astropy.io.fits.open`, for
   FITS files from unrecognized instruments.  Warnings from astropy are
   promoted to exceptions by :class:`warnings.catch_warnings` +
   ``filterwarnings('error')`` and swallowed at the branch boundary.
   Returns ``filter_info=None``.
6. **PIL / 16-bit TIFF** — :func:`~picmaker.io.read_array`.
7. **PDS3 auto-detection** —
   :func:`~picmaker.io.read_pds_labeled_image_array` tries to parse the
   input file itself as a PDS3 label; if that fails and the extension is
   not ``.lbl``, it also checks for a sibling ``.lbl`` / ``.LBL`` file
   next to the data file.  Returns ``None`` (falls through to the final
   :class:`OSError`) if no parseable label is found.

The cascade-end :class:`OSError` is chained from an
:class:`ExceptionGroup` that carries every per-reader failure for
diagnostic purposes.

:func:`picmaker.io.read_image_array` is the multi-file wrapper: it
delegates to :func:`~picmaker.io.read_one_image_array` per file and
stacks the resulting arrays along the band axis with
:func:`numpy.vstack`. The combined result inherits the
``default_is_up`` and ``filter_info`` of the first file.

:func:`picmaker.io.read_pds_labeled_image_array` handles the PDS3
label / detached-data case. Pointer resolution lives here:
``^IMAGE = 2`` (attached integer offset), ``^IMAGE = "data.dat"``
(detached, full file), and ``^IMAGE = ("data.dat", 3)`` (detached
with record offset) are all distinct branches.

:func:`picmaker.io.read_pil` and :func:`picmaker.io.read_array` are
the Pillow-side helpers used by PIL-readable inputs and by
:func:`~picmaker.io.read_one_image_array`'s PIL branch.

Path planning
~~~~~~~~~~~~~

:func:`picmaker.io.get_outfile` derives the output file path for one
input. It honors four ``replace=`` policies (``'all'`` — silent
overwrite; ``'none'`` — return ``''`` to signal the loop should
skip; ``'warn'`` — overwrite and emit :class:`UserWarning`;
``'error'`` — raise :class:`OSError`). It creates the parent
directory tree if it does not already exist.

:func:`picmaker.pipeline.find_common_path` derives the recursive
output tree's root by calling :func:`os.path.commonpath` over the
input directories. The legacy hand-rolled version of this function
used ``/`` as a literal separator and was wrong on Windows; the
current implementation handles platform separators correctly and
returns ``''`` when the inputs share only the root.

Per-image pipeline
~~~~~~~~~~~~~~~~~~

:func:`picmaker.pipeline.images_to_pics` runs the per-image pipeline
shown in the flowchart above. The body is now a thin loop that builds
a :class:`~picmaker.options.PicmakerOptions`, backfills the legacy
``None``-means-default kwargs, and delegates each filename to
:func:`!picmaker.pipeline._process_one_image`. That helper runs the
following phases for one input file:

1. Build the output path (:func:`~picmaker.io.get_outfile`); skip if
   ``replace='none'`` returned ``''``.
2. Read the array (:func:`~picmaker.io.read_image_array`).  Paths
   ending in ``.LBL`` are auto-parsed inside
   :func:`~picmaker.io.read_one_image_array` and dispatched to the PDS3
   label branch of the reader cascade.  The caller's ``reuse`` tuple
   short-circuits the read for the single-file batches that
   :func:`process_images` builds per ``option_dict``.
3. Resolve the colormap: if ``tint=True``, ask
   :func:`picmaker.color.tinted_colormap` for a filter-specific colormap
   override; otherwise use the user's ``colormap`` option.
4. Run the instrument hooks, in priority order:

   a. If ``tint=True`` and the instrument module defines
      :func:`!apply_tint`, call it with ``(array3d, filter_info,
      options)``.  A non-``None`` return is the final RGB array.
   b. Else if ``mosaic=True`` and the instrument module defines
      :func:`!apply_mosaic`, call it with ``(array3d, filter_info,
      options, default_is_up=…, colormap=…, imagefile=…)``.  A
      non-``None`` return is the final RGB array and orientation is
      treated as already-baked (``this_display_upward`` is set to
      ``False``).
   c. Otherwise: slice (:func:`~picmaker.geometry.slice_array`),
      optionally fill zebra stripes
      (:func:`~picmaker.enhance.fill_zebra_stripes`), compute limits
      (:func:`~picmaker.enhance.get_limits`), apply the colormap
      (:func:`~picmaker.enhance.apply_colormap`).
5. Apply the orientation override
   (:func:`~picmaker.geometry.rotate_array_rgb`) and gamma
   (:func:`~picmaker.enhance.apply_gamma`).
6. Convert to a PIL image (:func:`~picmaker.pil_utils.array_to_pil`),
   apply the PIL filter (:func:`~picmaker._filters.filter_image`),
   resize (:func:`~picmaker.geometry.resize_image`), optionally wrap
   (:func:`~picmaker.geometry.wrap_image`), optionally pad
   (:func:`~picmaker.geometry.pad_image`).
7. Write (:func:`~picmaker.pil_utils.write_pil`), which dispatches
   16-bit output to :func:`picmaker.tiff16.write_tiff16` and
   everything else to :meth:`PIL.Image.Image.save`.

The function returns ``(low, high, reuse)`` so callers (or the
``--movie`` second pass) can either consume the limits or replay the
read.

The HST mosaic path (step 4b) delegates the panel-assembly geometry to
two private helpers in :mod:`picmaker.instruments.hst`:
:func:`!_wfpc2_mosaic` (four detectors, PC1/WF2/WF3/WF4 in a 2×2
quadrant) and :func:`!_acs_panel_mosaic` (two detectors, WFC1 above
and WFC2 below).  Both helpers are unit-tested directly in
:file:`tests/test_pipeline_helpers.py`.

:func:`picmaker.pipeline.process_images` is the thin loop that drives
:func:`~picmaker.pipeline.images_to_pics` per file; its only real
job is the movie-mode two-pass dance described above.

Enhancement helpers
~~~~~~~~~~~~~~~~~~~

:func:`picmaker.enhance.get_limits` is the most option-heavy function
in the codebase. It supports four ways of choosing the stretch range
that can be combined:

* Explicit ``limits=(lo, hi)`` — passed through unchanged.
* ``percentiles=(lo%, hi%)`` — uses :func:`numpy.histogram` over the
  valid pixels and linear interpolation to find the corresponding DN
  values.
* ``trim=N`` — drop ``N`` pixels from each edge before computing.
* ``trim_zeros=True`` — peel all-zero exterior rows and columns
  before computing.
* ``footprint=D`` — apply a circular median filter (footprint
  diameter ``D``) and tighten the limits to the filter output.

:func:`picmaker.enhance.apply_colormap` maps a 2-D stretched array to
a 3-D RGB array using either a named hyphen-separated colormap (e.g.
``'red-blue'``), a list of ``(R, G, B)`` tuples, or the per-instrument
tint from :func:`picmaker.color.tinted_colormap`. It also handles the
out-of-range and invalid-pixel highlight colors.

:func:`picmaker.enhance.apply_gamma` is the final power-law correction
(``array ** gamma``).

:func:`picmaker.enhance.fill_zebra_stripes` cleans up leading- and
trailing-zero artifacts in compressed spacecraft images. The
implementation is currently a Python pixel loop; vectorization is
tracked in `issue #18
<https://github.com/SETI/rms-picmaker/issues/18>`__.

Geometry helpers
~~~~~~~~~~~~~~~~

:func:`picmaker.geometry.slice_array` takes the raw 3-D
``(bands, lines, samples)`` array and returns a 2-D band-averaged
array plus an optional invalid-pixel mask. It honors ``samples``,
``lines``, ``bands``, ``valid``, and ``crop`` slice arguments.

:func:`picmaker.geometry.crop_array` strips constant-value borders
(typically ``crop=0`` for zero-padded fields). It returns the input
unchanged if the whole array equals the crop value.

:func:`picmaker.geometry.rotate_array_rgb` applies the
``--rotate {fliplr,fliptb,rot90,rot180,rot270}`` choice and the
``display_upward`` override.

:func:`picmaker.geometry.get_size` is the resize planner. It returns
``(unwrapped_size, wrapped_size, sections, wrap_axis)``; the caller
uses ``unwrapped_size`` to resize the image and the remaining three
fields to wrap it (when ``sections > 1``).

:func:`picmaker.geometry.resize_image`,
:func:`picmaker.geometry.wrap_image`, and
:func:`picmaker.geometry.pad_image` execute the plan against a PIL
image. :func:`~picmaker.geometry.resize_image` upscales with
``NEAREST`` and downscales with ``LANCZOS`` so the output is
pixel-art-friendly for small inputs and Lanczos-smoothed for large
ones.

Color, filter, and PIL bridges
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:func:`picmaker.color.tinted_colormap` is the entry point for
per-filter tinting. It normalizes HST's ``CL1`` / ``CL2`` /
``CLEAR*`` / ``N/A`` filter-tuple quirks, picks the right instrument
module via :func:`picmaker.instruments.lookup`, and delegates to its
``tint_for`` callable (e.g.
:func:`picmaker.instruments.cassini.tint_for`).

:func:`picmaker._filters.filter_image` applies one of the
:data:`picmaker._filters.FILTER_DICT` PIL presets to a PIL image,
or raises :class:`KeyError` if the case-folded filter name is not in
the dict.

:func:`picmaker.pil_utils.array_to_pil`,
:func:`picmaker.pil_utils.pil_to_array`, and
:func:`picmaker.pil_utils.write_pil` are the three numpy ↔ PIL
bridges. :func:`~picmaker.pil_utils.write_pil` dispatches 16-bit
output (list-of-three ``'I'``-mode images, or a single ``'I'``-mode
image) through :func:`picmaker.tiff16.write_tiff16` and the 8-bit
path through :meth:`PIL.Image.Image.save`.
