
from abc import abstractmethod
import logging
from pathlib import Path

from modis_water.model.BandReader import BandReader as br


# -----------------------------------------------------------------------------
# class BandReaderModis
#
# Directory Structure: base-directory/MOD09GA/year
#                                     MOD09GQ/year
#                                     MYD09GA/year
#                                     MYD09GQ/year
#
# Base directory: /css/modis/Collection6.1/L2G
# -----------------------------------------------------------------------------
class BandReaderModis(br):

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

    GA_BANDS = set([br.SENZ, br.SOLZ, br.SR3, br.SR4, br.SR5, br.SR6,
                    br.SR7, br.STATE])
    
    GQ_BANDS = set([br.SR1, br.SR2])

    # Sensors
    MOD = 'MOD'
    MYD = 'MYD'
    SENSORS = set([MOD, MYD])

    # -------------------------------------------------------------------------
    # __init__
    # -------------------------------------------------------------------------
    def __init__(self, 
                 baseDir: Path, 
                 logger: logging.RootLogger = None):

        super(BandReaderModis, self).__init__(baseDir, logger) 

    # -------------------------------------------------------------------------
    # getBandMap
    # -------------------------------------------------------------------------
    @staticmethod
    def _getBandMap() -> dict:
        
         return {br.SENZ: BandReaderModis.SENZ,
                 br.SOLZ: BandReaderModis.SOLZ,
                 br.SR1: BandReaderModis.SR1,
                 br.SR2: BandReaderModis.SR2,
                 br.SR3: BandReaderModis.SR3,
                 br.SR4: BandReaderModis.SR4,
                 br.SR5: BandReaderModis.SR5,
                 br.SR6: BandReaderModis.SR6,
                 br.SR7: BandReaderModis.SR7,
                 br.STATE: BandReaderModis.STATE}
        
    # -------------------------------------------------------------------------
    # getFullBandNames
    # -------------------------------------------------------------------------
    @staticmethod
    def _getFullBandNames() -> dict:
        
        return {br.SENZ: ':MODIS_Grid_1km_2D:SensorZenith_1',
                br.SOLZ: ':MODIS_Grid_1km_2D:SolarZenith_1',
                br.SR1: ':MODIS_Grid_2D:sur_refl_b01_1',
                br.SR2: ':MODIS_Grid_2D:sur_refl_b02_1',
                br.SR3: ':MODIS_Grid_500m_2D:sur_refl_b03_1',
                br.SR4: ':MODIS_Grid_500m_2D:sur_refl_b04_1',
                br.SR5: ':MODIS_Grid_500m_2D:sur_refl_b05_1',
                br.SR6: ':MODIS_Grid_500m_2D:sur_refl_b06_1',
                br.SR7: ':MODIS_Grid_500m_2D:sur_refl_b07_1',
                br.STATE: ':MODIS_Grid_1km_2D:state_1km_1'}
        
    # -------------------------------------------------------------------------
    # read
    # -------------------------------------------------------------------------
    def read(self, sensor: str, year: int, day: int, tile: str) -> dict:

        self._validate(sensor, year, day, tile)

        # Define the base glob pattern
        pattern = str(year)

        if day:

            pattern += str(day).zfill(3)

        else:
            pattern += '*'

        pattern += '.' + tile + '*.hdf'

        # Do we need GA files, GQ files, or both?
        gaBands = self._bands & BandReaderModis.GA_BANDS
        gqBands = self._bands & BandReaderModis.GQ_BANDS
        subDsPrefix = 'HDF4_EOS:EOS_GRID'
        bandDict = {}
        
        if gaBands:

            hdfFiles: list = (self._baseDir / (sensor + '09GA') / str(year)). \
                glob('*GA.A' + pattern)
            
            bandDict.update(self._readBandsFromHdfs(hdfFiles, 
                                                    gaBands,
                                                    subDsPrefix=subDsPrefix))

        if gqBands:

            hdfFiles: list = (self._baseDir / (sensor + '09GQ') / str(year)). \
                glob('*GQ.A' + pattern)

            bandDict.update(self._readBandsFromHdfs(hdfFiles=hdfFiles, 
                                                    bands=gqBands, 
                                                    setXform=True,
                                                    subDsPrefix=subDsPrefix))

        return bandDict

    # -------------------------------------------------------------------------
    # sensors
    # -------------------------------------------------------------------------
    @staticmethod
    def sensors() -> set:
        return BandReaderModis.SENSORS
