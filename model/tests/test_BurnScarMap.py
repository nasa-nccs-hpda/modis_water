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
        tile0 = 'h16v01'
        tile1 = 'h13v14'
        dummyDir = tempfile.gettempdir()

        streamHandler = logging.StreamHandler(sys.stdout)
        logger.addHandler(streamHandler)

        burnScarOutputPathTile0 = BurnScarMap.generateAnnualBurnScarMap(
            'MOD', 2020, tile=tile0, mcdDir='Test',
            classifierName='rf', outDir=dummyDir, logger=logger)

        self.assertTrue(os.path.exists(burnScarOutputPathTile0))

        burnScarOutputPathTile0 = BurnScarMap.generateAnnualBurnScarMap(
            'MOD', 2020, tile=tile1, mcdDir='Test',
            classifierName='rf', outDir=dummyDir, logger=logger)

        self.assertTrue(os.path.exists(burnScarOutputPathTile0))

    # -------------------------------------------------------------------------
    # testHandleMcdError
    # -------------------------------------------------------------------------
    def testThrowMcdError(self):
        tile = 'h09v05'
        dummyDir = tempfile.gettempdir()

        streamHandler = logging.StreamHandler(sys.stdout)
        logger.addHandler(streamHandler)

        with self.assertRaises(FileNotFoundError):
            BurnScarMap.generateAnnualBurnScarMap(
                'MOD', 2020, tile=tile, mcdDir='Test',
                classifierName='rf', outDir=dummyDir, logger=logger)
