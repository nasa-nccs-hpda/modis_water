import glob
import os

import numpy as np
import numpy.ma as ma

from core.model.ImageFile import ImageFile
from modis_water.model.SimpleClassifier import SimpleClassifier

# -----------------------------------------------------------------------------
# Class SimpleClassifierValidator
#
# /att/nobackup/mcarrol2/MODIS_water/Dynamic_Water/Terra/2019
# -----------------------------------------------------------------------------
class SimpleClassifierValidator(object):
    
    # -------------------------------------------------------------------------
    # __init__
    # -------------------------------------------------------------------------
    def __init__(self, imageDir, imagePrefix):

        if not imageDir:
            
            raise RuntimeError('An image directory must be provided.')
            
        if not os.path.exists(imageDir):
            
            raise RuntimeError('Image directory, ' + 
                               str(imageDir) +
                               ', does not exist.')

        if not os.path.isdir(imageDir):
            
            raise RuntimeError('Image directory, ' +
                               str(imageDir) +
                               ', must be a directory.')
               
        pattern = imagePrefix + '*.tif'
        self._imageNames = glob.glob(os.path.join(imageDir, pattern))
        self._imageDir = imageDir
        
    # -------------------------------------------------------------------------
    # runLand
    # -------------------------------------------------------------------------
    def runLand(self, image):

        self._validateInputImage(image)
        outFile = '/att/nobackup/rlgill/SystemTesting/modis-water/sumsLand.bin'
        return self._validate(SimpleClassifier.OUT_LAND_VAL, image, outFile)
        
    # -------------------------------------------------------------------------
    # runWater
    # -------------------------------------------------------------------------
    def runWater(self, image):

        self._validateInputImage(image)
        
        outFile = '/att/nobackup/rlgill/SystemTesting/modis-water/' + \
                  'sumsWater.bin'

        return self._validate(SimpleClassifier.OUT_WATER_VAL, image, outFile)
        
    # -------------------------------------------------------------------------
    # _validate
    # -------------------------------------------------------------------------
    def _validate(self, classificationVal, image, outFile):

        size = 4800  # This is useful for debugging.
        
        # Add the water viues from all the images.
        total = np.zeros((size, size))
        
        for imageName in self._imageNames:
            
            gif = ImageFile(imageName)
            npPixels = gif._getDataset().ReadAsArray(0, 0, size, size)
            total += npPixels == classificationVal
        
        total.astype(np.ubyte).tofile(outFile)
            
        vi = np.fromfile(image, dtype=np.ubyte).reshape((4800, 4800))
        
        if (total != vi).any():
            
            self._stats(vi, total, size)
            return False
            
        else:
            return True
         
    # -------------------------------------------------------------------------
    # _stats
    # -------------------------------------------------------------------------
    def _stats(self, vi, total, size):
        
        print('vi =', vi)
        print('total =', total)

        viNumNonzeroes = np.sum(vi != 0)
        sumNumNonzeroes = np.sum(total != 0)
        viNumZeroes = np.sum(vi == 0)
        sumNumZeroes = np.sum(total == 0)
        numPixels = size * size

        if viNumNonzeroes + viNumZeroes != numPixels:
            
            raise RuntimeError('Validation image: ' + 
                               'The number of non-zeroes + zeroes ' +
                               '!= image size: ' +
                               str(viNumNonZeroes + viNumZeroes) + 
                               ' != ' + \
                               str(numPixels))

        if sumNumNonzeroes + sumNumZeroes != numPixels:
            
            raise RuntimeError('Summation array: ' + 
                               'The number of non-zeroes + zeroes ' +
                               '!= image size: ' +
                               str(sumNumNonZeroes + sumNumZeroes) + 
                               ' != ' + \
                               str(numPixels))
        
        numMatches = np.sum(total == vi)
        numNonzeroMatches = np.sum((total != 0) & (total == vi))
        numZeroMatches = np.sum((total == 0) & (total == vi))

        print('Matches: ', numMatches)
        print('Non-zero matches: ', numNonzeroMatches)
        print('Zero matches: ', numZeroMatches)
        print('Non-zero values: ', sumNumNonzeroes)
        print('Non-zero values in validation image: ', viNumNonzeroes)
        
    # -------------------------------------------------------------------------
    # _validateInputImage
    # -------------------------------------------------------------------------
    def _validateInputImage(self, image):
        
         if not image:
     
             raise RuntimeError('A validation image must be provided.')
     
         if not os.path.exists(image):
     
             raise RuntimeError('Validation image, ' + 
                                str(image) +
                                ', does not exist.')
        