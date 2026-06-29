#!/bin/bash
################################################################################
# Create preview images for COISS images, Jupiter and Saturn. This version
# overwrites and preview images that already exist.
#
# Sample usage:
#   COISS_previews.sh [.../holdings/volumes/COISS_2xxx/COISS_2100] ...
#
# Output files are writtin into the parallel directory tree:
#    .../holdings/volumes/COISS_2xxx/COISS_2100/data/...
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
    mkdir -p $outpath/data

    picmaker $volpath/data \
        --directory $outpath/data --pattern \*.IMG \
        --recursive --proceed --versions=COISS_previews.txt

    if [ "$?" = "2" ]; then
        exit 2
    fi

done

