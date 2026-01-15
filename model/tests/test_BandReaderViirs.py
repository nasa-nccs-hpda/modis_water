import logging
from pathlib import Path
import sys
import unittest

import numpy as np

from modis_water.model.BandReader import BandReader
from modis_water.model.BandReaderViirs import BandReaderViirs
from modis_water.model.MaskGenerator import MaskGenerator

logger = logging.getLogger()
logger.level = logging.DEBUG


# -----------------------------------------------------------------------------
# class BandReaderViirsTestCase
#
# python -m unittest discover model/tests/
# python -m unittest modis_water.model.tests.test_BandReaderViirs
# python -m unittest modis_water.model.tests.test_BandReaderViirs.BandReaderViirsTestCase.testState
# -----------------------------------------------------------------------------
class BandReaderViirsTestCase(unittest.TestCase):

    # -------------------------------------------------------------------------
    # testValidInit
    # -------------------------------------------------------------------------
    def testValidInit(self):

        BandReaderViirs(Path('/explore/nobackup/projects/ilab/data/' + \
                             'MODIS/compare_MODIS_VIIRS'), 
                        logger=None)
                        
    # -------------------------------------------------------------------------
    # testReadFiles
    # -------------------------------------------------------------------------
    def testReadFiles(self):

        streamHandler = logging.StreamHandler(sys.stdout)
        logger.addHandler(streamHandler)

        br = BandReaderViirs(Path('/explore/nobackup/projects/ilab/data/' + \
                                  'MODIS/compare_MODIS_VIIRS'), 
                             logger)
                             
        br.setBands([BandReader.SENZ, BandReader.SR1])
        bandDict = br.read(BandReaderViirs.VNP, 2020, 161, 'h09v05')

        self.assertTrue(BandReader.SENZ in bandDict)
        self.assertTrue(BandReader.SR1 in bandDict)
        self.assertIsNotNone(bandDict[BandReader.SENZ])
        self.assertIsNotNone(bandDict[BandReader.SR1])

        hdfFiles = br._findHdfFiles(BandReaderViirs.VNP, 2020, 161, 'h09v05')

        self.assertEqual(bandDict[BandReader.SENZ][212, 212], 461)
        self.assertEqual(bandDict[BandReader.SR1][212, 212], 1436)

    # -------------------------------------------------------------------------
    # testState
    # -------------------------------------------------------------------------
    def testState(self):

        # Create the band reader.
        streamHandler = logging.StreamHandler(sys.stdout)
        logger.addHandler(streamHandler)

        br = BandReaderViirs(Path('/explore/nobackup/projects/ilab/data/' + \
                                  'MODIS/compare_MODIS_VIIRS'), 
                             logger)
                             
        # Read state.
        br.setBands([BandReader.STATE])
        bandDict = br.read(BandReaderViirs.VNP, 2020, 161, 'h09v05')

        # Get the VIIRS bands that comprise state.
        hdfFiles = br._findHdfFiles(BandReaderViirs.VNP, 2020, 161, 'h09v05')
        
        qfBands: dict = br._readBandsFromHdfs(hdfFiles=hdfFiles, 
                                              bands=[BandReaderViirs.QF1,
                                                     BandReaderViirs.QF2],
                                              subDsPrefix='HDF5', 
                                              setXform=True)

        qf1: np.ndarray = qfBands[BandReaderViirs.QF1]
        qf2: np.ndarray = qfBands[BandReaderViirs.QF2]
        
        # Check various pixel locations.
        x = 0
        y = 0
        self._validatePixelState(x, y, qf1, qf2, bandDict)
        
        x = 100
        y = 100
        self._validatePixelState(x, y, qf1, qf2, bandDict)
        
        x = 212
        y = 212
        self._validatePixelState(x, y, qf1, qf2, bandDict)
        
        x = 21
        y = 12
        self._validatePixelState(x, y, qf1, qf2, bandDict)
        
        return True

    # -------------------------------------------------------------------------
    # validateOneStateComponent
    # -------------------------------------------------------------------------
    def _validateOneStateComponent(self, 
                                   qf: int, 
                                   state: int,
                                   vMask: int,
                                   sMask: int):
        
        qfTest = qf & vMask == vMask
        stateTest = state & sMask == sMask
        self.assertEqual(qfTest, stateTest)
        
    # -------------------------------------------------------------------------
    # validatePixelState
    # -------------------------------------------------------------------------
    def _validatePixelState(self, 
                            x: int, 
                            y: int, 
                            qf1: np.ndarray, 
                            qf2: np.ndarray,
                            bandDict: dict) -> None:
        
        stateBand = bandDict[BandReader.STATE]
        stateVal = stateBand[x, y]  
        qf1Val = qf1[x, y]
        qf2Val = qf2[x, y]
        
        self._validateOneStateComponent(qf1Val, 
                                        stateVal, 
                                        BandReaderViirs.VIIRS_CLOUDY,
                                        MaskGenerator.CLOUDY)

        self._validateOneStateComponent(qf1Val, 
                                        stateVal, 
                                        BandReaderViirs.VIIRS_CLOUD_MIXED,
                                        MaskGenerator.CLOUD_MIXED)

        self._validateOneStateComponent(qf2Val, 
                                        stateVal, 
                                        BandReaderViirs.VIIRS_CLOUD_SHADOW,
                                        MaskGenerator.CLOUD_SHADOW)

        self._validateOneStateComponent(qf2Val, 
                                        stateVal, 
                                        BandReaderViirs.VIIRS_AERO_MASK,
                                        MaskGenerator.AERO_MASK)
        