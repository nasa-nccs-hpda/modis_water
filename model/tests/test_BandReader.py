import logging
import sys
import unittest

from modis_water.model.BandReader import BandReader

logger = logging.getLogger()
logger.level = logging.DEBUG


# -----------------------------------------------------------------------------
# class BandReaderTestCase
#
# python -m unittest discover model/tests/
# python -m unittest modis_water.model.tests.test_BandReader
# -----------------------------------------------------------------------------
class BandReaderTestCase(unittest.TestCase):

    # -------------------------------------------------------------------------
    # testValidInit
    # -------------------------------------------------------------------------
    def testValidInit(self):

        BandReader(bands=None, logger=None)
        BandReader(bands=[BandReader.SENZ, BandReader.SR1], logger=None)

    # -------------------------------------------------------------------------
    # testReadFiles
    # -------------------------------------------------------------------------
    def testReadFiles(self):

        streamHandler = logging.StreamHandler(sys.stdout)
        logger.addHandler(streamHandler)

        br = BandReader([BandReader.SENZ, BandReader.SR1],
                        BandReader.BASE_DIR,
                        logger)

        bandDict = br.read(BandReader.MOD, 2003, 'h09v05', 161)
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
