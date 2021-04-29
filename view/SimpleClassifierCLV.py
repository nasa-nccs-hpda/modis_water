#!/usr/bin/python

import argparse
import logging
import sys

from modis_water.model.SimpleClassifier import SimpleClassifier


# -----------------------------------------------------------------------------
# main
#
# modis_water/view/SimpleClassifierCLV.py 2003 --moDir /css/modis/Collection6.1/L2G/MOD09GA -t h09v05 -o /att/nobackup/rlgill/SystemTesting/modis-water -d 161 -r 4008 4633 1 1
# -----------------------------------------------------------------------------
def main():

    # Process command-line args.
    desc = 'Use this application to classify MODIS into water, land, bad' + \
           ' or no-data pixels.'

    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('-d',
                        type=int,
                        help='julian day of year; this is helpful for testing')

    parser.add_argument('--moDir',
                        default='.',
                        help='Path to MO input directory')

    parser.add_argument('-o',
                        default='.',
                        help='Path to output directory')

    parser.add_argument('-r',
                        nargs='+',
                        help='Rectangle to process; x y xLen, yLen')

    parser.add_argument('-t',
                        help='Tile to process; format h##v##')

    parser.add_argument('year',
                        type=int,
                        help='Year to process')

    args = parser.parse_args()

    # Logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    sc = SimpleClassifier(args.moDir, args.year, args.o, args.t, args.d,
                          logger)

    sc.run(args.r)


# -----------------------------------------------------------------------------
# Invoke the main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
