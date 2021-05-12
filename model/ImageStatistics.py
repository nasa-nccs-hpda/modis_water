import glob
import os

from core.model.ImageFile import ImageFile
from modis_water.model.SimpleClassifier import SimpleClassifier

# -----------------------------------------------------------------------------
# class ImageStatistics
# -----------------------------------------------------------------------------
class ImageStatistics(object):
    
    # -------------------------------------------------------------------------
    # run
    # -------------------------------------------------------------------------
    @staticmethod
    def run(imageDir, verbose=False):
        
        globStr = os.path.join(imageDir, 
                               SimpleClassifier.OUT_IMAGE_PREFIX + '*.tif')

        files = glob.glob(globStr)
        print('Found ' + str(len(files)) + ' images.')

        if verbose:
            print('Glob string: ', globStr)
            
        zeroImages = []
        
        for f in files:
            
            image = ImageFile(f)
            
            (minimum, maximum, mean, stdDev) = \
                image._getDataset().GetRasterBand(1).GetStatistics(0, 1)
            
            if verbose:
                
                print(f)
                print('\tMinimum: ', minimum)
                print('\tMaximum: ', maximum)
                print('\tMean:    ', mean)
                print('\tStd Dev: ', stdDev)

            if mean == 0: zeroImages.append(f)
            
        print('Number of all-zero images: ', len(zeroImages))
        print('Not-all-zero images: ', set(files) - set(zeroImages))
        
        if verbose:
            print('All-zero images: ', zeroImages)
