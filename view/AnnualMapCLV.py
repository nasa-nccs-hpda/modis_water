#!/usr/bin/python

import argparse
import logging
import sys

from modis_water.model.AnnualMap import AnnualMap
from modis_water.model.BandReader import BandReader as br
from modis_water.model.RandomForestClassifier import RandomForestClassifier
from modis_water.model.SimpleClassifier import SimpleClassifier


# -----------------------------------------------------------------------------
# main
#
# modis_water/view/AnnualMapCLV.py -i /att/nobackup/rlgill/SystemTesting/modis-water3 -y 2020 -t h09v05 --classifier rf
# -----------------------------------------------------------------------------
def main():

    # Process command-line args.
    desc = 'Use this application to create an annual map from a directory ' + \
           'of predictions.'

    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('--classifier',
                        required=True,
                        default='simple',
                        choices=['simple', 'rf'],
                        help='Choose which classifier to use')

    parser.add_argument('-i',
                        default='.',
                        help='Path to input directory')

    parser.add_argument('-t',
                        required=True,
                        help='Tile to process; format h##v##')

    parser.add_argument('-y',
                        required=True,
                        type=int,
                        help='Year to process')

    args = parser.parse_args()

    # Classifier name
    classifierName = None

    if args.classifier == 'simple':
        classifierName = SimpleClassifier.CLASSIFIER_NAME

    if args.classifier == 'rf':
        classifierName = RandomForestClassifier.CLASSIFIER_NAME

    # Logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    AnnualMap.createAnnualMap(args.i,
                              args.y,
                              args.t,
                              br.MOD,
                              classifierName,
                              logger)


# -----------------------------------------------------------------------------
# Invoke the main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
