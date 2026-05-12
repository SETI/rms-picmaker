Adding a new instrument
=======================

Every supported mission lives in its own module under
:mod:`picmaker.instruments`. The four functions every instrument
module exposes form a small structural protocol — there is no formal
:class:`typing.Protocol` declaration but each module is structurally
identical and the tests pin the contract.

The four-function protocol
--------------------------

.. code-block:: python

   def detect_vicar(vic) -> tuple[str, str, str] | None: ...
   def detect_fits(hdulist) -> tuple[str, str, str] | None: ...
   def matches(inst_host: str, inst_id: str) -> bool: ...
   def tint_for(inst_id: str, filter_name) -> list[tuple[int, int, int]] | None: ...

* ``detect_vicar(vic)`` — given a :class:`vicar.VicarImage`, return a
  ``(host, id, filter_name)`` triple if this module owns the label,
  else ``None``. Missions that are not delivered as VICAR return
  ``None`` unconditionally.
* ``detect_fits(hdulist)`` — same shape but for
  :class:`astropy.io.fits.HDUList`. Missions that are not delivered
  as FITS return ``None`` unconditionally.
* ``matches(inst_host, inst_id)`` — quick host-level predicate used
  by :func:`picmaker.instruments.lookup` once the cascade already
  has a ``filter_info`` triple in hand (e.g. when ``--tint`` is set
  on a non-detected file).
* ``tint_for(inst_id, filter_name)`` — given the filter, return the
  three-stop colormap ``[black, tint, white]``, the two-stop fallback
  ``[black, white]``, or ``None`` if the filter is genuinely unknown
  (the HST wavelength-inference path uses ``None`` to signal "unable
  to infer; keep the user's colormap").

Step-by-step
------------

1. **Create the module.** Copy
   :file:`src/picmaker/instruments/voyager.py` as a template — it
   uses the simplest of the four detection patterns (a constant
   ``FILTER_DICT`` plus a ``LAB02[:3] == 'VGR'`` predicate).

   .. code-block:: python

      """My-Mission MyInstrument detection and tint."""

      from typing import Any

      from vicar import VicarError

      _FILTER_DICT: dict[str, tuple[int, int, int]] = {
          'BLUE': (110, 110, 210),
          'RED':  (190, 100, 100),
          # ... per-filter tints here ...
      }


      def detect_vicar(vic: Any) -> tuple[str, str, str] | None:
          """Return ('MYMISSION', 'MYINST', filter) or None."""
          try:
              if vic['INSTRUMENT_HOST_NAME'] == 'MY MISSION':
                  return ('MYMISSION', 'MYINST', vic['FILTER_NAME'])
          except (VicarError, KeyError):
              pass
          return None


      def detect_fits(hdulist: Any) -> tuple[str, str, str] | None:
          """Not delivered as FITS — always None."""
          return None


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


      __all__ = ['detect_fits', 'detect_vicar', 'matches', 'tint_for']

2. **Register the module.** Open
   :file:`src/picmaker/instruments/__init__.py` and add the new
   module to the three dispatch lists. If the new instrument only
   handles VICAR or only FITS, add it to that list plus
   :data:`~picmaker.instruments.ALL_INSTRUMENTS`:

   .. code-block:: python

      from picmaker.instruments import cassini, galileo, hst, mymission, nh, voyager

      VICAR_INSTRUMENTS = [cassini, galileo, voyager, mymission]
      FITS_INSTRUMENTS = [hst, nh]
      ALL_INSTRUMENTS = [cassini, voyager, galileo, hst, nh, mymission]

   .. note::

      Consolidating these three lists into one is tracked in
      `issue #13 <https://github.com/SETI/rms-picmaker/issues/13>`__.
      Until that lands, every new module needs entries in two or
      three places.

3. **Add a fixture recipe.** Create
   :file:`tests/fixture_recipes/mymission_myinst.recipe.py` that
   builds a tiny synthetic VICAR or FITS file with the metadata
   keys your ``detect_*`` reads. Run it once from the venv to
   create the fixture binary:

   .. code-block:: bash

      python tests/fixture_recipes/mymission_myinst.recipe.py

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

   :file:`tests/test_io.py::test_instrument_detection` parametrizes
   over this list, so the new entry exercises both
   :func:`picmaker.io.read_one_image_array` (via the parametrize)
   and :func:`picmaker.instruments.lookup` (via the new fixture's
   ``filter_info`` triple).

5. **Add direct unit tests for the per-instrument helpers.** Open
   :file:`tests/test_instruments_branches.py` and add a parametrize
   case for every ``tint_for`` branch you want pinned, mirroring
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

7. **Document it.** Open :file:`docs/user_guide.rst` and add a
   section under "Supported instruments and filters" describing the
   new instrument's detection labels, filter set, and tint table.

   :file:`tests/test_cli.py::test_user_guide_documents_every_cli_flag`
   does not catch undocumented instruments today; this is
   author-discipline rather than CI-enforced.

8. **Run the full check suite.**

   .. code-block:: bash

      bash scripts/run-all-checks.sh

   The new module must pass ruff, mypy strict, bandit, and vulture.

When to break the protocol
--------------------------

Two existing modules already deviate slightly from the four-function
template:

* :mod:`picmaker.instruments.cassini` keeps the tint chain in a
  private helper :func:`!picmaker.instruments.cassini._iss_tint`
  rather than a public dict, because the chain is substring-based
  (``IR``, ``UV``, ``BL``, …) rather than a fixed mapping.
* :mod:`picmaker.instruments.hst` derives the tint from
  wavelength-inferred-from-digits rather than a fixed mapping, and
  has special cases for NICMOS scaling, WFPC2 quad filters
  (``FQUV*`` / ``FQCH4*``), polarizers (``POL0S`` / ``POL0L``), and
  long-pass broadband filters (``F350LP``, ``F606W``, ``LONG_PASS``).

Both still expose the four-function protocol; the internal
implementation just differs.
