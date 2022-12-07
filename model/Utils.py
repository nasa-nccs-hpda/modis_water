from collections import namedtuple
import datetime
import os

from osgeo import gdal


DayRange = namedtuple('DayRange', 'start end')

# -----------------------------------------------------------------------------
# Class Utils
# -----------------------------------------------------------------------------
class Utils(object):

    INCLUSIONS = {'v00': DayRange(177, 256),
                  'v01': DayRange(161, 256),
                  'v02': DayRange(145, 288),
                  'v03': DayRange(129, 304)}
                  
    EXCLUSIONS = {'v17': DayRange(177, 256),
                  'v16': DayRange(161, 256),
                  'v15': DayRange(145, 288),
                  'v14': DayRange(129, 304)}

    # -------------------------------------------------------------------------
    # getImageName
    # -------------------------------------------------------------------------
    @staticmethod
    def getImageName(year, tile, sensor, classifier, day=None, postFix=None):

        name = str(year) + '-'

        if day:
            name += str(day).zfill(3) + '-'

        name += str(tile) + '-' + \
            str(sensor) + '-' + \
            str(classifier)

        if postFix:
            name += '-' + str(postFix)

        return name

    # -------------------------------------------------------------------------
    # writeRaster
    # -------------------------------------------------------------------------
    @staticmethod
    def writeRaster(outDir, pixels, name, cols=0, rows=0, projection=None,
                    transform=None):

        cols = pixels.shape[0]
        rows = pixels.shape[1] if len(pixels.shape) > 1 else 1
        imageName = os.path.join(outDir, name + '.tif')
        driver = gdal.GetDriverByName('GTiff')

        ds = driver.Create(imageName, cols, rows, 1, gdal.GDT_Int16,
                           options=['COMPRESS=LZW'])
        if projection:
            ds.SetProjection(projection)
        if transform:
            ds.SetGeoTransform(transform)

        ds.WriteRaster(0, 0, cols, rows, pixels.tobytes())

    # -------------------------------------------------------------------------
    # _getPostStr()
    # -------------------------------------------------------------------------
    @staticmethod
    def getPostStr():
        sdtdate = datetime.datetime.now()
        year = sdtdate.year
        hm = sdtdate.strftime('%H%M')
        sdtdate = sdtdate.timetuple()
        jdate = sdtdate.tm_yday
        post_str = '{}{:03}{}'.format(year, jdate, hm)
        return post_str
