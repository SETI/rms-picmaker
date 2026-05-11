``picmaker`` Module
=====================

The :mod:`picmaker` package is decomposed into a handful of leaf modules
plus an :mod:`~picmaker.instruments` subpackage. The legacy
``picmaker.picmaker`` module is a backward-compatibility re-export shim
and is intentionally **not** documented here — its symbols are
documented in their canonical leaf locations.

Pipeline
--------
.. automodule:: picmaker.pipeline
   :members:

I/O
---
.. automodule:: picmaker.io
   :members:

Enhancement
-----------
.. automodule:: picmaker.enhance
   :members:

Geometry
--------
.. automodule:: picmaker.geometry
   :members:

Color
-----
.. automodule:: picmaker.color
   :members:

PIL utilities
-------------
.. automodule:: picmaker.pil_utils
   :members:

Filters
-------
.. automodule:: picmaker._filters
   :members:
   :private-members:

CLI
---
.. automodule:: picmaker.cli
   :members:
