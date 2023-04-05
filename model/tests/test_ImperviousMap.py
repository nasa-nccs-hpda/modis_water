import unittest

import numpy as np
from scipy.ndimage import binary_dilation

from modis_water.model.ImperviousMap import ImperviousMap


class test_ImperviousMap(unittest.TestCase):

    def testGetImperviousPercentageArray(self):
        with self.assertRaises(FileNotFoundError):
            ImperviousMap._getImperviousPercentageArray(
                'h09v05', '/path/to/impervious/dir')

    def testDilateImpervious(self):
        mock_impervious_array = np.zeros((2400, 2400), dtype=np.uint8)
        mock_impervious_array[1000:1400, 1000:1400] = 1
        dilated_array = ImperviousMap._dialateImpervious(mock_impervious_array)

        kernel = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]])
        expected_dilated_array = binary_dilation(
            mock_impervious_array, structure=kernel)

        np.testing.assert_array_equal(dilated_array, expected_dilated_array)
