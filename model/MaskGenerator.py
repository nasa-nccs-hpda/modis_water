
import numpy as np

from modis_water.model.BandReader import BandReader as br


# -----------------------------------------------------------------------------
# MaskGenerator
# -----------------------------------------------------------------------------
class MaskGenerator(object):

    AERO_MASK = 192
    CLOUDY = 1
    CLOUD_MIXED = 2
    CLOUD_SHADOW = 4
    CLOUD_INT = 1024

    BAD_DATA = 0
    GOOD_DATA = 1

    REQUIRED_BANDS = set([br.SR1, br.SR2, br.SR3, br.SR4, br.SR5, br.SR6,
                          br.SR7, br.SENZ, br.SOLZ, br.STATE])

    # -------------------------------------------------------------------------
    # __init__
    #
    # This is meant to use bands already read for a classification algorithm.
    # Pass them in, so we need not read them twice.
    # -------------------------------------------------------------------------
    def __init__(self, bandDict):

        if len(bandDict) == 0:
            raise RuntimeError('A dictionary of bands must be provided.')

        missingBands = MaskGenerator.REQUIRED_BANDS - set(bandDict.keys())

        if missingBands:
            raise RuntimeError('These necessary bands were not passed: ' +
                               str(missingBands))

        self._bandDict = bandDict

    # -------------------------------------------------------------------------
    # generateGeneralMask
    # -------------------------------------------------------------------------
    def generateGeneralMask(self, debug=False) -> np.ndarray:

        # Apply the rules.
        mask = np.where(
            ((self._bandDict[br.SR1] < -100) |
             (self._bandDict[br.SR2] < -100) |
             (self._bandDict[br.SOLZ] > 6500) |
             (self._bandDict[br.STATE] & MaskGenerator.AERO_MASK ==
                MaskGenerator.AERO_MASK)),
            MaskGenerator.BAD_DATA,
            MaskGenerator.GOOD_DATA).astype(np.int16)

        if debug:
            self._printGeneralMaskDebugInfo()

        return mask

    # -------------------------------------------------------------------------
    # generateLandMask
    # -------------------------------------------------------------------------
    def generateLandMask(self, debug=False) -> np.ndarray:

        # Apply the rules.
        mask = np.where(
            ((self._bandDict[br.STATE] & MaskGenerator.CLOUDY ==
                MaskGenerator.CLOUDY) |
             (self._bandDict[br.STATE] & MaskGenerator.CLOUD_MIXED ==
                MaskGenerator.CLOUD_MIXED) |
             (self._bandDict[br.STATE] & MaskGenerator.CLOUD_SHADOW ==
                MaskGenerator.CLOUD_SHADOW) |
             (self._bandDict[br.STATE] & MaskGenerator.CLOUD_INT ==
                MaskGenerator.CLOUD_INT)),
            MaskGenerator.BAD_DATA,
            MaskGenerator.GOOD_DATA).astype(np.int16)

        if debug:
            self._printLandMaskDebugInfo()

        return mask

    # -------------------------------------------------------------------------
    # _printGeneralMaskDebugInfo
    # -------------------------------------------------------------------------
    def _printGeneralMaskDebugInfo(self):

        print('SR1 < -100:', (self._bandDict[br.SR1] < -100).any())
        print('SR2 < -100:', (self._bandDict[br.SR1] < -100).any())

        print('Aero:',
              (self._bandDict[br.STATE] & MaskGenerator.AERO_MASK ==
                  MaskGenerator.AERO_MASK).any())

    # -------------------------------------------------------------------------
    # _printLandMaskDebugInfo
    # -------------------------------------------------------------------------
    def _printLandMaskDebugInfo(self):

        print('Cloudy:',
              (self._bandDict[br.STATE] & MaskGenerator.CLOUDY ==
                  MaskGenerator.CLOUDY).any())

        print('Cloud mixed:',
              (self._bandDict[br.STATE] & MaskGenerator.CLOUD_MIXED ==
                  MaskGenerator.CLOUD_MIXED).any())

        print('Cloud shadow:',
              (self._bandDict[br.STATE] & MaskGenerator.CLOUD_SHADOW ==
                  MaskGenerator.CLOUD_SHADOW).any())

        print('Cloud internal:',
              (self._bandDict[br.STATE] & MaskGenerator.CLOUD_INT ==
                  MaskGenerator.CLOUD_INT).any())
