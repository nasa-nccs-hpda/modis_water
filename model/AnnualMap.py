
import os

import numpy as np

from osgeo import gdal

from modis_water.model.BandReader import BandReader
from modis_water.model.Classifier import Classifier
from modis_water.model.Utils import Utils


# -----------------------------------------------------------------------------
# Class AnnualMap
# -----------------------------------------------------------------------------
class AnnualMap(object):

    # -------------------------------------------------------------------------
    # accumulateDays
    # -------------------------------------------------------------------------
    @staticmethod
    def accumulateDays(dailyDir, year, tile, sensor, classifierName, logger):

        shape = (BandReader.COLS, BandReader.ROWS)
        sumWater = np.zeros(shape, dtype=np.int16)
        sumLand = np.zeros(shape, dtype=np.int16)
        sumBad = np.zeros(shape, dtype=np.int16)

        for day in range(1, 366):

            sumWater, sumLand, sumBad = \
                AnnualMap.accumulateDay(dailyDir,
                                        year,
                                        day,
                                        tile,
                                        sensor,
                                        classifierName,
                                        sumWater,
                                        sumLand,
                                        sumBad,
                                        logger)

        sumObs = sumWater + sumLand + sumBad

        probWater = \
            np.where(sumWater + sumLand > 0,
                     (sumWater / (sumWater + sumLand) * 100).astype(np.int16),
                     0)

        mask = np.where(probWater >= 50,
                        Classifier.WATER,
                        Classifier.LAND).astype(np.int16)

        return sumWater, sumLand, sumObs, probWater, mask

    # -------------------------------------------------------------------------
    # accummulateDay
    # -------------------------------------------------------------------------
    @staticmethod
    def accumulateDay(dailyDir, year, day, tile, sensor, classifierName,
                      sumWater, sumLand, sumBad, logger):

        # Read the daily probability image.
        imageName = \
            os.path.join(dailyDir,
                         Utils.getImageName(year, tile, sensor, classifierName,
                                            day) + '.tif')

        if os.path.exists(imageName):

            ds = gdal.Open(imageName)
            image = ds.ReadAsArray()

            sumWater += np.where(image == Classifier.WATER, 1, 0)
            sumLand += np.where(image == Classifier.LAND, 1, 0)
            sumBad += np.where(image == Classifier.BAD_DATA, 1, 0)

        else:

            if logger:
                logger.warn('Day image does not exist: ' + imageName)

        return sumWater, sumLand, sumBad

    # -------------------------------------------------------------------------
    # createAnnualMap
    # -------------------------------------------------------------------------
    @staticmethod
    def createAnnualMap(dailyDir, year, tile, sensor, classifierName, logger):

        sumWater, sumLand, sumObs, probWater, mask = \
            AnnualMap.accumulateDays(dailyDir,
                                     year,
                                     tile,
                                     sensor,
                                     classifierName,
                                     logger)

        AnnualMap.writeTotal(sumWater, year, tile, sensor, classifierName,
                             'SumWater', dailyDir)

        AnnualMap.writeTotal(sumLand, year, tile, sensor, classifierName,
                             'SumLand', dailyDir)

        AnnualMap.writeTotal(sumObs, year, tile, sensor, classifierName,
                             'SumObs', dailyDir)

        AnnualMap.writeTotal(probWater, year, tile, sensor, classifierName,
                             'ProbWater', dailyDir)

        AnnualMap.writeTotal(mask, year, tile, sensor, classifierName,
                             'Mask', dailyDir)

    # -------------------------------------------------------------------------
    # writeTotal
    # -------------------------------------------------------------------------
    @staticmethod
    def writeTotal(raster, year, tile, sensor, classifierName, postFix,
                   outDir):

        name = Utils.getImageName(year,
                                  tile,
                                  sensor,
                                  classifierName,
                                  None,
                                  postFix)

        Utils.writeRaster(outDir, raster, name)