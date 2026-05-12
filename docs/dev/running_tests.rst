Running the test suite
======================

The suite is :mod:`pytest`-based with ``pytest-xdist`` for parallel
execution and ``pytest-cov`` for coverage. Configuration lives under
``[tool.pytest.ini_options]`` in ``pyproject.toml``::

   pytest

For a single-worker run that is easier to read::

   pytest -n 1

The :file:`scripts/run-all-checks.sh` orchestrator runs lint, type
checks, tests, Sphinx, and pymarkdown in parallel and is what CI
mirrors::

   bash scripts/run-all-checks.sh

Snapshot tests in :file:`tests/test_snapshots.py` are byte-identical
against committed expected files under
:file:`tests/fixtures/expected/`. If a pipeline change is intentional,
regenerate the snapshots with::

   python tests/fixture_recipes/generate_snapshots.py

and commit the resulting :file:`tests/fixtures/expected/\\*` updates
together with the production-code change.
