import os

from osgeo import gdal
from skimage.segmentation import find_boundaries
import numpy as np

from modis_water.model.BandReader import BandReader
from modis_water.model.Utils import Utils


# -------------------------------------------------------------------------
# SevenClassMap
# -------------------------------------------------------------------------
class SevenClassMap(object):

    TIF_BASE_NAME = 'Master_7class_maxextent_'
    DTYPE = np.uint8
    NODATA = 253

    # -------------------------------------------------------------------------
    # generateSevenClass
    # -------------------------------------------------------------------------
    @staticmethod
    def generateSevenClass(
            sensor,
            year,
            tile,
            staticSevenClassDir,
            annualProductPath,
            classifierName,
            outDir,
            logger,
            geoTiff=False,
            georeferenced=False):

        annualProductDataset = gdal.Open(annualProductPath)
        annualProductArray = annualProductDataset.GetRasterBand(
            1).ReadAsArray()
        transform = annualProductDataset.GetGeoTransform() \
            if georeferenced else None
        projection = annualProductDataset.GetProjection() \
            if georeferenced else None

        outputSevenClassArray = np.zeros((BandReader.COLS, BandReader.ROWS))

        exclusionDays = Utils.EXCLUSIONS.get(tile[3:])

        if exclusionDays:

            if logger:
                msg = 'Antarctic tiles have no seven class. Filling nodata.'
                logger.info(msg)
            outputSevenClassArray.fill(SevenClassMap.NODATA)

        else:
            # Search and read in annual product and static seven-class.
            staticSevenPath = SevenClassMap._getStaticSevenClassPath(
                staticSevenClassDir, tile)
            staticSevenDataset = gdal.Open(staticSevenPath)
            staticSevenArray = staticSevenDataset.GetRasterBand(1).ReadAsArray()

            restArray = annualProductArray.copy()

            # Perform checks.
            outputSevenClassArray = np.where(
                annualProductArray == 0, 1, outputSevenClassArray)

            restArray = np.where(annualProductArray == 0, 0, restArray)

            annualEqualsOne = (annualProductArray == 1)

            deepInland = np.logical_and(annualEqualsOne, staticSevenArray == 5)

            outputSevenClassArray = np.where(
                deepInland, 5, outputSevenClassArray)

            restArray = np.where(deepInland, 0, restArray)

            shallowOcean = np.logical_and(
                annualEqualsOne, staticSevenArray == 0)

            outputSevenClassArray = np.where(shallowOcean, 0,
                                             outputSevenClassArray)

            restArray = np.where(shallowOcean, 0, restArray)

            moderateOcean = np.logical_and(
                annualEqualsOne, staticSevenArray == 6)

            outputSevenClassArray = np.where(moderateOcean, 6,
                                             outputSevenClassArray)

            restArray = np.where(moderateOcean, 0, restArray)

            deepOcean = np.logical_and(annualEqualsOne, staticSevenArray == 7)

            outputSevenClassArray = np.where(
                deepOcean, 7, outputSevenClassArray)

            restArray = np.where(deepOcean, 0, restArray)

            outputSevenClassArray = np.where(restArray == 1, 3,
                                             outputSevenClassArray)

            shoreLine = SevenClassMap._generateShoreline(outputSevenClassArray)

            outputSevenClassArray = np.where(shoreLine == 1, 2,
                                             outputSevenClassArray)

        # Write out the seven-class.
        outputSevenClassName = '{}44W.A{}.{}.{}.AnnualSevenClass.{}'.format(
            sensor,
            year,
            tile,
            classifierName,
            Utils.getPostStr())

        imageName = \
            SevenClassMap._writeSevenClass(
                outDir,
                outputSevenClassName,
                outputSevenClassArray,
                logger=logger,
                projection=projection,
                geoTiff=geoTiff,
                transform=transform)
        return imageName

    # -------------------------------------------------------------------------
    # getStaticSevenClassPath
    # -------------------------------------------------------------------------
    @staticmethod
    def _getStaticSevenClassPath(staticSevenClassDir, tile):
        staticSevenClassFileName = '{}{}.tif'.format(
            SevenClassMap.TIF_BASE_NAME, tile)
        staticSevenClassPath = os.path.join(
            staticSevenClassDir, staticSevenClassFileName)
        if os.path.exists(staticSevenClassPath):
            return staticSevenClassPath
        else:
            msg = 'Static MODIS 7-class: {} does not exist'\
                .format(staticSevenClassPath)
            raise FileNotFoundError(msg)

    # -------------------------------------------------------------------------
    # generateShoreline
    # -------------------------------------------------------------------------
    @staticmethod
    def _generateShoreline(sevenClass):
        inland = (sevenClass == 3)
        inland = np.where(inland, 1, 0)
        shorelineInland = SevenClassMap._shoreline(inland)
        shallow = np.where(sevenClass == 0, 1, 0)
        shorelineShallow = SevenClassMap._shoreline(shallow)
        shoreLine = np.logical_or(shorelineInland, shorelineShallow)
        shoreLine = np.where(shoreLine, 1, 0)
        shoreLine = np.where((shoreLine == 1) & (sevenClass == 1), 1, 0)
        return shoreLine

    # -------------------------------------------------------------------------
    # shoreline
    # -------------------------------------------------------------------------
    @staticmethod
    def _shoreline(arr_in):
        arr = np.where(arr_in > 100, 1, arr_in)
        arr = np.where(arr != 1, 0, arr)
        bnd = find_boundaries(arr,
                              connectivity=2,
                              mode='outer',
                              background=0).astype(SevenClassMap.DTYPE)
        return bnd

    # -------------------------------------------------------------------------
    # writeSevenClass
    # -------------------------------------------------------------------------
    @staticmethod
    def _writeSevenClass(outDir, outName, sevenClassArray, logger, projection,
                         transform, geoTiff=False):
        cols = sevenClassArray.shape[0]
        rows = sevenClassArray.shape[1] if len(
            sevenClassArray.shape) > 1 else 1
        fileType = '.tif' if geoTiff else '.bin'
        imageName = os.path.join(outDir, outName + fileType)
        driver = gdal.GetDriverByName('GTiff') if geoTiff \
            else gdal.GetDriverByName('ENVI')
        options = ['COMPRESS=LZW'] if geoTiff else []
        ds = driver.Create(imageName, cols, rows, 1, gdal.GDT_Byte,
                           options=options)
        if projection:
            ds.SetProjection(projection)
        if transform:
            ds.SetGeoTransform(transform)
        band = ds.GetRasterBand(1)
        band.WriteArray(sevenClassArray, 0, 0)
        band = None
        ds = None
        if logger:
            logger.info('Wrote annual seven class to: {}'.format(imageName))
        return imageName
