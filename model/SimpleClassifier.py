
import glob
import os
import struct

from osgeo import gdal
from osgeo import gdalconst

from core.model.Chunker import Chunker
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

    OUT_BAD_VAL = 0
    OUT_LAND_VAL = 1
    OUT_UNCLASS_VAL = 2
    OUT_WATER_VAL = 3

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

        # Discover which years' files are in the tile directory.
        oneFile = glob.glob(os.path.join(self._tileDir, 'MO', '*.hdf'))[0]
        dateSegment = os.path.basename(oneFile).split('.')[1]
        self._year = dateSegment[1:5]

        # ---
        # Aerosol:
        # In add_SDS_250m.c: ... & aerosol) << 7
        # 0000000011000000 = 0b11000000 = 0xC0
        # 5432109876543210
        #           123456 shift 6
        #
        # Note, there is no need to shift single-bit fields.  Instead,
        # logically "and" the mask with the entire state field to get a 1 or 0.
        # ---
        self._AERO_MASK = 0b11000000          # matches 0xC0 from MOD44C.h
        self._AERO_SHIFT = 6                  # >> 6
        self._CLOUD_MASK = 3                  # c doesn't shift cloud
        self._INT_CLOUD_MASK = 0b10000000000  # matches 0x400 from MOD44C.h
        self._SHADOW_MASK = 0b100             # matches 0x4 from MOD44C.h

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
    def classify(self, fileDict, outImage, rect):

        # ---
        # We have a stack of 10 images.  Chunker reads into Numpy arrays.
        # Make chunk size adjustable.  It will be easier to test and debug
        # smaller chunks.  Chunk size can be increased later.
        # ---
        xSize = int(rect[2]) if rect else 4
        ySize = int(rect[3]) if rect else 4

        outChunker = self._getChunker(outImage, xSize, ySize, False)
        chunkerDict = {}

        for band in fileDict:

            bandFile = fileDict[band]
            chunkerDict[band] = self._getChunker(bandFile, xSize, ySize)

        # ---
        # Start chunking.  Chunker does not know it's finished until it reads
        # past the end of the image.
        # ---
        finished = False
        loc = (int(rect[0]), int(rect[1])) if rect else (0, 0)

        while not finished:

            if outChunker.isComplete():
                break

            if rect:

                finished = True
                loc, outCh = outChunker.getChunk(loc[0], loc[1])
                print('Chunk (', loc[0], ', ', loc[1], ')', sep='')

                # These are Numpy arrays.
                solzCh = chunkerDict[self._SOLZ].getChunk(loc[0],
                                                          loc[1])[1] / 100

                sr1Ch = chunkerDict[self._SR1].getChunk(loc[0], loc[1])[1]
                sr2Ch = chunkerDict[self._SR2].getChunk(loc[0], loc[1])[1]
                sr3Ch = chunkerDict[self._SR3].getChunk(loc[0], loc[1])[1]
                sr4Ch = chunkerDict[self._SR4].getChunk(loc[0], loc[1])[1]
                sr5Ch = chunkerDict[self._SR5].getChunk(loc[0], loc[1])[1]
                sr6Ch = chunkerDict[self._SR6].getChunk(loc[0], loc[1])[1]
                sr7Ch = chunkerDict[self._SR7].getChunk(loc[0], loc[1])[1]
                stateCh = chunkerDict[self._STATE].getChunk(loc[0], loc[1])[1]

            else:

                loc, outCh = outChunker.getChunk()

                if loc[0] % 1000 == 0 and loc[1] % 1000 == 0:
                    print('Chunk (', loc[0], ', ', loc[1], ')', sep='')

                if outChunker.isComplete():
                    break

                # These are Numpy arrays.
                solzCh = chunkerDict[self._SOLZ].getChunk()[1] / 100
                sr1Ch = chunkerDict[self._SR1].getChunk()[1]
                sr2Ch = chunkerDict[self._SR2].getChunk()[1]
                sr3Ch = chunkerDict[self._SR3].getChunk()[1]
                sr4Ch = chunkerDict[self._SR4].getChunk()[1]
                sr5Ch = chunkerDict[self._SR5].getChunk()[1]
                sr6Ch = chunkerDict[self._SR6].getChunk()[1]
                sr7Ch = chunkerDict[self._SR7].getChunk()[1]
                stateCh = chunkerDict[self._STATE].getChunk()[1]

            self.classifyChunk(xSize, ySize, solzCh, sr1Ch, sr2Ch, sr3Ch,
                               sr4Ch, sr5Ch, sr6Ch, sr7Ch, stateCh, loc,
                               outChunker)

    # -------------------------------------------------------------------------
    # classifyChunk
    # -------------------------------------------------------------------------
    def classifyChunk(self, xSize, ySize, solzCh, sr1Ch, sr2Ch, sr3Ch, sr4Ch,
                      sr5Ch, sr6Ch, sr7Ch, stateCh, loc, outChunker):

        for x in range(xSize):
            for y in range(ySize):

                outVal = None

                # Bad data?
                if sr1Ch[x][y] < -100 or \
                   sr2Ch[x][y] < -100 or \
                   solzCh[x][y] >= 65 or \
                   (stateCh[x][y] & self._AERO_MASK) >> self._AERO_SHIFT == 3:

                    outVal = SimpleClassifier.OUT_BAD_VAL

                else:

                    try:
                        outVal = \
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

                        outVal = SimpleClassifier.OUT_BAD_VAL

                    # Write the output.  First, determine the output location.
                    outX = loc[0] + x
                    outY = loc[1] + y

                    outChunker._imageFile._getDataset(). \
                        WriteRaster(outX, outY, 1, 1, struct.pack('I', outVal))

    # -------------------------------------------------------------------------
    # createOutputImage
    # -------------------------------------------------------------------------
    def createOutputImage(self, suffix, julianDay, rect):

        xSize = int(rect[0]) + int(rect[2]) if rect else 4800
        ySize = int(rect[1]) + int(rect[3]) if rect else 4800

        outName = os.path.join(self._outDir, 'landWaterBad-' + suffix + '-' +
                                             str(julianDay) + '.tif')

        driver = gdal.GetDriverByName('GTiff')
        driver.Create(outName, xSize, ySize, 1, gdalconst.GDT_UInt16)
        return outName

    # -------------------------------------------------------------------------
    # detectWater
    # -------------------------------------------------------------------------
    def detectWater(self, sr1, sr2, sr3, sr4, sr5, sr6, sr7, state):

        waterChange = self._waterChange(sr1, sr2, sr3, sr4, sr5, sr6, sr7)

        if waterChange == 0:
            return SimpleClassifier.OUT_UNCLASS_VAL

        elif waterChange == 1:

            if state & self._CLOUD_MASK == 1 or state & self._CLOUD_MASK == 2:

                state |= self._INT_CLOUD_MASK

            if state & self._INT_CLOUD_MASK == 0 and \
               state & self._SHADOW_MASK == 0:

                return SimpleClassifier.OUT_LAND_VAL

            else:
                return SimpleClassifier.OUT_BAD_VAL

        elif waterChange == 3:

            return SimpleClassifier.OUT_WATER_VAL

        else:
            raise RuntimeError('There was a water change condition ' +
                               'for which there is no assigned output ' +
                               'value.')

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

            if nir < 1777:

                ndvi = (float(nir) - float(red)) / (float(nir) + float(red))

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
    def _getChunker(self, image, xSize, ySize, readOnly=True):

        chunker = Chunker(image, readOnly)
        chunker.setChunkSize(xSize, ySize)
        return chunker

    # -------------------------------------------------------------------------
    # _processOneSensor
    # -------------------------------------------------------------------------
    def _processOneSensor(self, sensorDir, rectangle):

        # ---
        # Each day must be processed.  For each day, there will be one GA and
        # one GQ file.  Instead of reading and sorting, and that messy
        # bookkeeping, explicitly loop over days.  If no files exist for a
        # day, print a message and continue.  MODIS uses julian days.
        # ---
        julianDays = [self._julianDay] if self._julianDay else range(365)

        for julianDay in julianDays:

            files = self._readFiles(sensorDir, julianDay)

            if files:

                sensor = os.path.basename(sensorDir)
                outName = self.createOutputImage(sensor, julianDay, rectangle)
                self.classify(files, outName, rectangle)

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

            # ---
            # Get the GQ name.  The last part of the GA name is the production
            # time stamp.  The GQ mate can have a different time stamp, so
            # remove it and glob again.
            # ---
            gqPattern = gaFile.replace('GA', 'GQ')
            gqPattern = os.path.splitext(gqPattern)[0]
            gqPattern = '.'.join(gqPattern.split('.')[0:-1]) + '*.hdf'

            gqFiles = glob.glob(gqPattern)

            if len(gqFiles) == 0:

                raise RuntimeError('No GQ file found for ' + gaFile)

            elif len(gqFiles) > 1:

                raise RuntimeError('Found more than one GQ file with ' +
                                   gqPattern)

            bands = [':MODIS_Grid_2D:sur_refl_b01_1',
                     ':MODIS_Grid_2D:sur_refl_b02_1']

            files.update(self._readBands(gqFiles[0], bands))

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

            # 'HDF4_EOS:EOS_GRID:"' +
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
    def run(self, rectangleToProcess):

        sensorDir = os.path.join(self._tileDir, 'MO')
        self._processOneSensor(sensorDir, rectangleToProcess)

        # sensorDir = os.path.join(tileDir, 'MY')
        # SimpleClassifier._processOneSensor(sensorDir, outDir)
