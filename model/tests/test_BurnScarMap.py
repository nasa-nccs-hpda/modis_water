import logging
import unittest

import numpy as np

from modis_water.model.BurnScarMap import BurnScarMap

logger = logging.getLogger()
logger.level = logging.DEBUG


# -----------------------------------------------------------------------------
# class BurnScarMapTestCase
#
# python -m unittest discover model/tests/
# python -m unittest modis_water.model.tests.test_BurnScarMap.py
# -----------------------------------------------------------------------------
class BurnScarMapTestCase(unittest.TestCase):

    # -------------------------------------------------------------------------
    # testGetAllFiles
    # -------------------------------------------------------------------------
    def testGetAllFiles(self):
        with self.assertRaises(RuntimeError):
            BurnScarMap.getAllFiles('test', 2020, 'h09v05')

    # -------------------------------------------------------------------------
    # testLogicalOrMat
    # -------------------------------------------------------------------------
    def testLogicalOrMat(self):
        orArr = list(BurnScarMap.logicalOrMask(
            [np.array([1, 0, 1]), np.array([0, 0, 1])]))
        self.assertEqual([1, 0, 1], orArr)
