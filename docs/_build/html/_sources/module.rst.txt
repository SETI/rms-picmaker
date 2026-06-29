``picmaker`` Module
=====================

The :mod:`picmaker` package is organized into a handful of leaf modules
plus an :mod:`~picmaker.instruments` subpackage; each symbol is
documented at its canonical leaf-module location below. Click any
function name to jump to its source via :mod:`sphinx.ext.viewcode`, or
follow the ``Source`` link under each section to view the file on
GitHub.

Public API
----------

Every name listed below is re-exported from the top-level :mod:`picmaker`
package, so callers should import from there::

    from picmaker import images_to_pics, read_one_image_array, PicmakerOptions

The per-leaf-module sections after this one are the authoritative
documentation for each symbol; the entries here are short pointers
arranged by topic.

**Top-level pipeline and CLI**

.. autofunction:: picmaker.images_to_pics
.. autofunction:: picmaker.process_images
.. autofunction:: picmaker.find_common_path
.. autofunction:: picmaker.main
.. autoclass:: picmaker.PicmakerOptions
   :no-members:

**Image I/O**

.. autofunction:: picmaker.read_image_array
.. autofunction:: picmaker.read_one_image_array
.. autofunction:: picmaker.read_pds_labeled_image_array
.. autofunction:: picmaker.read_pil
.. autofunction:: picmaker.read_array
.. autofunction:: picmaker.get_outfile
.. autofunction:: picmaker.write_pil
.. autoclass:: picmaker.ReadResult
   :no-members:
   :no-index:

The :data:`~picmaker.FilterInfo` type alias is documented in the I/O
section below.

**Enhancement**

.. autofunction:: picmaker.get_limits
.. autofunction:: picmaker.apply_gamma
.. autofunction:: picmaker.apply_colormap
.. autofunction:: picmaker.fill_zebra_stripes
.. autofunction:: picmaker.tinted_colormap

**Geometry**

.. autofunction:: picmaker.crop_array
.. autofunction:: picmaker.slice_array
.. autofunction:: picmaker.wrap_image
.. autofunction:: picmaker.pad_image
.. autofunction:: picmaker.resize_image
.. autofunction:: picmaker.rotate_array_rgb
.. autofunction:: picmaker.circle_mask
.. autofunction:: picmaker.get_size

**Filters and conversion**

.. autofunction:: picmaker.filter_image
.. autofunction:: picmaker.array_to_pil
.. autofunction:: picmaker.pil_to_array

**Re-exported constants**

The following module-level data names are re-exported from
:mod:`picmaker` and documented in their leaf-module sections below
(`Color` and `Filters`):

* :data:`picmaker.color.RGB_BY_NM`
* :data:`picmaker.color.RFUNC`, :data:`picmaker.color.GFUNC`,
  :data:`picmaker.color.BFUNC`
* :data:`picmaker._filters.FILTER_DICT`

Package
-------
Source: `src/picmaker/__init__.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/__init__.py>`__.

.. automodule:: picmaker

Backward-compatibility shim
---------------------------
Source: `src/picmaker/picmaker.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/picmaker.py>`__.

.. automodule:: picmaker.picmaker

Wavelength → RGB tables
-----------------------
Source: `src/picmaker/_rgb.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/_rgb.py>`__.

.. automodule:: picmaker._rgb
   :members:

Pipeline
--------
Source: `src/picmaker/pipeline.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/pipeline.py>`__.

.. automodule:: picmaker.pipeline
   :members:
   :private-members: _pds3_resolve_pointer, _hst_mosaic_rgb, _hst_wfpc2_mosaic, _hst_acs_panel_mosaic, _process_one_image

Options
-------
Source: `src/picmaker/options.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/options.py>`__.

.. automodule:: picmaker.options
   :members:

I/O
---
Source: `src/picmaker/io.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/io.py>`__.

.. automodule:: picmaker.io
   :members:

Enhancement
-----------
Source: `src/picmaker/enhance.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/enhance.py>`__.

.. automodule:: picmaker.enhance
   :members:

Geometry
--------
Source: `src/picmaker/geometry.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/geometry.py>`__.

.. automodule:: picmaker.geometry
   :members:

Color
-----
Source: `src/picmaker/color.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/color.py>`__.

.. automodule:: picmaker.color
   :members:

PIL utilities
-------------
Source: `src/picmaker/pil_utils.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/pil_utils.py>`__.

.. automodule:: picmaker.pil_utils
   :members:

Filters
-------
Source: `src/picmaker/_filters.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/_filters.py>`__.

.. automodule:: picmaker._filters
   :members:
   :private-members:

CLI
---
Source: `src/picmaker/cli.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/cli.py>`__.

.. automodule:: picmaker.cli
   :members:
   :private-members: _build_parser, _separate_files_and_dirs, _normalize_and_validate, _collect_option_dicts, _process_directory

Instruments
-----------
Source: `src/picmaker/instruments/
<https://github.com/SETI/rms-picmaker/tree/main/src/picmaker/instruments>`__.

.. automodule:: picmaker.instruments
   :members:

Cassini ISS
~~~~~~~~~~~
Source: `src/picmaker/instruments/cassini_iss.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/cassini_iss.py>`__.

.. automodule:: picmaker.instruments.cassini_iss
   :members:

Voyager ISS
~~~~~~~~~~~
Source: `src/picmaker/instruments/voyager_iss.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/voyager_iss.py>`__.

.. automodule:: picmaker.instruments.voyager_iss
   :members:

Galileo SSI
~~~~~~~~~~~
Source: `src/picmaker/instruments/galileo_ssi.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/galileo_ssi.py>`__.

.. automodule:: picmaker.instruments.galileo_ssi
   :members:

HST
~~~
Source: `src/picmaker/instruments/hst.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/hst.py>`__.

.. automodule:: picmaker.instruments.hst
   :members:

New Horizons LORRI
~~~~~~~~~~~~~~~~~~
Source: `src/picmaker/instruments/nh_lorri.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/nh_lorri.py>`__.

.. automodule:: picmaker.instruments.nh_lorri
   :members:

New Horizons MVIC
~~~~~~~~~~~~~~~~~
Source: `src/picmaker/instruments/nh_mvic.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/nh_mvic.py>`__.

.. automodule:: picmaker.instruments.nh_mvic
   :members:

TIFF 16
-------
Source: `src/picmaker/tiff16.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/tiff16.py>`__.

.. automodule:: picmaker.tiff16
   :members:

Color names
-----------
Source: `src/picmaker/colornames.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/colornames.py>`__.

.. automodule:: picmaker.colornames
   :members:
