
import unittest

import numpy as np

from modis_water.model.BandReader import BandReader
from modis_water.model.MaskGenerator import MaskGenerator


# -----------------------------------------------------------------------------
# class MaskGeneratorTestCase
#
# python -m unittest discover model/tests/
# python -m unittest modis_water.model.tests.test_MaskGenerator
# -----------------------------------------------------------------------------
class MaskGeneratorTestCase(unittest.TestCase):

    bandDict = {BandReader.SR1: np.zeros((2, 2), dtype=np.int16),
                BandReader.SR2: np.zeros((2, 2), dtype=np.int16),
                BandReader.SR3: np.zeros((2, 2), dtype=np.int16),
                BandReader.SR4: np.zeros((2, 2), dtype=np.int16),
                BandReader.SR5: np.zeros((2, 2), dtype=np.int16),
                BandReader.SR6: np.zeros((2, 2), dtype=np.int16),
                BandReader.SR7: np.zeros((2, 2), dtype=np.int16),
                BandReader.SENZ: np.zeros((2, 2), dtype=np.int16),
                BandReader.SOLZ: np.zeros((2, 2), dtype=np.int16),
                BandReader.STATE: np.zeros((2, 2), dtype=np.int16)}

    # -------------------------------------------------------------------------
    # testInit
    # -------------------------------------------------------------------------
    def testInit(self):

        with self.assertRaises(TypeError):
            MaskGenerator()

        with self.assertRaises(RuntimeError):
            MaskGenerator({})

        br = BandReader('/css/modis/Collection6.1/L2G',
                        [BandReader.SENZ, BandReader.SR1],
                        None)

        bandDict = br.read(BandReader.MOD, 2003, 'h09v05', 161)

        with self.assertRaises(RuntimeError):
            MaskGenerator(bandDict)

    # -------------------------------------------------------------------------
    # testQA
    # -------------------------------------------------------------------------
    def testQA(self):

        # Test all good values.
        testArray = np.array([[0, 0], [0, 0]])

        expected = [[MaskGenerator.GOOD_DATA, MaskGenerator.GOOD_DATA],
                    [MaskGenerator.GOOD_DATA, MaskGenerator.GOOD_DATA]]

        self.bandTester(BandReader.STATE, testArray, expected)

        # Test aerosol.
        testArray = np.array([[MaskGenerator.AERO_MASK, 0], [0, 0]])

        expected = [[MaskGenerator.BAD_DATA, MaskGenerator.GOOD_DATA],
                    [MaskGenerator.GOOD_DATA, MaskGenerator.GOOD_DATA]]

        self.bandTester(BandReader.STATE, testArray, expected)

        # Test cloudy.
        testArray = np.array([[0, 0], [0, MaskGenerator.CLOUDY]])

        expected = [[MaskGenerator.GOOD_DATA, MaskGenerator.GOOD_DATA],
                    [MaskGenerator.GOOD_DATA, MaskGenerator.BAD_DATA]]

        self.bandTester(BandReader.STATE, testArray, expected)

        # Test cloud mixed.
        testArray = np.array([[0, 0], [MaskGenerator.CLOUD_MIXED,
                                       MaskGenerator.CLOUD_MIXED]])

        expected = [[MaskGenerator.GOOD_DATA, MaskGenerator.GOOD_DATA],
                    [MaskGenerator.BAD_DATA, MaskGenerator.BAD_DATA]]

        self.bandTester(BandReader.STATE, testArray, expected)

        # Test cloud internal.
        testArray = np.array([[0, MaskGenerator.CLOUD_INT], [0, 0]])

        expected = [[MaskGenerator.GOOD_DATA, MaskGenerator.BAD_DATA],
                    [MaskGenerator.GOOD_DATA, MaskGenerator.GOOD_DATA]]

        self.bandTester(BandReader.STATE, testArray, expected)

    # -------------------------------------------------------------------------
    # bandTester
    # -------------------------------------------------------------------------
    def bandTester(self, bandName, testArray, expectedOutput):

        bd = MaskGeneratorTestCase.bandDict
        bd[bandName] = testArray
        mg = MaskGenerator(bd)
        mask = mg.generateMask()
        bd[bandName] = np.zeros((2, 2), dtype=np.int16)  # reset band
        self.assertTrue(np.array_equal(mask, expectedOutput))

    # -------------------------------------------------------------------------
    # srTester
    # -------------------------------------------------------------------------
    def srTester(self, band):

        # Test -101
        testArray = np.array([[9999, 9999], [-101, 9999]])

        expected = [[MaskGenerator.GOOD_DATA, MaskGenerator.GOOD_DATA],
                    [MaskGenerator.BAD_DATA, MaskGenerator.GOOD_DATA]]

        self.bandTester(band, testArray, expected)

        # Test 16000
        testArray = np.array([[9999, 16001], [9999, 9999]])

        expected = [[MaskGenerator.GOOD_DATA, MaskGenerator.BAD_DATA],
                    [MaskGenerator.GOOD_DATA, MaskGenerator.GOOD_DATA]]

        self.bandTester(band, testArray, expected)

    # -------------------------------------------------------------------------
    # testSRs
    # -------------------------------------------------------------------------
    def testSRs(self):

        self.srTester(BandReader.SR1)
        self.srTester(BandReader.SR2)
        self.srTester(BandReader.SR3)
        self.srTester(BandReader.SR4)
        self.srTester(BandReader.SR5)
        self.srTester(BandReader.SR6)
        self.srTester(BandReader.SR7)
