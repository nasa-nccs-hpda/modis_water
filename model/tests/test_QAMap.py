import unittest

import numpy as np

from modis_water.model.QAMap import QAMap


class test_QAMap(unittest.TestCase):

    def setUp(self):
        self.tile = 'h18v04'
        self.dem_dir = '.'
        self.ancillary_dir = '.'
        self.sensor = 'MODIS'
        self.classifier = 'RandomForest'
        self.postfix = 'Test'
        self.year = 2023
        self.out_dir = '.'
        self.out_name = 'out_qa'
        self.logger = None

        self.qa = QAMap()

    def testGetGMTEDArray(self):
        # Test exclusion tile
        exclusion_tile = 'v17'
        expected_array = np.zeros((QAMap.NCOLS, QAMap.NROWS),
                                  dtype=QAMap.DTYPE)
        array = self.qa._getGMTEDArray(f'h00{exclusion_tile}', self.dem_dir)
        self.assertEqual(array.shape, expected_array.shape)
        self.assertTrue(np.all(array == expected_array))

        # Test with missing file
        with self.assertRaises(FileNotFoundError):
            self.qa._getGMTEDArray('invalid_tile', self.dem_dir)

    def testGetAncillaryArray(self):
        # Test exclusion tile
        exclusion_tile = 'v17'
        expected_array = np.full((QAMap.NCOLS, QAMap.NROWS),
                                 QAMap.ANCILLARY_FILL_VALUE,
                                 dtype=QAMap.DTYPE)
        array = self.qa._getAncillaryArray(
            f'h00{exclusion_tile}', self.ancillary_dir)
        self.assertEqual(array.shape, expected_array.shape)
        self.assertTrue(np.all(array == expected_array))

        # Test with missing file
        with self.assertRaises(FileNotFoundError):
            self.qa._getAncillaryArray('h99v99', self.ancillary_dir)

