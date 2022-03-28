import glob
import os

from osgeo import gdal
import numpy as np

from modis_water.model.Utils import Utils


# -------------------------------------------------------------------------
# QAMap
# -------------------------------------------------------------------------
class QAMap(object):

    DTYPE = np.uint8
    TR = 231.656358263958253

    # -------------------------------------------------------------------------
    # generateSevenClass
    # -------------------------------------------------------------------------
    @staticmethod
    def generateQA(year,
                   tile,
                   demDir,
                   burnedAreaPath,
                   annualProductPath,
                   classifierName,
                   outDir,
                   logger):

        # Search for, read in our post processing rasters.
        demSearchTerm = 'GMTED.{}.slope.tif'.format(tile)
        demSlopeDatasetPath = QAMap._getStaticDatasetPath(
            demDir, demSearchTerm)

        annualProductDataset = gdal.Open(annualProductPath)
        demSlopeDataset = gdal.Open(demSlopeDatasetPath)

        annualProductArray = annualProductDataset.GetRasterBand(
            1).ReadAsArray()
        demSlopeDataArray = demSlopeDataset.GetRasterBand(
            1).ReadAsArray()
        burnScarArray = QAMap._buildAndReadTranslatedVrt(burnedAreaPath)

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
            'MOD.A{}.{}.{}.AnnualWaterProduct.{}'.format(
                year, tile, classifierName, Utils.getPostStr())
        qaOutputName = 'MOD.A{}.{}.{}.AnnualWaterProductQA.{}'.format(
            year, tile, classifierName, Utils.getPostStr())

        annualPath = QAMap._writeProduct(
            outDir,
            annualProductOutputName,
            annualProductOutput,
            logger=logger)

        QAMap._writeProduct(outDir,
                            qaOutputName,
                            qaOutput,
                            logger=logger)

        return annualPath

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
    # buildAndReadTranslatedVrt
    # -------------------------------------------------------------------------
    @staticmethod
    def _buildAndReadTranslatedVrt(filepath, tr=231.656358, bandNum=1):
        vrt_opts = gdal.BuildVRTOptions(xRes=tr, yRes=tr, resampleAlg='cubic')
        vrt = gdal.BuildVRT('tmp.vrt', filepath, options=vrt_opts)
        band = vrt.GetRasterBand(bandNum).ReadAsArray()
        del vrt
        if os.path.exists('tmp.vrt'):
            os.remove('tmp.vrt')
        return band

    # -------------------------------------------------------------------------
    # writeProduct
    # -------------------------------------------------------------------------
    @staticmethod
    def _writeProduct(outDir, outName, array, logger):
        cols = array.shape[0]
        rows = array.shape[1] if len(
            array.shape) > 1 else 1
        imageName = os.path.join(outDir, outName + '.tif')
        driver = gdal.GetDriverByName('GTiff')
        ds = driver.Create(imageName, cols, rows, 1, gdal.GDT_Byte,
                           options=['COMPRESS=LZW'])
        band = ds.GetRasterBand(1)
        band.WriteArray(array)
        ds.FlushCache()
        if logger:
            logger.info('Wrote annual QA products to: {}'.format(imageName))
        return imageName
