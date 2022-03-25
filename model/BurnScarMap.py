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

    # -------------------------------------------------------------------------
    # generateAnnualBurnScarMap
    # -------------------------------------------------------------------------
    @staticmethod
    def generateAnnualBurnScarMap(year,
                                  tile,
                                  mcdDir,
                                  classifierName,
                                  outDir,
                                  logger):
        subdirhdfs = BurnScarMap._getAllFiles(
            path=mcdDir, year=year, tile=tile)
        burnScarMapList = [BurnScarMap._getMatFromHDF(
            subdir, 'Burn Date', 'Uncertainty') for subdir in subdirhdfs]
        outputAnnualMask = BurnScarMap._logicalOrMask(burnScarMapList)
        outpath = BurnScarMap._setupBurnScarOutputPath(
            year=year,
            tile=tile,
            classifierName=classifierName,
            outputPath=outDir)
        geo, proj, ncols, nrows = BurnScarMap._getBurnScarRasterInfo(
            subdirhdfs[0])
        BurnScarMap._outputBurnScarRaster(outPath=outpath,
                                          outmat=outputAnnualMask,
                                          geo=geo,
                                          proj=proj,
                                          ncols=ncols,
                                          nrows=nrows,
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
            raise RuntimeError(msg)

        subdirs = [os.path.join(pathToPrepend, subdir) for subdir in subdirs]

        try:
            subdirhdfs = [glob(os.path.join(subdir, '*{}*'.format(tile)))[0]
                          for subdir in subdirs]
        except IndexError:
            msg = 'Could not find burn scar files'
            raise RuntimeError(msg)

        return subdirhdfs

    # -------------------------------------------------------------------------
    # locicalOrMask
    # -------------------------------------------------------------------------
    @staticmethod
    def _logicalOrMask(matList):
        outputMat = np.empty(matList[0].shape)
        for mat in matList:
            outputMat = outputMat + mat
            mat = None
        outputMat = np.where(outputMat > 0, 1, 0)
        return outputMat.astype(np.uint8)

    # -------------------------------------------------------------------------
    # setupBurnScarOutputPath
    # -------------------------------------------------------------------------
    @staticmethod
    def _setupBurnScarOutputPath(year, tile, classifierName, outputPath):
        fileName = 'MOD.A{}.{}.{}.AnnualBurnScar.{}.tif'.format(
            year, tile, classifierName, Utils.getPostStr())
        outPath = os.path.join(outputPath, fileName)
        return outPath

    # -------------------------------------------------------------------------
    # getBurnScarRasterInfo
    # -------------------------------------------------------------------------
    @staticmethod
    def _getBurnScarRasterInfo(file):
        ds = gdal.Open(file, gdal.GA_ReadOnly)
        subd = [sd for sd, _ in ds.GetSubDatasets() if
                'Burn Date' in sd and 'Uncertainty' not in sd][0]
        ds = gdal.Open(subd, gdal.GA_ReadOnly)
        geo = ds.GetGeoTransform()
        proj = ds.GetProjection()
        ncols = ds.RasterXSize
        nrows = ds.RasterYSize
        ds = None
        return geo, proj, ncols, nrows

    # -------------------------------------------------------------------------
    # outputBurnScarRaster
    # -------------------------------------------------------------------------
    @staticmethod
    def _outputBurnScarRaster(outPath, outmat, geo, proj, ncols, nrows,
                              logger):
        # Output predicted binary raster masked with good-bad mask.
        driver = gdal.GetDriverByName('GTiff')
        outDs = driver.Create(outPath, ncols, nrows, 1,
                              gdal.GDT_Byte, options=['COMPRESS=LZW'])
        outDs.SetGeoTransform(geo)
        outDs.SetProjection(proj)
        outBand = outDs.GetRasterBand(1)
        outBand.WriteArray(outmat)
        outDs.FlushCache()
        if logger:
            logger.info('Wrote annual burn scar map to: {}'.format(outPath))
        outDs = None
        outBand = None
        driver = None
