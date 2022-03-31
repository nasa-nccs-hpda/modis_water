
import numpy as np

from modis_water.model.BandReader import BandReader as br
from modis_water.model.Classifier import Classifier


# -----------------------------------------------------------------------------
# class SimpleClassifier
# -----------------------------------------------------------------------------
class SimpleClassifier(Classifier):

    CLASSIFIER_NAME = 'Simple'

    # -------------------------------------------------------------------------
    # __init__
    # -------------------------------------------------------------------------
    def __init__(self, year, tile, outDir, modDir, startDay=1, endDay=365,
                 logger=None, sensors=set([br.MOD]), debug=False):

        super(SimpleClassifier, self). \
            __init__(year, tile, outDir, modDir, startDay, endDay, logger,
                     sensors, debug,
                     [br.SOLZ, br.STATE, br.SR1, br.SR2, br.SR3, br.SR4,
                      br.SR5, br.SR6, br.SR7])

    # -------------------------------------------------------------------------
    # getClassifierName
    # -------------------------------------------------------------------------
    def getClassifierName(self):
        return SimpleClassifier.CLASSIFIER_NAME

    # -------------------------------------------------------------------------
    # _runOneSensorOneDay
    # -------------------------------------------------------------------------
    def _runOneSensorOneDay(self, bandDict, outName):

        # Name the arrays as named in water_change.c
        red = bandDict[br.SR1]
        nir = bandDict[br.SR2]
        blue = bandDict[br.SR3]
        green = bandDict[br.SR4]
        swir5 = bandDict[br.SR5]
        swir6 = bandDict[br.SR6]
        swir7 = bandDict[br.SR7]

        # Add NDVI to bandDict.
        ndvi = self.computeNdvi(bandDict[br.SR1], bandDict[br.SR2])

        # ---
        # Define the rules as masks.
        # ---
        subcondition1 = (swir5 >= 453) & (blue < 675) & (nir > 100)
        land1 = (swir5 < 1017) & (swir7 < 773) & subcondition1
        water1 = (swir5 < 1017) & (swir7 < 773) & ~subcondition1

        water2 = (swir5 >= 1017) & (nir < 1777) & (ndvi < 0.0825) & \
                 (blue < 651)

        land2 = (swir5 >= 1017) & (nir < 1777) & (ndvi < 0.0825) & \
            (blue >= 651)

        land3 = (swir5 >= 1017) & (nir < 1777) & (ndvi >= 0.0825) & \
                (ndvi < 0.4125) & (nir >= 1329) & (swir7 < 1950)

        land4 = (swir5 >= 1017) & (nir < 1777) & (ndvi >= 0.0825) & \
                (ndvi >= 0.4125)

        land5 = (swir5 >= 1017) & (nir >= 1777)

        waterConditions = water1 | water2
        landConditions = land1 | land2 | land3 | land4

        # Apply the model.
        predictions = np.full((br.COLS, br.ROWS), Classifier.NO_DATA)
        predictions[waterConditions] = Classifier.WATER  # 3
        predictions[landConditions] = Classifier.LAND    # 1

        return predictions
