
import base64
import zlib


# -----------------------------------------------------------------------------
# class SimpleClassifierEncoder
# -----------------------------------------------------------------------------
class SimpleClassifierEncoder(object):
    
    # -------------------------------------------------------------------------
    # codeToEncode
    # -------------------------------------------------------------------------
    runOneSensorOneDay = ''

        # Mark requested this currently unused variable to be defined.
        red = bandDict[br.SR1]
    
        # Name the arrays as named in water_change.c
        nir = bandDict[br.SR2]
        blue = bandDict[br.SR3]
        swir5 = bandDict[br.SR5]
        swir7 = bandDict[br.SR7]

        # ---
        # Add NDVI to bandDict.
        # NDVI is normally calculated with range -1,1. This multiplies
        # that range by 10,000 making it an integer-friendly range.
        # The NDVI conditions listed in water_change.c are multiplied
        # by 10,000 to match the range of the computed NDVI.
        # ---
        ndvi = self.computeNdvi(bandDict[br.SR1], bandDict[br.SR2])
        ndviBadCalculation = (bandDict[br.SR1] + bandDict[br.SR2]) == 0

        # ---
        # Define the rules as masks.
        # ---
        subcondition1 = (swir5 >= 453) & (blue < 675) & (nir > 1000)
        land1 = (swir5 < 1017) & (swir7 < 773) & subcondition1
        water1 = (swir5 < 1017) & (swir7 < 773) & ~subcondition1

        water2 = (swir5 >= 1017) & (nir < 1777) & (ndvi < 825) & \
                 (blue < 651)

        land2 = (swir5 >= 1017) & (nir < 1777) & (ndvi < 825) & \
            (blue >= 651)

        land3 = (swir5 >= 1017) & (nir < 1777) & (ndvi >= 825) & \
                (ndvi < 4125) & (nir >= 1329) & (swir7 < 1950)

        land4 = (swir5 >= 1017) & (nir < 1777) & (ndvi >= 825) & \
                (ndvi >= 4125)

        land5 = (swir5 >= 1017) & (nir >= 1777)
    
        waterConditions = water1 | water2
        landConditions = land1 | land2 | land3 | land4 | land5

        # Apply the model.
        predictions = np.full((br.COLS, br.ROWS), Classifier.NO_DATA)
        predictions[waterConditions] = Classifier.WATER  # 1
        predictions[landConditions] = Classifier.LAND    # 0
        predictions = np.where(ndviBadCalculation,
                               Classifier.NO_DATA,
                               predictions)

        return predictions

    # -------------------------------------------------------------------------
    # saveModel
    # -------------------------------------------------------------------------
    @staticmethod
    def saveModel() -> None:
        
        def run(code): exec(zlib.decompress(base64.b16decode(code)))
        def enc(code): return base64.b16encode(zlib.compress(code))
        
        