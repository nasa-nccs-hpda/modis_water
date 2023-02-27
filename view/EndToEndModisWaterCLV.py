#!/usr/bin/python
import argparse
import logging
import os
import sys

from modis_water.model.AnnualMap import AnnualMap
from modis_water.model.BandReader import BandReader as br
from modis_water.model.BurnScarMap import BurnScarMap
from modis_water.model.QAMap import QAMap
from modis_water.model.RandomForestClassifier import RandomForestClassifier
from modis_water.model.SevenClass import SevenClassMap
from modis_water.model.SimpleClassifier import SimpleClassifier


# -----------------------------------------------------------------------------
# main
#
# python modis_water/view/EndToEndModisWaterCLV.py -y 2006 -t h09v05 \
#   --classifier rf \
#   -static /explore/nobackup/projects/ilab/data/MODIS/ancillary/MODIS_Seven_Class_maxextent \
#   -dem /explore/nobackup/projects/ilab/data/MODIS/ancillary/MODIS_GMTED_DEM_slope/ \
#   -burn /css/modis/Collection6/L3/MCD64A1-BurnArea \
#   -o . \
#   -mod /css/modis/Collection6.1/L2G
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

    parser.add_argument('--sensor',
                        action='store',
                        nargs='*',
                        default=['MOD'],
                        choices=['MOD', 'MYD'],
                        help='Choose which sensor to use')

    parser.add_argument('--debug',
                        action='store_true',
                        help='show extra output and write intermediate files')

    # parser.add_argument('--startDay',
    #                     type=int,
    #                     default=1,
    #                     choices=range(1, 367),  # for leap year
    #                     metavar='1-366',
    #                     help='the earliest julian day to classify')
    #
    # parser.add_argument('--endDay',
    #                     type=int,
    #                     default=365,
    #                     choices=range(1, 367),  # for leap year
    #                     metavar='1-366',
    #                     help='the latest julian day to classify')

    parser.add_argument('-static',
                        required=True,
                        help='Path to static MODIS 250m 7-class product')

    parser.add_argument('-dem',
                        required=True,
                        help='Path to GMTED DEM')

    parser.add_argument('-impervious',
                        required=True,
                        help='Path to impervious surface dir')

    parser.add_argument('-ancillary',
                        required=True,
                        help='Path to static ancillary dataset dir')

    parser.add_argument('-mod',
                        required=True,
                        help='Path to MODIS MOD09GA and GQ products')

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

    parser.add_argument('--georeferenced',
                        action='store_true',
                        help='Write products out georeferenced')

    parser.add_argument('--geotiff',
                        action='store_true',
                        help='Write products out as geotiff instead of bin.')

    args = parser.parse_args()

    # Sensor name
    sensors = set(args.sensor) & br.SENSORS

    # Logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s; %(levelname)s; %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    ch.setFormatter(formatter)
    logFileName = f'{args.y}.{args.t}.{args.classifier}{sensors}.log'
    fh = logging.FileHandler(os.path.join(args.o, logFileName))
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(fh)

    # ---
    # Validate day range.
    # ---
    # if args.startDay > args.endDay:
    #     raise ValueError('The start day must be before the end day.')

    classifier = None

    if args.classifier == 'simple':

        classifier = SimpleClassifier(args.y,
                                      args.t,
                                      args.o,
                                      args.mod,
                                      startDay=1,  # args.startDay,
                                      endDay=366,  # args.endDay,
                                      logger=logger,
                                      sensors=sensors,
                                      debug=args.debug)

    elif args.classifier == 'rf':

        classifier = RandomForestClassifier(args.y,
                                            args.t,
                                            args.o,
                                            args.mod,
                                            startDay=1,  # args.startDay,
                                            endDay=366,  # args.endDay,
                                            logger=logger,
                                            sensors=sensors,
                                            debug=args.debug)

    classifier.run()

    # ---
    # Create the annual map.
    # ---
    logger.info('Creating annual map.')
    for sensor in sensors:
        annualMapPath = AnnualMap.createAnnualMap(
            args.o,
            args.y,
            args.t,
            sensor,
            classifier.getClassifierName(),
            logger,
            georeferenced=args.georeferenced)

        # ---
        # Post processing
        # ---
        logger.info('Creating annual burn scar map.')
        postAnnualBurnScarPath = BurnScarMap.generateAnnualBurnScarMap(
            sensor,
            args.y,
            args.t,
            args.burn,
            classifier.getClassifierName(),
            args.o,
            logger)

        logger.info('Post processing.')
        postAnnualPath = QAMap.generateQA(
            sensor,
            args.y,
            args.t,
            args.dem,
            postAnnualBurnScarPath,
            args.ancillary,
            args.impervious,
            annualMapPath,
            classifier.getClassifierName(),
            args.o,
            logger,
            geoTiff=args.geotiff,
            georeferenced=args.georeferenced)

        SevenClassMap.generateSevenClass(
            sensor,
            args.y,
            args.t,
            args.static,
            postAnnualPath,
            classifier.getClassifierName(),
            args.o,
            logger,
            geoTiff=args.geotiff,
            georeferenced=args.georeferenced)


# -----------------------------------------------------------------------------
# Invoke the main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
