#!/usr/bin/python

import argparse
import logging
import sys

from modis_water.model.AnnualMap import AnnualMap
from modis_water.model.BandReader import BandReader as br
from modis_water.model.SevenClass import SevenClassMap
from modis_water.model.BurnScarMap import BurnScarMap
from modis_water.model.QAMap import QAMap
from modis_water.model.RandomForestClassifier import RandomForestClassifier
from modis_water.model.SimpleClassifier import SimpleClassifier


# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------
def main():

    # Process command-line args.
    desc = 'Use this application to run and post-process annual MODIS water.'

    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('--classifier',
                        required=True,
                        default='simple',
                        choices=['simple', 'rf'],
                        help='Choose which classifier to use')

    parser.add_argument('--debug',
                        action='store_true',
                        help='show extra output and write intermediate files')

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

    parser.add_argument('-static',
                        required=True,
                        help='Path to static MODIS 250m 7-class product')

    parser.add_argument('-dem',
                        required=True,
                        help='Path to GMTED DEM')

    parser.add_argument('-burn',
                        required=True,
                        help='Path to MCD burn scar product')

    parser.add_argument('-t',
                        required=True,
                        help='Tile to process; format h##v##')

    parser.add_argument('-y',
                        required=True,
                        type=int,
                        help='Year to process')

    parser.add_argument('-o',
                        default='.',
                        help='Output directory')

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

    # ---
    # Validate day range.
    # ---
    if args.startDay > args.endDay:
        raise ValueError('The start day must be before the end day.')

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
    logger.info('Creating annual map.')
    annualMapPath = AnnualMap.createAnnualMap(args.o,
                                              args.y,
                                              args.t,
                                              br.MOD,
                                              classifier.getClassifierName(),
                                              logger)

    # ---
    # Post processing
    # ---
    logger.info('Creating annual burn scar map.')
    postAnnualBurnScarPath = BurnScarMap.generateAnnualBurnScarMap(
        args.y,
        args.t,
        args.burn,
        classifier.getClassifierName(),
        args.o,
        logger
    )

    logger.info('Post processing.')
    postAnnualPath = QAMap.generateQA(args.y,
                                      args.t,
                                      args.dem,
                                      postAnnualBurnScarPath,
                                      annualMapPath,
                                      classifier.getClassifierName(),
                                      args.o,
                                      logger)

    SevenClassMap.generateSevenClass(args.y,
                                     args.t,
                                     args.static,
                                     postAnnualPath,
                                     classifierName,
                                     args.o,
                                     logger)


# -----------------------------------------------------------------------------
# Invoke the main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
