
import os

import joblib
import numpy as np
import pandas as pd

from modis_water.model.BandReader import BandReader
from modis_water.model.Classifier import Classifier
from modis_water.model.Utils import Utils


# -----------------------------------------------------------------------------
# class RandomForestClassifier
#
# The notebook specified hard-coded input files.  The files are opened as VRTs,
# then read into a dictionary.
# -----------------------------------------------------------------------------
class RandomForestClassifier(Classifier):

    CLASSIFIER_NAME = 'RandomForest'

    # -------------------------------------------------------------------------
    # __init__
    # -------------------------------------------------------------------------
    def __init__(self, year, tile, outDir, modDir, startDay=1, endDay=365,
                 logger=None, sensors=set([BandReader.MOD]), debug=False):

        super(RandomForestClassifier, self). \
            __init__(year, tile, outDir, modDir, startDay, endDay, logger,
                     sensors, debug,
                     [BandReader.SR1, BandReader.SR2, BandReader.SR3,
                      BandReader.SR4, BandReader.SR5, BandReader.SR6,
                      BandReader.SR7])

        # Read the model before we do any real work.
        modelFile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'RandomForestModel.sav')
        self._model = joblib.load(modelFile)

    # -------------------------------------------------------------------------
    # getClassifierName
    # -------------------------------------------------------------------------
    def getClassifierName(self):
        return RandomForestClassifier.CLASSIFIER_NAME

    # -------------------------------------------------------------------------
    # _runOneSensorOneDay
    # -------------------------------------------------------------------------
    def _runOneSensorOneDay(self, bandDict, outName):

        # ---
        # Collapse the 2D bands into one dimension, and combine all bands
        # into a 2D array.
        #
        # This model expects arrays in order from SR1 - SR7.  Just to be safe
        # sort them explicitly.
        # ---
        dims = (BandReader.ROWS * BandReader.COLS, 10)
        img = np.empty(dims, dtype=np.int16)
        img[:, 0] = bandDict[BandReader.SR1].ravel()
        img[:, 1] = bandDict[BandReader.SR2].ravel()
        img[:, 2] = bandDict[BandReader.SR3].ravel()
        img[:, 3] = bandDict[BandReader.SR4].ravel()
        img[:, 4] = bandDict[BandReader.SR5].ravel()
        img[:, 5] = bandDict[BandReader.SR6].ravel()
        img[:, 6] = bandDict[BandReader.SR7].ravel()

        img[:, 7] = self.computeNdvi(bandDict[BandReader.SR1],
                                     bandDict[BandReader.SR2]).ravel()

        # ---
        # Numpy sometimes alters data types when it encounters infinite
        # numbers.  Use np.where to prevent this.
        # ---
        img[:, 8] = \
            np.where(img[:, 1] + img[:, 5] != 0,
                     ((img[:, 1] - img[:, 5]) /
                      (img[:, 1] + img[:, 5]) *
                      10000).astype(np.int16),
                     0)

        img[:, 9] = \
            np.where(img[:, 1] + img[:, 6] != 0,
                     ((img[:, 1] - img[:, 6]) /
                      (img[:, 1] + img[:, 6]) *
                      10000).astype(np.int16),
                     0)

        # Run the model.  Should be {0, 1}.
        df = pd.DataFrame(img)
        predictions = self._model.predict(df)
        matrix = np.asarray(predictions, dtype=np.int16)

        reshp = matrix.reshape((BandReader.ROWS,
                                BandReader.COLS)).astype(np.int16)

        if self._debug:
            self._writeDebugImage(matrix, 'matrix')

        return reshp

    # -------------------------------------------------------------------------
    # _writeDebugImage
    # -------------------------------------------------------------------------
    def _writeDebugImage(self, pixels, name):

        print('Type ' + name + ':', str(pixels.dtype))
        matrix = np.asarray(pixels, dtype=np.int16)

        out = matrix.reshape((BandReader.ROWS,
                              BandReader.COLS)).astype(np.int16)

        Utils.writeRaster(self._outDir, out, name)
