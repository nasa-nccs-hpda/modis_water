#!/usr/bin/python

import argparse
import sys

from modis_water.model.SimpleClassifierValidator \
    import SimpleClassifierValidator


# -----------------------------------------------------------------------------
# main
#
# modis_water/view/SimpleClassifierValidatorCLV.py -d /att/nobackup/rlgill/SystemTesting/modis-water/ -l /att/nobackup/rlgill/SystemTesting/modis-water/Terra.Land.2019161.h09v05.bin
#
# modis_water/view/SimpleClassifierValidatorCLV.py -d /att/nobackup/rlgill/SystemTesting/modis-water/ -w /att/nobackup/rlgill/SystemTesting/modis-water/Terra.Water.2019161.h09v05.bin
# -----------------------------------------------------------------------------
def main():

    # Process command-line args.
    desc = 'Use this application to validate MODIS water images produced ' + \
           'by the Simple Classifier.'

    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('-d',
                        help='Path to the Simple Classifier images')

    parser.add_argument('-l',
                        help='Path to the land validation image')

    parser.add_argument('-p',
                        default='landWaterBad-MO-',
                        help='Prefix of the Simple Classifier images ' + \
                             'for which to search')

    parser.add_argument('-w',
                        help='Path to the water validation image')

    args = parser.parse_args()

    scv = SimpleClassifierValidator(args.d, args.p)
    
    if args.l:

        isValid = scv.runLand(args.l)
        print('Land valid: ', isValid)
    
    if args.w:

        isValid = scv.runWater(args.w)
        print('Water valid: ', isValid)
    
# -----------------------------------------------------------------------------
# Invoke the main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
