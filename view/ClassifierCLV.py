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
# modis_water/view/ClassifierCLV.py -y 2020 -t h09v05 -o /att/nobackup/rlgill/SystemTesting/modis-water4 --classifier rf --startDay 1 --endDay 1 --debug
# -----------------------------------------------------------------------------
def main():

    # Process command-line args.
    desc = 'Use this application to classify MODIS into water, land, bad' + \
           ' or no-data pixels.'

    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('-a',
                        default=False,
                        action='store_true',
                        help='create the annual map')

    parser.add_argument('--classifier',
                        required=True,
                        default='simple',
                        choices=['simple', 'rf'],
                        help='Choose which classifier to use')

    parser.add_argument('--debug',
                        action='store_true',
                        help='show extra output and write intermediate files')

    parser.add_argument('-o',
                        default='.',
                        help='Path to output directory')

    parser.add_argument('--startDay',
                        type=int,
                        default=1,
                        choices=range(1, 366),
                        metavar='1-365',
                        help='the earliest julian day to classify')

    parser.add_argument('--endDay',
                        type=int,
                        default=365,
                        choices=range(1, 366),
                        metavar='1-365',
                        help='the latest julian day to classify')

    parser.add_argument('-t',
                        required=True,
                        help='Tile to process; format h##v##')

    parser.add_argument('-y',
                        required=True,
                        type=int,
                        help='Year to process')

    args = parser.parse_args()

    # ---
    # Configure logging.
    # ---
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    # ---
    # Validate day range.
    # ---
    if args.startDay > args.endDay:
        raise ValueError('The start day must be before the end day.')

    # ---
    # Run the classifier.
    # ---
    classifier = None

    if args.classifier == 'simple':

        classifier = SimpleClassifier(args.y,
                                      args.t,
                                      args.o,
                                      startDay=args.startDay,
                                      endDay=args.endDay,
                                      logger=logger,
                                      sensors=set([br.MOD]),
                                      debug=args.debug)

    elif args.classifier == 'rf':

        classifier = RandomForestClassifier(args.y,
                                            args.t,
                                            args.o,
                                            startDay=args.startDay,
                                            endDay=args.endDay,
                                            logger=logger,
                                            sensors=set([br.MOD]),
                                            debug=args.debug)

    classifier.run()

    # ---
    # Create the annual map.
    # ---
    if args.a:

        logger.info('Creating annual map.')

        AnnualMap.createAnnualMap(args.o,
                                  args.y,
                                  args.t,
                                  br.MOD,
                                  classifier.getClassifierName(),
                                  logger)


# -----------------------------------------------------------------------------
# Invoke the main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
