Adding a new instrument
=======================

Every supported mission lives in its own module under
:mod:`picmaker.instruments`. Each module defines a subclass of
:class:`picmaker.instruments.ImageData`, which registers itself
automatically via :func:`ImageData.__init_subclass__`. There is no formal
:class:`typing.Protocol`; the contract is the set of ``detect_*`` static
methods described below, and the tests pin it.

The instrument protocol
-----------------------

An instrument is an :class:`~picmaker.instruments.ImageData` subclass
that implements one or more ``detect_*`` static methods, one per input
format it understands. The reader cascade in
:func:`!picmaker.instruments._read_one_image_array` tries the relevant
method against every registered instrument, in class-name order, and
uses the first non-``None`` result.

**Detection methods** — implement whichever apply to your instrument's
file format(s). Each returns an instance of your subclass on a match, or
``None`` to let the cascade try the next instrument:

.. code-block:: python

   @staticmethod
   def detect_in_pds3(label, filepath, **kwargs): ...   # parsed .lbl label

   @staticmethod
   def detect_in_vicar(vic, filepath, **kwargs): ...    # open VicarImage

   @staticmethod
   def detect_in_fits(hdulist, filepath, **kwargs): ... # open pyfits HDUList

   @staticmethod
   def detect_in_file(filepath, **kwargs): ...          # any other format

The cascade only calls a method that exists (it guards each call with
:func:`hasattr`), so an instrument that reads only FITS defines only
:func:`!detect_in_fits`.

**Construction.** Every ``detect_*`` method builds and returns
``cls(array, default_upward, default_tint)`` — the
:class:`~picmaker.instruments.ImageData` constructor:

* ``array`` — the pixel array, 2-D ``(lines, samples)`` or 3-D
  ``(bands, lines, samples)``.
* ``default_upward`` — ``True`` if the raw data is stored
  display-upward (typical for FITS), ``False`` otherwise (typical for
  VICAR / PDS3).
* ``default_tint`` — the default tint color (an ``(R, G, B)`` tuple or
  ``None``), used when ``--tint`` is set and the user gave no explicit
  ``--colormap``.

**Optional overrides** — define these on the subclass only when the
instrument needs behaviour the base class does not provide:

.. code-block:: python

   def apply_colormap(self, array, valid_limits, invalid_mask=None, **kwargs):
       ...   # override only for a non-standard colormap policy

   def apply_mosaic(self, arrays_rgb, **kwargs):
       ...   # define for instruments assembled from multiple detectors

The base :meth:`ImageData.apply_colormap
<picmaker.instruments.ImageData.apply_colormap>` already forwards to
:func:`picmaker.enhancement.apply_colormap` with the instrument's
``default_tint``, so most instruments never override it. Define
:func:`!apply_mosaic` when the instrument builds one image from several
detector panels; it receives the list of per-band RGB arrays (already
colormapped in :func:`~picmaker.picmaker.picmaker1`) and returns the
assembled array. It is invoked only when ``--mosaic`` is set and the
sliced array is still 3-D.

Method descriptions
~~~~~~~~~~~~~~~~~~~

* ``detect_in_pds3(label, filepath, **kwargs)`` — receives a parsed
  :class:`pdsparser.Pds3Label` (the cascade parses any ``.lbl`` input
  before dispatching) and the label's path. Inspect the label's
  metadata keys to decide ownership, then extract the array — usually
  via :func:`picmaker.instruments.read_pds3_image_array`, which resolves
  the ``^IMAGE`` pointer and reads the referenced data file.

* ``detect_in_vicar(vic, filepath, **kwargs)`` — receives an open
  :class:`vicar.VicarImage`. Read VICAR header keywords to decide
  ownership and take the array from ``vic.array``.

* ``detect_in_fits(hdulist, filepath, **kwargs)`` — receives an open
  :class:`astropy.io.fits.HDUList`. Read header cards to decide
  ownership and select the image HDU. The cascade copies the pixels out
  of the memory-mapped HDU after you return, so you may return a view.
  The FITS helpers in :mod:`!picmaker.instruments._fits_support`
  (:func:`~picmaker.instruments.get_fits_array`,
  :func:`!get_fits_image_hdu`, :func:`!get_fits_image_hdus`,
  :func:`!hdu_is_image`) handle HDU selection and the ``obj`` /
  ``pointers`` options.

* ``detect_in_file(filepath, **kwargs)`` — the catch-all for formats not
  covered above (pickle, ``.npy``, 16-bit TIFF, attached-label PDS3, and
  any PIL-readable image). This is where the always-accepting fallback
  :class:`!picmaker.instruments.zzz_generic.ZZZ_Generic` does its work.

Every method receives the full pipeline options as ``**kwargs``. Extract
what you need with ``kwargs.get('name', default)``, or declare named
parameters ahead of ``**kwargs`` (as ``detect_in_fits`` does for
``obj``, ``pointers``, ``retint``, and ``mosaic`` in
:mod:`picmaker.instruments.hst_acs`).

Shared format utilities
-----------------------

Helper modules whose names begin with an underscore are *not* imported
as instruments; they provide utilities that instrument modules import:

* :mod:`!picmaker.instruments._fits_support` —
  :func:`~picmaker.instruments.get_fits_array`,
  :func:`!get_fits_image_hdu`, :func:`!get_fits_image_hdus`, and
  :func:`!hdu_is_image` for selecting and extracting FITS image arrays.
* :mod:`!picmaker.instruments._pds3_support` —
  :func:`picmaker.instruments.read_pds3_image_array` (resolve a PDS3
  ``^IMAGE`` pointer and read the data file) plus the
  :data:`!PDS3_METHODS` list and :data:`!DEFAULT_PDS3_METHOD`.
* :mod:`!picmaker.instruments._hst_support` —
  :func:`!get_hst_filter_digits` (the integer embedded in an HST filter
  name) and :func:`!is_science_hdu`.

The package also exposes :func:`picmaker.instruments.tint_by_nm`, which
maps a wavelength in nanometers to an ``(R, G, B)`` tint; the HST
readers use it together with :func:`!get_hst_filter_digits` to derive a
default tint from the filter name.

Writing the instrument module
-----------------------------

1. **Create the module.** Add ``src/picmaker/instruments/mymission.py``
   (any name not starting with an underscore). Choose the ``detect_*``
   method(s) matching the format(s) your instrument produces.

   **VICAR-based instrument** (e.g. Cassini ISS, Voyager ISS,
   Galileo SSI):

   .. code-block:: python

      """My-Mission MyInstrument detector and reader."""

      from picmaker.instruments import ImageData

      _DEFAULT_UPWARD = False

      _FILTER_DICT = {
          'BLUE': (110, 110, 210),
          'RED':  (190, 100, 100),
          # ... per-filter tints here ...
      }


      class MyMission_MyInst(ImageData):
          """My-Mission MyInstrument detector and reader."""

          @staticmethod
          def detect_in_vicar(vic, filepath, **kwargs):
              try:
                  if vic['INSTRUMENT_HOST_NAME'] != 'MY MISSION':
                      return None
                  if vic['INSTRUMENT_ID'] != 'MYINST':
                      return None
              except (KeyError, IndexError):
                  return None

              filter_name = vic.get('FILTER_NAME', '')
              default_tint = _FILTER_DICT.get(filter_name)
              return MyMission_MyInst(vic.array[0], _DEFAULT_UPWARD, default_tint)

   **FITS-based instrument** (e.g. HST, New Horizons MVIC) — use
   ``detect_in_fits`` and the FITS helpers:

   .. code-block:: python

      from picmaker.instruments import ImageData, tint_by_nm
      from picmaker.instruments._fits_support import get_fits_array

      _DEFAULT_UPWARD = True


      class MyMission_MyInst(ImageData):

          @staticmethod
          def detect_in_fits(hdulist, filepath, obj=None, **kwargs):
              try:
                  if hdulist[0].header['TELESCOP'] != 'MY MISSION':
                      return None
                  if hdulist[0].header['INSTRUME'] != 'MYINST':
                      return None
              except (KeyError, IndexError):
                  return None

              array = get_fits_array(hdulist, obj=obj)
              return MyMission_MyInst(array, _DEFAULT_UPWARD, None)

   **PDS3-labeled instrument** (e.g. Cassini ISS via ``.LBL``, NH LORRI
   via ``.LBL``) — add a ``detect_in_pds3`` method and extract the array
   with :func:`~picmaker.instruments.read_pds3_image_array`:

   .. code-block:: python

      from picmaker.instruments import ImageData
      from picmaker.instruments._pds3_support import read_pds3_image_array


      class MyMission_MyInst(ImageData):

          @staticmethod
          def detect_in_pds3(label, filepath, **kwargs):
              try:
                  if label['INSTRUMENT_HOST_NAME'][:7] != 'MYMISSN':
                      return None
              except (KeyError, TypeError, IndexError):
                  return None

              array = read_pds3_image_array(label, **kwargs)
              return MyMission_MyInst(array, False, None)

   An instrument can implement several ``detect_*`` methods on the same
   subclass — for example ``detect_in_pds3`` for ``.LBL`` inputs and
   ``detect_in_vicar`` for bare VICAR data files (see
   :mod:`picmaker.instruments.cassini_iss` for a complete example).

2. **Registration is automatic — no ``__init__.py`` edit needed.**
   :mod:`picmaker.instruments` discovers and imports every module in the
   package whose name does not start with an underscore, so dropping the
   file in is enough; each ``ImageData`` subclass registers itself
   automatically via :func:`ImageData.__init_subclass__` when its module
   is imported.

   Ordering is by **class name**: the registry is kept sorted by
   ``__name__``, and the cascade returns on the first
   match. The always-accepting fallback is named ``ZZZ_Generic`` (in
   ``zzz_generic.py``) precisely so it sorts last and is only reached
   when no real instrument claims the file. If two instruments could
   both claim a file, choose class names whose alphabetical order puts
   the more-specific one first.

Writing the unit tests
----------------------

3. **Create a fixture recipe.** Add
   :file:`tests/fixture_recipes/mymission_recipe.py` that builds a tiny
   synthetic file in whatever format your instrument reads — VICAR,
   FITS, or a PDS3 label plus its data file. The file only needs the
   metadata keys your detection method reads; a 4×4 or 8×8 image is
   enough. Run it once from the venv to write the fixture into
   :file:`tests/fixtures/`, and commit the result:

   .. code-block:: bash

      python tests/fixture_recipes/mymission_recipe.py

   If the instrument reads both a bare data file and a ``.LBL`` label,
   create separate fixtures so both ``detect_*`` branches are exercised.

4. **Wire into the cascade tests.** Open
   :file:`tests/test_instruments_reading.py` and add an entry to
   ``INSTRUMENT_FIXTURES`` — a
   ``(fixture_name, expected_shape, default_upward, default_tint)``
   tuple:

   .. code-block:: python

      # (fixture_name, expected_shape, default_upward, default_tint)
      INSTRUMENT_FIXTURES = [
          ('cassini_iss.vic', (16, 16), False, None),
          # ... existing entries ...
          ('mymission.vic', (8, 8), False, (110, 110, 210)),
      ]

   ``test_instrument_detection`` parametrizes over this list, calling
   :func:`picmaker.instruments.read_image_array` on each fixture and
   asserting the array shape, ``default_upward``, and ``default_tint``.

5. **Add per-instrument read tests.** Add a
   :file:`tests/test_mymission_read.py` (modelled on
   :file:`tests/test_hst_acs_read.py` or
   :file:`tests/test_cassini_iss_previews.py`) covering each detection
   branch, each tint mapping you want pinned, and — if you defined
   :func:`!apply_mosaic` — each mosaic variant.

6. **Add a snapshot.** If the fixture should be part of the pixel-level
   regression suite, append its name to ``VICAR_FIXTURES`` or
   ``FITS_FIXTURES`` in
   :file:`tests/fixture_recipes/generate_snapshots.py` and regenerate:

   .. code-block:: bash

      python tests/fixture_recipes/generate_snapshots.py

   The script writes new files under :file:`tests/fixtures/expected/`
   and rewrites :file:`tests/snapshots_index.py`. Commit both.

Completing the addition
-----------------------

7. **Document it.** Open :file:`docs/user_guide.rst` and add a section
   under "Supported instruments and filters" describing the new
   instrument's detection labels, filter set, and tint table.

8. **Run the full check suite.**

   .. code-block:: bash

      bash scripts/run-all-checks.sh

   The new module must pass ruff, mypy strict, bandit, and vulture.

.. _adding-instrument-option:

Adding an instrument-specific option
-------------------------------------

Sometimes a new feature only makes sense for one instrument — for
example an HST-specific retint factor. Because options travel through
the pipeline as a plain ``dict`` and every ``detect_*`` method accepts
``**kwargs``, adding one is lightweight: there is no ``options.py``, no
``PicmakerOptions`` dataclass, and no per-function signature to thread
the value through.

How the forwarding works
~~~~~~~~~~~~~~~~~~~~~~~~

The validated option dict produced by
:func:`picmaker.picmaker.validate_options` flows unchanged through
:func:`picmaker.picmaker.picmaker` →
:func:`picmaker.picmaker.picmaker1` →
:func:`picmaker.instruments.read_image_array` →
:func:`!picmaker.instruments._read_one_image_array`, which passes it to
each instrument's ``detect_*`` method as ``**kwargs``. So any key you
add to the parser is automatically visible to every detection method;
instruments that do not care about it simply ignore it.

Step-by-step for a new instrument-specific option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Suppose you want to add ``--retint`` (used only by the HST readers):

1. **Add the CLI argument.** In :func:`picmaker.parser.get_parser`
   (:file:`src/picmaker/parser.py`), add the argument under an
   appropriate argument group:

   .. code-block:: python

      _instrument = parser.add_argument_group('instrument options')
      _instrument.add_argument(
          '--retint', type=float, default=None,
          help='factor by which to scale filter wavelengths for tinting.')

   The ``dest`` (here ``retint``) becomes the dictionary key.

2. **(Optional) validate it.** If the option interacts with others, add
   a mutex or range check in
   :func:`picmaker.picmaker.validate_options`
   (:file:`src/picmaker/picmaker.py`). A standalone value with a sensible
   default needs no change here.

3. **Consume it in the instrument.** In the relevant ``detect_*``
   method, read the value — either as a named parameter or via
   ``kwargs.get``:

   .. code-block:: python

      @staticmethod
      def detect_in_fits(hdulist, filepath, retint=None, **kwargs):
          retint = retint or 1.
          ...

   No other instrument needs changing: they all accept and ignore
   unknown keys through ``**kwargs``.

When to break the protocol
--------------------------

Several existing modules go beyond the minimal template:

* :mod:`picmaker.instruments.cassini_iss` computes its tint from a
  substring scan of the filter pair (``IR``, ``UV``, ``BL``, ``GRN``,
  …) in a private :func:`!_default_tint` helper rather than an exact-key
  lookup, and implements both :func:`!detect_in_pds3` and
  :func:`!detect_in_vicar` so it reads ``.LBL`` labels and bare VICAR
  files alike.
* The HST readers (:mod:`picmaker.instruments.hst_acs`,
  :mod:`picmaker.instruments.hst_wfc3`,
  :mod:`picmaker.instruments.hst_wfpc2`, and
  :mod:`picmaker.instruments.hst_nicmos`) derive the tint from the
  wavelength inferred from the filter-name digits
  (:func:`!get_hst_filter_digits` +
  :func:`~picmaker.instruments.tint_by_nm`) rather than a fixed mapping,
  and each treats "undiagnostic" filters (``CLEAR*``, polarizers,
  long-pass broadbands, ``FQCH4*``, …) as tint-neutral.
* :mod:`picmaker.instruments.hst_acs` and
  :mod:`picmaker.instruments.hst_wfpc2` gate a multi-detector array
  layout on the ``mosaic`` option inside :func:`!detect_in_fits`, and
  each defines an :func:`!apply_mosaic` method that assembles the panels
  (ACS/WFC stacks two CCDs; WFPC2 tiles four detectors into a 2×2
  quadrant). :func:`~picmaker.picmaker.picmaker1` calls
  :func:`!apply_mosaic` under ``--mosaic`` after colormapping each band.

All still subclass :class:`~picmaker.instruments.ImageData` (and so
register automatically); only the internals differ.
</content>
