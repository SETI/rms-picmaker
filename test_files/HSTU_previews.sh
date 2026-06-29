#!/bin/bash
################################################################################
# Create preview images for HST/WFPC2 images
#
# Sample usage:
#   HSTU_previews.sh <volumes path>/HSTU0_8634 ...
################################################################################

HOME=`pwd`

# get the absolute path of the executable
SELF_PATH=$(cd -P -- "$(dirname -- "$0")" && pwd -P) && SELF_PATH=$SELF_PATH/$(basename -- "$0")

# resolve symlinks
while [[ -h $SELF_PATH ]]; do
    # 1) cd to directory of the symlink
    # 2) cd to the directory of where the symlink points
    # 3) get the pwd
    # 4) append the basename
    DIR=$(dirname -- "$SELF_PATH")
    SYM=$(readlink "$SELF_PATH")
    SELF_PATH=$(cd "$DIR" && cd "$(dirname -- "$SYM")" && pwd)/$(basename -- "$SYM")
done

DIR=$(dirname "$SELF_PATH")
cd $DIR

for volpath in "$@"
do
    # If path does not exist, maybe it was relative to the original working dir
    if [ -d $volpath ]; then
        volpath=$volpath
    else
        volpath=$HOME/$volpath
    fi

    outpath=${volpath/volumes/previews}
    mkdir -p $outpath/DATA

    picmaker $volpath/DATA \
        --directory $outpath/DATA --pattern \*.LBL \
        --recursive --verbose=2 --proceed \
        --mosaic --pointer D0M_TIFF_DOCUMENT --alt_pointer D0M_JPEG_DOCUMENT \
        --strip _RAW --alt_strip _DRZ \
        --percentile 0.02 99.95 -x jpg --trim 100 --gamma 1.2 \
        --versions HSTU_previews.txt

    if [ "$?" = "2" ]; then
        exit 2
    fi

done

