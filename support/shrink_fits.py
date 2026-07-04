#!/usr/bin/env python3
"""Shrink FITS images by block-averaging every IMAGE HDU.

For each input file, every IMAGE object is reduced by an integer factor in each
direction via NxN-block pixel averaging over its trailing two (line, sample)
axes; any leading axes (e.g. a detector or band cube) are preserved. Edge pixels
that don't fill a full block are cropped. Integer arrays are rounded back to
their original integer type. Every header card is preserved except the
NAXIS1/NAXIS2 sizes, and BSCALE/BZERO scaling is kept intact (data is handled in
its raw stored representation), so the output stays FITS-standard compliant.

Usage:
    python support/shrink_fits.py [-f FACTOR] [-s SUFFIX] FILE [FILE ...]

Each output is written beside its input with SUFFIX inserted before ".fits"
(default "_small"), e.g. foo.fits -> foo_small.fits.
"""

import argparse
import os

import numpy as np
from astropy.io import fits

IMAGE_TYPES = ('PrimaryHDU', 'ImageHDU')


def block_average(data, f):
    *lead, ny, nx = data.shape
    ny2, nx2 = ny // f, nx // f
    cropped = data[..., :ny2 * f, :nx2 * f]
    reshaped = cropped.reshape(*lead, ny2, f, nx2, f)
    avg = reshaped.mean(axis=(-3, -1), dtype=np.float64)
    if np.issubdtype(data.dtype, np.integer):
        info = np.iinfo(data.dtype)
        rounded = np.clip(np.rint(avg), info.min, info.max)
        return rounded.astype(data.dtype)
    return avg.astype(data.dtype)


def shrink_file(path, factor, suffix):
    root, ext = os.path.splitext(path)
    out = root + suffix + ext
    hdul = fits.open(path, do_not_scale_image_data=True)
    for i, hdu in enumerate(hdul):
        if type(hdu).__name__ not in IMAGE_TYPES:
            continue
        data = hdu.data
        if data is None or data.ndim < 2:
            continue
        old_shape, old_dtype = data.shape, data.dtype
        new_data = block_average(data, factor)
        assert new_data.dtype == old_dtype, (new_data.dtype, old_dtype)
        hdu.data = new_data
        print(f'{os.path.basename(path)} HDU{i} {hdu.name}: '
              f'{old_shape} {old_dtype} -> {new_data.shape} {new_data.dtype}')
    hdul.writeto(out, overwrite=True)
    hdul.close()
    print(f'  wrote {out} ({os.path.getsize(out):,} bytes)\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('files', nargs='+', help='FITS files to shrink')
    parser.add_argument('-f', '--factor', type=int, default=5,
                        help='shrink factor in each direction (default: 5)')
    parser.add_argument('-s', '--suffix', default='_small',
                        help='suffix inserted before .fits (default: _small)')
    args = parser.parse_args()
    for path in args.files:
        shrink_file(path, args.factor, args.suffix)


if __name__ == '__main__':
    main()
