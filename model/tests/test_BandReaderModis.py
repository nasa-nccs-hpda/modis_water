import logging
from pathlib import Path
import sys
import unittest

from modis_water.model.BandReader import BandReader
from modis_water.model.BandReaderModis import BandReaderModis

logger = logging.getLogger()
logger.level = logging.DEBUG


# -----------------------------------------------------------------------------
# class BandReaderModisTestCase
#
# python -m unittest discover model/tests/
# python -m unittest modis_water.model.tests.test_BandReaderModis
# -----------------------------------------------------------------------------
class BandReaderModisTestCase(unittest.TestCase):

    # -------------------------------------------------------------------------
    # testValidInit
    # -------------------------------------------------------------------------
    def testValidInit(self):

        BandReaderModis(Path('/css/modis/Collection6.1/L2G'), logger=None)
                        
    # -------------------------------------------------------------------------
    # testReadFiles
    # -------------------------------------------------------------------------
    def testReadFiles(self):

        streamHandler = logging.StreamHandler(sys.stdout)
        logger.addHandler(streamHandler)

        br = BandReaderModis(Path('/css/modis/Collection6.1/L2G'), logger)
        br.setBands([BandReader.SENZ, BandReader.SR1])
        bandDict = br.read(BandReaderModis.MOD, 2003, 161, 'h09v05')
        print('bandDict:', bandDict)

        self.assertTrue(BandReader.SENZ in bandDict)
        self.assertTrue(BandReader.SR1 in bandDict)
        self.assertIsNotNone(bandDict[BandReader.SENZ])
        self.assertIsNotNone(bandDict[BandReader.SR1])

        # ---
        # gdallocationinfo
        # MOD09GQ.A2003161.h09v05.061.2020094170809-sur_refl_b01_1.tif
        # 2112 2112
        # ---
        self.assertEqual(bandDict[BandReader.SENZ][2112][2112], 1570)
        self.assertEqual(bandDict[BandReader.SR1][2112][2112], 784)
