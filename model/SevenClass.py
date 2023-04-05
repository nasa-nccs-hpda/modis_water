import os

from osgeo import gdal
from skimage.segmentation import find_boundaries
import numpy as np

from modis_water.model.BandReader import BandReader
from modis_water.model.QAMap import QAMap
from modis_water.model.Utils import Utils


# -------------------------------------------------------------------------
# SevenClassMap
# -------------------------------------------------------------------------
class SevenClassMap(object):

    DTYPE = np.uint8
    NODATA: int = 253

    # Seven Class Mask
    SC_SHALLOW_BIT_MASK: int = 128  # 0b10000000
    SC_LAND_BIT_MASK: int = 256  # 0b100000000
    SC_PL0_BIT_MASK: int = 512  # 0b1000000000
    SC_INLAND_BIT_MASK: int = 1024  # 0b10000000000
    SC_PL1_BIT_MASK: int = 2048  # 0b100000000000
    SC_DIN_BIT_MASK: int = 4096  # 0b1000000000000
    SC_MOC_BIT_MASK: int = 8192  # 0b10000000000000
    SC_DOC_BIT_MASK: int = 16384  # 0b100000000000000
    SC_NODATA_BIT_MASK: int = 32640  # 0b111111110000000

    SC_SHALLOW_VALUE: int = 0
    SC_LAND_VALUE: int = 1
    SC_PL0_VALUE: int = 2
    SC_INLAND_VALUE: int = 3
    SC_PL1_VALUE: int = 4
    SC_DEEP_INLAND_VALUE: int = 5
    SC_MODERATE_OCEAN_VALUE: int = 6
    SC_DEEP_OCEAN_VALUE: int = 7
    SC_NODATA_VALUE: int = 253

    SEVEN_CLASS_BIT_MASK_DICT: dict = {
        SC_SHALLOW_VALUE: SC_SHALLOW_BIT_MASK,
        SC_LAND_VALUE: SC_LAND_BIT_MASK,
        SC_PL0_VALUE: SC_PL0_BIT_MASK,
        SC_INLAND_VALUE: SC_INLAND_BIT_MASK,
        SC_PL1_VALUE: SC_PL1_BIT_MASK,
        SC_DEEP_INLAND_VALUE: SC_DIN_BIT_MASK,
        SC_MODERATE_OCEAN_VALUE: SC_MOC_BIT_MASK,
        SC_DEEP_OCEAN_VALUE: SC_DOC_BIT_MASK,
        SC_NODATA_VALUE: SC_NODATA_BIT_MASK
    }

    # -------------------------------------------------------------------------
    # generateSevenClass
    # -------------------------------------------------------------------------
    @staticmethod
    def generateSevenClass(
            sensor,
            year,
            tile,
            postProcessingDir,
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

        exclusionTile = tile[3:] in Utils.QA_ANTARCTIC_EXCLUSION

        if exclusionTile:

            if logger:
                msg = 'Antarctic tiles have no seven class. Filling nodata.'
                logger.info(msg)
            outputSevenClassArray.fill(SevenClassMap.NODATA)

        else:
            # Search and read in annual product and static seven-class.
            postProcessingArray = QAMap._getPostProcessingMask(
                tile,
                postProcessingDir)
            staticSevenArray = SevenClassMap._extractSevenClassArray(
                postProcessingArray)

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
    # _extractSevenClassArray
    # -------------------------------------------------------------------------
    @staticmethod
    def _extractSevenClassArray(postProcessingMask: np.ndarray) -> np.ndarray:
        scBitMaskDict = SevenClassMap.SEVEN_CLASS_BIT_MASK_DICT
        scNoDataBitMask = SevenClassMap.SC_NODATA_BIT_MASK
        scDataArray = np.zeros(
            (BandReader.COLS, BandReader.ROWS), dtype=SevenClassMap.DTYPE)
        for sevenClassValue in scBitMaskDict.keys():
            bitMask = scBitMaskDict[sevenClassValue]
            condition = (postProcessingMask & bitMask) == bitMask
            scDataArray = np.where(condition, sevenClassValue,
                                   scDataArray)
        noDataCondition = (postProcessingMask & scNoDataBitMask) == \
            scNoDataBitMask
        scDataArray = np.where(noDataCondition,
                               SevenClassMap.NODATA,
                               scDataArray)
        return scDataArray

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
