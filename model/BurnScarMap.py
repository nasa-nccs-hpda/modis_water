from glob import glob
import os

import numpy as np
from osgeo import gdal

from modis_water.model.Utils import Utils


# -------------------------------------------------------------------------
# BurnScarMap
# -------------------------------------------------------------------------
class BurnScarMap(object):
    DTYPE = np.uint8
    COLS = 2400
    ROWS = 2400

    # -------------------------------------------------------------------------
    # generateAnnualBurnScarMap
    # -------------------------------------------------------------------------
    @staticmethod
    def generateAnnualBurnScarMap(
            sensor,
            year,
            tile,
            mcdDir,
            classifierName,
            outDir,
            logger):

        # Test to see if tile in list of tiles which do not
        # need a burn scar product.
        inclusionDays = Utils.INCLUSIONS.get(tile[3:])
        exclusionDays = Utils.EXCLUSIONS.get(tile[3:])

        try:
            subdirhdfs = BurnScarMap._getAllFiles(
                path=mcdDir, year=year, tile=tile)
            burnScarMapList = [BurnScarMap._getMatFromHDF(
                subdir, 'Burn Date', 'Uncertainty') for subdir in subdirhdfs]
        except McdNotFoundError as McdException:
            if exclusionDays or inclusionDays:
                if logger:
                    logger.info('MCD64A1 not found for ' + tile +
                                '. Using empty burn scar product.')
                burnScarMapList = []
            else:
                raise McdException

        outputAnnualMask = BurnScarMap._logicalOrMask(burnScarMapList)
        outpath = BurnScarMap._setupBurnScarOutputPath(
            sensor=sensor,
            year=year,
            tile=tile,
            classifierName=classifierName,
            outputPath=outDir)
        BurnScarMap._outputBurnScarRaster(outPath=outpath,
                                          outmat=outputAnnualMask,
                                          logger=logger)
        return outpath

    # -------------------------------------------------------------------------
    # getMatFromHDF
    # -------------------------------------------------------------------------
    @staticmethod
    def _getMatFromHDF(hdf, substr, excludeStr):
        hdf = gdal.Open(hdf)
        subd = [sd for sd, _ in hdf.GetSubDatasets() if
                substr in sd and excludeStr not in sd][0]
        del hdf
        ds = gdal.Open(subd)
        burnScarMask = ds.GetRasterBand(1).ReadAsArray()
        burnScarMask = np.where(burnScarMask > 0, 1, 0)
        del ds
        return burnScarMask

    # -------------------------------------------------------------------------
    # getAllFiles
    # -------------------------------------------------------------------------
    @staticmethod
    def _getAllFiles(path, year, tile):
        pathToPrepend = os.path.join(path, str(year))
        try:
            subdirs = sorted(os.listdir(pathToPrepend))
        except FileNotFoundError:
            msg = 'Could not find dirs in {}'.format(pathToPrepend)
            raise McdNotFoundError(msg)

        subdirs = [os.path.join(pathToPrepend, subdir) for subdir in subdirs]

        try:
            subdirhdfs = [glob(os.path.join(subdir, '*{}*'.format(tile)))[0]
                          for subdir in subdirs]
        except IndexError:
            raise McdNotFoundError()

        return subdirhdfs

    # -------------------------------------------------------------------------
    # locicalOrMask
    # -------------------------------------------------------------------------
    @staticmethod
    def _logicalOrMask(matList):
        outputMat = np.zeros((BurnScarMap.COLS, BurnScarMap.ROWS))
        for mat in matList:
            outputMat = outputMat + mat
            mat = None
        outputMat = np.where(outputMat > 0, 1, 0)
        return outputMat.astype(np.uint8)

    # -------------------------------------------------------------------------
    # setupBurnScarOutputPath
    # -------------------------------------------------------------------------
    @staticmethod
    def _setupBurnScarOutputPath(sensor, year, tile, classifierName,
                                 outputPath):
        fileName = '{}.A{}.{}.{}.AnnualBurnScar.{}.tif'.format(
            sensor, year, tile, classifierName, Utils.getPostStr())
        outPath = os.path.join(outputPath, fileName)
        return outPath

    # -------------------------------------------------------------------------
    # outputBurnScarRaster
    # -------------------------------------------------------------------------
    @staticmethod
    def _outputBurnScarRaster(outPath, outmat, logger):
        # Output predicted binary raster masked with good-bad mask.
        ncols, nrows = BurnScarMap.COLS, BurnScarMap.ROWS
        driver = gdal.GetDriverByName('GTiff')
        outDs = driver.Create(outPath, ncols, nrows, 1,
                              gdal.GDT_Byte, options=['COMPRESS=LZW'])
        outBand = outDs.GetRasterBand(1)
        outBand.WriteArray(outmat)
        outDs.FlushCache()
        if logger:
            logger.info('Wrote annual burn scar map to: {}'.format(outPath))
        outDs = None
        outBand = None
        driver = None


# -------------------------------------------------------------------------
# McdNotFoundError
# -------------------------------------------------------------------------
class McdNotFoundError(Exception):
    """
    Custom exception used to only handle an error
    where the MCD64A1 is not found.
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        self._message = args[0] if args else None

    def __str__(self):
        base_str = 'Could not find MCD64A1 files.'
        if self._message:
            return f'{base_str} {self._message}'
        else:
            return base_str
