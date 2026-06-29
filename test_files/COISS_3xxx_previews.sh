#!/bin/bash
################################################################################
# Create preview images for COISS_3xxx maps and images
#
# Sample usage:
#   COISS_3xxx_previews.sh <volumes path>/COISS_3001 ...
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
pwd

for volpath in "$@"
do
    # If path does not exist, maybe it was relative to the original working dir
    if [ -d $volpath ]; then
        volpath=$volpath
    else
        volpath=$HOME/$volpath
    fi

    outpath=${volpath/volumes/previews}
    mkdir -p $outpath/data/images

    cp $volpath/data/images/*.IMG $outpath/data/images/
    ./strip_attached_label.py $outpath/data/images/*.IMG

    for file in $outpath/data/images/*.IMG
    do
        echo $file
        picmaker $file --extension=jpg --versions=COISS_3xxx_previews.txt

        if [ "$?" = "2" ]; then
            exit 2
        fi

    done

    rm $outpath/data/images/*.IMG

    mkdir -p $outpath/data/maps
    cp $volpath/data/maps/*.PDF $outpath/data/maps

    for file in $outpath/data/maps/*.PDF
    do
        echo $file
        prefix=${file%.PDF}
        outfile=$prefix.png
        convert $file $outfile

        picmaker $outfile --extension=png --versions=COISS_3xxx_previews.txt

        if [ "$?" = "2" ]; then
            exit 2
        fi

        rm $outfile
        rm $file
    done

done

