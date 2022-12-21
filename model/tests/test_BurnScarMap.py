import logging
import os
import sys
import tempfile
import unittest

from modis_water.model.BurnScarMap import BurnScarMap

logger = logging.getLogger()
logger.level = logging.DEBUG


# -----------------------------------------------------------------------------
# class BurnScarTestCase
#
# python -m unittest discover model/tests/
# python -m unittest modis_water.model.tests.test_BurnScarMap
# -----------------------------------------------------------------------------
class BurnScarTestCase(unittest.TestCase):

    # -------------------------------------------------------------------------
    # testHandleMcdError
    # -------------------------------------------------------------------------
    def testHandleMcdError(self):
        tile0 = 'h20v00'
        tile1 = 'h16v01'
        tile2 = 'h15v14'
        tile3 = 'h13v15'
        tile4 = 'h13v16'
        tile5 = 'h13v17'
        dummyDir = tempfile.gettempdir()

        streamHandler = logging.StreamHandler(sys.stdout)
        logger.addHandler(streamHandler)

        burnScarOutputPathTile0 = BurnScarMap.generateAnnualBurnScarMap(
            'MOD', 2020, tile=tile0, mcdDir='Test',
            classifierName='rf', outDir=dummyDir, logger=logger)

        self.assertTrue(os.path.exists(burnScarOutputPathTile0))

        burnScarOutputPathTile1 = BurnScarMap.generateAnnualBurnScarMap(
            'MOD', 2020, tile=tile1, mcdDir='Test',
            classifierName='rf', outDir=dummyDir, logger=logger)

        self.assertTrue(os.path.exists(burnScarOutputPathTile1))

        burnScarOutputPathTile2 = BurnScarMap.generateAnnualBurnScarMap(
            'MOD', 2020, tile=tile2, mcdDir='Test',
            classifierName='rf', outDir=dummyDir, logger=logger)

        self.assertTrue(os.path.exists(burnScarOutputPathTile2))

        burnScarOutputPathTile3 = BurnScarMap.generateAnnualBurnScarMap(
            'MOD', 2020, tile=tile3, mcdDir='Test',
            classifierName='rf', outDir=dummyDir, logger=logger)

        self.assertTrue(os.path.exists(burnScarOutputPathTile3))

        burnScarOutputPathTile4 = BurnScarMap.generateAnnualBurnScarMap(
            'MOD', 2020, tile=tile4, mcdDir='Test',
            classifierName='rf', outDir=dummyDir, logger=logger)

        self.assertTrue(os.path.exists(burnScarOutputPathTile4))

        burnScarOutputPathTile5 = BurnScarMap.generateAnnualBurnScarMap(
            'MOD', 2020, tile=tile5, mcdDir='Test',
            classifierName='rf', outDir=dummyDir, logger=logger)

        self.assertTrue(os.path.exists(burnScarOutputPathTile5))

    # -------------------------------------------------------------------------
    # testHandleMcdError
    # -------------------------------------------------------------------------
    def testThrowMcdError(self):
        tile0 = 'h16v02'
        tile1 = 'h17v13'
        dummyDir = tempfile.gettempdir()

        streamHandler = logging.StreamHandler(sys.stdout)
        logger.addHandler(streamHandler)

        with self.assertRaises(FileNotFoundError):
            BurnScarMap.generateAnnualBurnScarMap(
                'MOD', 2020, tile=tile0, mcdDir='Test',
                classifierName='rf', outDir=dummyDir, logger=logger)

        with self.assertRaises(FileNotFoundError):
            BurnScarMap.generateAnnualBurnScarMap(
                'MOD', 2020, tile=tile1, mcdDir='Test',
                classifierName='rf', outDir=dummyDir, logger=logger)
