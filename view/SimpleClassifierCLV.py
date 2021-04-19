#!/usr/bin/python

import argparse
import logging
import sys

from modis_water.model.SimpleClassifier import SimpleClassifier


# -----------------------------------------------------------------------------
# main
#
# This container does not have HDF4:  cisto-centos-singularity-gdal-3.0.0.sif
# 
# UL: 725, 1376
# LR: 735, 1386
#
# gdallocationinfo landWaterBad-MO-161.tif  973 1800  -->  cloud = 0 cur 3
# gdallocationinfo landWaterBad-MO-161.tif 1431 2049  -->  cloud = 2 cur 3
# gdallocationinfo landWaterBad-MO-161.tif  659 1372  -->  water = 3 cur 2
# gdallocationinfo landWaterBad-MO-161.tif  577 1411  -->  water = 3 cur 2
# 
# modis_water/view/SimpleClassifierCLV.py -i /att/pubrepo/ILAB/projects/modis_water/h09v05 -o /att/nobackup/rlgill/SystemTesting/modis-water -d 161 -r 4008 4633 1 1
# -----------------------------------------------------------------------------
def main():

    # Process command-line args.
    desc = 'Use this application to classify MODIS into water, land, bad' + \
           ' or no-data pixels.'

    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('-d',
                        type=int,
                        help='julian day of year; this is helpful for testing')

    parser.add_argument('-i',
                        default='.',
                        help='Path to input directory')

    parser.add_argument('-o',
                        default='.',
                        help='Path to output directory')

    parser.add_argument('-r',
                        nargs='+',
                        help='Rectangle to process; x y xLen, yLen')

    args = parser.parse_args()

    # Logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    sc = SimpleClassifier(args.i, args.o, args.d, logger)
    sc.run(args.r)

# -----------------------------------------------------------------------------
# Invoke the main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
