# rms-picmaker

<!-- pyml disable MD025 -->

[![GitHub release; latest by date](https://img.shields.io/github/v/release/SETI/rms-picmaker)](https://github.com/SETI/rms-picmaker/releases)
[![GitHub Release Date](https://img.shields.io/github/release-date/SETI/rms-picmaker)](https://github.com/SETI/rms-picmaker/releases)
[![Test Status](https://img.shields.io/github/actions/workflow/status/SETI/rms-picmaker/run-tests.yml?branch=main)](https://github.com/SETI/rms-picmaker/actions)
[![Documentation Status](https://readthedocs.org/projects/rms-picmaker/badge/?version=latest)](https://rms-picmaker.readthedocs.io/en/latest/?badge=latest)
[![Code coverage](https://img.shields.io/codecov/c/github/SETI/rms-picmaker/main?logo=codecov)](https://codecov.io/gh/SETI/rms-picmaker)
<br />
[![PyPI - Version](https://img.shields.io/pypi/v/rms-picmaker)](https://pypi.org/project/rms-picmaker)
[![PyPI - Format](https://img.shields.io/pypi/format/rms-picmaker)](https://pypi.org/project/rms-picmaker)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/rms-picmaker)](https://pypi.org/project/rms-picmaker)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/rms-picmaker)](https://pypi.org/project/rms-picmaker)
<br />
[![GitHub commits since latest release](https://img.shields.io/github/commits-since/SETI/rms-picmaker/latest)](https://github.com/SETI/rms-picmaker/commits/main/)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/SETI/rms-picmaker)](https://github.com/SETI/rms-picmaker/commits/main/)
[![GitHub last commit](https://img.shields.io/github/last-commit/SETI/rms-picmaker)](https://github.com/SETI/rms-picmaker/commits/main/)
<br />
[![Number of GitHub open issues](https://img.shields.io/github/issues-raw/SETI/rms-picmaker)](https://github.com/SETI/rms-picmaker/issues)
[![Number of GitHub closed issues](https://img.shields.io/github/issues-closed-raw/SETI/rms-picmaker)](https://github.com/SETI/rms-picmaker/issues)
[![Number of GitHub open pull requests](https://img.shields.io/github/issues-pr-raw/SETI/rms-picmaker)](https://github.com/SETI/rms-picmaker/pulls)
[![Number of GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed-raw/SETI/rms-picmaker)](https://github.com/SETI/rms-picmaker/pulls)
<br />
![GitHub License](https://img.shields.io/github/license/SETI/rms-picmaker)
[![Number of GitHub stars](https://img.shields.io/github/stars/SETI/rms-picmaker)](https://github.com/SETI/rms-picmaker/stargazers)
![GitHub forks](https://img.shields.io/github/forks/SETI/rms-picmaker)
[![DOI](https://zenodo.org/badge/713118372.svg)](https://zenodo.org/badge/latestdoi/713118372)
<!-- start-after-point -->

# Features

`rms-picmaker` converts binary 2-D or 3-D astronomy images — PDS3-labeled images,
VICAR images, and FITS images — into JPEG, TIFF, PNG, or other popular display
formats. It is used by the PDS Ring-Moon Systems Node (SETI Institute) for image
preview generation.

It ships both as a command-line tool (`picmaker`) and as an importable Python
library (`from picmaker import picmaker`). Features include
percentile stretching, gamma correction, histogram equalization, colormap and
filter-aware tinting, cropping, resizing, padding, and 16-bit TIFF output.

# Installation

The `picmaker` module is available via the `rms-picmaker` package on PyPI and can be
installed with:

```sh
pip install rms-picmaker
```

# Getting Started

Convert a single image to JPEG with the defaults:

```sh
picmaker input.IMG --directory out/
```

Process a directory of VICAR images into 8-bit PNGs with a 1–99% percentile
stretch and a gamma of 0.7:

```sh
picmaker -r --pattern '*.vic' --extension png \
         --percentiles 1 99 --gamma 0.7 \
         --directory out/ inputs/
```

Use as a library:

```python
from picmaker import picmaker
from picmaker.options import get_parser

# Let the argument parser fill in every default, then run the pipeline.
options = get_parser().parse_args([
    'input.IMG',
    '--directory', 'out/',
    '--extension', 'jpg',
    '--percentiles', '1', '99',
    '--gamma', '0.7',
])
picmaker(**vars(options))
```

> **Security note:** `picmaker` also accepts Python pickle files as a fallback
> input format. Only pass pickle inputs you trust — unpickling executes
> arbitrary code from the file.

Details are available in the [module documentation](https://rms-picmaker.readthedocs.io/en/latest/module.html).

# Contributing

Information on contributing to this package can be found in the
[Contributing Guide](https://github.com/SETI/rms-picmaker/blob/main/CONTRIBUTING.md).

# Links

- [Documentation](https://rms-picmaker.readthedocs.io)
- [Repository](https://github.com/SETI/rms-picmaker)
- [Issue tracker](https://github.com/SETI/rms-picmaker/issues)
- [PyPi](https://pypi.org/project/rms-picmaker)

# Licensing

This code is licensed under the [Apache License v2.0](https://github.com/SETI/rms-picmaker/blob/main/LICENSE).
