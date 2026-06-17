Adding a new instrument
=======================

Every supported mission lives in its own module under
:mod:`picmaker.instruments`. Each module exposes a small structural
protocol — there is no formal :class:`typing.Protocol` declaration but
every module is structurally identical and the tests pin the contract.

The instrument protocol
-----------------------

**Required** — every instrument module must implement these three
functions:

.. code-block:: python

   def read_file(
       filename: str | os.PathLike[str] | pdsparser.PdsLabel,
       obj: ObjectSelector = None,
       **kwargs: Any,
   ) -> ReadResult | None: ...

   def matches(inst_host: str, inst_id: str) -> bool: ...

   def tint_for(inst_id: str, filter_name) -> list[tuple[int, int, int]] | None: ...

**Optional** — define this only when the instrument needs a custom
colorization algorithm that cannot be expressed as a fixed colormap:

.. code-block:: python

   def apply_tint(
       array3d: NDArray[Any],
       filter_info: FilterInfo,
       options: PicmakerOptions,
   ) -> NDArray[Any] | None: ...

Function descriptions
~~~~~~~~~~~~~~~~~~~~~

* ``read_file(filename, obj, **kwargs)`` — the instrument's complete
  file reader.  *filename* is either a file path (``str | PathLike``)
  or a pre-parsed :class:`pdsparser.PdsLabel` (passed when the pipeline
  is given a ``.LBL`` input).  The function must detect whether the
  input belongs to this instrument (via magic bytes, header keywords,
  file extension, label metadata, or any other heuristic) and return a
  :class:`~picmaker._types.ReadResult` on success, or ``None`` if the
  file / label is not owned by this instrument.  Each instrument owns
  its own format detection; the caller never pre-opens the file.
  Instruments that only support VICAR or FITS paths can safely receive
  a :class:`pdsparser.PdsLabel` and return ``None`` — the shared
  helpers (:func:`~picmaker.instruments._shared.try_open_vicar` and
  :func:`~picmaker.instruments._shared.is_fits_file`) both handle a
  label argument gracefully.  Shared format utilities are available in
  :mod:`picmaker.instruments._shared`.

  ``**kwargs`` carries every pipeline option listed in
  :data:`picmaker.options.READ_FILE_KWARGS`; currently that is ``hst``
  and ``pds3_label_method``.  Instruments that do not need any of these
  values simply accept and ignore them.  An instrument that *does* need
  one extracts it with ``kwargs.get('key', default)`` — see
  :mod:`picmaker.instruments.hst` for the ``hst`` example and
  :ref:`adding-instrument-option` below for how to introduce a new
  instrument-specific option.

* ``matches(inst_host, inst_id)`` — quick host-level predicate used
  by :func:`picmaker.instruments.lookup` once the cascade already has a
  ``filter_info`` triple (e.g. when ``--tint`` is applied to a file
  whose metadata was read without going through ``read_file``).

* ``tint_for(inst_id, filter_name)`` — given the filter, return the
  three-stop colormap ``[black, tint, white]``, the two-stop fallback
  ``[black, white]``, or ``None`` if the filter is genuinely unknown
  (the HST wavelength-inference path uses ``None`` to mean "unable to
  infer; keep the user's colormap").

* ``apply_tint(array3d, filter_info, options)`` — checked via
  :func:`hasattr` in
  :func:`picmaker.pipeline._process_one_image`; only define it when the
  tinting algorithm cannot be expressed as a fixed colormap list.
  Return a ``(lines, samples, 3)`` uint8 RGB array to bypass the
  standard colormap pipeline, or ``None`` to fall through to
  :func:`picmaker.color.tinted_colormap` / ``_band_to_rgb``.

Shared format utilities
-----------------------

:mod:`picmaker.instruments._shared` provides helpers that multiple
instrument modules can import without circular-import issues:

* :func:`~picmaker.instruments._shared.try_open_vicar` — parse
  *filename* as a VICAR file and return a :class:`vicar.VicarImage`, or
  ``None`` on any error (including non-VICAR files or a
  :class:`pdsparser.PdsLabel` argument).
* :func:`~picmaker.instruments._shared.is_fits_file` — return ``True``
  iff the file begins with the FITS magic bytes ``b'SIMPLE  ='``; also
  returns ``False`` safely when given a :class:`pdsparser.PdsLabel`.
* :func:`~picmaker.instruments._shared.extract_fits_array` — extract a
  3-D ``(bands, lines, samples)`` array from an open FITS HDU list,
  handling ``obj=None`` (auto-detect), list/tuple (stack), and scalar
  (direct index) selectors.
* :func:`~picmaker.instruments._shared.read_pds3_image_array` — resolve
  the first ``^*IMAGE`` pointer in a :class:`pdsparser.PdsLabel`, then
  read the referenced data file as VICAR or FITS.  Used by instruments
  that support PDS3 label inputs and by the generic PDS3 fallback in
  :func:`picmaker.io.read_one_image_array`.

Step-by-step
------------

1. **Create the module.** The template below covers the VICAR case —
   the most common pattern.

   .. code-block:: python

      """My-Mission MyInstrument detection and tint."""

      import os
      from typing import Any

      from vicar import VicarError

      from picmaker._types import ObjectSelector, ReadResult
      from picmaker.instruments import _shared

      _FILTER_DICT: dict[str, tuple[int, int, int]] = {
          'BLUE': (110, 110, 210),
          'RED':  (190, 100, 100),
          # ... per-filter tints here ...
      }


      def _detect_vicar(vic: Any) -> tuple[str, str, str] | None:
          """Return ('MYMISSION', 'MYINST', filter) or None."""
          try:
              if vic['INSTRUMENT_HOST_NAME'] == 'MY MISSION':
                  return ('MYMISSION', 'MYINST', vic['FILTER_NAME'])
          except (VicarError, KeyError):
              pass
          return None


      def read_file(
          filename: str | os.PathLike[str] | pdsparser.PdsLabel,
          obj: ObjectSelector = None,
          **kwargs: Any,
      ) -> ReadResult | None:
          """Try to detect and read a My-Mission VICAR image."""
          vic = _shared.try_open_vicar(filename)
          if vic is None:
              return None
          filter_info = _detect_vicar(vic)
          if filter_info is None:
              return None
          array3d = vic.data_3d
          if array3d.ndim == 2:
              array3d = array3d.reshape((1, *array3d.shape))
          return ReadResult(array3d, False, filter_info)


      def matches(inst_host: str, inst_id: str) -> bool:
          """Host-level predicate."""
          return inst_host.startswith('MY MISSION')


      def tint_for(
          inst_id: str, filter_name: Any
      ) -> list[tuple[int, int, int]] | None:
          """Return [black, tint, white] for known filters."""
          if not inst_id.startswith('MYINST'):
              return [(0, 0, 0), (255, 255, 255)]
          return [(0, 0, 0), _FILTER_DICT[filter_name], (255, 255, 255)]


      __all__ = ['matches', 'read_file', 'tint_for']

   For a **FITS-based instrument**, replace ``_detect_vicar`` +
   ``try_open_vicar`` with ``_detect_fits`` + ``is_fits_file``:

   .. code-block:: python

      import warnings

      import astropy.io.fits as pyfits

      def _detect_fits(hdulist: Any) -> tuple[str, str, Any] | None:
          """Return ('MYMISSION', 'MYINST', filter) or None."""
          try:
              if hdulist[0].header['TELESCOP'] == 'MY MISSION':
                  return ('MYMISSION', 'MYINST',
                          hdulist[0].header.get('FILTER'))
          except KeyError:
              pass
          return None

      def read_file(
          filename: str | os.PathLike[str] | pdsparser.PdsLabel,
          obj: ObjectSelector = None,
          **kwargs: Any,
      ) -> ReadResult | None:
          """Try to detect and read a My-Mission FITS image."""
          if not _shared.is_fits_file(filename):
              return None
          try:
              with warnings.catch_warnings(), pyfits.open(str(filename)) as hdulist:
                  warnings.filterwarnings('error')
                  filter_info = _detect_fits(hdulist)
                  if filter_info is None:
                      return None
                  array3d = _shared.extract_fits_array(hdulist, obj)
                  return ReadResult(array3d, True, filter_info)
          except (UserWarning, OSError):
              return None

2. **Register the module.** Open
   :file:`src/picmaker/instruments/__init__.py` and add the new module
   to the import line and to :data:`~picmaker.instruments.ALL_INSTRUMENTS`:

   .. code-block:: python

      from picmaker.instruments import cassini_iss, galileo_ssi, hst, mymission, nh_lorri, voyager_iss

      ALL_INSTRUMENTS: list[ModuleType] = [cassini_iss, voyager_iss, galileo_ssi, hst, nh_lorri, mymission]

   Order matters: the cascade tries each instrument in list order and
   returns on the first match, so put more-specific instruments before
   more-general ones.

3. **Add a fixture recipe.** Create
   :file:`tests/fixture_recipes/mymission_myinst_recipe.py` that
   builds a tiny synthetic VICAR or FITS file containing the metadata
   keys your :func:`!_detect_vicar` / :func:`!_detect_fits` reads.  Run
   it once from the venv to create the fixture binary:

   .. code-block:: bash

      python tests/fixture_recipes/mymission_myinst_recipe.py

   Then add :file:`tests/fixtures/mymission_myinst.vic` (or ``.fits``)
   to git.

4. **Wire it into the cross-instrument tests.** Open
   :file:`tests/test_io.py` and add an entry to ``INSTRUMENT_FIXTURES``:

   .. code-block:: python

      INSTRUMENT_FIXTURES = [
          ('cassini_iss.vic', ('CASSINI', 'ISS', 'CL1+GRN'), False),
          # ... existing entries ...
          ('mymission_myinst.vic', ('MYMISSION', 'MYINST', 'BLUE'), False),
      ]

   :func:`!tests.test_io.test_instrument_detection` parametrizes over
   this list, so the new entry exercises both
   :func:`picmaker.io.read_one_image_array` (the full cascade) and
   :func:`picmaker.instruments.lookup` (the ``filter_info`` triple).

5. **Add direct unit tests for the per-instrument helpers.** Open
   :file:`tests/test_instruments_branches.py` and add a parametrize
   case for every :func:`!tint_for` branch you want pinned, mirroring
   the existing Cassini and Voyager parametrize blocks.

6. **Add a snapshot.** If the new fixture supports the ``--tint``,
   ``--default``, ``--rot90``, etc. combinations exercised by
   :file:`tests/fixture_recipes/generate_snapshots.py`, append the
   fixture name to ``ALL_FIXTURES`` in that file and regenerate:

   .. code-block:: bash

      python tests/fixture_recipes/generate_snapshots.py

   The script writes new files under :file:`tests/fixtures/expected/`
   and rewrites :file:`tests/snapshots_index.py`. Both should be
   committed.

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

Sometimes a new feature only makes sense for one instrument — for example
a Cassini-specific decompression mode or an HST-specific scaling flag.
The pipeline is designed so that adding such an option touches exactly
three files; no other instrument files and neither :mod:`picmaker.io` nor
:mod:`picmaker.pipeline` need to change.

How the forwarding works
~~~~~~~~~~~~~~~~~~~~~~~~

:data:`picmaker.options.READ_FILE_KWARGS` is a tuple of
:class:`~picmaker.options.PicmakerOptions` field names that the pipeline
forwards to every ``read_file`` call as keyword arguments:

.. code-block:: python

   # options.py
   READ_FILE_KWARGS: tuple[str, ...] = ('hst', 'pds3_label_method')

In :func:`picmaker.pipeline._process_one_image` the kwargs dict is
assembled generically from those names:

.. code-block:: python

   **{k: getattr(options, k) for k in READ_FILE_KWARGS}

:func:`picmaker.io.read_one_image_array` then forwards the whole dict
unchanged to every instrument's ``read_file``.  Instruments that do not
need a value ignore it silently; instruments that do extract it with
``kwargs.get``.

Step-by-step for a new instrument-specific option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Suppose you want to add ``--cassini-encoding`` (a Cassini-only flag):

1. **Add the CLI argument.** In :file:`src/picmaker/cli.py`, add the
   ``--cassini-encoding`` argument to the argparse parser in
   :func:`!_build_parser`.

2. **Register the option.** In :file:`src/picmaker/options.py`, do two
   things in the same edit:

   a. Add the field to :class:`~picmaker.options.PicmakerOptions`:

      .. code-block:: python

         cassini_encoding: str = 'standard'

   b. Add its name to :data:`~picmaker.options.READ_FILE_KWARGS`:

      .. code-block:: python

         READ_FILE_KWARGS: tuple[str, ...] = (
             'cassini_encoding', 'hst', 'pds3_label_method'
         )

   That is the only change required to make the value flow from the CLI
   all the way to the instrument reader — no edits to
   :mod:`picmaker.pipeline` or :mod:`picmaker.io` are needed.

3. **Consume the option in the instrument.** In
   :file:`src/picmaker/instruments/cassini_iss.py`, extract the value at
   the top of ``read_file``:

   .. code-block:: python

      def read_file(
          filename: str | os.PathLike[str],
          obj: ObjectSelector = None,
          **kwargs: Any,
      ) -> ReadResult | None:
          encoding: str = kwargs.get('cassini_encoding', 'standard')
          ...

   All other instrument ``read_file`` functions already accept
   ``**kwargs`` and ignore it, so they need no changes.

When to break the protocol
--------------------------

Three existing modules deviate slightly from the minimal template:

* :mod:`picmaker.instruments.cassini_iss` keeps the tint chain in a private
  helper :func:`!picmaker.instruments.cassini_iss._iss_tint` rather than a
  fixed dict, because the chain is substring-based (``IR``, ``UV``,
  ``BL``, …) rather than an exact-key mapping.
* :mod:`picmaker.instruments.hst` derives the tint from wavelength
  inferred from filter-name digits rather than a fixed mapping, and has
  special cases for NICMOS scaling, WFPC2 quad filters (``FQUV*`` /
  ``FQCH4*``), polarizers (``POL0S`` / ``POL0L``), and long-pass
  broadband filters (``F350LP``, ``F606W``, ``LONG_PASS``).
* :mod:`picmaker.instruments.hst` also contains a private
  :func:`!_extract_hst_array` helper that handles ACS/WFC two-detector
  and WFPC2 four-detector mosaic extraction in :func:`!read_file`,
  because the array layout depends on the instrument sub-type, and it
  extracts ``hst = kwargs.get('hst', False)`` at the top of
  ``read_file`` to gate the mosaic assembly path.

All three still expose the full required protocol; the internal
implementation just differs.
