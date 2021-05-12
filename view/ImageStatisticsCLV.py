#!/usr/bin/python

import argparse
import sys

from modis_water.model.ImageStatistics import ImageStatistics


# -----------------------------------------------------------------------------
# main
#
# modis_water/view/ImageStatisticsCLV.py -d /att/nobackup/rlgill/SystemTesting/modis-water -v
# -----------------------------------------------------------------------------
def main():

    # Process command-line args.
    desc = 'Use this application to compute statistics on the water ' + \
           'classifier results.'
           
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('-d',
                        default='.',
                        help='Path to classified images')

    parser.add_argument('-v',
                        action='store_true',
                        help='Show verbose statistics')

    args = parser.parse_args()
    ImageStatistics.run(args.d, args.v)


# -----------------------------------------------------------------------------
# Invoke the main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
