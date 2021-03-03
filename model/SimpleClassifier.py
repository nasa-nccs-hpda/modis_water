
import glob
import os

from osgeo import gdal
from osgeo import gdalconst

from core.model.Chunker import Chunker
from core.model.ImageFile import ImageFile
from core.model.SystemCommand import SystemCommand


# -----------------------------------------------------------------------------
# class SimpleClassifier
#
# run
#    _processOneSensor
#       _readFiles
#           _readBands
#              readFile
#       createOutputImage
#       classify
#           getChunker
#           detectWater
#               waterChange
#
# - To read into a structure other than an image file or to use a different
#   resampling method, override readFile().
#
# - To use a different classification algorithm, override classify().
#
# - To use a different output structure, override createOutputImage().
#
# - To use a different water detection algorithm, override detectWater.
# -----------------------------------------------------------------------------
class SimpleClassifier(object):

    # -------------------------------------------------------------------------
    # __init__
    # -------------------------------------------------------------------------
    def __init__(self, tileDir, outDir, julianDay=None, logger=None):

        if not os.path.exists(outDir):
            raise RuntimeError('Output dir., ' + outDir + ', does not exist.')

        if not os.path.isdir(outDir):

            raise RuntimeError('Output dir., ' +
                               outDir +
                               ', must be a directory.')

        if not os.path.exists(tileDir):
            raise RuntimeError('Tile dir., ' + tileDir + ', does not exist.')

        self._julianDay = julianDay
        self._logger = logger
        self._outDir = outDir
        self._tileDir = tileDir
        
        # Discover which year's files are in the tile directory.
        oneFile = glob.glob(os.path.join(self._tileDir, 'MO', '*.hdf'))[0]
        dateSegment = os.path.basename(oneFile).split('.')[1]
        self._year = dateSegment[1:5]

        self._MASK_AERO = 0b1100000
        self._MASK_CLOUD_SHADOW = 0b100
        self._MASK_INT_CLOUD = 0b1000000000
        self._OUT_BAD_VAL = 0
        self._OUT_LAND_VAL = 1
        self._OUT_UNCLASS_VAL = 2
        self._OUT_WATER_VAL = 3
        self._SENZ = 'SensorZenith_1'
        self._SOLZ = 'SolarZenith_1'
        self._SR1 = 'sur_refl_b01_1'
        self._SR2 = 'sur_refl_b02_1'
        self._SR3 = 'sur_refl_b03_1'
        self._SR4 = 'sur_refl_b04_1'
        self._SR5 = 'sur_refl_b05_1'
        self._SR6 = 'sur_refl_b06_1'
        self._SR7 = 'sur_refl_b07_1'
        self._STATE = 'state_1km_1'

    # -------------------------------------------------------------------------
    # classify
    #
    # Could Numpy help here?  https://jakevdp.github.io/PythonDataScienceHandbook/02.03-computation-on-arrays-ufuncs.html
    # Is Numpy vectorization subject to Python speeds no matter what?  https://stackoverflow.com/questions/25494804/perform-operations-on-elements-of-a-numpy-array
    # -------------------------------------------------------------------------
    def classify(self, fileDict, outImage):

        # ---
        # We have a stack of 10 images.  Chunker reads into Numpy arrays.
        # Make chunk size adjustable.  It will be easier to test and debug
        # smaller chunks.  Chunk size can be increased later.
        # ---
        chunkSize = 4
        outChunker = self._getChunker(outImage, chunkSize)
        chunkerDict = {}

        for band in fileDict:

            bandFile = fileDict[band]
            chunkerDict[band] = self._getChunker(bandFile, chunkSize)

        # ---
        # Start chunking.  Chunker does not know it's finished until it reads
        # past the end of the image.
        # ---
        while True:

            loc, outCh = outChunker.getChunk()

            if outChunker.isComplete():
                break

            if loc[0] % 1000 == 0 and loc[1] % 1000 == 0:
                print('Chunk (', loc[0], ', ', loc[1], ')', sep='')

            # These are Numpy arrays.
            solzCh = chunkerDict[self._SOLZ].getChunk()[1] / 1000
            sr1Ch = chunkerDict[self._SR1].getChunk()[1]
            sr2Ch = chunkerDict[self._SR2].getChunk()[1]
            sr3Ch = chunkerDict[self._SR3].getChunk()[1]
            sr4Ch = chunkerDict[self._SR4].getChunk()[1]
            sr5Ch = chunkerDict[self._SR5].getChunk()[1]
            sr6Ch = chunkerDict[self._SR6].getChunk()[1]
            sr7Ch = chunkerDict[self._SR7].getChunk()[1]
            stateCh = chunkerDict[self._STATE].getChunk()[1]

            for x in range(chunkSize):
                for y in range(chunkSize):

                    # Bad data?
                    if sr1Ch[x][y] < -100 or \
                       sr2Ch[x][y] < -100 or \
                       solzCh[x][y] >= 65 or \
                       (stateCh[x][y] & self._MASK_AERO) >> 5 == 3:

                        outCh[x][y] = self._OUT_BAD_VAL

                    else:

                        try:
                            water = \
                                self.detectWater(sr1Ch[x][y], sr2Ch[x][y],
                                                 sr3Ch[x][y], sr4Ch[x][y],
                                                 sr5Ch[x][y], sr6Ch[x][y],
                                                 sr7Ch[x][y], stateCh[x][y])

                        except ZeroDivisionError as e:
                            
                            if self._logger:
                                
                                msg = str(e) + \
                                      '.  This is probably because ' + \
                                      'sr1 + sr2 = 0.  ' + \
                                      'loc: ' + str(loc) + \
                                      ', (x, y): (' + str(x) + ', ' + \
                                      str(y) + ')' + \
                                      ', (sr1, sr2): (' + str(sr1Ch[x][y]) + \
                                      ', ' + str(sr2Ch[x][y]) + ')'
                                      
                                self._logger.error(msg)
                                                 
                        outCh[x][y] = water

    # -------------------------------------------------------------------------
    # createOutputImage
    # -------------------------------------------------------------------------
    def createOutputImage(self, suffix, julianDay):

        outName = os.path.join(self._outDir, 'landWaterBad-' + suffix + '-' +
                                             str(julianDay) + '.tif')
        
        driver = gdal.GetDriverByName('GTiff')
        outDs = driver.Create(outName, 4800, 4800, 1, gdalconst.GDT_UInt16)
        return outName

    # -------------------------------------------------------------------------
    # detectWater
    # -------------------------------------------------------------------------
    def detectWater(self, sr1, sr2, sr3, sr4, sr5, sr6, sr7, state):

        waterChange = self._waterChange(sr1, sr2, sr3, sr4, sr5, sr6, sr7)
        
        if waterChange == 0:
            return self._OUT_UNCLASS_VAL
            
        if waterChange == 3:
            return self._OUT_WATER_VAL
            
        if waterChange == 1:
            
            if (state & self._MASK_INT_CLOUD) >> 9 == 0 and \
               (state & self._MASK_CLOUD_SHADOW) >> 2 == 0:
               
               return self._OUT_LAND_VAL
               
            else:
                return self._OUT_WATER_VAL
                                        
    # -------------------------------------------------------------------------
    # waterChange
    #
    # This returns 0, 1 or 3, no 2.  This is to match the original C code.
    # -------------------------------------------------------------------------
    def _waterChange(self, red, nir, blue, green, swir5, swir6, swir7):
        
        waterChange = 0
        
        if swir5 < 1017:

            if swir7 < 773:

                if swir5 >= 453 and blue < 675 and nir > 1000:

                    waterChange = 1
                else:

                    waterChange = 3
        else:

            ndvi = float(nir - red) / float(nir + red)
            
            if nir < 1777:

                if ndvi < 0.0825:

                    if blue < 651:

                        waterChange = 3

                    else:
                        waterChange = 1
                else:

                    if ndvi < 0.4125:

                        if nir >= 1329 and swir7 < 1950:

                            waterChange = 1

                    else:
                        waterChange = 1

            else:
                waterChange = 1

        return waterChange

    # -------------------------------------------------------------------------
    # _getChunker
    # -------------------------------------------------------------------------
    def _getChunker(self, image, chunkSize):

        chunker = Chunker(image)
        chunker.setChunkSize(chunkSize, chunkSize)
        return chunker

    # -------------------------------------------------------------------------
    # _processOneSensor
    # -------------------------------------------------------------------------
    def _processOneSensor(self, sensorDir):

        # ---
        # Each day must be processed.  For each day, there will be one GA and
        # one GQ file.  Instead of reading and sorting, and that messy 
        # bookkeeping, explicitly loop over days.  If no files exist for a
        # day, print a message and continue.  MODIS uses julian days.
        # ---
        julianDays = [self._julianDay] or range(365)

        for julianDay in julianDays:

            files = self._readFiles(sensorDir, julianDay)
            
            if files:
            
                sensor = os.path.basename(sensorDir)
                outName = self.createOutputImage(sensor, julianDay)
                self.classify(files, outName)

            elif self._logger:
                
                self._logger.info('There are no files for day ' +
                                  str(julianDay) + '.')
                                  
    # -------------------------------------------------------------------------
    # _readFiles
    # -------------------------------------------------------------------------
    def _readFiles(self, sensorDir, julianDay):

        # This is a dictionary mapping the band name to its file.
        files = {}
        pattern = '*GA*A' + self._year + str(julianDay).zfill(3) + '*.hdf'
        gaDays = glob.glob(os.path.join(sensorDir, pattern))

        for gaFile in gaDays:

            bands = [':MODIS_Grid_1km_2D:SensorZenith_1',
                     ':MODIS_Grid_1km_2D:SolarZenith_1',
                     ':MODIS_Grid_1km_2D:state_1km_1',
                     ':MODIS_Grid_500m_2D:sur_refl_b03_1',
                     ':MODIS_Grid_500m_2D:sur_refl_b04_1',
                     ':MODIS_Grid_500m_2D:sur_refl_b05_1',
                     ':MODIS_Grid_500m_2D:sur_refl_b06_1',
                     ':MODIS_Grid_500m_2D:sur_refl_b07_1']

            files.update(self._readBands(gaFile, bands))

            # Get the GQ name.
            gqFile = gaFile.replace('GA', 'GQ')

            bands = [':MODIS_Grid_2D:sur_refl_b01_1',
                     ':MODIS_Grid_2D:sur_refl_b02_1']

            files.update(self._readBands(gqFile, bands))

        return files

    # -------------------------------------------------------------------------
    # _readBands
    # -------------------------------------------------------------------------
    def _readBands(self, hdfFile, bands):

        bandFiles = {}

        for band in bands:

            bandFile = self.readFile(hdfFile, band)

            if band not in bandFiles:

                # Remove the resolution string from the band name.
                bandFiles[band.split(':')[-1]] = bandFile

        return bandFiles

    # -------------------------------------------------------------------------
    # readFile
    # -------------------------------------------------------------------------
    def readFile(self, dayFile, band):

        outBaseName = os.path.splitext(os.path.basename(dayFile))[0]
        bandName = band.split(':')[-1]

        outName = os.path.join(self._outDir,
                               outBaseName + '-' + bandName + '.tif')

        # Only bother reading, if the file does not exist.
        if not os.path.exists(outName):

            cmd = 'gdal_translate -tr 231.656358 231.656358 ' + \
                  'HDF4_EOS:EOS_GRID:"' + \
                  dayFile + '"' + \
                  band + ' ' + \
                  outName

            SystemCommand(cmd, self._logger, True)

        return outName

    # -------------------------------------------------------------------------
    # run
    # -------------------------------------------------------------------------
    def run(self):

        sensorDir = os.path.join(self._tileDir, 'MO')
        self._processOneSensor(sensorDir)

        # sensorDir = os.path.join(tileDir, 'MY')
        # SimpleClassifier._processOneSensor(sensorDir, outDir)
