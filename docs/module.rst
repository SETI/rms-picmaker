``picmaker`` Module
=====================

The command-line entry point and the two pipeline functions come first,
followed by the public API (re-exported from the top-level :mod:`picmaker`
package, so ``from picmaker import ...``) in alphabetical order, and then
the per-instrument readers.

.. autofunction:: picmaker.main.main
.. autofunction:: picmaker.picmaker.picmaker
.. autofunction:: picmaker.picmaker.picmaker1

.. autofunction:: picmaker.apply_colormap
.. autofunction:: picmaker.array_to_pil
.. autoclass:: picmaker.ColorNames
   :members:
.. autofunction:: picmaker.fill_zebra_stripes
.. autofunction:: picmaker.filter_pil_image
.. autofunction:: picmaker.get_filepaths
.. autofunction:: picmaker.get_limits
.. autofunction:: picmaker.get_outfile
.. autofunction:: picmaker.get_size
.. autofunction:: picmaker.get_versions
.. autoclass:: picmaker.ImageData
   :members:
.. autofunction:: picmaker.pad_pil_image
.. autofunction:: picmaker.pil_to_array
.. autofunction:: picmaker.read_image_array
.. autofunction:: picmaker.read_tiff16
.. autofunction:: picmaker.resize_pil_image
.. autofunction:: picmaker.rotate_rgb_array
.. autofunction:: picmaker.slice_array
.. autofunction:: picmaker.tint_by_nm
.. autofunction:: picmaker.validate_options
.. autofunction:: picmaker.wrap_pil_image
.. autofunction:: picmaker.write_pil
.. autofunction:: picmaker.write_tiff16

.. automodule:: picmaker.instruments.cassini_iss
   :members:
   :member-order: bysource
.. automodule:: picmaker.instruments.voyager_iss
   :members:
   :member-order: bysource
.. automodule:: picmaker.instruments.galileo_ssi
   :members:
   :member-order: bysource
.. automodule:: picmaker.instruments.hst_acs
   :members:
   :member-order: bysource
.. automodule:: picmaker.instruments.hst_wfc3
   :members:
   :member-order: bysource
.. automodule:: picmaker.instruments.hst_wfpc2
   :members:
   :member-order: bysource
.. automodule:: picmaker.instruments.hst_nicmos
   :members:
   :member-order: bysource
.. automodule:: picmaker.instruments.nh_lorri
   :members:
   :member-order: bysource
.. automodule:: picmaker.instruments.nh_mvic
   :members:
   :member-order: bysource
.. automodule:: picmaker.instruments.zzz_generic
   :members:
   :member-order: bysource
