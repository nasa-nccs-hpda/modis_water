
from abc import abstractmethod
import logging
from pathlib import Path

import numpy as np

from modis_water.model.BandReader import BandReader as br
from modis_water.model.MaskGenerator import MaskGenerator


# -----------------------------------------------------------------------------
# class BandReaderViirs
# -----------------------------------------------------------------------------
class BandReaderViirs(br):

    # Bands
    QF1 = 'SurfReflect_QF1_1'
    QF2 = 'SurfReflect_QF2_1'
    SENZ = 'SensorZenith_1'
    SOLZ = 'SolarZenith_1'
    SR1 = 'SurfReflect_I1_1'
    SR2 = 'SurfReflect_I2_1'
    SR3 = 'SurfReflect_M2_1'
    SR4 = 'SurfReflect_M4_1'
    SR5 = 'SurfReflect_M8_1'
    SR6 = 'SurfReflect_I3_1'
    SR7 = 'SurfReflect_M11_1'

    # ---
    # Sensors
    #
    # This probably does not matter for VIIRS because each file type has the
    # same structure.
    # ---
    VNP = 'VNP'
    VJ1 = 'VJ1'
    SENSORS = set([VNP, VJ1])

    # State
    VIIRS_CLOUDY = int('110', 2)          # 6
    VIIRS_CLOUD_MIXED = int('100', 2)     # 4
    VIIRS_CLOUD_SHADOW = int('100', 2)    # 4
    VIIRS_AERO_MASK = int('1000', 2)      # 8
        
    # ---
    # Not all VIIRS bands have the same rows and columns.  Define them here.
    # It looks like the "I" bands are 2400 x 2400, while the "M" bands are
    # 1200 x 1200.
    # ---
    # COL_MAP = {SENZ: (1200, 1200),
    #            SOLZ: (1200, 1200),
    #            SR1: (2400, 2400),   # I1
    #            SR2: (2400, 2400),   # I2
    #            SR3: (1200, 1200),   # M2
    #            SR4: (1200, 1200),   # M4
    #            SR5: (1200, 1200),   # M8
    #            SR6: (2400, 2400),   # I3
    #            SR7: (1200, 1200),   # M11
    #            QF1: (1200, 1200),
    #            QF2: (1200, 1200)}

    COLS = 2400
    ROWS = 2400
    
    # -------------------------------------------------------------------------
    # __init__
    # -------------------------------------------------------------------------
    def __init__(self, 
                 baseDir: Path, 
                 logger: logging.RootLogger = None):

        super(BandReaderViirs, self).__init__(baseDir, logger) 

    # -------------------------------------------------------------------------
    # composeState
    #
    # VIIRS state comes from two bands.  Read each band and make a composite
    # state bit field for each pixel location.
    #
    # - AERO_MASK:      QF2/bit 4: 0 (no heavy aerosol) | 1 (Heavy aerosol)
    # - CLOUDY:         QF1/bits 2-3: 11 (confident cloudy)
    # - CLOUD_MIXED:    QF1/bits 2-3: 10 (probably cloudy)
    # - CLOUD_SHADOW:   QF2/bit 3: 0 (No cloud shadow) | 1 (Shadow)
    # - CLOUD_INT:      "No need to worry about CLOUD_INT ..."
    #
    # Below is the mask that MaskGenerator uses. "Manually" set it according to
    # the interpretation of the VIIRS state fields.
    #
    # 1024      1
    # |         |
    # v         v
    # 00000000000 
    #           1 : CLOUDY if QF1 bits 2-3 == 11
    #          10 : CLOUD_MIXED if QF1 bits 2-3 == 10
    #         100 : CLOUD_SHADOW if QF2 bit 3 == 1
    #    11000000 : AERO_MASK if QF2 bit 4 == 1
    # 10000000000 : CLOUD_INT == 0
    # -------------------------------------------------------------------------
    def _composeState(self, hdfFiles: list):
        
        if not hdfFiles or len(hdfFiles) == 0:
            return None
            
        # To shorten long lines of code, use shorter names for class variables.
        mc = MaskGenerator.CLOUDY
        mcm = MaskGenerator.CLOUD_MIXED
        mcs = MaskGenerator.CLOUD_SHADOW
        mam = MaskGenerator.AERO_MASK
        vc = BandReaderViirs.VIIRS_CLOUDY
        vcm = BandReaderViirs.VIIRS_CLOUD_MIXED
        vcs = BandReaderViirs.VIIRS_CLOUD_SHADOW
        vam = BandReaderViirs.VIIRS_AERO_MASK
        
        qfBands: dict = self._readBandsFromHdfs(hdfFiles=hdfFiles, 
                                                bands=[BandReaderViirs.QF1,
                                                       BandReaderViirs.QF2],
                                                subDsPrefix='HDF5', 
                                                setXform=True)

        qf1: np.ndarray = qfBands[BandReaderViirs.QF1]
        qf2: np.ndarray = qfBands[BandReaderViirs.QF2]

        cloudy = np.where(qf1 & vc == vc, mc, 0)
        cloudMixed = np.where(qf1 & vcm == vcm, mcm, 0)
        cloudShadow = np.where(qf2 & vcs == vcs, mcs, 0)
        aeroMask = np.where(qf2 & vam == vam, mam, 0)
        
        mask = cloudy | cloudMixed | cloudShadow | aeroMask
        
        return mask

    # -------------------------------------------------------------------------
    # findHdfFiles
    #
    # This is for unit testing, so we can validate composeState().
    # -------------------------------------------------------------------------
    def _findHdfFiles(self, sensor: str, year: int, day: int, tile: str):
        
        self._validate(sensor, year, day, tile)

        # Define the base glob pattern
        pattern = str(year)

        if day:

            pattern += str(day).zfill(3)

        else:
            pattern += '*'

        pattern += '.' + tile + '*.h5'

        hdfFiles = list((self._baseDir / (sensor + '09GA')). \
                        glob('*GA.A' + pattern))
                        
        return hdfFiles

    # -------------------------------------------------------------------------
    # getBandMap
    # -------------------------------------------------------------------------
    @staticmethod
    def _getBandMap() -> dict:
        
         return {br.SENZ: BandReaderViirs.SENZ,
                 br.SOLZ: BandReaderViirs.SOLZ,
                 br.SR1: BandReaderViirs.SR1,
                 br.SR2: BandReaderViirs.SR2,
                 br.SR3: BandReaderViirs.SR3,
                 br.SR4: BandReaderViirs.SR4,
                 br.SR5: BandReaderViirs.SR5,
                 br.SR6: BandReaderViirs.SR6,
                 br.SR7: BandReaderViirs.SR7,
                 br.STATE: BandReaderViirs.STATE}
        
    # -------------------------------------------------------------------------
    # getCols
    # -------------------------------------------------------------------------
    def getCols(self) -> int:
        return BandReaderViirs.COLS
        
    # -------------------------------------------------------------------------
    # getFullBandNames
    # -------------------------------------------------------------------------
    @staticmethod
    def _getFullBandNames() -> dict:
        
        return {br.SENZ: '//HDFEOS/GRIDS/' + \
                         'VIIRS_Grid_1km_2D/Data_Fields/SensorZenith_1',
                br.SOLZ: '//HDFEOS/GRIDS/' + \
                         'VIIRS_Grid_1km_2D/Data_Fields/SolarZenith_1',
                br.SR1: '//HDFEOS/GRIDS/' + \
                        'VIIRS_Grid_500m_2D/Data_Fields/SurfReflect_I1_1',
                br.SR2: '//HDFEOS/GRIDS/' + \
                        'VIIRS_Grid_500m_2D/Data_Fields/SurfReflect_I2_1',
                br.SR3: '//HDFEOS/GRIDS/' + \
                        'VIIRS_Grid_1km_2D/Data_Fields/SurfReflect_M2_1',
                br.SR4: '//HDFEOS/GRIDS/' + \
                        'VIIRS_Grid_1km_2D/Data_Fields/SurfReflect_M4_1',
                br.SR5: '//HDFEOS/GRIDS/' + \
                        'VIIRS_Grid_1km_2D/Data_Fields/SurfReflect_M8_1',
                br.SR6: '//HDFEOS/GRIDS/' + \
                        'VIIRS_Grid_500m_2D/Data_Fields/SurfReflect_I3_1',
                br.SR7: '//HDFEOS/GRIDS/' + \
                        'VIIRS_Grid_1km_2D/Data_Fields/SurfReflect_M11_1',
                BandReaderViirs.QF1: '//HDFEOS/GRIDS/' + \
                        'VIIRS_Grid_1km_2D/Data_Fields/SurfReflect_QF1_1',
                BandReaderViirs.QF2: '//HDFEOS/GRIDS/' + \
                        'VIIRS_Grid_1km_2D/Data_Fields/SurfReflect_QF2_1'}
        
    # -------------------------------------------------------------------------
    # getRows
    # -------------------------------------------------------------------------
    def getRows(self) -> int:
        return BandReaderViirs.ROWS
        
    # -------------------------------------------------------------------------
    # read
    # -------------------------------------------------------------------------
    def read(self, sensor: str, year: int, day: int, tile: str) -> dict:

        hdfFiles: list = self._findHdfFiles(sensor, year, day, tile)
        
        # ---
        # VIIRS state requires two bands to be read.  Read all the other
        # bands, then read state separately and add it to bandDict.
        # ---
        bandsExceptState = self._bands.copy()

        if br.STATE in self._bands:
            bandsExceptState.remove(br.STATE)

        bandDict: dict = self._readBandsFromHdfs(hdfFiles=hdfFiles, 
                                                 bands=bandsExceptState,
                                                 subDsPrefix='HDF5', 
                                                 setXform=True)
                                
        if br.STATE in self._bands:

            state = self._composeState(hdfFiles)
            
            if state is not None:
                bandDict[br.STATE] = self._composeState(hdfFiles)
        
        return bandDict
        
    # -------------------------------------------------------------------------
    # sensors
    # -------------------------------------------------------------------------
    @staticmethod
    def sensors() -> list:
        return BandReaderViirs.SENSORS
