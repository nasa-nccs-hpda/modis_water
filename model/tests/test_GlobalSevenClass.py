import logging
import pathlib
import numpy as np

import unittest
from unittest.mock import MagicMock, patch

from modis_water.model.GlobalSevenClass import GlobalSevenClassMap

logger = logging.getLogger()
logger.level = logging.DEBUG


# -----------------------------------------------------------------------------
# class GlobalSevenClassMapTestCase
#
# python -m unittest discover model/tests/
# python -m unittest modis_water.model.tests.test_GlobalSevenClass
# -----------------------------------------------------------------------------
class GlobalSevenClassMapTestCase(unittest.TestCase):

    # -------------------------------------------------------------------------
    # testGetSevenClassHDFs
    # -------------------------------------------------------------------------
    @patch('modis_water.model.GlobalSevenClass.GlobalSevenClassMap.validateFileExists')
    def testGetSevenClassHDFs(self, mock_validate_file_exists):
        # Mock the validateFileExists method to do nothing
        mock_validate_file_exists.side_effect = lambda filepath: None

        # Create an instance of GlobalSevenClassMap
        scGlobalMapInstance = GlobalSevenClassMap(
            hdfDirectory='/path/to/hdf/dir',
            ancFilePath='/path/to/anc/dir/mask',
            postProcessingDir='/path/to/pp/dir',
            year=2023,
            sensor='MOD',
            tr='250m',
            version='000',
            outputDir='/path/to/output/dir',
            logger=logger,
            debug=True
        )

        # Mock the _getAllHdfProducts function to return some dummy file paths
        scGlobalMapInstance._getAllHdfProducts = MagicMock(return_value=[
            'file1.hdf',
            'file2.hdf'
        ])

        # Call the function under test
        products = scGlobalMapInstance._getSevenClassProducts()

        # Assertions
        self.assertEqual(products, ['file1.hdf', 'file2.hdf'])
        scGlobalMapInstance._getAllHdfProducts.assert_called_once_with('*.hdf')

    # -------------------------------------------------------------------------
    # testValidateNumberOfNoShoreProducts
    # -------------------------------------------------------------------------
    def testRevertShorelineFromArray(self):
        # Generate a dummy array with shorelines
        arrayWithShore = np.array([[0, 2, 1],
                                   [2, 2, 1],
                                   [1, 1, 2]], dtype=np.uint8)

        # Call the function under test
        arrayNoShore = GlobalSevenClassMap.revertShorelineFromArray(
            arrayWithShore)

        # Expected result
        expectedArray = np.array([[0, 1, 1],
                                  [1, 1, 1],
                                  [1, 1, 1]], dtype=np.uint8)

        # Assertions
        np.testing.assert_array_equal(arrayNoShore, expectedArray)

    # -------------------------------------------------------------------------
    # testValidateNumberOfNoShoreProducts
    # -------------------------------------------------------------------------
    @patch('modis_water.model.GlobalSevenClass.GlobalSevenClassMap.validateFileExists')
    def testValidateNumberOfNoShorelineProducts(self, mock_validate_file_exists):
        # Mock the validateFileExists method to do nothing
        mock_validate_file_exists.side_effect = lambda filepath: None

        # Create an instance of GlobalSevenClassMap
        scGlobalMapInstance = GlobalSevenClassMap(
            hdfDirectory='/path/to/hdf/dir',
            ancFilePath='/path/to/anc/dir/mask',
            postProcessingDir='/path/to/pp/dir',
            year=2023,
            sensor='MYD',
            tr='500m',
            version='000',
            outputDir='/path/to/output/dir',
            logger=logger,
            debug=True
        )

        # Mock the noShorelineProducts list with 318 elements
        noShorelineProducts = [f'file{i}.hdf' for i in range(1, 319)]

        # Call the function under test
        result = scGlobalMapInstance._validateNumberOfNoShorelineProducts(
            noShorelineProducts)

        # Assertions
        self.assertTrue(result)

        noShorelineProducts = [f'file{i}.hdf' for i in range(1, 300)]

        with self.assertRaises(RuntimeError):
            scGlobalMapInstance._validateNumberOfNoShorelineProducts(
                noShorelineProducts
            )

    # -------------------------------------------------------------------------
    # testPostProcessShoreline
    # -------------------------------------------------------------------------
    def testPostProcessShoreline(self):
        # Create some dummy input arrays
        shoreInland = np.array([[1, 0, 1],
                                [1, 1, 1],
                                [1, 0, 0]], dtype=np.uint8)
        shoreShallow = np.array([[0, 1, 1],
                                 [0, 1, 0],
                                 [1, 0, 0]], dtype=np.uint8)
        sevenClass = np.array([[1, 1, 2],
                               [2, 1, 0],
                               [0, 2, 1]], dtype=np.uint8)

        # Call the function under test
        result = GlobalSevenClassMap.postProcessShoreline(shoreInland,
                                                          shoreShallow,
                                                          sevenClass)

        # Expected result
        expectedResult = np.array([[1, 1, 0],
                                   [0, 1, 0],
                                   [0, 0, 0]], dtype=np.uint8)

        # Assertions
        np.testing.assert_array_equal(result, expectedResult)

    # -------------------------------------------------------------------------
    # testAddShorelineToSevenClass
    # -------------------------------------------------------------------------
    def testAddShorelineToSevenClass(self):
        # Create some dummy input arrays
        sevenClass = np.array([[0, 1, 2],
                               [2, 1, 0],
                               [0, 2, 1]], dtype=np.uint8)
        shoreline = np.array([[0, 1, 1],
                              [0, 0, 0],
                              [1, 1, 0]], dtype=np.uint8)

        # Call the function under test
        result = GlobalSevenClassMap.addShorelineToSevenClass(
            sevenClass, shoreline, shoreLineValue=2)

        # Expected result
        expectedResult = np.array([[0, 2, 2],
                                   [2, 1, 0],
                                   [2, 2, 1]], dtype=np.uint8)

        # Assertions
        np.testing.assert_array_equal(result, expectedResult)


if __name__ == '__main__':
    unittest.main()
