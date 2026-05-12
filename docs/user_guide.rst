User Guide
==========

This guide takes a new user from "I have a PDS3, VICAR, or FITS file on
disk" to "I have a JPEG or TIFF" without reading the source code.

.. contents::
   :local:
   :depth: 2


1. Overview
-----------

``rms-picmaker`` is a SETI / PDS Rings Node tool that converts binary
2-D and 3-D astronomy images into picture files suitable for visual
display. It accepts:

* PDS3 detached-label images (``.LBL`` + ``.IMG`` pair, or any image
  whose attached PDS3 label points at an ``IMAGE`` object), via
  `rms-pdsparser <https://github.com/SETI/rms-pdsparser>`_.
* VICAR images, via `rms-vicar <https://github.com/SETI/rms-vicar>`_.
* FITS images, via `astropy.io.fits
  <https://docs.astropy.org/en/stable/io/fits/>`_.
* Pickled NumPy arrays (``.pkl``) and ``.npy`` files.
* Any raster format that Pillow's :class:`PIL.Image` can open (BMP,
  GIF, JPEG, PNG, TIFF, …).

It produces:

* JPEG, PNG, BMP, GIF, or TIFF picture files (8-bit per channel by
  default; 16-bit TIFF when ``--16`` is set).

``rms-picmaker`` ships as both a command-line tool (``picmaker``) and
an importable Python library (``import picmaker``). The CLI is the
fastest way to get a single image converted; the library lets you
script multi-file pipelines and embed the conversion inside larger
tools.

The library entry-point :func:`picmaker.images_to_pics` accepts the
same keyword arguments the CLI binds to, so any CLI invocation is
exactly equivalent to one library call.


2. Installation
---------------

End users::

   pip install rms-picmaker

Developers should set up a venv as the project's other scripts expect::

   python -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"

The ``[dev]`` extra pulls in ``pytest``, ``ruff``, ``mypy``,
``pymarkdownlnt``, ``pip-audit``, ``pyroma``, and the docs extras
(Sphinx + sphinx-rtd-theme).

``rms-picmaker`` requires Python 3.11 or later, and depends on
``numpy``, ``scipy``, ``pillow``, ``astropy``, and the SETI sibling
packages ``rms-pdsparser``, ``rms-tabulation``, and ``rms-vicar``.


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

   from picmaker import images_to_pics

   images_to_pics(
       ['tests/fixtures/cassini_iss.vic'],
       directory='/tmp/out',
   )


4. Command-line reference
-------------------------

The flag groups below mirror the ``picmaker --help`` output exactly.
For each flag the ``dest`` column is the attribute name on the parsed
:class:`argparse.Namespace` and the keyword argument forwarded to
:func:`picmaker.pipeline.images_to_pics`.

Control options
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 22 14 14 50

   * - Flag
     - dest
     - Default
     - Effect
   * - ``--directory DIR``
     - ``directory``
     - input dir
     - Output directory. Required when ``--recursive`` is set.
   * - ``-r``, ``--recursive``
     - ``recursive``
     - ``False``
     - Descend into directory trees, mirroring the input layout under
       ``--directory``.
   * - ``--pattern PATTERN``
     - ``pattern``
     - ``'*'``
     - Glob filter applied to file names during recursion.
   * - ``--movie``
     - ``movie``
     - ``False``
     - Share one set of enhancement limits across every input.
       Incompatible with ``--hst``.
   * - ``--versions FILE``
     - ``versions``
     - ``None``
     - For each non-blank line in ``FILE``, re-parse the CLI with that
       line appended to ``sys.argv`` and run the resulting pipeline.
       Produces one output per non-blank line.
   * - ``--verbose N``
     - ``verbose``
     - ``0``
     - ``1`` prints each directory in a recursive walk; ``2`` prints
       every file path.
   * - ``--replace POLICY``
     - ``replace``
     - ``'all'``
     - One of ``all`` (silent overwrite), ``none`` (skip silently),
       ``warn`` (overwrite + ``UserWarning``), ``error`` (raise
       ``OSError``).
   * - ``--proceed``
     - ``proceed``
     - ``False``
     - On a per-file error, log the traceback and continue with the
       remaining inputs instead of aborting.

Output options
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 22 14 14 50

   * - Flag
     - dest
     - Default
     - Effect
   * - ``-x EXT``, ``--extension EXT``
     - ``extension``
     - ``jpg`` (``tiff`` if ``--16``)
     - Output file format. Choices: ``bmp``, ``dib``, ``gif``, ``jpg``,
       ``jpeg``, ``png``, ``tif``, ``tiff`` (any-case).
   * - ``-s STR``, ``--suffix STR``
     - ``suffix``
     - ``''``
     - Inserted between the file stem and ``.<ext>``.
   * - ``--strip STR``
     - ``strip``
     - ``''``
     - Substring to remove from the output filename's stem before
       appending the suffix.
   * - ``--alt-strip STR``, ``--alt_strip STR``
     - ``alt_strip``
     - ``None``
     - Additional substring to strip; both ``--strip`` and
       ``--alt-strip`` apply.
   * - ``-q N``, ``--quality N``
     - ``quality``
     - ``75``
     - JPEG quality, 1-100. Ignored for non-JPEG outputs.
   * - ``--16``
     - ``twobytes``
     - ``False``
     - Emit a 16-bit grayscale or 16-bit RGB TIFF. Forces
       ``--extension`` to ``tiff`` when unset. Incompatible with
       ``--filter`` (16-bit filters are not supported).

Selection options
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 22 14 14 50

   * - Flag
     - dest
     - Default
     - Effect
   * - ``-b N``, ``--band N``
     - ``band``
     - ``0``
     - Select a single band from a 3-D array. Incompatible with
       ``--bands`` (except when ``band == bands[0] == bands[1]``).
   * - ``--bands LO HI``
     - ``bands``
     - ``(band, band+1)``
     - Average bands ``LO..HI-1`` (Python half-open range).
   * - ``--rectangle S1 L1 S2 L2``
     - ``rectangle``
     - ``None``
     - Sub-region selection: sample / line corners. Converted to
       half-open ``samples`` / ``lines`` slices internally.
   * - ``-o N``, ``--object N``
     - ``obj``
     - first valid
     - Index of the PDS object to read when a file contains multiple
       image objects.
   * - ``--pointer PTR``
     - ``pointer``
     - ``'IMAGE'``
     - PDS pointer name (without leading ``^``) identifying the image
       object in a detached label.
   * - ``--alt-pointer PTR``, ``--alt_pointer PTR``
     - ``alt_pointer``
     - ``None``
     - Fallback pointer tried when ``--pointer`` is not in the label.

Sizing options
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 22 14 14 50

   * - Flag
     - dest
     - Default
     - Effect
   * - ``--size W H``
     - ``size``
     - ``None``
     - Force output dimensions in pixels. Incompatible with
       ``--frame``.
   * - ``--scale PCT``
     - ``scale``
     - ``100``
     - Uniform percentage scale. Incompatible with ``--wscale`` /
       ``--hscale``.
   * - ``--wscale PCT``
     - ``wscale``
     - ``--scale`` value
     - Horizontal-only percentage scale.
   * - ``--hscale PCT``
     - ``hscale``
     - ``--scale`` value
     - Vertical-only percentage scale.
   * - ``--crop VALUE``
     - ``crop``
     - ``None``
     - Crop outer rows / columns whose every pixel equals ``VALUE``
       (typically used to trim CCD frames of zeros).
   * - ``--frame W H``
     - ``frame``
     - ``None``
     - Fit the image inside a ``W x H`` box, preserving aspect ratio.
       Incompatible with ``--size`` and ``--wrap-ratio``.
   * - ``--pad``
     - ``pad``
     - ``False``
     - When set with ``--frame``, pad the output to the full frame
       size; otherwise the output is cropped to content.
   * - ``--pad-color NAME``
     - ``pad_color``
     - ``'black'``
     - Padding fill color (any X11 name from
       :class:`picmaker.colornames.ColorNames` or ``#RRGGBB``).
   * - ``--frame_max PCT``
     - ``frame_max``
     - ``None``
     - When set with ``--frame``, the up-scaling is capped at this
       percentage of the input size (prevents up-scaling a tiny image
       to fill a large frame).

Layout options
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 22 14 14 50

   * - Flag
     - dest
     - Default
     - Effect
   * - ``--wrap``
     - ``wrap``
     - ``False``
     - Split very elongated images into stacked sections.
   * - ``--wrap-ratio R``
     - ``wrap_ratio``
     - ``None``
     - Wrap when ``max(W, H) / min(W, H) > R``. Incompatible with
       ``--frame``.
   * - ``--overlap PCT``
     - ``overlap``
     - ``0``
     - Per-section overlap percentage (single value).
       Incompatible with ``--overlaps``.
   * - ``--overlaps LO HI``
     - ``overlaps``
     - ``None``
     - Range of overlap percentages explored to pick the best fit.
   * - ``--gap-size N``, ``--gapsize N``
     - ``gap_size``
     - ``1``
     - Width in pixels of the gap drawn between wrapped sections.
   * - ``--gap-color NAME``, ``--gapcolor NAME``
     - ``gap_color``
     - ``'white'``
     - Gap color (X11 name or ``#RRGGBB``).
   * - ``--hst``
     - ``hst``
     - ``False``
     - Construct a mosaic from all HST detector panels (ACS/WFC,
       WFPC2). Incompatible with ``--band`` / ``--bands`` /
       ``--movie``.

Scaling options (histogram and intensity controls)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 22 14 14 50

   * - Flag
     - dest
     - Default
     - Effect
   * - ``-v LO HI``, ``--valid LO HI``
     - ``valid``
     - ``None``
     - Pixels outside ``[LO, HI]`` are treated as invalid (filled with
       ``--invalid`` color, excluded from the histogram).
   * - ``-l LO HI``, ``--limits LO HI``
     - ``limits``
     - ``None``
     - Force the histogram stretch endpoints. Overrides
       ``--percentiles``.
   * - ``-p LO HI``, ``--percentiles LO HI``
     - ``percentiles``
     - ``(0, 100)``
     - Percentile cut for the histogram stretch. Used when ``--limits``
       is not set.
   * - ``--trim N``
     - ``trim``
     - ``0``
     - Pixels at the image edge to ignore when computing the histogram.
   * - ``--trim-zeros``, ``--trimzeros``
     - ``trim_zeros``
     - ``False``
     - Ignore exterior rows / columns that are entirely zero (CCD
       overscan cleanup).
   * - ``--footprint D``
     - ``footprint``
     - ``0``
     - Diameter in pixels of a circular footprint passed to the
       ``scipy.ndimage`` median filter used to compute the histogram.
   * - ``--histogram``
     - ``histogram``
     - ``False``
     - Use a flat-histogram stretch instead of the linear stretch.

Enhancement options
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 22 14 14 50

   * - Flag
     - dest
     - Default
     - Effect
   * - ``-c NAME``, ``--colormap NAME``
     - ``colormap``
     - ``None``
     - Apply a named colormap (e.g. ``black-white``,
       ``red-blue``, ``black-blue-white``). Names are hyphen-separated
       lists of stops resolved via :class:`~picmaker.colornames.ColorNames`.
   * - ``--below COLOR``
     - ``below_color``
     - ``None``
     - Colour used for pixels below the lower limit.
   * - ``--above COLOR``
     - ``above_color``
     - ``None``
     - Colour used for pixels above the upper limit.
   * - ``--invalid COLOR``
     - ``invalid_color``
     - ``'black'``
     - Colour used for invalid pixel values and NaNs.
   * - ``-g G``, ``--gamma G``
     - ``gamma``
     - ``1.0``
     - Power-law correction applied to the grayscale axis.
   * - ``--tint``
     - ``tint``
     - ``False``
     - Override the colormap with the per-instrument tint inferred
       from the filter name. See section 6.

Orientation options
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 22 14 14 50

   * - Flag
     - dest
     - Default
     - Effect
   * - ``-u``, ``--up``
     - ``display_upward``
     - ``False``
     - Force the image to be drawn with line numbers increasing upward
       (overrides per-instrument default).
   * - ``-d``, ``--down``
     - ``display_downward``
     - ``False``
     - Force line numbers increasing downward. Incompatible with
       ``--up``.
   * - ``--rotate KIND``
     - ``rotate``
     - ``'none'``
     - One of ``none``, ``fliplr``, ``fliptb``, ``rot90``, ``rot180``,
       ``rot270`` (any-case).

Processing options
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 22 14 14 50

   * - Flag
     - dest
     - Default
     - Effect
   * - ``-f NAME``, ``--filter NAME``
     - ``filter``
     - ``'none'``
     - One of the PIL :class:`PIL.ImageFilter` presets (``blur``,
       ``contour``, ``detail``, ``edge_enhance``, ``edge_enhance_more``,
       ``emboss``, ``find_edges``, ``smooth``, ``smooth_more``,
       ``sharpen``, ``median_<n>``, ``minimum_<n>``, ``maximum_<n>``
       for ``n`` in 3, 5, 7), plus ``none``. Any-case.
   * - ``--zebra``
     - ``zebra``
     - ``False``
     - Interpolate across the black "zebra stripes" some legacy
       detectors put at the start and end of each line.


5. Supported input formats
--------------------------

The reader cascade in :func:`picmaker.io.read_one_image_array` tries
each of the following in order. The first to succeed wins; failures
fall through silently.

1. **Pickle** (``pickle.load``). Detected by the standard pickle magic
   bytes. Reading raises any exception the pickle stream produces; on
   failure the cascade moves on.
2. **NumPy ``.npy``** (``numpy.load``). Detected by NumPy's own magic
   bytes. On failure (corrupt file or unsupported dtype) the cascade
   moves on.
3. **VICAR** (``vicar.VicarImage``). Detected by the ``LBLSIZE`` magic
   string in the first few bytes. The cascade iterates the registered
   VICAR instruments (Cassini, Galileo, Voyager) calling each one's
   ``detect_vicar`` predicate; the first match returns
   ``(inst_host, inst_id, filter_name)``.
4. **FITS** (``astropy.io.fits.open``). Detected by the ``SIMPLE =``
   magic at byte offset 0. The cascade iterates the registered FITS
   instruments (HST, New Horizons) calling each one's ``detect_fits``
   predicate.
5. **Pillow** (``PIL.Image.open``). Used for BMP / GIF / JPEG / PNG /
   plain TIFF inputs.
6. **PDS3 detached label** (``rms-pdsparser``). Used when the input is
   a ``.LBL`` file, or when an attached PDS3 label is detected; the
   ``^IMAGE`` pointer (or ``--pointer`` / ``--alt-pointer``) identifies
   the embedded image object.

When every reader fails the function raises
``OSError('Unrecognized image file format')`` with the source filename
in the message.

The reader returns a triple ``(array3d, default_is_up, filter_info)``
where:

* ``array3d`` is the image as a ``(bands, lines, samples)`` NumPy
  array;
* ``default_is_up`` reflects the per-instrument default orientation
  (used when neither ``--up`` nor ``--down`` is given);
* ``filter_info`` is ``(inst_host, inst_id, filter_name)`` or
  ``None`` when no registered instrument matched.

The ``filter_info`` triple is what :func:`picmaker.color.tinted_colormap`
uses to pick a per-filter colormap.


6. Supported instruments and filters
------------------------------------

Cassini ISS
~~~~~~~~~~~

Detected via :func:`picmaker.instruments.cassini.detect_vicar`, which
matches VICAR labels with ``INSTRUMENT_HOST_NAME == 'CASSINI ORBITER'``
and reads the 2-element ``FILTER_NAME`` tuple. The two filter names
are joined with ``'+'`` to form the lookup key.

The tint is produced by a chain of substring tests (in declaration
order): ``IR``, ``UV``, ``VIO``, ``BL``, ``GRN``, ``RED``, ``MT1``,
``CB1``, ``HAL``, ``MT``, ``CB``. The first match wins; unknown
filters fall back to grey ``(127, 127, 127)``.

A worked example: ``FILTER_NAME == ('CL1', 'GRN')`` produces the
filter key ``'CL1+GRN'``. The chain finds ``'GRN'`` (the ``BL`` branch
fails because there is no ``BL`` substring) and the second clause of
the ``GRN`` branch returns ``(110, 190, 110)`` because ``'RED'`` is
not in the key.

.. image:: _static/user_guide/cassini_iss_tint.jpg
   :alt: Cassini ISS thumbnail rendered with --tint

Voyager ISS
~~~~~~~~~~~

Detected via :func:`picmaker.instruments.voyager.detect_vicar`, which
matches VICAR labels with ``LAB02[:3] == 'VGR'``; the filter name is
taken from characters 37..43 of ``LAB03`` (stripped of trailing
spaces). The full table:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Filter
     - Tint (R, G, B)
   * - ``UV``
     - (200, 60, 255)
   * - ``VIOLET``
     - (200, 120, 255)
   * - ``BLUE``
     - (110, 110, 255)
   * - ``GREEN``
     - (110, 255, 110)
   * - ``ORANGE``
     - (255, 170, 100)
   * - ``NAD``
     - (110, 255, 110)
   * - ``SODIUM``
     - (110, 255, 110)
   * - ``CH4_U`` / ``CH4/U``
     - (255, 60, 60)
   * - ``CH4_JS`` / ``CH4/JS``
     - (255, 60, 60)

.. image:: _static/user_guide/voyager_iss_tint.jpg
   :alt: Voyager ISS thumbnail rendered with --tint

Galileo SSI
~~~~~~~~~~~

Detected via :func:`picmaker.instruments.galileo.detect_vicar`. Two
label conventions are tried in order:

1. ``MISSION == 'GALILEO'`` with a numeric ``FILTER`` index into the
   declaration-order array
   ``['CLEAR', 'GREEN', 'RED', 'VIOLET', 'IR-7560', 'IR-9680',
   'IR-7270', 'IR-8890']``.
2. ``LAB01[:7] == 'GLL/SSI'`` with ``FILTER=<digit>`` somewhere in
   ``LAB03`` (the digit indexes the same array).

The filter dictionary:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Filter
     - Tint (R, G, B)
   * - ``CLEAR``
     - (128, 128, 128)
   * - ``RED``
     - (190, 130, 100)
   * - ``GREEN``
     - (110, 190, 110)
   * - ``VIOLET``
     - (160, 100, 200)
   * - ``IR-7270``
     - (200, 100, 100)
   * - ``IR-7560``
     - (210, 80, 80)
   * - ``IR-8890``
     - (220, 60, 60)
   * - ``IR-9680``
     - (230, 40, 40)

.. image:: _static/user_guide/galileo_ssi_tint_a.jpg
   :alt: Galileo SSI thumbnail (variant a) rendered with --tint
.. image:: _static/user_guide/galileo_ssi_tint_b.jpg
   :alt: Galileo SSI thumbnail (variant b) rendered with --tint

HST (WFC3 / ACS / WFPC2 / NICMOS)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Detected via :func:`picmaker.instruments.hst.detect_fits` from the
FITS keywords ``TELESCOP``, ``INSTRUME``, and (optionally)
``DETECTOR``. The filter name comes from one of ``FILTER``,
``FILTER1``/``FILTER2``, or ``FILTNAM1``/``FILTNAM2`` — whichever is
present last in that order.

The tint color is derived from the wavelength inferred by parsing the
digits out of the filter name (e.g. ``'F606W'`` → 606 nm) and looking
that wavelength up in the
:data:`picmaker._rgb.RGB_BY_NM` CIE-style table via the
:data:`picmaker._rgb.RFUNC` / :data:`picmaker._rgb.GFUNC` /
:data:`picmaker._rgb.BFUNC` splines.

Per-detector adjustments:

* **NICMOS** scales the inferred number by 3.5 (NICMOS filter names
  encode tens of nm, not nm).
* **WFC3/IR** and **ACS/SBC** scale by 3.5 when the inferred number
  is below 200.
* **WFPC2** quad-filters ``FQUV*`` and ``FQCH4*`` are pinned to 300
  nm and 900 nm respectively.
* **NICMOS** polarisers ``POL0S`` / ``POL0L`` are pinned to 110 nm
  and 220 nm before the NICMOS ×3.5 scaling.

The broadband filters ``F350LP``, ``F606W``, and ``LONG_PASS``
short-circuit to the plain ``[black, white]`` colormap.

When no wavelength can be inferred, a WARNING is logged ("Unknown HST
filter: <inst_id> <filter_name>") and ``tinted_colormap`` returns
``None``, leaving the existing colormap in place.

.. image:: _static/user_guide/hst_wfc3_tint.jpg
   :alt: HST/WFC3 thumbnail rendered with --tint
.. image:: _static/user_guide/hst_acs_tint.jpg
   :alt: HST/ACS thumbnail rendered with --tint
.. image:: _static/user_guide/hst_wfpc2_tint.jpg
   :alt: HST/WFPC2 thumbnail rendered with --tint

New Horizons MVIC
~~~~~~~~~~~~~~~~~

Detected via :func:`picmaker.instruments.nh.detect_fits` from the FITS
keywords ``HOSTNAME``, ``INSTRU``, and ``FILTER``. Only the ``MVIC``
camera gets a colored tint:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Filter
     - Tint (R, G, B)
   * - ``BLUE``
     - (110, 110, 210)
   * - ``RED``
     - (190, 100, 100)
   * - ``NIR``
     - (210, 65, 45)
   * - ``CH4``
     - (230, 35, 35)

.. image:: _static/user_guide/nh_mvic_tint.jpg
   :alt: New Horizons MVIC thumbnail rendered with --tint


7. Output formats and their controls
------------------------------------

``--extension`` (alias ``-x``) chooses the output container. Each
value is forwarded to ``PIL.Image.save`` as the file suffix and
extension, so the format Pillow infers controls the encoder:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Extension
     - Encoder
     - Notes
   * - ``bmp`` / ``dib``
     - Windows Bitmap
     - 8-bit grayscale or 24-bit RGB; lossless.
   * - ``gif``
     - GIF
     - 8-bit indexed; transparency not preserved.
   * - ``jpg`` / ``jpeg``
     - JPEG
     - 8-bit RGB only; ``--quality 1..100`` controls compression.
   * - ``png``
     - PNG
     - 8-bit grayscale or 24-bit RGB; lossless.
   * - ``tif`` / ``tiff``
     - TIFF
     - 8-bit by default. With ``--16`` the writer emits a 16-bit
       grayscale TIFF (or 16-bit RGB when the colormap path produced
       3-channel data) via :func:`picmaker.tiff16.WriteTiff16`.

The output stem is built as ``<input-stem><suffix>.<extension>``,
with ``--strip`` and ``--alt-strip`` each removing the first
occurrence of their value from ``<input-stem>``.

.. image:: _static/user_guide/output_jpg.jpg
   :alt: Default JPEG output
.. image:: _static/user_guide/output_png.png
   :alt: PNG output (lossless)
.. image:: _static/user_guide/output_tiff.tiff
   :alt: 8-bit TIFF output
.. image:: _static/user_guide/output_tiff16.tiff
   :alt: 16-bit TIFF output (--16)


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
4. ``--colormap NAME`` maps the stretched values into RGB. Names are
   hyphen-separated lists of X11 color names, resolved by
   :class:`picmaker.colornames.ColorNames`. ``--tint`` overrides this
   step with the per-instrument tint from section 6.
5. ``--below``, ``--above``, ``--invalid`` override the colors used
   for the three special cases.
6. ``--gamma G`` applies a final power-law correction (``out =
   in ** (1 / G)``).

The thumbnails below show successive overrides on the same Galileo
SSI fixture:

.. image:: _static/user_guide/enhance_default.jpg
   :alt: Default stretch
.. image:: _static/user_guide/enhance_pct5_95.jpg
   :alt: Percentile stretch (5-95)
.. image:: _static/user_guide/enhance_gamma2.jpg
   :alt: Gamma 2.0
.. image:: _static/user_guide/enhance_colormap.jpg
   :alt: --colormap red-blue
.. image:: _static/user_guide/enhance_histogram.jpg
   :alt: --histogram flat-stretch
.. image:: _static/user_guide/enhance_tint.jpg
   :alt: --tint instrument-aware colormap


9. Geometry controls
--------------------

Geometry runs in this order:

1. ``--rectangle`` / ``--crop`` / ``--trim`` shrink the working
   region.
2. ``--rotate`` (or the implicit ``default_is_up`` from the per-
   instrument detector geometry) flips / rotates the working array.
3. ``--size`` / ``--scale`` / ``--wscale`` / ``--hscale`` resize the
   working array. ``--frame W H`` instead picks the largest scale
   that fits inside ``W x H``; ``--frame_max PCT`` caps how far the
   image may be enlarged.
4. ``--wrap`` / ``--wrap-ratio`` / ``--overlap`` / ``--overlaps``
   split very elongated images into stacked panels separated by a
   ``--gap-size`` × ``--gap-color`` gap.
5. ``--pad`` re-introduces the full ``--frame`` box, filling with
   ``--pad-color``.

The thumbnails below show successive overrides on the same Cassini
ISS fixture:

.. image:: _static/user_guide/geom_default.jpg
   :alt: Default size
.. image:: _static/user_guide/geom_scale200.jpg
   :alt: --scale 200
.. image:: _static/user_guide/geom_frame_pad.jpg
   :alt: --frame 64 64 --pad
.. image:: _static/user_guide/geom_frame_max_50.jpg
   :alt: --frame_max 50
.. image:: _static/user_guide/geom_rot90.jpg
   :alt: --rotate rot90


10. The ``--versions FILE`` form
--------------------------------

``--versions FILE`` re-parses the CLI once per non-blank line in
``FILE``, appending the line's tokens to ``sys.argv`` for each run.
The same input file therefore produces one output per line, each
with its own suffix / quality / colormap / etc.

For example, ``two_versions.txt``::

   --suffix _v1 --extension jpg --quality 90
   --suffix _v2 --extension tif --16

paired with ``input.IMG`` produces ``input_v1.jpg`` and
``input_v2.tif`` in one read.

Lines starting with ``#`` and blank lines are skipped. Every
mutex / value-validity check raised by argparse fires per line, so an
invalid version doesn't abort the others (when combined with
``--proceed``).


11. Programmatic usage
----------------------

The library mirrors the CLI: every flag binds to a keyword argument
of :func:`picmaker.pipeline.images_to_pics`.

.. code-block:: python

   from picmaker import images_to_pics

   # Convert one file with a percentile stretch and a colormap.
   images_to_pics(
       ['data/cassini.vic'],
       directory='/tmp/out',
       percentiles=(5.0, 95.0),
       colormap='black-blue-white',
       extension='png',
   )

   # Re-use the same stretch across a sequence of frames (movie mode).
   limits, _, _ = images_to_pics(['frame_001.vic'], directory='/tmp/out')
   for n in range(2, 100):
       images_to_pics(
           [f'frame_{n:03d}.vic'],
           directory='/tmp/out',
           limits=limits,
       )

Lower-level helpers are re-exported on the top-level package:

.. code-block:: python

   from picmaker import (
       read_one_image_array,
       tinted_colormap,
       apply_colormap,
       array_to_pil,
   )

   array3d, default_is_up, filter_info = read_one_image_array('data.vic')
   colormap = tinted_colormap(filter_info)

See :doc:`module` for the per-leaf-module API reference.


12. Troubleshooting
-------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Error
     - Meaning
   * - ``OSError: Unrecognized image file format``
     - None of the reader branches (pickle, NumPy, VICAR, FITS, PIL,
       PDS3) recognised the file. Check the file is not truncated and
       that the magic bytes match the expected format.
   * - ``WARNING Unknown HST filter: <inst> <name>``
     - HST wavelength inference failed for this filter; no tint is
       applied and the existing colormap is preserved. Add the filter
       to the per-detector branch in
       :func:`picmaker.instruments.hst.tint_for` if a tint is needed.
   * - ``ValueError: hst and band options are incompatible``
     - ``--hst`` (mosaic mode) consumes every detector panel, so it
       cannot be combined with ``--band`` or ``--bands``.
   * - ``ValueError: band and bands options are incompatible``
     - ``--band`` and ``--bands`` were both given with mismatched
       values. Use one or the other.
   * - ``ValueError: scale and wscale options are incompatible``
     - ``--scale`` sets both axes; use ``--wscale`` / ``--hscale``
       instead for per-axis control.
   * - ``ValueError: frame and size options are incompatible``
     - ``--frame`` and ``--size`` both specify the output dimensions
       and can't be combined.
   * - ``ValueError: frame and wrap_ratio options are incompatible``
     - ``--frame`` and ``--wrap-ratio`` produce conflicting layout
       decisions.
   * - ``ValueError: only tiffs can be written in 16-bit mode``
     - ``--16`` requires ``--extension tiff`` (Pillow's other 16-bit
       paths are not supported).
   * - ``ValueError: 16-bit filter options are not supported``
     - The Pillow ``ImageFilter`` presets only work on 8-bit images;
       drop ``--filter`` when using ``--16``.
