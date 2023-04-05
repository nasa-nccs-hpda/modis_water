import unittest

import numpy as np

from modis_water.model.QAMap import QAMap


class test_QAMap(unittest.TestCase):

    def setUp(self):
        self.year = 2021
        self.tile = 'h18v04'
        self.sensor = 'MODIS'
        self.classifierName = 'MYD'
        self.postFix = '.hdf'
        self.outputDir = '/path/to/output/dir'

    def test_getAnnualStatPath_error(self):
        # Call the function and assert that it raises a FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            QAMap._getAnnualStatPath(
                self.year, self.tile, self.sensor,
                self.classifierName, self.postFix, self.outputDir)

    def test_extractPackedBitBinaryArray(self):
        # Test case 1
        postProcessingMask1 = np.array(
            [0b0101, 0b1100, 0b0010], dtype=np.uint8)
        bitMask1 = 0b0010
        expected1 = np.array([0, 0, 1], dtype=np.uint8)
        result1 = QAMap._extractPackedBitBinaryArray(
            postProcessingMask1, bitMask1)
        np.testing.assert_array_equal(result1, expected1)

        # Test case 2
        postProcessingMask2 = np.array(
            [0b1010, 0b1111, 0b1100], dtype=np.uint8)
        bitMask2 = 0b1100
        expected2 = np.array([0, 1, 1], dtype=np.uint8)
        result2 = QAMap._extractPackedBitBinaryArray(
            postProcessingMask2, bitMask2)
        np.testing.assert_array_equal(result2, expected2)

        # Test case 3
        postProcessingMask3 = np.array(
            [0b0000, 0b1111, 0b0011], dtype=np.uint8)
        bitMask3 = 0b0101
        expected3 = np.array([0, 1, 0], dtype=np.uint8)
        result3 = QAMap._extractPackedBitBinaryArray(
            postProcessingMask3, bitMask3)
        np.testing.assert_array_equal(result3, expected3)
