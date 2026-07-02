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

    from picmaker import picmaker, read_image_array, validate_options

The per-leaf-module sections after this one are the authoritative
documentation for each symbol; the entries here are short pointers
arranged by topic.

**Top-level pipeline**

.. autofunction:: picmaker.picmaker
.. autofunction:: picmaker.picmaker1
.. autofunction:: picmaker.validate_options
.. autofunction:: picmaker.get_versions

The command-line entry point (:func:`picmaker.main.main`) and its
argument parser (:func:`picmaker.parser.get_parser`) are documented in
the CLI sections below; they are not re-exported from the top-level
package.

**Image reading and I/O**

.. autofunction:: picmaker.read_image_array
.. autofunction:: picmaker.get_filepaths
.. autofunction:: picmaker.get_outfile
.. autofunction:: picmaker.write_pil
.. autofunction:: picmaker.read_tiff16
.. autofunction:: picmaker.write_tiff16

**Enhancement and stretch**

.. autofunction:: picmaker.get_limits
.. autofunction:: picmaker.apply_colormap

**Geometry and layout**

.. autofunction:: picmaker.slice_array
.. autofunction:: picmaker.get_size
.. autofunction:: picmaker.resize_pil_image
.. autofunction:: picmaker.rotate_rgb_array
.. autofunction:: picmaker.pad_pil_image
.. autofunction:: picmaker.wrap_pil_image

**Processing and conversion**

.. autofunction:: picmaker.fill_zebra_stripes
.. autofunction:: picmaker.filter_pil_image
.. autofunction:: picmaker.array_to_pil
.. autofunction:: picmaker.pil_to_array

**Instruments and color**

.. autofunction:: picmaker.register_instrument
.. autofunction:: picmaker.tint_by_nm
.. autoclass:: picmaker.ImageData
   :no-members:
   :no-index:
.. autoclass:: picmaker.ColorNames
   :no-members:
   :no-index:

Package
-------
Source: `src/picmaker/__init__.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/__init__.py>`__.

.. automodule:: picmaker

Core
----
Source: `src/picmaker/picmaker.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/picmaker.py>`__.

.. automodule:: picmaker.picmaker
   :members:

CLI entry point
---------------
Source: `src/picmaker/main.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/main.py>`__.

.. automodule:: picmaker.main
   :members:

Argument parser
---------------
Source: `src/picmaker/parser.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/parser.py>`__.

.. automodule:: picmaker.parser
   :members:

File control and I/O
--------------------
Source: `src/picmaker/control.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/control.py>`__.

.. automodule:: picmaker.control
   :members:

Enhancement
-----------
Source: `src/picmaker/enhancement.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/enhancement.py>`__.

.. automodule:: picmaker.enhancement
   :members:

Stretch
-------
Source: `src/picmaker/stretch.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/stretch.py>`__.

.. automodule:: picmaker.stretch
   :members:

Processing
----------
Source: `src/picmaker/processing.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/processing.py>`__.

.. automodule:: picmaker.processing
   :members:

Sizing
------
Source: `src/picmaker/sizing.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/sizing.py>`__.

.. automodule:: picmaker.sizing
   :members:

Slicing
-------
Source: `src/picmaker/slicing.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/slicing.py>`__.

.. automodule:: picmaker.slicing
   :members:

Layout
------
Source: `src/picmaker/layout.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/layout.py>`__.

.. automodule:: picmaker.layout
   :members:

Orientation
-----------
Source: `src/picmaker/orientation.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/orientation.py>`__.

.. automodule:: picmaker.orientation
   :members:

PIL utilities
-------------
Source: `src/picmaker/pil_utils.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/pil_utils.py>`__.

.. automodule:: picmaker.pil_utils
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

Instruments
-----------
Source: `src/picmaker/instruments/
<https://github.com/SETI/rms-picmaker/tree/main/src/picmaker/instruments>`__.

.. automodule:: picmaker.instruments
   :members:

FITS support
~~~~~~~~~~~~
Source: `src/picmaker/instruments/_fits_support.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/_fits_support.py>`__.

.. automodule:: picmaker.instruments._fits_support
   :members:
   :private-members:

HST support
~~~~~~~~~~~
Source: `src/picmaker/instruments/_hst_support.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/_hst_support.py>`__.

.. automodule:: picmaker.instruments._hst_support
   :members:
   :private-members:

PDS3 support
~~~~~~~~~~~~
Source: `src/picmaker/instruments/_pds3_support.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/_pds3_support.py>`__.

.. automodule:: picmaker.instruments._pds3_support
   :members:
   :private-members:

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

HST ACS
~~~~~~~
Source: `src/picmaker/instruments/hst_acs.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/hst_acs.py>`__.

.. automodule:: picmaker.instruments.hst_acs
   :members:

HST WFC3
~~~~~~~~
Source: `src/picmaker/instruments/hst_wfc3.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/hst_wfc3.py>`__.

.. automodule:: picmaker.instruments.hst_wfc3
   :members:

HST WFPC2
~~~~~~~~~
Source: `src/picmaker/instruments/hst_wfpc2.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/hst_wfpc2.py>`__.

.. automodule:: picmaker.instruments.hst_wfpc2
   :members:

HST NICMOS
~~~~~~~~~~
Source: `src/picmaker/instruments/hst_nicmos.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/hst_nicmos.py>`__.

.. automodule:: picmaker.instruments.hst_nicmos
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

Generic reader
~~~~~~~~~~~~~~
Source: `src/picmaker/instruments/zzz_generic.py
<https://github.com/SETI/rms-picmaker/blob/main/src/picmaker/instruments/zzz_generic.py>`__.

.. automodule:: picmaker.instruments.zzz_generic
   :members:
