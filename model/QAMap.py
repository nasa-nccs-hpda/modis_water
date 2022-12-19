import glob
import os

from osgeo import gdal
import rasterio as rio
import numpy as np

from modis_water.model.BandReader import BandReader
from modis_water.model.Utils import Utils


# -------------------------------------------------------------------------
# QAMap
# -------------------------------------------------------------------------
class QAMap(object):

    DTYPE = np.uint8
    NCOLS, NROWS = 4800, 4800

    # -------------------------------------------------------------------------
    # generateSevenClass
    # -------------------------------------------------------------------------
    @staticmethod
    def generateQA(
            sensor,
            year,
            tile,
            demDir,
            burnedAreaPath,
            annualProductPath,
            classifierName,
            outDir,
            logger,
            geoTiff=False,
            georeferenced=False):

        # Search for, read in our post processing rasters.
        demSlopeDataArray = QAMap._getGMTEDArray(tile, demDir)

        annualProductDataset = gdal.Open(annualProductPath)
        annualProductArray = annualProductDataset.GetRasterBand(
            1).ReadAsArray()

        burnScarArray = QAMap._readAndResample(burnedAreaPath)

        annualProductOutput = annualProductArray.copy()
        qaOutput = np.zeros(annualProductArray.shape, dtype=QAMap.DTYPE)

        # Perform checks.
        annualProductOutput = np.where(
            burnScarArray == 1, 0, annualProductArray)
        qaOutput = np.where(burnScarArray == 1, 6, qaOutput)

        qaOutput = np.where(
            (demSlopeDataArray > 5) & (annualProductArray == 1), 4, qaOutput)
        annualProductOutput = np.where(
            demSlopeDataArray > 5, 0, annualProductArray)

        # Write out the final annual product in addition to the QA map.
        annualProductOutputName = \
            '{}44W.A{}.{}.{}.AnnualWaterProduct.{}'.format(
                sensor, year, tile, classifierName, Utils.getPostStr())
        qaOutputName = '{}44W.A{}.{}.{}.AnnualWaterProductQA.{}'.format(
            sensor, year, tile, classifierName, Utils.getPostStr())

        transform = annualProductDataset.GetGeoTransform() \
            if georeferenced else None
        projection = annualProductDataset.GetProjection() \
            if georeferenced else None

        annualPath = QAMap._writeProduct(
            outDir,
            annualProductOutputName,
            annualProductOutput,
            logger=logger,
            projection=projection,
            transform=transform,
            geoTiff=geoTiff)

        QAMap._writeProduct(outDir,
                            qaOutputName,
                            qaOutput,
                            logger=logger,
                            projection=projection,
                            transform=transform,
                            geoTiff=geoTiff)

        return annualPath

    # -------------------------------------------------------------------------
    # _getGMTEDArray
    # -------------------------------------------------------------------------
    @staticmethod
    def _getGMTEDArray(tile, demDir):
        exclusionDays = Utils.EXCLUSIONS.get(tile[3:])
        try:
            demSearchTerm = 'GMTED.{}.slope.tif'.format(tile)
            demSlopeDatasetPath = QAMap._getStaticDatasetPath(
                demDir, demSearchTerm)
            demSlopeDataset = gdal.Open(demSlopeDatasetPath)
            demSlopeDataArray = demSlopeDataset.GetRasterBand(
                1).ReadAsArray()
        except FileNotFoundError as initialException:
            if exclusionDays:
                demSlopeDataArray = np.zeros(
                    (BandReader.COLS, BandReader.ROWS),
                    dtype=QAMap.DTYPE)
            else:
                raise initialException
        return demSlopeDataArray

    # -------------------------------------------------------------------------
    # getStaticDatasetPath
    # -------------------------------------------------------------------------
    @staticmethod
    def _getStaticDatasetPath(inDir, searchTerm):
        searchPath = os.path.join(
            inDir, searchTerm)
        staticPath = glob.glob(searchPath)
        if len(staticPath) > 0:
            staticPath = staticPath[0]
            return staticPath
        else:
            msg = '{} not found.'.format(searchPath)
            raise FileNotFoundError(msg)

    # -------------------------------------------------------------------------
    # _readAndResample
    # -------------------------------------------------------------------------
    @staticmethod
    def _readAndResample(filepath, bandNum=1):
        outShape = (BandReader.COLS, BandReader.ROWS)
        resamplingMethod = rio.enums.Resampling(2)
        with rio.open(filepath) as dataset:
            band = dataset.read(bandNum, out_shape=outShape,
                                resampling=resamplingMethod)
        return band

    # -------------------------------------------------------------------------
    # writeProduct
    # -------------------------------------------------------------------------
    @staticmethod
    def _writeProduct(outDir, outName, array, logger, projection, transform,
                      geoTiff=False):
        cols = array.shape[0]
        rows = array.shape[1] if len(
            array.shape) > 1 else 1
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
        band.WriteArray(array, 0, 0)
        band = None
        ds = None
        if logger:
            logger.info('Wrote annual QA products to: {}'.format(imageName))
        return imageName
