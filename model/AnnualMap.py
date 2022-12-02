import glob
import os

import numpy as np

from osgeo import gdal

from core.model.GeospatialImageFile import GeospatialImageFile
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

        exclusionDays = Utils.EXCLUSIONS.get(tile[3:])
            
        if exclusionDays and logger:
            
            logger.info('Found exclusion days for ' + tile + ': ' +
                        str(exclusionDays.start) + ' - ' + 
                        str(exclusionDays.end))
            
        for day in range(1, 366):

            if exclusionDays and \
                (day < exclusionDays.start or \
                 day > exclusionDays.end):
            
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
            else:
                if logger:
                    logger.info('Excluding day ' + str(day))

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
    def createAnnualMap(dailyDir, year, tile, sensor, classifierName, logger,
                        georeferenced=False):

        sumWater, sumLand, sumObs, probWater, mask = \
            AnnualMap.accumulateDays(dailyDir,
                                     year,
                                     tile,
                                     sensor,
                                     classifierName,
                                     logger)
        if georeferenced:
            projection, transform = AnnualMap.getGeospatialInformation(
                dailyDir, year, tile, sensor, classifierName)
        else:
            projection, transform = None, None

        AnnualMap.writeTotal(sumWater, year, tile, sensor, classifierName,
                             'SumWater', dailyDir)

        AnnualMap.writeTotal(sumLand, year, tile, sensor, classifierName,
                             'SumLand', dailyDir)

        AnnualMap.writeTotal(sumObs, year, tile, sensor, classifierName,
                             'SumObs', dailyDir)

        AnnualMap.writeTotal(probWater, year, tile, sensor, classifierName,
                             'ProbWater', dailyDir)

        AnnualMap.writeTotal(mask, year, tile, sensor, classifierName,
                             'Mask', dailyDir, projection, transform)

        name = Utils.getImageName(
            year, tile, sensor, classifierName, None, 'Mask')
        return os.path.join(dailyDir, name + '.tif')

    # -------------------------------------------------------------------------
    # geoGeoSpatialInformation
    # -------------------------------------------------------------------------
    @staticmethod
    def getGeospatialInformation(dailyDir, year, tile, sensor, classifierName):
        imageName = os.path.join(dailyDir, Utils.getImageName(
            year, tile, sensor, classifierName, day='***') + '.tif')
        oneDailyFileList = glob.glob(imageName)
        try:
            oneDailyFile = oneDailyFileList[0]
        except IndexError:
            msg = 'Could not find any daily files: {}'.format(imageName)
            raise RuntimeError(msg)
        ds = GeospatialImageFile(oneDailyFile)._getDataset()
        transform = ds.GetGeoTransform()
        projection = ds.GetProjection()
        return projection, transform

    # -------------------------------------------------------------------------
    # writeTotal
    # -------------------------------------------------------------------------
    @staticmethod
    def writeTotal(raster, year, tile, sensor, classifierName, postFix,
                   outDir, projection=None, transform=None):

        name = Utils.getImageName(year,
                                  tile,
                                  sensor,
                                  classifierName,
                                  None,
                                  postFix)

        Utils.writeRaster(outDir, raster, name,
                          projection=projection, transform=transform)
