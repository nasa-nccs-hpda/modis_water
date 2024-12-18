import unittest
import numpy as np
from modis_water.model.PostProcessingGenerator import PostProcessingMap


class TestPostProcessingMap(unittest.TestCase):

    # -------------------------------------------------------------------------
    # setUp
    # -------------------------------------------------------------------------
    def setUp(self):
        """Set up a PostProcessingMap instance for testing."""
        self.ppm = PostProcessingMap(
            tile='h18v04',
            outDir='/dummy/output',
            imperviousDir='/dummy/impervious',
            permanentWaterDir='/dummy/permanentWater',
            gmtedDir='/dummy/gmted',
            ancillaryDir='/dummy/ancillary',
            sevenClassDir='/dummy/sevenClass'
        )

    # -------------------------------------------------------------------------
    # testGeneratePositionalBinaryArray
    # -------------------------------------------------------------------------
    def testGeneratePositionalBinaryArray(self):
        """Test _generatePositionalBinaryArray with a simple binary array."""
        binary_array = np.array([[1, 0], [0, 1]])
        bitmask = 4  # Example bitmask
        expected_output = np.array([[4, 0], [0, 4]])
        output = self.ppm._generatePositionalBinaryArray(binary_array,
                                                         bitmask)
        np.testing.assert_array_equal(output, expected_output)

    # -------------------------------------------------------------------------
    # testGenerateDemPositionalBinaryArray
    # -------------------------------------------------------------------------
    def testGenerateDemPositionalBinaryArray(self):
        """
        Test _generateDEMPositionalBinaryArray with example DEM,
        sevenClass, and ancillary arrays.
        """
        dem_array = np.array([[6, 3], [2, 8]])
        seven_class_array = np.array([[1, 0], [3, 1]])
        ancillary_array = np.array([[0, 1], [1, 1]])
        expected_output = np.array([[0, 0], [0, 1]])
        output = self.ppm._generateDEMPositionalBinaryArray(
            dem_array, seven_class_array, ancillary_array)
        np.testing.assert_array_equal(output, expected_output)

    # -------------------------------------------------------------------------
    # testAddSevenClassToPackedBits
    # -------------------------------------------------------------------------
    def testAddSevenClassToPackedBits(self):
        """Test _addSevenClassToPackedBits with an example sevenClass array."""
        seven_class_array = np.array([[0, 1], [2, 3]])
        post_processing_mask = np.zeros((2, 2), dtype=np.uint16)
        expected_output = np.array([[128, 256], [512, 1024]])
        output = self.ppm._addSevenClassToPackedBits(seven_class_array,
                                                     post_processing_mask)
        np.testing.assert_array_equal(output, expected_output)

    # -------------------------------------------------------------------------
    # testAddOutOfProjectionPackedBits
    # -------------------------------------------------------------------------
    def testAddOutOfProjectionPackedBits(self):
        """
        Test _addOutOfProjectionPackedBits with an example sevenClass array.
        """
        seven_class_array = np.array([[250, 0], [0, 250]])
        post_processing_mask = np.zeros((2, 2), dtype=np.uint16)
        expected_output = np.array([[32768, 0], [0, 32768]])
        output = self.ppm._addOutOfProjectionPackedBits(
            seven_class_array, post_processing_mask)
        np.testing.assert_array_equal(output, expected_output)


if __name__ == '__main__':
    unittest.main()
