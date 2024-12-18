import os
from pathlib import Path
import re

import numpy as np

from osgeo import gdal
from osgeo import gdal_array
from osgeo.osr import SpatialReference

from modis_water.model.BandReader import BandReader as br
from modis_water.model.MaskGenerator import MaskGenerator
from modis_water.model.Utils import Utils


# -----------------------------------------------------------------------------
# class Classifier
#
# Directory Structure: base-directory/MOD09GA/year
#                                     MOD09GQ/year
#                                     MYD09GA/year
#                                     MYD09GQ/year
#
# -----------------------------------------------------------------------------
class Classifier(object):

    BAD_DATA = -999
    NO_DATA = -9999
    LAND = 0
    WATER = 1

    MODIS_SINUSOIDAL_6842 = SpatialReference(            'PROJCS["Sinusoidal",GEOGCS["GCS_Undefined",DATUM["Undefined",SPHEROID["User_Defined_Spheroid",6371007.181,0.0]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Sinusoidal"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",0.0],UNIT["Meter",1.0]]')  # noqa: E501

    # -------------------------------------------------------------------------
    # __init__
    # -------------------------------------------------------------------------
    def __init__(self,
                 year,
                 tile,
                 outDir,
                 modDir,
                 startDay=1,
                 endDay=365,
                 logger=None,
                 sensors=br.SENSORS,
                 debug=False,
                 inBands=br.ALL_BANDS,
                 generateMasks=True,
                 dataType: int = np.int16,
                 noData: int = None,
                 badData: int = None):

        # ---
        # Validate output directory.
        # ---
        if not os.path.exists(outDir):
            raise RuntimeError('Output dir., ' + outDir + ', does not exist.')

        if not os.path.isdir(outDir):

            raise RuntimeError('Output dir., ' +
                               outDir +
                               ', must be a directory.')

        self._outDir = outDir

        # ---
        # Validate sensors.
        # ---
        invalidSensors = sensors - br.SENSORS

        if invalidSensors:
            raise RuntimeError('Invalid sensors: ' + str(invalidSensors))

        self._sensors = sensors

        # ---
        # Validate tile.
        # ---
        if tile:

            rex = re.compile('^[h][0-9]{2}[v][0-9]{2}')

            if not rex.match(tile):

                msg = 'The tile must be specified as h##v##.  It was ' + \
                      'specified as ' + str(tile)

                raise RuntimeError(msg)

        self._tile = tile

        # ---
        # Validate year.
        # ---
        if year < 1999:
            raise RuntimeError('Invalid year: ' + str(year))

        self._year = year

        # ---
        # Set the bands.  MaskGenerator needs a certain set of bands.  Ensure
        # those are read, too.
        # ---
        bands = br.ALL_BANDS if inBands is None else set(inBands)
        bands = bands.union(MaskGenerator.REQUIRED_BANDS)
        self._bandReader = br(modDir, bands)

        # ---
        # Set the days.
        # ---
        if startDay > endDay:
            raise ValueError('Start day must be before end day.')

        self._days = range(startDay, endDay + 1)

        self._logger = logger
        self._generateMasks = generateMasks
        self._debug: bool = debug
        self._npDt: int = dataType
        self._gdalDt = gdal_array.NumericTypeCodeToGDALTypeCode(self._npDt)
        self._noData: int = noData or Classifier.NO_DATA
        self._badData: int = badData or Classifier.BAD_DATA

    # -------------------------------------------------------------------------
    # computeNdvi
    # -------------------------------------------------------------------------
    def computeNdvi(self, sr1, sr2):

        ndvi_unfiltered = \
            (((sr2 - sr1) / (sr2 + sr1)) * 10000).astype(self._npDt)

        ndvi = np.where(sr1 + sr2 != 0, ndvi_unfiltered, 0)
        return ndvi

    # -------------------------------------------------------------------------
    # createOutputImage
    # -------------------------------------------------------------------------
    def _createOutputImage(self, name, predictions):

        driver = gdal.GetDriverByName('GTiff')

        ds = driver.Create(name, br.COLS, br.ROWS, 1, self._gdalDt,
                           options=['COMPRESS=LZW'])

        ds.SetSpatialRef(Classifier.MODIS_SINUSOIDAL_6842)
        ds.SetGeoTransform(self._bandReader.getXform())
        ds.SetProjection(self._bandReader.getProj())
        ds.GetRasterBand(1).SetNoDataValue(self._noData)
        ds.WriteRaster(0, 0, br.COLS, br.ROWS, predictions.tobytes())

        if self._debug and self._logger:

            self._logger.info('Writing image as ' + str(self._gdalDt))
            self._logger.info('GDT_Int16 is ' + str(self._gdalDt))

    # -------------------------------------------------------------------------
    # createOutputImageName
    # -------------------------------------------------------------------------
    def _createOutputImageName(self, sensor, julianDay):

        outName = \
            os.path.join(self._outDir,
                         Utils.getImageName(self._year,
                                            self._tile,
                                            sensor,
                                            self.getClassifierName(),
                                            julianDay) + '.tif')

        return outName

    # -------------------------------------------------------------------------
    # getClassifierName
    # -------------------------------------------------------------------------
    def getClassifierName(self):

        raise NotImplementedError()

    # -------------------------------------------------------------------------
    # maskClassifyWrite
    # -------------------------------------------------------------------------
    def _maskClassifyWrite(self, bandDict, outName):

        # ---
        # Create mask
        # ---
        if self._logger:
            self._logger.info('Generating mask')

        maskGen = MaskGenerator(bandDict)
        
        # int64, bandDict int16
        generalMask: np.ndarray = maskGen.generateGeneralMask(self._debug)
        landMask: np.ndarray = maskGen.generateLandMask(self._debug)

        if self._debug:

            if self._logger:
                self._logger.info('Mask type: ' + str(generalMask.dtype))

            Utils.writeRaster(self._outDir, generalMask, 'GeneralMask')
            Utils.writeRaster(self._outDir, landMask, 'LandMask')

        # ---
        # Classify
        # ---
        if self._logger:
            self._logger.info('Classifiying')

        predictedImage = \
            self._runOneSensorOneDay(bandDict, outName)

        if self._debug:

            if self._logger:

                self._logger.info('SR5 type:' + str(bandDict[br.SR5].dtype))

                self._logger.info('Predictions type: ' +
                                  str(predictedImage.dtype))

            Utils.writeRaster(self._outDir,
                              predictedImage,
                              'predBeforeMask')

        # ---
        # Final image
        # ---
        if self._logger:
            self._logger.info('Masking')

        generalMaskedImage = \
            np.where(generalMask == MaskGenerator.GOOD_DATA,
                     predictedImage,
                     Classifier.BAD_DATA).astype(self._npDt)
                                      
        predictedLandAndMasked = ((generalMaskedImage == Classifier.LAND) &
                                  (landMask == MaskGenerator.BAD_DATA))

        finalImage = np.where(predictedLandAndMasked,
                              self._badData,
                              generalMaskedImage).astype(self._npDt)

        self._createOutputImage(outName, finalImage)

        if self._debug:
            if self._logger:
                self._logger.info('Final image type: ' +
                                  str(finalImage.dtype))

    # -------------------------------------------------------------------------
    # run
    # -------------------------------------------------------------------------
    def run(self):

        for sensor in self._sensors:

            for day in self._days:

                if self._logger:

                    self._logger.info('Reading ' + str(sensor) +
                                      ' tile ' + str(self._tile) +
                                      ' for day ' + str(day))

                try:
                    outName = self._createOutputImageName(sensor, day)

                    if not os.path.exists(outName):

                        if self._logger:
                            self._logger.info('Creating ' + outName)

                        bandDict = self._bandReader.read(sensor,
                                                         self._year,
                                                         self._tile,
                                                         day)

                        if self._debug:
                            self._writeBands(bandDict)
                            
                        if len(bandDict) > 0:

                            self._maskClassifyWrite(bandDict, outName)

                        elif self._logger:

                            self._logger.info('No matching HDFs found.')

                    else:

                        if self._logger:

                            self._logger.info('Output file, ' + outName +
                                              ', already exists.')

                except Exception:

                    if self._logger:

                        self._logger.info(None, exc_info=True)

                        msg = 'Sensor ' + str(sensor) + \
                              ', day ' + str(day) + \
                              ' skipped due to a run-time error.'

                        self._logger.info(msg)

                    # raise e
                    continue

    # -------------------------------------------------------------------------
    # _runOneSensorOneDay
    # -------------------------------------------------------------------------
    def _runOneSensorOneDay(self, bandDict, outName):

        raise NotImplementedError()

    # -------------------------------------------------------------------------
    # _writeBands
    # -------------------------------------------------------------------------
    def _writeBands(self, bandDict):

        outName: Path = Path(self._outDir) / ('bands.tif')
        numBands = len(bandDict)
        cols, rows = list(bandDict.values())[0].shape
        
        ds = gdal.GetDriverByName('GTiff').Create(
            str(outName),
            rows,
            cols,
            numBands,
            gdal.GDT_Int16,
            options=['BIGTIFF=YES'])

        ds.SetSpatialRef(Classifier.MODIS_SINUSOIDAL_6842)
        ds.SetGeoTransform(self._bandReader.getXform())
        ds.SetProjection(self._bandReader.getProj())
        outBandIndex = 0

        for band in bandDict:
            
            outBandIndex += 1
            gdBand = ds.GetRasterBand(outBandIndex)
            gdBand.WriteArray(bandDict[band])
            gdBand.SetMetadataItem('Name', band)
            gdBand.FlushCache()
            gdBand = None

        ds = None
        
