
import glob
import os
import re

from osgeo import gdal


# -----------------------------------------------------------------------------
# class BandReader
#
# Directory Structure: base-directory/MOD09GA/year
#                                     MOD09GQ/year
#                                     MYD09GA/year
#                                     MYD09GQ/year
#
# Base directory: /css/modis/Collection6.1/L2G
# -----------------------------------------------------------------------------
class BandReader(object):

    BASE_DIR = '/css/modis/Collection6.1/L2G'
    COLS = 4800
    ROWS = COLS
    
    # Bands
    SENZ = 'SensorZenith_1'
    SOLZ = 'SolarZenith_1'
    SR1 = 'sur_refl_b01_1'
    SR2 = 'sur_refl_b02_1'
    SR3 = 'sur_refl_b03_1'
    SR4 = 'sur_refl_b04_1'
    SR5 = 'sur_refl_b05_1'
    SR6 = 'sur_refl_b06_1'
    SR7 = 'sur_refl_b07_1'
    STATE = 'state_1km_1'
    
    GA_BANDS = set([SENZ, SOLZ, SR3, SR4, SR5, SR6, SR7, STATE])
    GQ_BANDS = set([SR1, SR2])
    ALL_BANDS = GA_BANDS | GQ_BANDS
    
    # Sensors
    MOD = 'MOD'
    MYD = 'MYD'
    SENSORS = set([MOD, MYD])
    
    # -------------------------------------------------------------------------
    # __init__
    # -------------------------------------------------------------------------
    def __init__(self, bands=None, baseDir=BASE_DIR, logger=None):

        if not baseDir or \
            not os.path.exists(baseDir) or \
                not os.path.isdir(baseDir):
                
            raise RuntimeError('Base dir., ' + 
                               str(baseDir) + 
                               ', does not exist.')
        
        self._baseDir = baseDir
        self._logger = logger
        self._xform = None
        self._proj = None
        
        # ---
        # Set the bands.
        # ---
        if bands == None:
            
            self._bands = BandReader.ALL_BANDS

        else:
            
            setOfBands = set(bands)
            self._bands = setOfBands.intersection(BandReader.ALL_BANDS)
                          
            if setOfBands != self._bands:
                if self._logger:
                    self._logger.WARN('Some input bands are invalid.')
                    
    # -------------------------------------------------------------------------
    # getBandName
    # -------------------------------------------------------------------------
    @staticmethod
    def getBandName(bandFile):
        
        band = os.path.splitext(os.path.basename(bandFile))[0]. \
               split('-')[1]
        
        return band
        
    # -------------------------------------------------------------------------
    # getXform
    # -------------------------------------------------------------------------
    def getXform(self):

        return self._xform
                
    # -------------------------------------------------------------------------
    # getProj
    # -------------------------------------------------------------------------
    def getProj(self):

        return self._proj
            
    # -------------------------------------------------------------------------
    # read
    #
    # The argument "read" can be set to false to produce a list of potential
    # files, which is useful for testing.  ListExpectedFiles uses this.
    # -------------------------------------------------------------------------
    def read(self, sensor, year, tile, day, read=True):
        
        self._validate(sensor, year, tile, day)

        # Define the base glob pattern
        pattern = str(year)
        
        if day:
        
            pattern += str(day).zfill(3)
            
        else:
            pattern += '*'

        pattern += '.' + tile + '*.hdf'

        # Do we need GA files, GQ files, or both?
        gaBands = self._bands & BandReader.GA_BANDS
        gqBands = self._bands & BandReader.GQ_BANDS
        bandDict = {}
        
        if gaBands:
            
            globDir = os.path.join(self._baseDir, 
                                   sensor + '09GA', 
                                   str(year), 
                                   '*GA.A' + pattern)
            
            hdfFiles = glob.glob(globDir)
            bandDict.update(self._readBandsFromHdfs(hdfFiles, gaBands))
            
        if gqBands:

            globDir = os.path.join(self._baseDir, 
                                   sensor + '09GQ', 
                                   str(year), 
                                   '*GQ.A' + pattern)
            
            hdfFiles = glob.glob(globDir)
            bandDict.update(self._readBandsFromHdfs(hdfFiles, gqBands, True))

        return bandDict
        
    # -------------------------------------------------------------------------
    # _readBandsFromHdfs
    # -------------------------------------------------------------------------
    def _readBandsFromHdfs(self, hdfFiles, bands, setXform=False):

        # ---
        # We use abbreviated band names elsewhere, but we must use full names
        # now.
        # ---
        FULL_BAND_NAMES = {
            BandReader.SENZ: ':MODIS_Grid_1km_2D:SensorZenith_1',
            BandReader.SOLZ: ':MODIS_Grid_1km_2D:SolarZenith_1',
            BandReader.SR1: ':MODIS_Grid_2D:sur_refl_b01_1',
            BandReader.SR2: ':MODIS_Grid_2D:sur_refl_b02_1',
            BandReader.SR3: ':MODIS_Grid_500m_2D:sur_refl_b03_1',
            BandReader.SR4: ':MODIS_Grid_500m_2D:sur_refl_b04_1',
            BandReader.SR5: ':MODIS_Grid_500m_2D:sur_refl_b05_1',
            BandReader.SR6: ':MODIS_Grid_500m_2D:sur_refl_b06_1',
            BandReader.SR7: ':MODIS_Grid_500m_2D:sur_refl_b07_1',
            BandReader.STATE: ':MODIS_Grid_1km_2D:state_1km_1'
        }

        bandDict = {}
        
        for hdfFile in hdfFiles:
            
            for band in bands:
            
                subDataSet = 'HDF4_EOS:EOS_GRID:"' + \
                             hdfFile + '":' + \
                             FULL_BAND_NAMES[band]

                ds = gdal.Open(subDataSet)
                
                if setXform and not self._xform:
                    self._xform = ds.GetGeoTransform()

                if setXform and not self._proj:
                    self._proj = ds.GetProjection()
                
                bandDict[band] = ds.ReadAsArray(0, 0, None, None, None,
                                                BandReader.COLS,
                                                BandReader.ROWS)
                                                
        return bandDict

    # -------------------------------------------------------------------------
    # validate
    # -------------------------------------------------------------------------
    def _validate(self, sensor, year, tile, day):

        if sensor not in BandReader.SENSORS:
            raise RuntimeError('Invalid sensor, ' + sensor)

        # Validate tile.
        if tile:

            rex = re.compile('^[h][0-9]{2}[v][0-9]{2}')

            if not rex.match(tile):

                msg = 'The tile must be specified as h##v##.  It was ' + \
                      'specified as ' + str(tile)

                raise RuntimeError(msg)

        if year < 1999:
            raise RuntimeError('Invalid year: ' + str(year))        
        