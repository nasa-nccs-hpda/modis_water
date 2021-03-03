#!/usr/bin/python

import argparse
import logging
import sys

from modis_water.model.SimpleClassifier import SimpleClassifier


# -----------------------------------------------------------------------------
# main
#
# modis_water/view/SimpleClassifierCLV.py -i /att/pubrepo/ILAB/projects/modis_water/h09v05 -m 1 -o /att/nobackup/rlgill/SystemTesting/modis-water
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

    args = parser.parse_args()

    # Logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    sc = SimpleClassifier(args.i, args.o, args.d, logger)
    sc.run()

# -----------------------------------------------------------------------------
# Invoke the main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
