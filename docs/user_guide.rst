User Guide
==========

This guide takes a new user from "I have a PDS3, VICAR, or FITS file on
disk" to "I have a JPEG or TIFF".

.. contents::
   :local:
   :depth: 2


1. Overview
-----------

``rms-picmaker`` is a SETI / PDS Ring-Moon Systems Node tool that
converts binary 2-D and 3-D astronomy images into picture files
suitable for visual display. It accepts:

* PDS3-labeled images, with either attached or detached labels.
* VICAR images.
* FITS images.
* Pickled NumPy arrays and ``.npy`` files.
* Common raster formats: BMP, GIF, JPEG, PNG, plain TIFF.

It produces JPEG, PNG, BMP, GIF, or TIFF picture files (8-bit per
channel by default; 16-bit TIFF when ``--16`` is set).

``rms-picmaker`` ships as both a command-line tool (``picmaker``) and an
importable Python library (``import picmaker``). The CLI is the fastest
way to get a single image converted; the library lets you script
multi-file pipelines and embed the conversion inside larger tools.

The library entry point is ``picmaker``, which accepts the same
keyword arguments the CLI binds to, so any CLI invocation is exactly
equivalent to one library call.


2. Installation
---------------

Install from PyPI::

   pip install rms-picmaker

If you only need the command-line tool, ``pipx`` keeps it isolated from
your other Python environments::

   pipx install rms-picmaker

``rms-picmaker`` requires Python 3.12 or later.


3. Quick start
--------------

Convert one VICAR image to a JPEG::

   picmaker tests/fixtures/cassini_iss.vic --directory /tmp/out

The output file is written next to the input by default, or in
``--directory`` when given. Globbing across a tree is done by combining
``--recursive`` with ``--pattern``::

   picmaker --pattern '*.IMG' --recursive /path/to/data --directory /tmp/out

The full command-line reference is in section 4 below.

The same operation from Python:

.. code-block:: python

   from picmaker import picmaker
   from picmaker.options import get_parser

   options = get_parser().parse_args(
       ['tests/fixtures/cassini_iss.vic', '--directory', '/tmp/out'],
   )
   picmaker(**vars(options))


4. Command-line reference
-------------------------

The full list of options below is generated directly from the argument
parser, so it always matches the ``picmaker --help`` output exactly.

.. argparse::
   :module: picmaker.options
   :func: get_parser
   :prog: picmaker


5. Image processing details
---------------------------

This section expands on how ``picmaker``'s main options behave: the order in
which the processing pipeline applies them, the ``--versions`` multi-output
form, and the output-format controls.

Pipeline
~~~~~~~~

Regardless of the order in which they appear on the command line, the options
are applied to each image in the following order:

1. ``--zebra`` — interpolate across the zero-valued "zebra stripes" some
   detectors write at the start and end of each line.
2. ``--bands``, ``--lines``, ``--samples``, ``--crop`` — coadd the selected
   bands and reduce the array to the requested sub-region, optionally cropping constant
   borders.
3. ``--valid`` — mark pixels outside the valid range (and NaNs) as invalid,
   to be colored later, in step 8.
4. Only when ``--limits`` is *not* given, the stretch endpoints are derived
   from the pixel statistics: ``--trim``, ``--trim-zeros``, ``--footprint``,
   ``--percentiles``.
5. ``--histogram`` — use a flat-histogram stretch instead of the linear one.
6. ``--gamma`` — adjust the mid-level intensities relative to the extremes.
7. ``--colormap``, ``--tint``, ``--retint`` — map the stretched grayscale into
   RGB. ``--tint`` substitutes the per-instrument color
   (:ref:`section 6 <supported-instruments>`), and
   ``--retint`` scales the inferred filter wavelength for some instruments.
8. ``--above``, ``--below``, ``--invalid`` — apply the colors for above-limit,
   below-limit, and invalid pixels.
9. ``--up``, ``--down`` — set the vertical (line-number) direction.
10. ``--rotate`` — flip or rotate the image.
11. ``--filter`` — apply an optional image processing filter.
12. ``--size``, ``--scale``, ``--wscale``, ``--hscale``, ``--frame``,
    ``--frame_max`` — resize the image and fit it inside its designated frame.
13. ``--wrap``, ``--wrap-ratio``, ``--overlap``, ``--overlaps``, ``--gap-size``,
    ``--gap-color`` — wrap an elongated image if necessary.
14. ``--pad``, ``--pad-color`` — pad the output to the full frame.

The ``--versions FILE`` option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``--versions FILE`` re-parses the command line once per non-blank line
in ``FILE``, appending the line's tokens to the command for each run.
The same input file therefore produces one output per line, each with
its own suffix / quality / colormap / etc.

For example, ``two_versions.txt``::

   --suffix _v1 --extension jpg --quality 90
   --suffix _v2 --extension tif --16

paired with ``input.IMG`` produces ``input_v1.jpg`` and
``input_v2.tif`` in one read.

Lines starting with ``#`` and blank lines are skipped. Every
mutex / value-validity check the CLI performs fires per line, so an
invalid version doesn't abort the others (when combined with
``--proceed``).

Output formats and their controls
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``--extension`` (alias ``-x``) chooses the output container:

* ``bmp`` / ``dib`` — Windows Bitmap. 8-bit grayscale or 24-bit RGB;
  lossless.
* ``gif`` — GIF. 8-bit indexed; transparency not preserved.
* ``jpg`` / ``jpeg`` — JPEG. 8-bit RGB only; ``--quality 1..100``
  controls compression.
* ``png`` — PNG. 8-bit grayscale or 24-bit RGB; lossless.
* ``tif`` / ``tiff`` — TIFF. 8-bit by default. With ``--16`` the output
  is a 16-bit grayscale TIFF (or 16-bit RGB when the colormap path
  produced 3-channel data).

The output filename stem is built as
``<input-stem><suffix>.<extension>``, with ``--strip`` removing each of
its one-or-more substrings from ``<input-stem>``.


.. _supported-instruments:

6. Supported instruments and formats
------------------------------------

``rms-picmaker`` reads image data from PDS3 (attached or detached label),
VICAR, and FITS containers, as well as NumPy ``.npy`` files, pickled
arrays (``.pkl``), and the common raster formats (BMP, GIF, JPEG, PNG,
TIFF). Within the PDS3, VICAR, and FITS containers it automatically
recognizes a number of specific instruments; recognition drives the
per-instrument default orientation and, when ``--tint`` is enabled, a
per-filter tint color. Anything it does not recognize as a specific
instrument is handled by the generic reader described at the end of this
section.

When a PDS3 label points at more than one ``IMAGE`` object, ``--pointer``
selects which pointer(s) to follow.

Supported instruments:

* **Cassini ISS** — VICAR or PDS3.
* **Voyager ISS** — VICAR or PDS3.
* **Galileo SSI** — VICAR or PDS3.
* **HST ACS** (WFC / HRC / SBC) — FITS.
* **HST COS** — FITS.
* **HST FOC** — FITS.
* **HST NICMOS** — FITS.
* **HST STIS** — FITS.
* **HST WFC3** (UVIS / IR) — FITS.
* **HST WFPC** (WFPC1) — FITS.
* **HST WFPC2** — FITS.
* **New Horizons LORRI** — PDS3 or FITS.
* **New Horizons MVIC** — PDS3 or FITS.

The per-instrument subsections below add the detail that only applies
under ``--tint`` — which filter maps to which color. Instruments with a
single broadband channel, notably New Horizons LORRI and HST COS, are recognized
and oriented like any other but define no filter-based tint, so ``--tint``
leaves their coloring unchanged; use ``--colormap`` for explicit
pseudo-color. The generic reader is described last.

Cassini ISS
~~~~~~~~~~~

Recognized from VICAR labels for the Cassini Orbiter and the ISS instrument.
The default tint is chosen from the filter name:

* ``IR`` → reddish IR shading
* ``UV`` → violet
* ``VIO`` → violet
* ``BL`` → blue
* ``GRN`` → green
* ``RED`` → red
* ``MT1``, ``CB1``, ``HAL``, ``MT``, ``CB`` → narrowband methane /
  hydrogen-alpha shadings

The clear filters (``CL1`` and ``CL2``) are ignored when combined with a color
filter. Images involving both ``CL1`` or ``CL2`` fall back to neutral gray.

Voyager ISS
~~~~~~~~~~~

Recognized from Voyager VICAR labels. Supported filters and their tints:

* ``UV`` → (200, 60, 255)
* ``VIOLET`` → (200, 120, 255)
* ``BLUE`` → (110, 110, 255)
* ``GREEN`` → (110, 255, 110)
* ``ORANGE`` → (255, 170, 100)
* ``NAD`` → (110, 255, 110)
* ``SODIUM`` → (110, 255, 110)
* ``CH4_U`` / ``CH4/U`` → (255, 60, 60)
* ``CH4_JS`` / ``CH4/JS`` → (255, 60, 60)

The ``CLEAR`` filter falls back to neutral gray.

Galileo SSI
~~~~~~~~~~~

Recognized from Galileo SSI VICAR labels. Supported filters and their
tints:

* ``CLEAR`` → (128, 128, 128)
* ``RED`` → (190, 130, 100)
* ``GREEN`` → (110, 190, 110)
* ``VIOLET`` → (160, 100, 200)
* ``IR-7270`` → (200, 100, 100)
* ``IR-7560`` → (210, 80, 80)
* ``IR-8890`` → (220, 60, 60)
* ``IR-9680`` → (230, 40, 40)

HST Instruments
~~~~~~~~~~~~~~~~

Recognized from FITS headers. For most cameras the tint is derived from a wavelength
inferred by parsing the
digits out of the filter name and looking the result up in an internal color
table; the inferred wavelength is scaled by ``--retint`` (see its per-detector
default above) before the lookup, which maps IR and UV bands back into the
visible range.

Per-instrument wavelength handling:

* **ACS/HRC**, **ACS/WFC**, **FOC**, **STIS/CCD**, **WFC3/UVIS**, **WF/PC**, and
  **WFPC2**: The filter name is interpreted as a wavelength in nm (e.g.
  ``F606W`` → 606 nm) and the tint is derived from it. UV wavelengths map to a
  deep violet and IR wavelengths to a deep red. Very wide, clear, prism, polarizer,
  or neutral-density filters (e.g.
  ``CLEAR*``, ``POL*``, and ``*ND``) do not contribute to the tinting.
* **NICMOS** and **WFC3/IR**: For these IR instruments, wavelengths are scaled
  by 0.4 for the default tinting, so the color carries usable information.
* **ACS/SBC** and STIS/NUV, FUV: For these UV instrument, wavelengths are scaled
  by a factor of 3 to obtain tints in the visual range.
* **COS/NUV**: COS imaging uses a broadband mirror (``MIRRORA``/``MIRRORB``) with
  no wavelength filter, so no default tint is applied; use ``--colormap`` for
  false color.

For every HST camera, when no diagnostic wavelength can be inferred (an
undiagnostic or unrecognized filter or aperture), no tint is applied and the
existing colormap or grayscale is left in place.

HST exposures that span multiple detector panels can be reassembled into a
single image with ``--mosaic``. For WFPC2 and WF/PC this produces a 2x2
grid of the four detectors (for WFPC2 the PC1 image is placed at upper right and
is not re-sized relative to the others). For ACS/WFC and WFC3/UVIS, images
involving both chips are stacked one above the other.

New Horizons LORRI
~~~~~~~~~~~~~~~~~~

Recognized from New Horizons LORRI PDS3 labels and FITS headers. LORRI is
a panchromatic imager with a single broadband channel, so it defines no
per-filter tint: its images are recognized and oriented correctly, and
``--tint`` has no effect on them. Apply a ``--colormap`` explicitly to add
pseudo-color.

New Horizons MVIC
~~~~~~~~~~~~~~~~~

Recognized from New Horizons MVIC PDS3 labels and FITS headers. Supported
filters and their tints:

* ``BLUE`` → (110, 110, 210)
* ``RED`` → (190, 100, 100)
* ``NIR`` → (210, 65, 45)
* ``CH4`` → (230, 35, 35)

Generic reader
~~~~~~~~~~~~~~

Any image that none of the instruments above recognizes is handled by the
generic reader — the last stage in the detection cascade. It reads:

* Unrecognized **VICAR**, **PDS3** (attached or detached label), and
  **FITS** images — files in those containers that carry no identifiable
  instrument, or whose instrument ``rms-picmaker`` does not model.
* **NumPy** ``.npy`` files and **pickled** arrays (``.pkl``).
* **16-bit TIFFs**.
* Common raster formats read through Pillow: **BMP**, **GIF**, **JPEG**,
  **PNG**, and plain **TIFF**.

The generic reader carries no instrument knowledge, so:

* **No default tint.** ``default_tint`` is unset, so ``--tint`` has no
  effect; use ``--colormap`` to add color explicitly.
* **No instrument-specific orientation.** The default line direction is
  upward for FITS inputs (matching the FITS bottom-origin convention) and
  downward for everything else. Override it with ``--up`` / ``--down`` or
  ``--rotate``.

Every other option — the stretch, sizing, layout, and processing
controls — applies to generic inputs exactly as it does to a recognized
instrument.


7. Programmatic usage
---------------------

The library entry point is the :func:`~picmaker.picmaker.picmaker` function.
It accepts the same options as the command line, one keyword argument per
option, and carries out the whole conversion: resolving the input files,
reading and processing each one, and writing the output pictures. It returns
``None``; its result is the files it writes.

.. code-block:: python

   from picmaker import picmaker

   # Convert one file with a percentile stretch and a three-stop colormap.
   picmaker(
       files=['data/cassini.vic'],
       directory='/tmp/out',
       percentiles=(5, 95),
       colormap=['black', 'blue', 'white'],
       extension='png',
   )

Each keyword is the option's long name with dashes turned into underscores,
except for a few whose keyword differs from the flag: ``patterns``
(``--pattern``), ``obj`` (``--object``), ``pointers`` (``--pointer``),
``below_color`` / ``above_color`` / ``invalid_color`` (``--below`` /
``--above`` / ``--invalid``), ``display_upward`` / ``display_downward``
(``--up`` / ``--down``), and ``twobytes`` (``--16``). Every keyword is
optional; anything you omit takes its documented default. The
:func:`~picmaker.picmaker.picmaker` reference in :doc:`module` lists every
option in full.

Values follow ordinary Python conventions:

* Colors may be an X11 name (``'blue'``), an ``(R, G, B)`` tuple of integers
  in the range 0-255, or the string form of such a tuple (``'(0,0,255)'``).
* Paired options are tuples: ``percentiles=(5, 95)``, ``size=(800, 600)``,
  ``bands=(0, 3)``.
* Boolean flags are ``True`` / ``False``: ``tint=True``, ``movie=True``.

.. important::

   The image-object, band, line, and sample indices — ``obj``, ``band``,
   ``bands``, ``lines``, and ``samples`` — are **zero-based and exclusive** of
   the upper limit when you call :func:`~picmaker.picmaker.picmaker` directly,
   whereas the command line takes **one-based, inclusive** indices and
   converts them for you. The command line ``--bands 1 3`` therefore
   corresponds to ``bands=(0, 3)`` in a direct call.

Because the function takes every option at once, "movie" mode — sharing one
set of enhancement limits across a sequence of frames — is simply a matter of
passing all the frames together with ``movie=True``:

.. code-block:: python

   from picmaker import picmaker

   picmaker(
       files=['frame_001.vic', 'frame_002.vic', 'frame_003.vic'],
       directory='/tmp/out',
       movie=True,
   )

To reproduce a command-line invocation verbatim, let the argument parser build
the option namespace and splat it in. Note that this route skips the
one-based-to-zero-based index conversion the command line performs, so it
matches the CLI exactly only for invocations that use no ``obj``, ``band``,
``bands``, ``lines``, or ``samples`` indices:

.. code-block:: python

   from picmaker import picmaker
   from picmaker.options import get_parser

   options = get_parser().parse_args([
       'data/cassini.vic', '--directory', '/tmp/out',
       '--percentiles', '5', '95', '--extension', 'png',
   ])
   picmaker(**vars(options))

For finer-grained work, the lower-level helpers are re-exported on the
top-level package — for example, ``read_image_array`` reads a file into an
``ImageData`` object whose ``.array`` attribute holds the raw pixels. See
:doc:`module` for the full API reference.


8. Troubleshooting
------------------

* ``unrecognized file format in <path>`` — None of the supported readers
  recognized the file. Check the file is not truncated and that its
  magic bytes match one of the supported formats.
* When HST wavelength inference fails for a filter, no tint is applied
  and the existing colormap is preserved.
* ``--band and --bands options are incompatible`` — ``--band`` and
  ``--bands`` were both given. Use one or the other.
* ``--scale and --wscale options are incompatible`` (likewise
  ``--scale and --hscale``) — ``--scale`` sets both axes; use
  ``--wscale`` / ``--hscale`` instead for per-axis control.
* ``--frame and --size options are incompatible`` — ``--frame`` and
  ``--size`` both specify the output dimensions and can't be combined.
* ``only tiffs can be written in 16-bit mode`` — ``--16`` requires an
  explicit ``--extension tiff`` (or ``tif``).
* ``image filters are not supported for 2-byte images`` — The Pillow
  filter presets only work on 8-bit images; drop ``--filter`` when using
  ``--16``.
