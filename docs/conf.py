#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Configuration file for the Sphinx documentation builder.

# -- Path setup --------------------------------------------------------------

import datetime
import importlib.metadata
import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

# Verify the source path exists
if not os.path.exists(os.path.abspath('../src')):
    import warnings
    warnings.warn("Source directory '../src' not found. API documentation may be incomplete.")

# -- Project information -----------------------------------------------------

project = 'rms-picmaker'
copyright = f'{datetime.date.today().year}, SETI Institute'
author = 'SETI Institute'

# The full version, including alpha/beta/rc tags
try:
    release = importlib.metadata.version('rms-picmaker')
except importlib.metadata.PackageNotFoundError:
    release = '1.0.0'  # fallback for development

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinxcontrib.mermaid',
    'myst_parser',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# CONTRIBUTING.md is split in contributing.rst; the tail fragment starts at
# "## ..." so MyST reports a false-positive heading-level warning.
suppress_warnings = ['myst.header']

# The suffix(es) of source filenames.
source_suffix = ['.rst', '.md']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = 'sphinx_rtd_theme'

add_module_names = False
autodoc_typehints_format = "short"

# Show class inheritance in automodule output. `:members:` is set
# explicitly per directive in `module.rst` rather than globally so
# that auto-documenting every imported re-export does not produce
# noisy duplicate entries.
autodoc_default_options = {
    'show-inheritance': True,
}

# -- Extension configuration -------------------------------------------------

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Intersphinx settings
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
    'pil': ('https://pillow.readthedocs.io/en/stable/', None),
    'astropy': ('https://docs.astropy.org/en/stable/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
    'pytest': ('https://docs.pytest.org/en/stable/', None),
}

# Nitpicky mode (sphinx-build -n) flags any unresolved cross-reference.
# Suppress references to the sibling SETI packages and a few legacy
# internal names that don't appear in any automodule output.
nitpick_ignore = [
    # Sibling SETI packages without published intersphinx inventories.
    ('py:class', 'vicar.VicarImage'),
    ('py:class', 'vicar.VicarError'),
    ('py:class', 'tabulation.Tabulation'),
    # Module-level dunders are intentional and not documented separately.
    ('py:data', '__all__'),
    ('py:data', '__version__'),
    # Module-level constants documented inline rather than as autodata.
    # autodoc skips undocumented module-level assignments by default;
    # adding explicit autodata directives for each would bloat
    # docs/module.rst without producing a more useful API page.
    ('py:data', 'picmaker._filters.FILTER_DICT'),
    ('py:data', 'picmaker._rgb.RGB_BY_NM'),
    ('py:data', 'picmaker._rgb.RFUNC'),
    ('py:data', 'picmaker._rgb.GFUNC'),
    ('py:data', 'picmaker._rgb.BFUNC'),
    ('py:data', 'picmaker.io.ImageInfo'),
    ('py:data', 'picmaker.instruments.galileo_ssi.FILTER_DICT'),
    ('py:data', 'picmaker.instruments.galileo_ssi.FILTER_NAMES'),
    ('py:data', 'picmaker.instruments.nh_mvic.FILTER_DICT'),
    ('py:data', 'picmaker.instruments.voyager_iss.FILTER_DICT'),
    # ColorNames is a singleton-style class whose only public surface
    # is a staticmethod; autodoc treats the ClassVar dicts as primary
    # members and the class itself disappears from the index.
    ('py:class', 'picmaker.colornames.ColorNames'),
    # Private CLI helpers are referenced by name for context but live
    # in `picmaker.cli` and are unit-tested directly; they are not part
    # of the documented public API.
    ('py:func', 'picmaker.cli._normalize_and_validate'),
]

# MyST-Parser settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

# Mermaid settings — use client-side rendering so no mmdc binary is required
# in CI or on ReadTheDocs.
mermaid_output_format = 'raw'
