#!/usr/bin/python
import argparse
import logging
import os
import sys

from modis_water.model.PostProcessingGenerator import PostProcessingMap


# -----------------------------------------------------------------------------
# main
#
# Example usage:
# STATIC_DIR="MODIS_Seven_Class_maxextent_v70.0.1"
# DEM_DIR="/panfs/ccds02/nobackup/projects/ilab/data/MODIS/ancillary/MODIS_GMTED_DEM_slope/MODIS_GMTED_DEM_slope_v61.0.0"  # noqa: E501
# ANC_DIR="/panfs/ccds02/nobackup/projects/ilab/data/MODIS/ancillary/MODIS_ancillary_data/MODIS_ancillary_data_v70.0.0"  # noqa: E501
# IMP_DIR="/panfs/ccds02/nobackup/projects/ilab/data/MODIS/ancillary/MODIS_impervious_data/MODIS_impervious_data_v61.0.0"  # noqa: E501
# PRM_DIR="/panfs/ccds02/nobackup/projects/ilab/data/MODIS/ancillary/MODIS_permanent_rivers/MODIS_permanent_rivers_v61.0.0"  # noqa: E501
#
# singularity exec -B /explore,/panfs,/css,/nfs4m --env PYTHONPATH=$PWD:$PWD/modis_water:$PWD/core /explore/nobackup/projects/ilab/containers/modis-water-4.0.0-2024.02 \  # noqa: E501
#     python modis_water/view/PostProcessingMaskCLV.py \
#     -t $1 \
#     -o test_output \
#     -impervious ${IMP_DIR} \
#     -permanent ${PRM_DIR} \
#     -gmted ${DEM_DIR} \
#     -ancillary ${ANC_DIR} \
#     -sevenclass ${STATIC_DIR}
# -----------------------------------------------------------------------------
def main():
    # Process command-line args.
    desc = 'Use this application to run and post-process annual MODIS water.'

    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('--debug',
                        action='store_true',
                        help='show extra output and write intermediate files')

    parser.add_argument('-t',
                        required=True,
                        help='Tile to process; format h##v##')

    parser.add_argument('-o',
                        default='.',
                        help='Output directory')

    parser.add_argument(
        '-impervious',
        required=True,
        help='Directory containing impervious surface ancillary products.')

    parser.add_argument(
        '-permanent',
        required=True,
        help='Directory containing permanent water ancillary products.')

    parser.add_argument('-gmted',
                        required=True,
                        help='Directory containing GMTED ancillary products.')

    parser.add_argument('-ancillary',
                        required=True,
                        help='Directory containing ancillary mask products.')

    parser.add_argument(
        '-sevenclass',
        required=True,
        help='Directory containing seven-class ancillary mask products.')

    args = parser.parse_args()

    # Logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s; %(levelname)s; %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    ch.setFormatter(formatter)
    logFileName = f'{args.t}.postprocessingmaskgeneration.log'
    fh = logging.FileHandler(os.path.join(args.o, logFileName))
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(fh)

    postProcessingMap = PostProcessingMap(tile=args.t,
                                          outDir=args.o,
                                          imperviousDir=args.impervious,
                                          permanentWaterDir=args.permanent,
                                          gmtedDir=args.gmted,
                                          ancillaryDir=args.ancillary,
                                          sevenClassDir=args.sevenclass)
    postProcessingMap.generatePostProcessingMask()


# -----------------------------------------------------------------------------
# Invoke the main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
