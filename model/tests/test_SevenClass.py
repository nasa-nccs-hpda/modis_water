import logging
import unittest

from modis_water.model.SevenClass import SevenClassMap

logger = logging.getLogger()
logger.level = logging.DEBUG


# -----------------------------------------------------------------------------
# class SevenClassMapTestCase
#
# python -m unittest discover model/tests/
# python -m unittest modis_water.model.tests.test_SevenClass.py
# -----------------------------------------------------------------------------
class SevenClassMapTestCase(unittest.TestCase):

    # -------------------------------------------------------------------------
    # testGetStaticSevenClassPath
    # -------------------------------------------------------------------------
    def testGetStaticSevenClassPath(self):

        with self.assertRaises(FileNotFoundError):
            SevenClassMap.getStaticSevenClassPath('test', 'h09v05')

    # -------------------------------------------------------------------------
    # testReadRaster
    # -------------------------------------------------------------------------
    def testReadRaster(self):
        with self.assertRaises(RuntimeError):
            SevenClassMap.readRaster('test')
