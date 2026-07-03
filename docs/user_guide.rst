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
* Pickled NumPy arrays (``.pkl``) and ``.npy`` files.
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

``rms-picmaker`` requires Python 3.11 or later.


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
   from picmaker.parser import get_parser

   options = get_parser().parse_args(
       ['tests/fixtures/cassini_iss.vic', '--directory', '/tmp/out'],
   )
   picmaker(**vars(options))


4. Command-line reference
-------------------------

The full list of options below is generated directly from the argument
parser, so it always matches the ``picmaker --help`` output exactly.

.. argparse::
   :module: picmaker.parser
   :func: get_parser
   :prog: picmaker


5. Supported input formats
--------------------------

``rms-picmaker`` reads the following input formats:

* **PDS3 detached label** — a ``.LBL`` file pointing at one or more
  ``IMAGE`` objects in a sibling data file. ``--pointer`` chooses
  which pointer(s) to follow when more than one is present.
* **PDS3 attached label** — the label header precedes the image data
  in the same file.
* **VICAR** — including per-instrument variants (Cassini ISS, Voyager
  ISS, Galileo SSI). The instrument is recognized automatically from
  the label, which enables instrument-aware tinting (see section 6).
* **FITS** — including HST (WFC3, ACS, WFPC2, NICMOS) and New
  Horizons (LORRI, MVIC). HST mosaics across multiple detector panels are
  reconstructed with ``--mosaic``.
* **Pickled NumPy arrays** (``.pkl``) and **NumPy** ``.npy`` files.
* **Common raster formats** — BMP, GIF, JPEG, PNG, plain TIFF.


6. Supported instruments
------------------------

``rms-picmaker`` automatically recognizes images from the instruments
listed below, reading the instrument identity from the file's VICAR
label, PDS3 label, or FITS header. Recognition drives the per-instrument
default orientation and, when ``--tint`` is enabled, a per-filter tint
color.

Supported instruments:

* **Cassini ISS** — VICAR or PDS3.
* **Voyager ISS** — VICAR or PDS3.
* **Galileo SSI** — VICAR or PDS3.
* **HST ACS** (WFC / HRC / SBC) — FITS.
* **HST WFC3** (UVIS / IR) — FITS.
* **HST WFPC2** — FITS.
* **HST NICMOS** — FITS.
* **New Horizons LORRI** — PDS3 or FITS.
* **New Horizons MVIC** — PDS3 or FITS.
* **Generic reader** — the fallback for any image no instrument above
  claims: unrecognized VICAR, PDS3, or FITS files, plus ``.npy`` and
  ``.pkl`` arrays, 16-bit TIFFs, and the common raster formats (BMP, GIF,
  JPEG, PNG, TIFF).

Every instrument above is fully supported as an input. The per-instrument
subsections below add the detail that only applies under ``--tint`` —
which filter maps to which color. Instruments with a single broadband
channel, notably New Horizons LORRI, are recognized and oriented like any
other but define no filter-based tint, so ``--tint`` leaves their coloring
unchanged; use ``--colormap`` for explicit false color. The generic
reader, described last, is the catch-all for everything else.

Cassini ISS
~~~~~~~~~~~

Recognized from VICAR labels for the Cassini Orbiter. Filters are
selected from the ``FILTER_NAME`` tuple joined with ``'+'`` (e.g.
``CL1+GRN``). The tint is chosen by a chain of substring tests on the
filter key:

* ``IR`` → reddish IR shading
* ``UV`` → violet
* ``VIO`` → violet
* ``BL`` → blue
* ``GRN`` → green
* ``RED`` → red
* ``MT1``, ``CB1``, ``HAL``, ``MT``, ``CB`` → narrowband methane /
  hydrogen-alpha shadings

Unknown filters fall back to neutral gray.

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

HST (WFC3 / ACS / WFPC2 / NICMOS)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Recognized from FITS headers. The tint is derived from a wavelength
inferred by parsing the digits out of the filter name and looking the
result up in an internal color table. The inferred wavelength is then
scaled by ``--retint`` (see its per-detector default above) before the
lookup; this is what maps IR and UV bands back into the visible range.

Per-detector wavelength handling:

* **ACS** (WFC / HRC / SBC): the wavelength is the mean of the digits in
  ``FILTER1`` / ``FILTER2`` (e.g. ``F606W`` → 606 nm), read directly as nm
  and scaled by the retint default (``1``, or ``3`` for the UV-only SBC).
  Filters matching ``CLEAR*``, ``POL*``, ``G800L``, or ``N/A`` carry no
  diagnostic wavelength and are left untinted.
* **WFC3/UVIS**: the filter digits are read directly as nm (``F606W`` → 606
  nm), scaled by the retint default ``1``.
* **WFC3/IR**: IR filter names encode wavelength / 10 (``F160W`` → 1600 nm),
  so the digits are multiplied by 10 and then by the retint default ``0.4``.
  The broad long-pass filters ``F200LP`` and ``F350LP`` are left untinted.
* **NICMOS**: filter names likewise encode wavelength / 10, so the digits
  are multiplied by 10 and then by the retint default ``0.4`` (``F187N`` →
  1870 nm → 748 nm). Polariser filters (``POL*``) are left untinted.
* **WFPC2**: the wavelength is the mean of the digits in ``FILTNAM1`` /
  ``FILTNAM2``, with the ``FQUVN`` quad filter pinned to 387 nm; ``--retint``
  is not applied. Filters matching ``F130LP``, ``F165LP``, ``F606W``,
  ``FQCH4*``, or ``POL*`` are left untinted, and only calibrated science
  products (``*_c0f`` / ``*_d0f``) are tinted at all.

For every HST detector, when no diagnostic wavelength can be inferred (an
undiagnostic or unrecognized filter), no tint is applied and the existing
colormap or grayscale is left in place.

New Horizons LORRI
~~~~~~~~~~~~~~~~~~

Recognized from New Horizons LORRI PDS3 labels and FITS headers. LORRI is
a panchromatic imager with a single broadband channel, so it defines no
per-filter tint: its images are recognized and oriented correctly, and
``--tint`` has no effect on them. Apply a ``--colormap`` explicitly to add
false color.

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


7. Output formats and their controls
------------------------------------

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


8. Enhancement controls
-----------------------

The intensity pipeline runs in this order:

1. ``--valid LO HI`` masks pixels outside the range (replaced with
   ``--invalid`` color).
2. ``--limits`` or ``--percentiles`` chooses the linear stretch
   endpoints (``--limits`` wins when both are set). ``--trim`` /
   ``--trim-zeros`` / ``--footprint`` further refine which pixels are
   considered.
3. ``--histogram`` switches the stretch from linear to
   flat-histogram-equalised.
4. ``--gamma G`` applies a power-law correction to the stretched
   grayscale (``out = in ** G``) before the colormap is applied. Values
   ``> 1`` darken the midtones; values ``< 1`` brighten them.
5. ``--colormap COLOR ...`` maps the stretched values into RGB. Supply
   one or more X11 color names (or ``(R,G,B)`` tuples) as separate color
   stops. ``--tint`` overrides this step with the per-instrument tint
   from section 6.
6. ``--below``, ``--above``, ``--invalid`` override the colors used for
   the three special cases.


9. Geometry controls
--------------------

Geometry runs in this order:

1. ``--lines`` / ``--samples`` / ``--crop`` / ``--trim`` shrink the
   working region.
2. ``--rotate`` (or the implicit default from the per-instrument
   detector geometry) flips / rotates the working array.
3. ``--size`` / ``--scale`` / ``--wscale`` / ``--hscale`` resize the
   working array. ``--frame W H`` instead picks the largest scale that
   fits inside ``W x H``; ``--frame_max PCT`` caps how far the image
   may be enlarged.
4. ``--wrap`` / ``--wrap-ratio`` / ``--overlap`` / ``--overlaps`` split
   very elongated images into stacked panels separated by a
   ``--gap-size`` × ``--gap-color`` gap.
5. ``--pad`` re-introduces the full ``--frame`` box, filling with
   ``--pad-color``.


10. The ``--versions FILE`` form
--------------------------------

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


11. Programmatic usage
----------------------

The library mirrors the CLI: every flag binds to a keyword argument of
``picmaker``. The most robust way to assemble a complete set of options
is to let the argument parser fill in all of the defaults, then pass the
resulting namespace straight through:

.. code-block:: python

   from picmaker import picmaker
   from picmaker.parser import get_parser

   # Convert one file with a percentile stretch and a colormap.
   options = get_parser().parse_args([
       'data/cassini.vic',
       '--directory', '/tmp/out',
       '--percentiles', '5', '95',
       '--colormap', 'black', 'blue', 'white',
       '--extension', 'png',
   ])
   picmaker(**vars(options))

   # Re-use one set of enhancement limits across a sequence of frames by
   # passing every frame at once with ``--movie``.
   options = get_parser().parse_args([
       'frame_001.vic', 'frame_002.vic', 'frame_003.vic',
       '--directory', '/tmp/out',
       '--movie',
   ])
   picmaker(**vars(options))

Lower-level helpers are re-exported on the top-level package. For example,
``read_image_array`` reads a file into an ``ImageData`` object whose
``.array`` holds the raw pixels:

.. code-block:: python

   from picmaker import (
       read_image_array,
       apply_colormap,
       array_to_pil,
   )

   image_data = read_image_array('data/cassini.vic')
   pixels = image_data.array

See :doc:`module` for the full API reference.


12. Troubleshooting
-------------------

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
