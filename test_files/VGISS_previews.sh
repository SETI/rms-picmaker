#!/bin/bash
################################################################################
# Create preview images for VGISS images
#
# Sample usage:
#   VGISS_previews.sh <volumes path>/VGISS_5101 ...
################################################################################

cd /Tools/pds-tools-dev-git/website/previews/VGISS

for volpath in "$@"
do
    outpath=${volpath/volumes/previews}
    mkdir -p $outpath/data

    python ../picmaker.py $volpath/DATA \
        --directory=$outpath/DATA --pattern=\*_CLEANED.IMG --strip _CLEANED \
        --recursive --down --verbose --proceed --extension=jpg \
        --percentiles 0.1 99.9 --trim=5 --versions=VGISS_versions.txt

    if [ "$?" = "2" ]; then
        exit 2
    fi

    python ../picmaker.py $volpath/DATA \
        --directory=$outpath/DATA --pattern=\*_RAW.IMG --strip _RAW \
        --recursive --down --verbose=2 --proceed --extension=jpg \
        --percentiles 0.1 99.9 --trim=5 --suffix=_full

    if [ "$?" = "2" ]; then
        exit 2
    fi

done

