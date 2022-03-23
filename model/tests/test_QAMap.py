import logging
import unittest

from modis_water.model.QAMap import QAMap

logger = logging.getLogger()
logger.level = logging.DEBUG


# -----------------------------------------------------------------------------
# class QAMapTestCase
#
# python -m unittest discover model/tests/
# python -m unittest modis_water.model.tests.test_QAMap.py
# -----------------------------------------------------------------------------
class QAMapTestCase(unittest.TestCase):

    # -------------------------------------------------------------------------
    # testGetStaticDatasetPath
    # -------------------------------------------------------------------------
    def testGetStaticDatasetPath(self):
        with self.assertRaises(FileNotFoundError):
            QAMap.getStaticDatasetPath('test', 'h09v05')

    # -------------------------------------------------------------------------
    # testReadRaster
    # -------------------------------------------------------------------------
    def testReadRaster(self):
        with self.assertRaises(RuntimeError):
            QAMap.readRaster('test')
