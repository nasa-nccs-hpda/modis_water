
from abc import ABC
from abc import abstractmethod
import logging
from pathlib import Path
import re

from osgeo import gdal


# -----------------------------------------------------------------------------
# class BandReader
#
# Especially upon the addition of VIIRS data, a better OO design would include
# a Band class.
# -----------------------------------------------------------------------------
class BandReader(ABC):

    COLS = 4800
    ROWS = COLS

    # Bands
    SENZ = 'SensorZenith'
    SOLZ = 'SolarZenith'
    SR1 = 'sur_refl_b01'
    SR2 = 'sur_refl_b02'
    SR3 = 'sur_refl_b03'
    SR4 = 'sur_refl_b04'
    SR5 = 'sur_refl_b05'
    SR6 = 'sur_refl_b06'
    SR7 = 'sur_refl_b07'
    STATE = 'state_1km'

    ALL_BANDS = set([SENZ, SOLZ, SR1, SR2, SR3, SR4, SR5, SR6, SR7, STATE])

    # -------------------------------------------------------------------------
    # __init__
    # -------------------------------------------------------------------------
    def __init__(self, 
                 baseDir: Path, 
                 logger: logging.RootLogger = None):

        if not baseDir or not baseDir.exists() or not baseDir.is_dir():

            raise RuntimeError('Base dir., ' +
                               str(baseDir) +
                               ', does not exist.')

        self._bands: list = None
        self._baseDir: Path = baseDir
        self._logger: logging.RootLogger = logger
        self._xform = None
        self._proj = None

    # -------------------------------------------------------------------------
    # getBandMap
    # -------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _getBandMap() -> dict:
        pass
        
    # -------------------------------------------------------------------------
    # getBandName
    # -------------------------------------------------------------------------
    @staticmethod
    def getBandName(bandFile: Path):

        band = bandFile.name.stem.split('-')[1]

        return band

    # -------------------------------------------------------------------------
    # getCols
    # -------------------------------------------------------------------------
    def getCols(self) -> int:
        return BandReader.COLS
        
    # -------------------------------------------------------------------------
    # getFullBandNames
    # -------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def _getFullBandNames() -> dict:
        pass
        
    # -------------------------------------------------------------------------
    # getProj
    # -------------------------------------------------------------------------
    def getProj(self):

        return self._proj

    # -------------------------------------------------------------------------
    # getRows
    # -------------------------------------------------------------------------
    def getRows(self) -> int:
        return BandReader.ROWS
        
    # -------------------------------------------------------------------------
    # getXform
    # -------------------------------------------------------------------------
    def getXform(self):

        return self._xform

    # -------------------------------------------------------------------------
    # read
    # -------------------------------------------------------------------------
    @abstractmethod
    def read(self, sensor: str, year: int, day: int, tile: str) -> dict:
        pass
        
    # -------------------------------------------------------------------------
    # _readBandsFromHdfs
    # -------------------------------------------------------------------------
    def _readBandsFromHdfs(self, 
                           hdfFiles: list, 
                           bands: list, 
                           subDsPrefix: str,
                           setXform: bool = False) -> dict:

        bandDict = {}

        for hdfFile in hdfFiles:

            for band in bands:

                subDataSet = subDsPrefix + ':"' + \
                             str(hdfFile) + '":' + \
                             self._getFullBandNames()[band]

                ds = gdal.Open(subDataSet)
                
                if not ds:
                    raise RuntimeError('Unable to open dataset.')

                if setXform and not self._xform:
                    self._xform = ds.GetGeoTransform()

                if setXform and not self._proj:
                    self._proj = ds.GetProjection()
                    
                bandDict[band] = ds.ReadAsArray(0, 0, None, None, None,
                                                self.getCols(),
                                                self.getRows())
                
        return bandDict

    # -------------------------------------------------------------------------
    # sensors
    # -------------------------------------------------------------------------
    @staticmethod
    @abstractmethod
    def sensors() -> set:
        pass

    # -------------------------------------------------------------------------
    # setBands
    # -------------------------------------------------------------------------
    def setBands(self, bands: list = ALL_BANDS) -> None:
        
        setOfBands = set(bands)
        validatedBands = setOfBands.intersection(BandReader.ALL_BANDS)

        if setOfBands != validatedBands:

            if self._logger:
                self._logger.warning('Some input bands are invalid.')
        
        # ---
        # Bands must be expressed in base-class terms, and translated only
        # in the derived classes as they do their work.
        #
        # self._bands = {self._getBandMap()[b] for b in validatedBands}
        # ---
        self._bands = validatedBands

    # -------------------------------------------------------------------------
    # setLogger
    # -------------------------------------------------------------------------
    def setLogger(self, logger: logging.RootLogger) -> None:
        self._logger = logger
        
    # -------------------------------------------------------------------------
    # validate
    #
    # TODO: validate day
    # -------------------------------------------------------------------------
    def _validate(self, sensor: str, year: int, day: int, tile: str):

        if sensor not in self.sensors():
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
