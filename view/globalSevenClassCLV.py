#!/usr/bin/python
import argparse
import logging
import os
import sys

from modis_water.model.BandReader import BandReader as br
from modis_water.model.GlobalSevenClass import GlobalSevenClassMap


# -----------------------------------------------------------------------------
# main
#
# python modis_water/view/globalSevenClassCLV.py \
#   -hdf /path/to/hdfs \
#   --sensor MOD \
#   -y 2006 \
#   -o . \
# -----------------------------------------------------------------------------
def main():
    # Process command-line args.
    desc = 'Use this application to run and post-process annual MODIS water.'

    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('-hdf',
                        required=True,
                        help='Directory containing MOD44W HDF products')

    parser.add_argument('-anc',
                        required=True,
                        help='Path to antarctic ancillary product')

    parser.add_argument('-postprocessing',
                        required=True,
                        help='Path to post-processing dir')

    parser.add_argument('--sensor',
                        action='store',
                        nargs='*',
                        default=['MOD'],
                        choices=['MOD', 'MYD'],
                        help='Choose which sensor to use')

    parser.add_argument('--debug',
                        action='store_true',
                        help='show extra output and write intermediate files')

    parser.add_argument('-y',
                        required=True,
                        type=int,
                        help='Year to process')

    parser.add_argument('-o',
                        default='.',
                        help='Output directory')

    args = parser.parse_args()

    # Sensor name
    sensors = set(args.sensor) & br.SENSORS
    sensorsStr = '.'.join(list(sensors))

    # Logging
    logger = logging.getLogger()
    logLevel = logging.DEBUG if args.debug else logging.INFO
    logger.setLevel(logLevel)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logLevel)
    formatter = logging.Formatter(
        '%(asctime)s,%(msecs)03d %(levelname)-8s ' +
        '[%(filename)s:%(lineno)d] %(message)s'
    )
    ch.setFormatter(formatter)
    logFileName = f'globalSevenClassGeneration.{args.y}.' + \
        f'{sensorsStr}.log'
    fh = logging.FileHandler(os.path.join(args.o, logFileName))
    fh.setLevel(logLevel)
    fh.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(fh)

    # ---
    # Create the annual map.
    # ---
    logger.info('Creating global seven class map.')
    for sensor in sensors:

        globalSevenClass = GlobalSevenClassMap(args.hdf,
                                               args.anc,
                                               args.postprocessing,
                                               args.y,
                                               sensor,
                                               args.o,
                                               logger,
                                               args.debug)

        globalSevenClass.generateGlobalSevenClass()


# -----------------------------------------------------------------------------
# Invoke the main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
