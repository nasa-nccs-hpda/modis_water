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
        demSlopeDatasetPath = QAMap.getStaticDatasetPath(demDir, demSearchTerm)

        annualProductDataDict = QAMap.readRaster(annualProductPath)
        demSlopeDataDict = QAMap.readRaster(demSlopeDatasetPath)

        annualProductArray = annualProductDataDict['array']
        demSlopeDataArray = demSlopeDataDict['array']
        burnScarArray = QAMap.buildAndReadTranslatedVrt(burnedAreaPath)

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

        annualPath = QAMap.writeProduct(outDir,
                                        annualProductOutputName,
                                        annualProductOutput,
                                        annualProductDataDict['transform'],
                                        annualProductDataDict['projection'],
                                        logger=logger)
        _ = QAMap.writeProduct(outDir,
                               qaOutputName,
                               qaOutput,
                               annualProductDataDict['transform'],
                               annualProductDataDict['projection'],
                               logger=logger)

        return annualPath

    # -------------------------------------------------------------------------
    # getStaticDatasetPath
    # -------------------------------------------------------------------------
    @staticmethod
    def getStaticDatasetPath(inDir, searchTerm):
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
    def buildAndReadTranslatedVrt(filepath, tr=231.656358, bandNum=1):
        vrt_opts = gdal.BuildVRTOptions(xRes=tr, yRes=tr, resampleAlg='cubic')
        vrt = gdal.BuildVRT('tmp.vrt', filepath, options=vrt_opts)
        band = vrt.GetRasterBand(bandNum).ReadAsArray()
        print(type(band[0][0]))
        del vrt
        if os.path.exists('tmp.vrt'):
            os.remove('tmp.vrt')
        return band

    # -------------------------------------------------------------------------
    # readRaster
    # -------------------------------------------------------------------------
    @staticmethod
    def readRaster(rasterPath):
        rasterDataDict = {}
        try:
            rasterDataset = gdal.Open(rasterPath)
            rasterDataDict['transform'] = \
                rasterDataset.GetGeoTransform()
            rasterDataDict['projection'] = \
                rasterDataset.GetProjection()
            rasterDataDict['array'] = \
                rasterDataset.GetRasterBand(1).ReadAsArray()\
                .astype(QAMap.DTYPE)
            del rasterDataset
            return rasterDataDict
        except Exception as e:
            msg = 'RuntimeError encountered while attempting to open: ' + \
                '{} '.format(rasterPath) + \
                '{}'.format(e)
            raise RuntimeError(msg)

    # -------------------------------------------------------------------------
    # writeProduct
    # -------------------------------------------------------------------------
    @staticmethod
    def writeProduct(outDir, outName, array, transform,
                     projection, logger):
        cols = array.shape[0]
        rows = array.shape[1] if len(
            array.shape) > 1 else 1
        imageName = os.path.join(outDir, outName + '.tif')
        driver = gdal.GetDriverByName('GTiff')
        ds = driver.Create(imageName, cols, rows, 1, gdal.GDT_Byte,
                           options=['COMPRESS=LZW'])
        ds.SetGeoTransform(transform)
        ds.SetProjection(projection)
        band = ds.GetRasterBand(1)
        band.WriteArray(array)
        ds.FlushCache()
        if logger:
            logger.info('Wrote annual QA products to: {}'.format(imageName))
        return imageName
