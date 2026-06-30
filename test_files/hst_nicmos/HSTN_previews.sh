#!/bin/bash
################################################################################
# Create preview images for HST/NICMOS images
#
# Sample usage:
#   HSTN_previews.sh <volumes path>/HSTN0_9035 ...
################################################################################

FROM=`pwd`

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
        volpath=$FROM/$volpath
    fi

    outpath=${volpath/volumes/previews}
    mkdir -p $outpath/DATA

    picmaker $volpath/DATA \
        --directory $outpath/DATA --pattern \*.LBL \
        --percentile 0.02 99.98 -x jpg --gamma 0.5 \
        --recursive --proceed --versions HSTN_previews.txt

    if [ "$?" = "2" ]; then
        exit 2
    fi

done

