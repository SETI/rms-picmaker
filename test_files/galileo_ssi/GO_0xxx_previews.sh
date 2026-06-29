#!/bin/bash
################################################################################
# Create preview images for GO_0xxx images
#
# Sample usage:
#   GO_0xxx_previews.sh <volumes path>/GO_0xxx/GO_0017 ...
################################################################################

versionpath=${0/.sh/.txt}               # change ".sh" to ".txt" in script path

for volpath in "$@"
do
    outpath=${volpath/volumes/previews} # change "volumes" to "previews"
    mkdir -p $outpath

    /usr/local/bin/python3 /Users/Shared/bin/picmaker $volpath \
        --directory=$outpath \
        --recursive --down --verbose=2 --proceed --extension=jpg \
        --pattern=\*.IMG \
        --footprint=5 --trim-zeros --versions=$versionpath
done

